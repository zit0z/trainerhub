<?php
/**
 * SweetCheat Auth Library
 */

if (!defined('DB_PATH')) {
    define('DB_PATH', __DIR__ . '/../database/sweetcheat.db');
}

function getDB() {
    static $pdo = null;
    if ($pdo === null) {
        $pdo = new PDO('sqlite:' . DB_PATH);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $pdo->exec("PRAGMA foreign_keys = ON");
    }
    return $pdo;
}

function generateToken() {
    return bin2hex(random_bytes(32));
}

function getBearerToken() {
    $headers = [];
    if (function_exists('getallheaders')) {
        $headers = getallheaders();
    } else {
        foreach ($_SERVER as $key => $value) {
            if (strpos($key, 'HTTP_') === 0) {
                $name = str_replace('_', '-', substr($key, 5));
                $headers[ucwords(strtolower($name), '-')] = $value;
            }
        }
    }
    $auth = $headers['Authorization'] ?? '';
    if (preg_match('/Bearer\s+(.+)/', $auth, $matches)) {
        return $matches[1];
    }
    return null;
}

function checkAuth() {
    $pdo = getDB();
    $token = getBearerToken();
    if (!$token) {
        return ['error' => 'No token', 'code' => 401];
    }
    $stmt = $pdo->prepare("
        SELECT u.* FROM api_keys k
        JOIN users u ON u.id = k.user_id
        WHERE k.api_key = ? AND k.is_active = 1
        LIMIT 1
    ");
    $stmt->execute([$token]);
    $user = $stmt->fetch(PDO::FETCH_ASSOC);
    if (!$user) {
        return ['error' => 'Invalid token', 'code' => 401];
    }
    return ['user_id' => $user['id'], 'user' => $user];
}

function isPremium($user) {
    if (empty($user['subscription_status'])) return false;
    if ($user['subscription_status'] === 'active') return true;
    if ($user['subscription_status'] === 'premium') return true;
    if ($user['subscription_expires_at'] && $user['subscription_expires_at'] > time()) return true;
    return false;
}

function jsonResponse($data, $code = 200) {
    http_response_code($code);
    header('Content-Type: application/json');
    echo json_encode($data);
    exit;
}

// Premium feature flags
function getPremiumFeatures($user) {
    $base = [
        'max_games_per_day' => 3,
        'max_trainers_per_game' => 1,
        'advanced_scans' => false,
        'savegame_editor' => false,
        'hotkeys_enabled' => false,
        'priority_support' => false,
        'pattern_library' => false,
        'freeze_enabled' => false,
        'multi_value_scan' => false,
        'config_sync' => false,
        'trainer_history' => false,
        'custom_hotkeys' => false,
        'smapi_bridge' => false,
        'favorites' => false,
        'beta_features' => false,
    ];
    if (isPremium($user)) {
        return array_merge($base, [
            'max_games_per_day' => 9999,
            'max_trainers_per_game' => 99,
            'advanced_scans' => true,
            'savegame_editor' => true,
            'hotkeys_enabled' => true,
            'priority_support' => true,
            'pattern_library' => true,
            'freeze_enabled' => true,
            'multi_value_scan' => true,
            'config_sync' => true,
            'trainer_history' => true,
            'custom_hotkeys' => true,
            'smapi_bridge' => true,
            'favorites' => true,
            'beta_features' => true,
        ]);
    }
    return $base;
}

function logAudit($userId, $action, $endpoint = null, $details = null) {
    try {
        $pdo = getDB();
        $stmt = $pdo->prepare("INSERT INTO audit_log (user_id, action, endpoint, ip, user_agent, details, created_at) VALUES (?, ?, ?, ?, ?, ?, strftime('%s','now'))");
        $stmt->execute([
            $userId,
            $action,
            $endpoint,
            $_SERVER['REMOTE_ADDR'] ?? 'cli',
            $_SERVER['HTTP_USER_AGENT'] ?? '',
            $details ? json_encode($details) : null
        ]);
    } catch (Exception $e) {
        error_log("Audit log failed: " . $e->getMessage());
    }
}

function checkRateLimit($endpoint, $maxRequests = 100, $windowSeconds = 60) {
    try {
        $ip = $_SERVER['REMOTE_ADDR'] ?? 'cli';
        $pdo = getDB();
        $now = time();
        $windowStart = $now - $windowSeconds;
        // Clean old entries
        $pdo->prepare("DELETE FROM rate_limit WHERE window_start < ?")->execute([$windowStart]);
        // Get current count
        $stmt = $pdo->prepare("SELECT count, window_start FROM rate_limit WHERE ip = ? AND endpoint = ?");
        $stmt->execute([$ip, $endpoint]);
        $row = $stmt->fetch(PDO::FETCH_ASSOC);
        if (!$row) {
            $pdo->prepare("INSERT INTO rate_limit (ip, endpoint, count, window_start) VALUES (?, ?, 1, ?)")->execute([$ip, $endpoint, $now]);
            return true;
        }
        if ($row['count'] >= $maxRequests) {
            return false;
        }
        $pdo->prepare("UPDATE rate_limit SET count = count + 1 WHERE ip = ? AND endpoint = ?")->execute([$ip, $endpoint]);
        return true;
    } catch (Exception $e) {
        error_log("Rate limit check failed: " . $e->getMessage());
        return true;
    }
}


function requireVerified($user) {
    if (empty($user['email_verified'])) {
        jsonResponse(['success' => false, 'error' => 'E-Mail nicht bestätigt', 'needs_verification' => true], 403);
    }
}

function getRequestJson() {
    $raw = file_get_contents('php://input');
    $data = json_decode($raw, true);
    if ($data === null && !empty($raw)) {
        jsonResponse(['success' => false, 'error' => 'Ungültiges JSON'], 400);
    }
    return $data ?? [];
}

function validatePasswordStrength($password) {
    if (strlen($password) < 8) return 'Passwort muss mindestens 8 Zeichen haben';
    if (!preg_match('/[A-Z]/', $password)) return 'Passwort muss Großbuchstaben enthalten';
    if (!preg_match('/[a-z]/', $password)) return 'Passwort muss Kleinbuchstaben enthalten';
    if (!preg_match('/[0-9]/', $password)) return 'Passwort muss Ziffern enthalten';
    return null;
}

function rotateApiKey($userId) {
    $pdo = getDB();
    // Deactivate old keys
    $pdo->prepare("UPDATE api_keys SET is_active = 0 WHERE user_id = ?")->execute([$userId]);
    $newKey = generateToken();
    $pdo->prepare("INSERT INTO api_keys (user_id, api_key, created_at) VALUES (?, ?, strftime('%s','now'))")->execute([$userId, $newKey]);
    return $newKey;
}

function sanitizeEmail($email) {
    return strtolower(trim($email));
}

?>

