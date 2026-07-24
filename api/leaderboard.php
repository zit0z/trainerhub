<?php
require_once 'auth-lib.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$pdo = getDB();
$type = $_GET['type'] ?? 'activations';
$period = $_GET['period'] ?? '7d';
$days = (int)preg_replace('/[^0-9]/', '', $period);
if ($days < 1 || $days > 365) $days = 7;
$start = strtotime("-$days days");

if ($type === 'activations') {
    $stmt = $pdo->prepare("
        SELECT u.id, u.username, u.email, COUNT(*) as score
        FROM trainer_logs l
        JOIN users u ON u.id = l.user_id
        WHERE l.created_at >= ?
        GROUP BY u.id
        ORDER BY score DESC
        LIMIT 50
    ");
} elseif ($type === 'challenges') {
    $stmt = $pdo->prepare("
        SELECT u.id, u.username, u.email, COUNT(*) as score
        FROM user_challenges uc
        JOIN users u ON u.id = uc.user_id
        WHERE uc.completed = 1 AND uc.completed_at >= ?
        GROUP BY u.id
        ORDER BY score DESC
        LIMIT 50
    ");
} else {
    $stmt = $pdo->prepare("
        SELECT u.id, u.username, u.email, u.reputation as score
        FROM users u
        ORDER BY u.reputation DESC
        LIMIT 50
    ");
}
$stmt->execute([$start]);
$rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
foreach ($rows as $i => &$r) {
    $r['rank'] = $i + 1;
    $r['display'] = $r['username'] ?: preg_replace('/@.*/', '', $r['email']);
}
jsonResponse(['success' => true, 'type' => $type, 'leaderboard' => $rows]);
