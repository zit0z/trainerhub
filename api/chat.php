<?php
require_once 'auth-lib.php';
header('Content-Type: application/json');
require_once 'config.php';
$action = $_GET['action'] ?? 'history';
$pdo = getDB();

try {
    if ($action === 'history') {
        $channel = preg_replace('/[^a-z0-9_-]/', '', $_GET['channel'] ?? 'global');
        $stmt = $pdo->prepare("
            SELECT c.*, u.username, u.is_admin
            FROM chat_messages c
            JOIN users u ON u.id = c.user_id
            WHERE c.channel = ?
            ORDER BY c.created_at DESC
            LIMIT 50
        ");
        $stmt->execute([$channel]);
        $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
        echo json_encode(['success'=>true,'messages'=>array_reverse($rows)]);
    } elseif ($action === 'send') {
        $auth = checkAuth();
        if (!empty($auth['error'])) { http_response_code(401); echo json_encode(['success'=>false,'error'=>$auth['error']]); exit; }
        $user = $auth['user'];
        $input = json_decode(file_get_contents('php://input'), true) ?: [];
        $channel = preg_replace('/[^a-z0-9_-]/', '', $input['channel'] ?? 'global');
        $message = trim($input['message'] ?? '');
        if (!$message) { echo json_encode(['success'=>false,'error'=>'Empty']); exit; }
        $stmt = $pdo->prepare("INSERT INTO chat_messages (user_id, channel, message, created_at) VALUES (?, ?, ?, ?)");
        $stmt->execute([$user['id'], $channel, $message, time()]);
        echo json_encode(['success'=>true,'id'=>$pdo->lastInsertId()]);
    } else {
        echo json_encode(['success'=>false,'error'=>'Unknown']);
    }
} catch (Exception $e) { echo json_encode(['success'=>false,'error'=>$e->getMessage()]); }
