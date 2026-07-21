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
$action = $_GET['action'] ?? 'download';

if ($action === 'download') {
    $stmt = $pdo->prepare("SELECT config_data FROM user_configs WHERE user_id = ?");
    $stmt->execute([$user['id']]);
    $row = $stmt->fetch(PDO::FETCH_ASSOC);
    $data = [];
    if ($row && !empty($row['config_data'])) {
        $data = json_decode($row['config_data'], true) ?: [];
    }
    jsonResponse(['success' => true, 'config' => $data]);
}

if ($action === 'upload') {
    $input = json_decode(file_get_contents('php://input'), true) ?: [];
    $type = preg_replace('/[^a-z0-9_]/', '', $input['type'] ?? 'all');
    $data = $input['data'] ?? [];
    
    $stmt = $pdo->prepare("SELECT config_data FROM user_configs WHERE user_id = ?");
    $stmt->execute([$user['id']]);
    $row = $stmt->fetch(PDO::FETCH_ASSOC);
    $existing = [];
    if ($row && !empty($row['config_data'])) {
        $existing = json_decode($row['config_data'], true) ?: [];
    }
    
    if ($type === 'all') {
        $existing = $data;
    } else {
        $existing[$type] = $data;
    }
    
    $json = json_encode($existing);
    $stmt = $pdo->prepare("INSERT INTO user_configs (user_id, config_data, updated_at) VALUES (?, ?, strftime('%s','now')) ON CONFLICT(user_id) DO UPDATE SET config_data = excluded.config_data, updated_at = excluded.updated_at");
    $stmt->execute([$user['id'], $json]);
    jsonResponse(['success' => true, 'message' => 'Config gespeichert']);
}

jsonResponse(['success' => false, 'error' => 'Invalid action'], 400);
