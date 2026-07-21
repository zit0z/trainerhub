<?php
require_once 'auth-lib.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$ADMIN_PASSWORD = $_ENV['TRAINERHUB_ADMIN_PASSWORD'] ?? 'sayfehub2026';

$action = $_GET['action'] ?? '';
$pdo = getDB();

if ($action === 'stats') {
    $games = $pdo->query("SELECT COUNT(*) FROM games WHERE is_active = 1")->fetchColumn();
    $trainers = $pdo->query("SELECT COUNT(*) FROM trainers WHERE is_active = 1")->fetchColumn();
    $users = $pdo->query("SELECT COUNT(*) FROM users")->fetchColumn();
    $premium_users = $pdo->query("SELECT COUNT(*) FROM users WHERE subscription_status != 'free'")->fetchColumn();
    $community_patterns = $pdo->query("SELECT COUNT(*) FROM community_patterns")->fetchColumn();
    $downloads = 0;
    $zip = '/var/www/trainerhub/TrainerHub-windows.zip';
    if (file_exists($zip)) {
        $downloads = (int)(filesize($zip) / 1024 / 1024);
    }
    $dbSize = '0 MB';
    if (defined('DB_PATH') && file_exists(DB_PATH)) {
        $dbSize = round(filesize(DB_PATH) / 1024 / 1024, 2) . ' MB';
    }
    jsonResponse([
        'success' => true,
        'games' => (int)$games,
        'trainers' => (int)$trainers,
        'users' => (int)$users,
        'premium_users' => (int)$premium_users,
        'community_patterns' => (int)$community_patterns,
        'downloads' => $downloads,
        'db_size' => $dbSize
    ]);
}

if ($action === 'sync_stats') {
    // Recalculate user reputation and approved pattern counts
    $pdo->exec("UPDATE users SET reputation = 0");
    $stmt = $pdo->query("
        SELECT cp.user_id, COUNT(*) as cnt FROM community_patterns cp WHERE cp.status = 'approved' GROUP BY cp.user_id
    ");
    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
        $upd = $pdo->prepare("UPDATE users SET reputation = reputation + ? * 10 WHERE id = ?");
        $upd->execute([$row['cnt'], $row['user_id']]);
    }
    jsonResponse(['success' => true, 'message' => 'Statistiken neu berechnet']);
}

if ($action === 'purge_logs') {
    $cutoff = strtotime('-30 days');
    $stmt = $pdo->prepare("DELETE FROM trainer_logs WHERE created_at < ?");
    $stmt->execute([$cutoff]);
    $count = $stmt->rowCount();
    jsonResponse(['success' => true, 'message' => "$count alte Logs gelöscht"]);
}

if ($action === 'add_game') {
    $data = json_decode(file_get_contents('php://input'), true);
    $stmt = $pdo->prepare("INSERT INTO games (name, slug, process_name, genre, steam_app_id, is_active) VALUES (?, ?, ?, ?, ?, 1)");
    $stmt->execute([
        $data['name'] ?? '',
        $data['slug'] ?? '',
        $data['process_name'] ?? '',
        $data['genre'] ?? '',
        $data['steam_app_id'] ?? null
    ]);
    jsonResponse(['success' => true, 'game_id' => $pdo->lastInsertId()]);
}

if ($action === 'add_trainer') {
    $data = json_decode(file_get_contents('php://input'), true);
    $stmt = $pdo->prepare("INSERT INTO trainers (game_id, name, description, cheat_type, is_premium, is_active) VALUES (?, ?, ?, ?, ?, 1)");
    $stmt->execute([
        $data['game_id'] ?? 0,
        $data['name'] ?? '',
        $data['description'] ?? '',
        $data['cheat_type'] ?? 'memory_scan',
        isset($data['is_premium']) ? (int)$data['is_premium'] : 0
    ]);
    jsonResponse(['success' => true, 'trainer_id' => $pdo->lastInsertId()]);
}

if ($action === 'edit_trainer') {
    $data = json_decode(file_get_contents('php://input'), true);
    $stmt = $pdo->prepare("UPDATE trainers SET name=?, description=?, is_premium=? WHERE id=?");
    $stmt->execute([
        $data['name'] ?? '',
        $data['description'] ?? '',
        isset($data['is_premium']) ? (int)$data['is_premium'] : 0,
        $data['trainer_id'] ?? 0
    ]);
    jsonResponse(['success' => true, 'message' => 'Trainer aktualisiert']);
}

if ($action === 'delete_trainer') {
    $data = json_decode(file_get_contents('php://input'), true);
    $stmt = $pdo->prepare("DELETE FROM trainer_patterns WHERE trainer_id = ?");
    $stmt->execute([$data['trainer_id'] ?? 0]);
    $stmt = $pdo->prepare("DELETE FROM trainers WHERE id = ?");
    $stmt->execute([$data['trainer_id'] ?? 0]);
    jsonResponse(['success' => true, 'message' => 'Trainer gelöscht']);
}

