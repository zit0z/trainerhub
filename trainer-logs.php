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
$action = $_GET['action'] ?? 'list';

if ($action === 'list') {
    $limit = min((int)($_GET['limit'] ?? 50), 200);
    $stmt = $pdo->prepare("SELECT l.*, t.name as trainer_name, g.name as game_name FROM trainer_logs l LEFT JOIN trainers t ON t.id=l.trainer_id LEFT JOIN games g ON g.id=t.game_id WHERE l.user_id = ? ORDER BY l.created_at DESC LIMIT ?");
    $stmt->execute([$user['id'], $limit]);
    $logs = $stmt->fetchAll(PDO::FETCH_ASSOC);
    jsonResponse(['success' => true, 'logs' => $logs]);
}

if ($action === 'stats') {
    $stmt = $pdo->prepare("SELECT COUNT(*) as total_activations FROM trainer_logs WHERE user_id = ?");
    $stmt->execute([$user['id']]);
    $total = $stmt->fetchColumn();
    $stmt = $pdo->prepare("SELECT COUNT(*) FROM trainer_logs WHERE user_id = ? AND success = 1");
    $stmt->execute([$user['id']]);
    $successful = $stmt->fetchColumn();
    $stmt = $pdo->prepare("SELECT COUNT(*) FROM trainer_logs WHERE user_id = ? AND success = 0");
    $stmt->execute([$user['id']]);
    $failed = $stmt->fetchColumn();

    $success_rate = $total > 0 ? round(($successful / $total) * 100) : 0;

    // Last 14 days chart data
    $chart_data = [];
    for ($i = 13; $i >= 0; $i--) {
        $date = date('Y-m-d', strtotime("-$i days"));
        $start = strtotime($date);
        $end = $start + 86400;
        $stmt = $pdo->prepare("SELECT COUNT(*) FROM trainer_logs WHERE user_id = ? AND created_at >= ? AND created_at < ?");
        $stmt->execute([$user['id'], $start, $end]);
        $chart_data[] = ['date' => date('d.m', $start), 'count' => (int)$stmt->fetchColumn()];
    }

    // Recent logs
    $stmt = $pdo->prepare("SELECT l.*, t.name as trainer_name, g.name as game_name FROM trainer_logs l LEFT JOIN trainers t ON t.id=l.trainer_id LEFT JOIN games g ON g.id=t.game_id WHERE l.user_id = ? ORDER BY l.created_at DESC LIMIT 10");
    $stmt->execute([$user['id']]);
    $recent = $stmt->fetchAll(PDO::FETCH_ASSOC);

    jsonResponse([
        'success' => true,
        'total_activations' => (int)$total,
        'successful' => (int)$successful,
        'failed' => (int)$failed,
        'success_rate' => $success_rate,
        'chart_data' => $chart_data,
        'recent' => $recent
    ]);
}

if ($action === 'add') {
    $data = json_decode(file_get_contents('php://input'), true);
    $trainer_id = (int)($data['trainer_id'] ?? 0);
    $game_slug = $data['game_slug'] ?? '';
    $action_name = preg_replace('/[^a-z0-9_]/', '', $data['action'] ?? 'activate');
    $success = isset($data['success']) ? (int)$data['success'] : 1;
    $stmt = $pdo->prepare("INSERT INTO trainer_logs (user_id, trainer_id, action, success, ip, created_at) VALUES (?, ?, ?, ?, ?, strftime('%s','now'))");
    $stmt->execute([$user['id'], $trainer_id, $action_name, $success, $_SERVER['REMOTE_ADDR'] ?? '']);
    jsonResponse(['success' => true, 'message' => 'Log added']);
}

jsonResponse(['success' => false, 'error' => 'Invalid action'], 400);
