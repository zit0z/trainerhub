<?php
require_once 'auth-lib.php';
require_once 'mailer.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$pdo = getDB();

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Request new verification email
    $auth = checkAuth();
    if (isset($auth['error'])) {
        jsonResponse(['success' => false, 'error' => $auth['error']], $auth['code']);
    }
    $user = $auth['user'];
    if ($user['email_verified']) {
        jsonResponse(['success' => true, 'message' => 'E-Mail bereits bestätigt']);
    }
    $token = bin2hex(random_bytes(24));
    $stmt = $pdo->prepare("UPDATE users SET verification_token = ? WHERE id = ?");
    $stmt->execute([$token, $user['id']]);
    $html = getEmailTemplate('verify', ['token' => $token]);
    sendMail($user['email'], 'Bitte bestätige deine E-Mail-Adresse', $html, 'verify');
    jsonResponse(['success' => true, 'message' => 'Bestätigungs-E-Mail wurde gesendet']);
}

// GET verify with token
$token = $_GET['token'] ?? '';
if (!$token) {
    jsonResponse(['success' => false, 'error' => 'Token erforderlich'], 400);
}
$stmt = $pdo->prepare("SELECT * FROM users WHERE verification_token = ? LIMIT 1");
$stmt->execute([$token]);
$user = $stmt->fetch(PDO::FETCH_ASSOC);
if (!$user) {
    jsonResponse(['success' => false, 'error' => 'Ungültiger oder abgelaufener Token'], 400);
}
$stmt = $pdo->prepare("UPDATE users SET email_verified = 1, verification_token = NULL WHERE id = ?");
$stmt->execute([$user['id']]);
logAudit($user['id'], 'email_verified', 'verify-email.php', []);

// Send welcome email
$html = getEmailTemplate('welcome', []);
sendMail($user['email'], 'Willkommen bei SweetCheat!', $html, 'welcome');

jsonResponse(['success' => true, 'message' => 'E-Mail erfolgreich bestätigt. Willkommen!']);
