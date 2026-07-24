<?php
require_once 'auth-lib.php';
header('Content-Type: application/json');
require_once 'config.php';
$action = $_GET['action'] ?? 'list';
$pdo = getDB();

try {
    switch($action) {
        case 'list':
            $stmt = $pdo->prepare("
                SELECT r.*, u.username, COUNT(v.id) as vote_count,
                    (SELECT COUNT(*) FROM trainer_requests_votes WHERE request_id = r.id AND user_id = ?) as user_voted
                FROM trainer_requests r
                JOIN users u ON u.id = r.user_id
                LEFT JOIN trainer_requests_votes v ON v.request_id = r.id
                WHERE r.status = 'open'
                GROUP BY r.id
                ORDER BY vote_count DESC, r.created_at DESC
            ");
            $user_id = !empty($auth['user']) ? $auth['user']['id'] : 0;
            $stmt->execute([$user_id]);
            echo json_encode(['success'=>true,'requests'=>$stmt->fetchAll(PDO::FETCH_ASSOC)]);
            break;
        case 'create':
            $auth = checkAuth();
            if (!empty($auth['error'])) { http_response_code(401); echo json_encode(['success'=>false,'error'=>$auth['error']]); exit; }
            $user = $auth['user'];
            $input = json_decode(file_get_contents('php://input'), true) ?: [];
            $game_name = trim($input['game_name'] ?? '');
            $trainer_type = trim($input['trainer_type'] ?? '');
            $description = trim($input['description'] ?? '');
            if (!$game_name) { echo json_encode(['success'=>false,'error'=>'game_name required']); exit; }
            $stmt = $pdo->prepare("INSERT INTO trainer_requests (user_id, game_name, trainer_type, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)");
            $stmt->execute([$user['id'], $game_name, $trainer_type, $description, time(), time()]);
            echo json_encode(['success'=>true,'id'=>$pdo->lastInsertId()]);
            break;
        case 'vote':
            $auth = checkAuth();
            if (!empty($auth['error'])) { http_response_code(401); echo json_encode(['success'=>false,'error'=>$auth['error']]); exit; }
            $user = $auth['user'];
            $input = json_decode(file_get_contents('php://input'), true) ?: [];
            $request_id = intval($input['request_id'] ?? 0);
            $stmt = $pdo->prepare("INSERT OR IGNORE INTO trainer_requests_votes (request_id, user_id, created_at) VALUES (?, ?, ?)");
            $stmt->execute([$request_id, $user['id'], time()]);
            $stmt = $pdo->prepare("UPDATE trainer_requests SET votes = (SELECT COUNT(*) FROM trainer_requests_votes WHERE request_id = ?) WHERE id = ?");
            $stmt->execute([$request_id, $request_id]);
            echo json_encode(['success'=>true]);
            break;
        default:
            echo json_encode(['success'=>false,'error'=>'Unknown']);
    }
} catch (Exception $e) { echo json_encode(['success'=>false,'error'=>$e->getMessage()]); }
