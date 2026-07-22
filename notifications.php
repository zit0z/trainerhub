<?php
require_once 'auth-lib.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$auth = checkAuth();
if (isset($auth['error'])) jsonResponse(['success' => false, 'error' => $auth['error']], $auth['code']);
$user = $auth['user'];
$action = $_GET['action'] ?? 'list';
$pdo = getDB();

if ($action === 'list') {
    $stmt = $pdo->prepare("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 50");
    $stmt->execute([$user['id']]);
    $notes = $stmt->fetchAll(PDO::FETCH_ASSOC);
    $unread = count(array_filter($notes, function($n) { return empty($n['read']); }));
    jsonResponse(['success' => true, 'notifications' => $notes, 'unread' => $unread]);
}

if ($action === 'mark_read') {
    $id = (int)($_GET['id'] ?? 0);
    if ($id) {
        $pdo->prepare("UPDATE notifications SET read = 1 WHERE id = ? AND user_id = ?")->execute([$id, $user['id']]);
    }
    jsonResponse(['success' => true]);
}

if ($action === 'mark_all_read') {
    $pdo->prepare("UPDATE notifications SET read = 1 WHERE user_id = ?")->execute([$user['id']]);
    jsonResponse(['success' => true]);
}

jsonResponse(['success' => false, 'error' => 'Invalid action'], 400);
