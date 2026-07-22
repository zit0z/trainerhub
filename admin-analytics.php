<?php
require_once 'auth-lib.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$auth = checkAuth();
if (isset($auth['error'])) {
    jsonResponse(['success' => false, 'error' => $auth['error']], $auth['code']);
}
$user = $auth['user'];
if (empty($user['is_admin'])) {
    jsonResponse(['success' => false, 'error' => 'Admin required'], 403);
}

$pdo = getDB();
$period = $_GET['period'] ?? '7d';
$days = (int) preg_replace('/[^0-9]/', '', $period);
if ($days < 1 || $days > 365) $days = 7;
$start = strtotime("-$days days");

// User stats
$stmt = $pdo->prepare("SELECT COUNT(*) FROM users WHERE created_at >= ?");
$stmt->execute([$start]);
$new_users = (int)$stmt->fetchColumn();

$stmt = $pdo->prepare("SELECT COUNT(*) FROM users");
$stmt->execute();
$total_users = (int)$stmt->fetchColumn();

$stmt = $pdo->prepare("SELECT COUNT(*) FROM users WHERE is_premium = 1");
$stmt->execute();
$premium_users = (int)$stmt->fetchColumn();

// Activations
$stmt = $pdo->prepare("SELECT COUNT(*) FROM trainer_logs WHERE created_at >= ?");
$stmt->execute([$start]);
$activations = (int)$stmt->fetchColumn();

// Favorites
$stmt = $pdo->prepare("SELECT COUNT(*) FROM user_favorites WHERE created_at >= ?");
$stmt->execute([$start]);
$favorites = (int)$stmt->fetchColumn();

// Daily chart
$chart = [];
for ($i = $days - 1; $i >= 0; $i--) {
    $date = date('Y-m-d', strtotime("-$i days"));
    $day_start = strtotime($date);
    $day_end = $day_start + 86400;
    $stmt = $pdo->prepare("SELECT COUNT(*) FROM users WHERE created_at >= ? AND created_at < ?");
    $stmt->execute([$day_start, $day_end]);
    $u = (int)$stmt->fetchColumn();
    $stmt = $pdo->prepare("SELECT COUNT(*) FROM trainer_logs WHERE created_at >= ? AND created_at < ?");
    $stmt->execute([$day_start, $day_end]);
    $a = (int)$stmt->fetchColumn();
    $chart[] = ['date' => date('d.m', $day_start), 'users' => $u, 'activations' => $a];
}

// Top games by activations
$stmt = $pdo->prepare("
    SELECT g.name, COUNT(*) as count
    FROM trainer_logs l
    JOIN trainers t ON t.id = l.trainer_id
    JOIN games g ON g.id = t.game_id
    WHERE l.created_at >= ?
    GROUP BY g.id
    ORDER BY count DESC
    LIMIT 10
");
$stmt->execute([$start]);
$top_games = $stmt->fetchAll(PDO::FETCH_ASSOC);

jsonResponse([
    'success' => true,
    'new_users' => $new_users,
    'total_users' => $total_users,
    'premium_users' => $premium_users,
    'activations' => $activations,
    'favorites' => $favorites,
    'chart' => $chart,
    'top_games' => $top_games
]);
