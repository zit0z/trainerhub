<?php
require_once 'auth-lib.php';
require_once 'mailer.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$pdo = getDB();
$action = $_GET['action'] ?? '';

if ($action === 'request') {
    $data = json_decode(file_get_contents('php://input'), true);
    $email = strtolower(trim($data['email'] ?? ''));
    if (!$email) {
        jsonResponse(['success' => false, 'error' => 'E-Mail erforderlich'], 400);
    }
    $stmt = $pdo->prepare("SELECT id, email FROM users WHERE email = ? LIMIT 1");
    $stmt->execute([$email]);
    $user = $stmt->fetch(PDO::FETCH_ASSOC);
    if (!$user) {
        // Don't leak whether email exists
        jsonResponse(['success' => true, 'message' => 'Falls ein Account existiert, wurde eine E-Mail gesendet.']);
    }
    $token = bin2hex(random_bytes(24));
    $expires = time() + 3600;
    $stmt = $pdo->prepare("UPDATE users SET reset_token = ?, reset_expires_at = ? WHERE id = ?");
    $stmt->execute([$token, $expires, $user['id']]);
    $html = getEmailTemplate('reset', ['token' => $token]);
    sendMail($user['email'], 'Passwort zurücksetzen — SweetCheat', $html, 'reset');
    jsonResponse(['success' => true, 'message' => 'Falls ein Account existiert, wurde eine E-Mail gesendet.']);
}

if ($action === 'reset') {
    $data = json_decode(file_get_contents('php://input'), true);
    $token = $data['token'] ?? '';
    $password = $data['password'] ?? '';
    if (!$token || !$password || strlen($password) < 6) {
        jsonResponse(['success' => false, 'error' => 'Token und Passwort (min. 6 Zeichen) erforderlich'], 400);
    }
    $stmt = $pdo->prepare("SELECT id FROM users WHERE reset_token = ? AND reset_expires_at > ? LIMIT 1");
    $stmt->execute([$token, time()]);
    $user = $stmt->fetch(PDO::FETCH_ASSOC);
    if (!$user) {
        jsonResponse(['success' => false, 'error' => 'Ungültiger oder abgelaufener Token'], 400);
    }
    $hash = password_hash($password, PASSWORD_DEFAULT);
    $stmt = $pdo->prepare("UPDATE users SET password_hash = ?, reset_token = NULL, reset_expires_at = NULL WHERE id = ?");
    $stmt->execute([$hash, $user['id']]);
    logAudit($user['id'], 'password_reset', 'reset-password.php', []);
    jsonResponse(['success' => true, 'message' => 'Passwort erfolgreich zurückgesetzt. Du kannst dich jetzt einloggen.']);
}

jsonResponse(['success' => false, 'error' => 'Ungültige Aktion'], 400);
