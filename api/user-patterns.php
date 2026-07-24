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
    $stmt = $pdo->prepare("SELECT up.*, g.name as game_name, t.name as trainer_name FROM user_patterns up LEFT JOIN games g ON g.id=up.game_id LEFT JOIN trainers t ON t.id=up.trainer_id WHERE up.user_id = ? ORDER BY up.created_at DESC");
    $stmt->execute([$user['id']]);
    jsonResponse(['success' => true, 'patterns' => $stmt->fetchAll(PDO::FETCH_ASSOC)]);
}

if ($action === 'add') {
    $data = json_decode(file_get_contents('php://input'), true);
    $stmt = $pdo->prepare("INSERT INTO user_patterns (user_id, game_id, trainer_id, name, game_version, pattern, offset, value_type, value) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)");
    $stmt->execute([
        $user['id'],
        $data['game_id'] ?? null,
        $data['trainer_id'] ?? null,
        $data['name'] ?? 'Mein Pattern',
        $data['game_version'] ?? '*',
        $data['pattern'] ?? '',
        $data['offset'] ?? 0,
        $data['value_type'] ?? 'int32',
        $data['value'] ?? null
    ]);
    jsonResponse(['success' => true, 'pattern_id' => $pdo->lastInsertId()]);
}

if ($action === 'delete') {
    $data = json_decode(file_get_contents('php://input'), true);
    $stmt = $pdo->prepare("DELETE FROM user_patterns WHERE id = ? AND user_id = ?");
    $stmt->execute([$data['pattern_id'] ?? 0, $user['id']]);
    jsonResponse(['success' => true, 'deleted' => $stmt->rowCount()]);
}

jsonResponse(['success' => false, 'error' => 'Invalid action'], 400);
