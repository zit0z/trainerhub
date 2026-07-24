<?php
require_once 'auth-lib.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$action = $_GET['action'] ?? 'list';
$pdo = getDB();

if ($action === 'list') {
    $stmt = $pdo->query("
        SELECT c.*,
               (SELECT COUNT(*) FROM user_challenges WHERE challenge_id = c.id AND completed = 1) as completions
        FROM challenges c
        WHERE c.active = 1 AND (c.ends_at IS NULL OR c.ends_at > strftime('%s','now'))
        ORDER BY c.created_at DESC
    ");
    jsonResponse(['success' => true, 'challenges' => $stmt->fetchAll(PDO::FETCH_ASSOC)]);
}

$auth = checkAuth();
if (isset($auth['error'])) jsonResponse(['success' => false, 'error' => $auth['error']], $auth['code']);
$user = $auth['user'];
requireVerified($user);

if ($action === 'my') {
    $stmt = $pdo->prepare("
        SELECT c.*, uc.progress, uc.completed, uc.completed_at
        FROM challenges c
        LEFT JOIN user_challenges uc ON uc.challenge_id = c.id AND uc.user_id = ?
        WHERE c.active = 1
        ORDER BY c.created_at DESC
    ");
    $stmt->execute([$user['id']]);
    jsonResponse(['success' => true, 'challenges' => $stmt->fetchAll(PDO::FETCH_ASSOC)]);
}

jsonResponse(['success' => false, 'error' => 'Invalid action'], 400);
