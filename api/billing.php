<?php
require_once 'auth-lib.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$auth = checkAuth();
if (isset($auth['error'])) {
    jsonResponse(['success' => false, 'error' => $auth['error']], $auth['code']);
}
$user = $auth['user'];

$action = $_GET['action'] ?? '';
$pdo = getDB();

if ($action === 'status') {
    jsonResponse([
        'success' => true,
        'subscription' => isPremium($user) ? 'premium' : 'free',
        'expires_at' => $user['subscription_expires_at'],
        'email' => $user['email'] ?? null,
        'username' => $user['username'] ?? null,
        'message' => 'SweetCheat ist aktuell in Beta. Premium-Funktionen werden später verfügbar sein.'
    ]);
}

if ($action === 'upgrade_request') {
    // Users can request premium. Admin must approve via admin panel.
    $stmt = $pdo->prepare("INSERT OR IGNORE INTO subscriptions (user_id, provider, status, plan, amount, currency, starts_at, ends_at) VALUES (?, 'internal', 'pending', 'premium', 0, 'EUR', strftime('%s','now'), strftime('%s','now'))");
    $stmt->execute([$user['id']]);
    jsonResponse(['success' => true, 'message' => 'Premium-Anfrage eingereicht. Du erhältst eine Nachricht, sobald sie genehmigt wurde.']);
}

jsonResponse(['success' => false, 'error' => 'Invalid action'], 400);
?>
