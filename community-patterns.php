<?php
require_once __DIR__ . '/auth-lib.php';
header('Content-Type: application/json');

$action = $_GET['action'] ?? '';
$method = $_SERVER['REQUEST_METHOD'];

try {
    $pdo = getDB();
    $user = null;
    
    // Try to identify user by API token or fallback
    $token = null;
    if (function_exists('getallheaders')) {
        $headers = getallheaders();
        $auth = $headers['Authorization'] ?? '';
    } else {
        $auth = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
    }
    if (strpos($auth, 'Bearer ') === 0) {
        $token = substr($auth, 7);
        $stmt = $pdo->prepare("SELECT id FROM users WHERE api_token = ? LIMIT 1");
        $stmt->execute([$token]);
        $user = $stmt->fetch(PDO::FETCH_ASSOC);
    }
    
    if ($action === 'list') {
        $game = $_GET['game'] ?? '';
        $stmt = $pdo->prepare("
            SELECT cp.*, g.name as game_name, g.slug as game_slug, u.email as author
            FROM community_patterns cp
            JOIN games g ON cp.game_id = g.id
            JOIN users u ON cp.user_id = u.id
            WHERE g.slug = ? AND cp.status = 'approved'
            ORDER BY cp.votes DESC, cp.created_at DESC
            LIMIT 50
        ");
        $stmt->execute([$game]);
        echo json_encode(['success' => true, 'patterns' => $stmt->fetchAll(PDO::FETCH_ASSOC)]);
        exit;
    }
    
    if ($action === 'vote') {
        $data = json_decode(file_get_contents('php://input'), true);
        $pattern_id = (int)($data['pattern_id'] ?? 0);
        $vote = (int)($data['vote'] ?? 0);
        
        $stmt = $pdo->prepare("UPDATE community_patterns SET votes = votes + ? WHERE id = ?");
        $stmt->execute([$vote, $pattern_id]);
        
        // Award reputation to pattern author
        $author = $pdo->query("SELECT user_id FROM community_patterns WHERE id=$pattern_id")->fetchColumn();
        if ($author) {
            $rep = $pdo->prepare("
                INSERT INTO user_reputation (user_id, total_votes, reputation) 
                VALUES (?, ?, ?) 
                ON CONFLICT(user_id) DO UPDATE SET 
                    total_votes = total_votes + excluded.total_votes, 
                    reputation = reputation + excluded.reputation
            ");
            $rep->execute([$author, 1, $vote]);
        }
        
        echo json_encode(['success' => true, 'votes_added' => $vote]);
        exit;
    }
    
    if ($action === 'submit') {
        if (!$user) {
            http_response_code(401);
            echo json_encode(['success' => false, 'error' => 'Login required']);
            exit;
        }
        $data = json_decode(file_get_contents('php://input'), true);
        $stmt = $pdo->prepare("
            INSERT INTO community_patterns (user_id, game_id, trainer_id, name, game_version, pattern, offset, value_type, value) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ");
        $stmt->execute([
            $user['id'], $data['game_id'], $data.get('trainer_id'), $data['name'], 
            $data['game_version'], $data['pattern'], (int)($data['offset'] ?? 0), 
            $data['value_type'], $data['value']
        ]);
        echo json_encode(['success' => true, 'id' => $pdo->lastInsertId()]);
        exit;
    }
    
    echo json_encode(['success' => false, 'error' => 'Unknown action']);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => $e->getMessage()]);
}
