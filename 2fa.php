<?php
require_once 'auth-lib.php';
require_once 'mailer.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$action = $_GET['action'] ?? 'status';
$auth = checkAuth();
if (isset($auth['error'])) jsonResponse(['success' => false, 'error' => $auth['error']], $auth['code']);
$user = $auth['user'];
$pdo = getDB();

if ($action === 'status') {
    jsonResponse([
        'success' => true,
        'enabled' => (bool)$user['totp_enabled'],
        'method' => 'email'
    ]);
}

if ($action === 'enable') {
    // Generate 6-digit code and email it
    $code = str_pad(random_int(0, 999999), 6, '0', STR_PAD_LEFT);
    $expires = time() + 600;
    $pdo->prepare("UPDATE users SET totp_secret = ? WHERE id = ?")->execute([json_encode(['code' => $code, 'expires' => $expires]), $user['id']]);
    $html = getEmailTemplate('verify', ['token' => $code]);
    sendMail($user['email'], 'SweetCheat 2FA-Code', str_replace('E-Mail-Adresse bestätigen', '2FA-Code', $html), '2fa');
    jsonResponse(['success' => true, 'message' => 'Code per E-Mail gesendet']);
}

if ($action === 'verify') {
    $data = json_decode(file_get_contents('php://input'), true);
    $code = $data['code'] ?? '';
    $secret = json_decode($user['totp_secret'] ?? '{}', true);
    if (($secret['code'] ?? '') !== $code || ($secret['expires'] ?? 0) < time()) {
        jsonResponse(['success' => false, 'error' => 'Code ungültig oder abgelaufen'], 403);
    }
    $pdo->prepare("UPDATE users SET totp_enabled = 1, totp_secret = NULL WHERE id = ?")->execute([$user['id']]);
    jsonResponse(['success' => true, 'message' => '2FA aktiviert']);
}

if ($action === 'disable') {
    $pdo->prepare("UPDATE users SET totp_enabled = 0, totp_secret = NULL WHERE id = ?")->execute([$user['id']]);
    jsonResponse(['success' => true, 'message' => '2FA deaktiviert']);
}

jsonResponse(['success' => false, 'error' => 'Ungültige Aktion'], 400);
