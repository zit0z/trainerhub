<?php
header('Content-Type: application/json');
require_once __DIR__ . '/config.php';

$method = $_SERVER['REQUEST_METHOD'];
$action = $_GET['action'] ?? 'list';

try {
    $pdo = new PDO(DB_DSN, DB_USER, DB_PASS, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);

    if ($method === 'POST') {
        $api_key = '';
        $headers = getallheaders();
        if (isset($headers['Authorization'])) {
            if (preg_match('/Bearer\s+(\S+)/', $headers['Authorization'], $m)) {
                $api_key = $m[1];
            }
        }
        if (!$api_key) {
            http_response_code(401);
            echo json_encode(['success' => false, 'error' => 'Authorization required']);
            exit;
        }
        $stmt = $pdo->prepare("SELECT id FROM users WHERE api_key = ? LIMIT 1");
        $stmt->execute([$api_key]);
        $user = $stmt->fetch(PDO::FETCH_ASSOC);
        if (!$user) {
            http_response_code(401);
            echo json_encode(['success' => false, 'error' => 'Invalid API key']);
            exit;
        }
        $data = json_decode(file_get_contents('php://input'), true);
        $required = ['game_id', 'trainer_id', 'pattern', 'value_type', 'value'];
        foreach ($required as $r) {
            if (!isset($data[$r])) {
                http_response_code(400);
                echo json_encode(['success' => false, 'error' => "Missing $r"]);
                exit;
            }
        }
        $stmt = $pdo->prepare("INSERT INTO trainer_patterns (trainer_id, game_id, game_version, pattern, offset, value_type, value, created_by, is_active)
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)");
        $stmt->execute([
            $data['trainer_id'],
            $data['game_id'],
            $data['game_version'] ?? '*',
            $data['pattern'],
            $data['offset'] ?? 0,
            $data['value_type'],
            $data['value'],
            $user['id']
        ]);
        echo json_encode(['success' => true, 'id' => $pdo->lastInsertId()]);
        exit;
    }

    if ($action === 'list') {
        $trainer_id = $_GET['trainer_id'] ?? null;
        $game_id = $_GET['game_id'] ?? null;
        $sql = "SELECT * FROM trainer_patterns WHERE is_active = 1";
        $params = [];
        if ($trainer_id) {
            $sql .= " AND trainer_id = ?";
            $params[] = $trainer_id;
        }
        if ($game_id) {
            $sql .= " AND game_id = ?";
            $params[] = $game_id;
        }
        $sql .= " ORDER BY created_at DESC";
        $stmt = $pdo->prepare($sql);
        $stmt->execute($params);
        echo json_encode(['success' => true, 'patterns' => $stmt->fetchAll(PDO::FETCH_ASSOC)]);
    } else {
        echo json_encode(['success' => false, 'error' => 'Unknown action']);
    }
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => $e->getMessage()]);
}
