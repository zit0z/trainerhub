<?php
require_once 'auth-lib.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

// Cache helper
function getCache($key, $ttl = 300) {
    $pdo = getDB();
    $stmt = $pdo->prepare("SELECT value, created_at FROM api_cache WHERE key = ?");
    $stmt->execute([$key]);
    $row = $stmt->fetch(PDO::FETCH_ASSOC);
    if ($row && (time() - $row['created_at']) < $ttl) {
        return json_decode($row['value'], true);
    }
    return null;
}

function setCache($key, $value, $ttl = 300) {
    $pdo = getDB();
    $stmt = $pdo->prepare("INSERT OR REPLACE INTO api_cache (key, value, created_at, ttl) VALUES (?, ?, ?, ?)");
    $stmt->execute([$key, json_encode($value), time(), $ttl]);
}

$auth = checkAuth();
if (isset($auth['error'])) {
    jsonResponse(['success' => false, 'error' => $auth['error']], $auth['code']);
}
$user = $auth['user'];
$isPremium = isPremium($user);

$action = $_GET['action'] ?? 'list';
$pdo = getDB();

if ($action === 'list') {
    $slug = $_GET['game'] ?? 'stardew-valley';
    $cache_key = 'trainers_' . preg_replace('/[^a-z0-9-]/', '', $slug);
    $cached = getCache($cache_key, 300);
    if ($cached) {
        jsonResponse(['success' => true] + $cached + ['cached' => true]);
    }
    
    $stmt = $pdo->prepare("
        SELECT t.*, g.name as game_name, g.process_name, g.slug as game_slug
        FROM trainers t
        JOIN games g ON g.id = t.game_id
        WHERE g.slug = ? AND t.is_active = 1
        ORDER BY t.is_premium ASC, t.name ASC
    ");
    $stmt->execute([$slug]);
    $trainers = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    foreach ($trainers as &$t) {
        $t['locked'] = ($t['is_premium'] == 1 && !$isPremium);
        $t['title'] = $t['name'];
        $t['premium'] = (int)$t['is_premium'];
        $t['tags'] = $t['tags'] ? explode(',', $t['tags']) : [];
        if (empty($t['command'])) {
            unset($t['command']);
        }
        
        // Load patterns
        $stmt2 = $pdo->prepare("SELECT game_version, pattern, offset, value_type, value, scan_module FROM trainer_patterns WHERE trainer_id = ? ORDER BY game_version='*' DESC, id DESC");
        $stmt2->execute([$t['id']]);
        $t['patterns'] = $stmt2->fetchAll(PDO::FETCH_ASSOC);
        
        // Load game cheats too (official console commands / configs)
        $stmt3 = $pdo->prepare("SELECT name, description, cheat_type, command, params, effect, is_premium FROM game_cheats WHERE game_id = ? AND is_active = 1 ORDER BY cheat_type, name");
        $stmt3->execute([$t['game_id']]);
        $t['game_cheats'] = $stmt3->fetchAll(PDO::FETCH_ASSOC);
        foreach ($t['game_cheats'] as &$gc) {
            $gc['locked'] = ($gc['is_premium'] == 1 && !$isPremium);
        }
        
        // Keep trainer_id for activation, remove internal game_id
        $t['trainer_id'] = (int)$t['id'];
        unset($t['id']);
        unset($t['game_id']);
        foreach ($t['patterns'] as &$p) {
            unset($p['id']);
            unset($p['trainer_id']);
        }
    }
    
    $result = [
        'game' => $slug,
        'subscription' => $isPremium ? 'premium' : 'free',
        'expires_at' => $user['subscription_expires_at'],
        'trainers' => $trainers
    ];
    setCache($cache_key, $result, 300);
    
    jsonResponse(['success' => true] + $result + ['cached' => false]);
}

if ($action === 'activate') {
    $trainerId = (int)($_GET['trainer_id'] ?? 0);
    $stmt = $pdo->prepare("SELECT t.*, g.process_name FROM trainers t JOIN games g ON g.id = t.game_id WHERE t.id = ? AND t.is_active = 1");
    $stmt->execute([$trainerId]);
    $trainer = $stmt->fetch(PDO::FETCH_ASSOC);
    
    if (!$trainer) {
        jsonResponse(['success' => false, 'error' => 'Trainer not found'], 404);
    }
    
    if ($trainer['is_premium'] && !$isPremium) {
        jsonResponse(['success' => false, 'error' => 'Premium required'], 403);
    }
    
    $stmt = $pdo->prepare("INSERT INTO trainer_logs (user_id, trainer_id, action, ip, created_at) VALUES (?, ?, 'activate', ?, strftime('%s','now'))");
    $stmt->execute([$user['id'], $trainerId, $_SERVER['REMOTE_ADDR'] ?? '']);
    
    $stmt = $pdo->prepare("SELECT * FROM trainer_patterns WHERE trainer_id = ?");
    $stmt->execute([$trainerId]);
    $patterns = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    jsonResponse([
        'success' => true,
        'trainer' => $trainer['name'],
        'process_name' => $trainer['process_name'],
        'patterns' => $patterns
    ]);
}

jsonResponse(['success' => false, 'error' => 'Invalid action'], 400);
?>
