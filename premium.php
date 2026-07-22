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
$action = $_GET['action'] ?? 'status';

if ($action === 'status') {
    jsonResponse([
        'success' => true,
        'subscription' => isPremium($user) ? 'premium' : 'free',
        'features' => getPremiumFeatures($user),
        'upgrade_url' => 'https://sayfespace.online/sweetcheat/admin/' // manual admin upgrade
    ]);
}

if ($action === 'upgrade_request') {
    $pdo = getDB();
    $stmt = $pdo->prepare("INSERT INTO subscriptions (user_id, provider, status, plan, created_at) VALUES (?, 'manual', 'pending', 'premium', strftime('%s','now'))");
    $stmt->execute([$user['id']]);
    jsonResponse(['success' => true, 'message' => 'Upgrade-Anfrage gesendet. Admin wird benachrichtigt.']);
}

if ($action === 'leaderboard') {
    $pdo = getDB();
    $stmt = $pdo->prepare("
        SELECT u.id, u.email, COALESCE(ur.reputation,0) as reputation, COALESCE(ur.approved_patterns,0) as approved_patterns, COALESCE(ur.total_votes,0) as total_votes
        FROM users u LEFT JOIN user_reputation ur ON u.id = ur.user_id
        ORDER BY reputation DESC LIMIT 50
    ");
    $stmt->execute();
    jsonResponse(['success' => true, 'leaderboard' => $stmt->fetchAll(PDO::FETCH_ASSOC)]);
}

jsonResponse(['success' => false, 'error' => 'Invalid action'], 400);
