<?php
require_once 'auth-lib.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$auth = checkAuth();
if (isset($auth['error'])) {
    jsonResponse(['success' => false, 'error' => $auth['error']], $auth['code']);
}
$user = $auth['user'];
$pdo = getDB();
$action = $_GET['action'] ?? 'get';

if ($action === 'get') {
    jsonResponse([
        'success' => true,
        'user' => [
            'id' => $user['id'],
            'email' => $user['email'],
            'username' => $user['username'],
            'theme' => $user['theme'] ?? 'dark',
            'email_verified' => (bool)$user['email_verified'],
            'subscription' => isPremium($user) ? 'premium' : 'free'
        ]
    ]);
}

if ($action === 'update_profile') {
    $data = json_decode(file_get_contents('php://input'), true);
    $username = trim($data['username'] ?? '');
    $theme = in_array($data['theme'] ?? '', ['dark','light']) ? $data['theme'] : 'dark';
    $stmt = $pdo->prepare("UPDATE users SET username = ?, theme = ? WHERE id = ?");
    $stmt->execute([$username, $theme, $user['id']]);
    jsonResponse(['success' => true, 'message' => 'Profil aktualisiert']);
}

if ($action === 'change_email') {
    $data = json_decode(file_get_contents('php://input'), true);
    $email = sanitizeEmail($data['email'] ?? '');
    $password = $data['password'] ?? '';
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        jsonResponse(['success' => false, 'error' => 'Ungültige E-Mail'], 400);
    }
    if (!password_verify($password, $user['password_hash'])) {
        jsonResponse(['success' => false, 'error' => 'Falsches Passwort'], 403);
    }
    $token = bin2hex(random_bytes(24));
    $stmt = $pdo->prepare("UPDATE users SET email = ?, email_verified = 0, verification_token = ? WHERE id = ?");
    $stmt->execute([$email, $token, $user['id']]);
    // Send verification email
    require_once 'mailer.php';
    $html = getEmailTemplate('verify', ['token' => $token]);
    sendMail($email, 'E-Mail-Adresse bestätigen — SweetCheat', $html, 'verify');
    jsonResponse(['success' => true, 'message' => 'E-Mail geändert. Bitte bestätige die neue Adresse.']);
}

if ($action === 'change_password') {
    $data = json_decode(file_get_contents('php://input'), true);
    $current = $data['current_password'] ?? '';
    $new = $data['new_password'] ?? '';
    if (!password_verify($current, $user['password_hash'])) {
        jsonResponse(['success' => false, 'error' => 'Aktuelles Passwort falsch'], 403);
    }
    $err = validatePasswordStrength($new);
    if ($err) {
        jsonResponse(['success' => false, 'error' => $err], 400);
    }
    $hash = password_hash($new, PASSWORD_DEFAULT);
    $pdo->prepare("UPDATE users SET password_hash = ? WHERE id = ?")->execute([$hash, $user['id']]);
    logAudit($user['id'], 'password_change', 'user-settings.php', []);
    jsonResponse(['success' => true, 'message' => 'Passwort geändert']);
}

if ($action === 'rotate_key') {
    $newKey = rotateApiKey($user['id']);
    logAudit($user['id'], 'api_key_rotate', 'user-settings.php', []);
    jsonResponse(['success' => true, 'api_key' => $newKey]);
}

jsonResponse(['success' => false, 'error' => 'Ungültige Aktion'], 400);
