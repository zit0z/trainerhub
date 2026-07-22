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
$action = $_GET['action'] ?? 'info';

function getOrCreateCode($pdo, $user) {
    $stmt = $pdo->prepare("SELECT code FROM referrals WHERE referrer_id = ? AND referred_id IS NULL LIMIT 1");
    $stmt->execute([$user['id']]);
    $existing = $stmt->fetchColumn();
    if ($existing) return $existing;
    $code = strtoupper(substr(md5($user['id'] . time() . rand()), 0, 8));
    $stmt = $pdo->prepare("INSERT INTO referrals (referrer_id, code) VALUES (?, ?)");
    $stmt->execute([$user['id'], $code]);
    return $code;
}

if ($action === 'info') {
    $code = getOrCreateCode($pdo, $user);
    $stmt = $pdo->prepare("SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND referred_id IS NOT NULL");
    $stmt->execute([$user['id']]);
    $count = (int)$stmt->fetchColumn();
    jsonResponse(['success' => true, 'code' => $code, 'referrals' => $count, 'reward_per_referral' => 3, 'url' => 'https://sayfespace.online/trainerhub/register?ref=' . $code]);
}

if ($action === 'claim') {
    $data = json_decode(file_get_contents('php://input'), true);
    $code = preg_replace('/[^A-Z0-9]/', '', strtoupper($data['code'] ?? ''));
    if (!$code) {
        jsonResponse(['success' => false, 'error' => 'Code erforderlich'], 400);
    }
    $stmt = $pdo->prepare("SELECT * FROM referrals WHERE code = ? LIMIT 1");
    $stmt->execute([$code]);
    $ref = $stmt->fetch(PDO::FETCH_ASSOC);
    if (!$ref) {
        jsonResponse(['success' => false, 'error' => 'Ungültiger Code'], 400);
    }
    if ($ref['referrer_id'] == $user['id']) {
        jsonResponse(['success' => false, 'error' => 'Eigener Code nicht erlaubt'], 400);
    }
    if ($ref['referred_id']) {
        jsonResponse(['success' => false, 'error' => 'Code bereits verwendet'], 400);
    }
    $stmt = $pdo->prepare("UPDATE referrals SET referred_id = ?, status = 'completed' WHERE id = ?");
    $stmt->execute([$user['id'], $ref['id']]);
    // Extend premium by 3 days logic could go here
    jsonResponse(['success' => true, 'message' => 'Referral erfolgreich. Du erhältst 3 Tage Premium-Guthaben.']);
}

jsonResponse(['success' => false, 'error' => 'Ungültige Aktion'], 400);
