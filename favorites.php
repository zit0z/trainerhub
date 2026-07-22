<?php
require_once 'auth-lib.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$auth = checkAuth();
if (isset($auth['error'])) {
    jsonResponse(['success' => false, 'error' => $auth['error']], $auth['code']);
}
$user = $auth['user'];
$pdo = getDB();
$method = $_SERVER['REQUEST_METHOD'];

function fetchFavorites($pdo, $userId) {
    $stmt = $pdo->prepare("
        SELECT f.*,
               g.id as game_id, g.name as game_name, g.slug as game_slug, g.cover_url as game_icon,
               t.id as trainer_id, t.name as trainer_name, t.description as trainer_description
        FROM user_favorites f
        LEFT JOIN games g ON g.id = f.game_id
        LEFT JOIN trainers t ON t.id = f.trainer_id
        WHERE f.user_id = ?
        ORDER BY f.created_at DESC
    ");
    $stmt->execute([$userId]);
    return $stmt->fetchAll(PDO::FETCH_ASSOC);
}

if ($method === 'GET') {
    $favorites = fetchFavorites($pdo, $user['id']);
    jsonResponse(['success' => true, 'favorites' => $favorites, 'count' => count($favorites)]);
}

if ($method === 'POST') {
    $data = json_decode(file_get_contents('php://input'), true);
    $gameId = isset($data['game_id']) ? (int)$data['game_id'] : null;
    $trainerId = isset($data['trainer_id']) ? (int)$data['trainer_id'] : null;
    if ($gameId === 0) $gameId = null;
    if ($trainerId === 0) $trainerId = null;

    if (!$gameId && !$trainerId) {
        jsonResponse(['success' => false, 'error' => 'game_id or trainer_id required'], 400);
    }

    try {
        $stmt = $pdo->prepare("INSERT OR IGNORE INTO user_favorites (user_id, game_id, trainer_id) VALUES (?, ?, ?)");
        $stmt->execute([$user['id'], $gameId, $trainerId]);
        $favorites = fetchFavorites($pdo, $user['id']);
        jsonResponse(['success' => true, 'favorites' => $favorites, 'count' => count($favorites)]);
    } catch (Exception $e) {
        jsonResponse(['success' => false, 'error' => 'Database error: ' . $e->getMessage()], 500);
    }
}

if ($method === 'DELETE') {
    $data = json_decode(file_get_contents('php://input'), true);
    $gameId = isset($data['game_id']) ? (int)$data['game_id'] : null;
    $trainerId = isset($data['trainer_id']) ? (int)$data['trainer_id'] : null;
    if ($gameId === 0) $gameId = null;
    if ($trainerId === 0) $trainerId = null;

    if (!$gameId && !$trainerId) {
        jsonResponse(['success' => false, 'error' => 'game_id or trainer_id required'], 400);
    }

    $sql = "DELETE FROM user_favorites WHERE user_id = ?";
    $params = [$user['id']];
    if ($gameId) {
        $sql .= " AND game_id = ?";
        $params[] = $gameId;
    } else {
        $sql .= " AND game_id IS NULL";
    }
    if ($trainerId) {
        $sql .= " AND trainer_id = ?";
        $params[] = $trainerId;
    }
    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    $favorites = fetchFavorites($pdo, $user['id']);
    jsonResponse(['success' => true, 'favorites' => $favorites, 'count' => count($favorites)]);
}

jsonResponse(['success' => false, 'error' => 'Method not allowed'], 405);
