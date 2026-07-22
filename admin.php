<?php
require_once 'auth-lib.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
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
    $zip = '/var/www/sweetcheat/SweetCheat-windows.zip';
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

if ($action === 'config' || $action === 'login') {
    $data = json_decode(file_get_contents('php://input'), true);
    $pass = $data['password'] ?? '';
    if ($pass === $ADMIN_PASSWORD) {
        // Find first admin user to attach token to
        $stmt = $pdo->prepare("SELECT id FROM users WHERE is_admin = 1 ORDER BY id LIMIT 1");
        $stmt->execute();
        $adminId = $stmt->fetchColumn();
        if (!$adminId) {
            jsonResponse(['success' => false, 'error' => 'No admin user configured'], 500);
        }
        $token = generateToken();
        $stmt = $pdo->prepare("INSERT INTO api_keys (user_id, api_key) VALUES (?, ?)");
        $stmt->execute([$adminId, $token]);
        jsonResponse(['success' => true, 'token' => $token]);
    }
    jsonResponse(['success' => false, 'error' => 'Invalid password'], 401);
}

// Authenticated admin endpoints below
$token = getBearerToken();
$isAdmin = false;
$adminUser = null;
if ($token) {
    $stmt = $pdo->prepare("
        SELECT u.* FROM api_keys k
        JOIN users u ON u.id = k.user_id
        WHERE k.api_key = ?
        LIMIT 1
    ");
    $stmt->execute([$token]);
    $adminUser = $stmt->fetch(PDO::FETCH_ASSOC);
    if ($adminUser && !empty($adminUser['is_admin'])) {
        $isAdmin = true;
    }
}

if (!$isAdmin) {
    jsonResponse(['success' => false, 'error' => 'Unauthorized'], 403);
}

if ($action === 'verify') {
    jsonResponse(['success' => true, 'admin' => true, 'user' => $adminUser]);
}

if ($action === 'users') {
    $stmt = $pdo->prepare("
        SELECT id, email, username, subscription_status, subscription_expires_at, created_at
        FROM users
        ORDER BY created_at DESC
    ");
    $stmt->execute();
    jsonResponse(['success' => true, 'users' => $stmt->fetchAll(PDO::FETCH_ASSOC)]);
}

if ($action === 'create_user') {
    $data = json_decode(file_get_contents('php://input'), true);
    if (empty($data['email']) || empty($data['username'])) {
        jsonResponse(['success' => false, 'error' => 'E-Mail und Username erforderlich'], 400);
    }
    $pass = password_hash($data['password'] ?? bin2hex(random_bytes(8)), PASSWORD_DEFAULT);
    $stmt = $pdo->prepare("
        INSERT INTO users (email, username, password_hash, subscription_status, subscription_expires_at, created_at)
        VALUES (?, ?, ?, ?, ?, strftime('%s','now'))
    ");
    $stmt->execute([
        $data['email'],
        $data['username'],
        $pass,
        $data['subscription_status'] ?? 'free',
        !empty($data['subscription_expires_at']) ? (int)$data['subscription_expires_at'] : null
    ]);
    logAudit(0, 'admin_create_user', 'admin.php', ['target_user' => (int)$pdo->lastInsertId()]);
    jsonResponse(['success' => true, 'user_id' => $pdo->lastInsertId()]);
}

if ($action === 'update_user') {
    $data = json_decode(file_get_contents('php://input'), true);
    if (empty($data['id'])) {
        jsonResponse(['success' => false, 'error' => 'User ID erforderlich'], 400);
    }
    $stmt = $pdo->prepare("
        UPDATE users SET email = ?, username = ?, subscription_status = ?, subscription_expires_at = ?, is_premium = ?
        WHERE id = ?
    ");
    $isPremium = ($data['subscription_status'] ?? '') === 'premium' ? 1 : 0;
    $stmt->execute([
        $data['email'] ?? '',
        $data['username'] ?? '',
        $data['subscription_status'] ?? 'free',
        !empty($data['subscription_expires_at']) ? (int)$data['subscription_expires_at'] : null,
        $isPremium,
        (int)$data['id']
    ]);
    logAudit((int)$adminUser['id'], 'admin_update_user', 'admin.php', ['target_user' => (int)$data['id']]);
    jsonResponse(['success' => true, 'message' => 'Benutzer aktualisiert']);
}

if ($action === 'delete_user') {
    $data = json_decode(file_get_contents('php://input'), true);
    $id = (int)($data['id'] ?? 0);
    if (!$id) {
        jsonResponse(['success' => false, 'error' => 'User ID erforderlich'], 400);
    }
    if ($id === (int)$adminUser['id']) {
        jsonResponse(['success' => false, 'error' => 'Eigenes Konto nicht löschbar'], 400);
    }
    $pdo->prepare("DELETE FROM api_keys WHERE user_id = ?")->execute([$id]);
    $pdo->prepare("DELETE FROM user_favorites WHERE user_id = ?")->execute([$id]);
    $pdo->prepare("DELETE FROM trainer_logs WHERE user_id = ?")->execute([$id]);
    $pdo->prepare("DELETE FROM users WHERE id = ?")->execute([$id]);
    logAudit((int)$adminUser['id'], 'admin_delete_user', 'admin.php', ['target_user' => $id]);
    jsonResponse(['success' => true, 'message' => 'Benutzer gelöscht']);
}

if ($action === 'system') {
    $dbSize = file_exists(DB_PATH) ? round(filesize(DB_PATH) / 1024 / 1024, 2) . ' MB' : 'N/A';
    $zipSize = file_exists('/var/www/sweetcheat/SweetCheat-windows.zip') ? round(filesize('/var/www/sweetcheat/SweetCheat-windows.zip') / 1024 / 1024, 1) . ' MB' : 'N/A';
    $setupSize = file_exists('/var/www/sweetcheat/SweetCheat-Setup.exe') ? round(filesize('/var/www/sweetcheat/SweetCheat-Setup.exe') / 1024 / 1024, 1) . ' MB' : 'N/A';
    jsonResponse([
        'success' => true,
        'version' => '0.7.1',
        'php_version' => PHP_VERSION,
        'server_time' => date('Y-m-d H:i:s'),
        'database_size' => $dbSize,
        'zip_size' => $zipSize,
        'setup_size' => $setupSize,
        'disk_free' => round(disk_free_space('/') / 1024 / 1024 / 1024, 2) . ' GB'
    ]);
}

if ($action === 'test_apis') {
    $endpoints = ['auth.php?action=status', 'games.php?per_page=1', 'trainers.php?action=count', 'version.php'];
    $results = [];
    foreach ($endpoints as $ep) {
        $url = 'https://' . ($_SERVER['HTTP_HOST'] ?? 'sayfespace.online') . '/sweetcheat/api/' . $ep;
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 5);
        $resp = curl_exec($ch);
        $http = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        $results[$ep] = ['http' => $http, 'ok' => $http === 200];
    }
    jsonResponse(['success' => true, 'results' => $results]);
}

// Legacy trainer/game admin endpoints
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

jsonResponse(['success' => false, 'error' => 'Invalid action'], 400);