if ($action === 'config' || $action === 'login') {
    $data = json_decode(file_get_contents('php://input'), true);
    $pass = $data['password'] ?? '';
    if ($pass === $ADMIN_PASSWORD) {
        $token = generateToken();
        $stmt = $pdo->prepare("INSERT INTO api_keys (user_id, api_key) VALUES (0, ?)");
        $stmt->execute([$token]);
        jsonResponse(['success' => true, 'token' => $token]);
    }
    jsonResponse(['success' => false, 'error' => 'Invalid password'], 401);
}

$token = getBearerToken();
$stmt = $pdo->prepare("SELECT 1 FROM api_keys WHERE api_key = ? AND user_id = 0 AND is_active = 1 LIMIT 1");
$stmt->execute([$token]);
if (!$stmt->fetch()) {
    jsonResponse(['success' => false, 'error' => 'Unauthorized'], 401);
}

if ($action === 'list_users') {
    $stmt = $pdo->query("SELECT id, email, username, subscription_status, subscription_expires_at, created_at FROM users ORDER BY id DESC");
    $users = $stmt->fetchAll(PDO::FETCH_ASSOC);
    jsonResponse(['success' => true, 'users' => $users]);
}

if ($action === 'grant_premium' || $action === 'revoke_premium') {
    $data = json_decode(file_get_contents('php://input'), true);
    $userId = (int)($data['user_id'] ?? 0);
    $enable = $action === 'grant_premium';
    $status = $enable ? 'active' : 'free';
    $expires = $enable ? strtotime('+100 years') : null;
    $stmt = $pdo->prepare("UPDATE users SET subscription_status=?, subscription_expires_at=? WHERE id=?");
    $stmt->execute([$status, $expires, $userId]);
    jsonResponse(['success' => true, 'message' => $enable ? 'Premium granted' : 'Premium revoked']);
}

if ($action === 'list_trainers') {
    $stmt = $pdo->query("
        SELECT t.*, g.name as game_name, g.process_name 
        FROM trainers t 
        JOIN games g ON g.id = t.game_id 
        ORDER BY g.name, t.name
    ");
    $trainers = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    foreach ($trainers as &$t) {
        $stmt2 = $pdo->prepare("SELECT * FROM trainer_patterns WHERE trainer_id = ?");
        $stmt2->execute([$t['id']]);
        $t['patterns'] = $stmt2->fetchAll(PDO::FETCH_ASSOC);
    }
    
    jsonResponse(['success' => true, 'trainers' => $trainers]);
}

if ($action === 'add_pattern') {
    $data = json_decode(file_get_contents('php://input'), true);
    $stmt = $pdo->prepare("INSERT INTO trainer_patterns (trainer_id, game_version, pattern, offset, value_type, value, scan_module) VALUES (?, ?, ?, ?, ?, ?, ?)");
    $stmt->execute([
        $data['trainer_id'] ?? 0,
        $data['game_version'] ?? '*',
        $data['pattern'] ?? '',
        $data['offset'] ?? 0,
        $data['value_type'] ?? 'int32',
        $data['value'] ?? null,
        $data['scan_module'] ?? null
    ]);
    jsonResponse(['success' => true, 'pattern_id' => $pdo->lastInsertId()]);
}

if ($action === 'delete_pattern') {
    $data = json_decode(file_get_contents('php://input'), true);
    $stmt = $pdo->prepare("DELETE FROM trainer_patterns WHERE id = ?");
    $stmt->execute([$data['pattern_id'] ?? 0]);
    jsonResponse(['success' => true]);
}

if ($action === 'list_community_patterns') {
    $stmt = $pdo->query("
        SELECT cp.*, u.email as author, g.name as game_name, g.slug as game_slug, t.name as trainer_name
        FROM community_patterns cp
        JOIN users u ON u.id = cp.user_id
        JOIN games g ON g.id = cp.game_id
        LEFT JOIN trainers t ON t.id = cp.trainer_id
        ORDER BY cp.status, cp.votes DESC, cp.created_at DESC
    ");
    jsonResponse(['success' => true, 'patterns' => $stmt->fetchAll(PDO::FETCH_ASSOC)]);
}

if ($action === 'approve_community_pattern') {
    $data = json_decode(file_get_contents('php://input'), true);
    $stmt = $pdo->prepare("UPDATE community_patterns SET status = 'approved' WHERE id = ?");
    $stmt->execute([$data['pattern_id'] ?? 0]);
    jsonResponse(['success' => true, 'message' => 'Approved']);
}

if ($action === 'reject_community_pattern') {
    $data = json_decode(file_get_contents('php://input'), true);
    $stmt = $pdo->prepare("UPDATE community_patterns SET status = 'rejected' WHERE id = ?");
    $stmt->execute([$data['pattern_id'] ?? 0]);
    jsonResponse(['success' => true, 'message' => 'Rejected']);
}

jsonResponse(['success' => false, 'error' => 'Invalid action'], 400);
?>
