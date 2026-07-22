<?php
require_once 'auth-lib.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$action = $_GET['action'] ?? '';
$pdo = getDB();

if ($action === 'register') {
    $data = json_decode(file_get_contents('php://input'), true);
    $email = strtolower(trim($data['email'] ?? ''));
    $password = $data['password'] ?? '';
    
    if (!filter_var($email, FILTER_VALIDATE_EMAIL) || strlen($password) < 6) {
        jsonResponse(['success' => false, 'error' => 'Invalid email or password too short'], 400);
    }
    
    $hash = password_hash($password, PASSWORD_BCRYPT);
    $apiKey = generateToken();
    
    try {
        $stmt = $pdo->prepare("INSERT INTO users (email, password_hash, subscription_status) VALUES (?, ?, 'free')");
        $stmt->execute([$email, $hash]);
        $userId = $pdo->lastInsertId();
        
        $stmt = $pdo->prepare("INSERT INTO api_keys (user_id, api_key) VALUES (?, ?)");
        $stmt->execute([$userId, $apiKey]);
        
        jsonResponse(['success' => true, 'api_key' => $apiKey]);
    } catch (PDOException $e) {
        jsonResponse(['success' => false, 'error' => 'Email already exists'], 409);
    }
}

if ($action === 'login') {
    $data = json_decode(file_get_contents('php://input'), true);
    $email = strtolower(trim($data['email'] ?? $data['username'] ?? ''));
    $password = $data['password'] ?? '';
    
    // Try email first, then username
    $stmt = $pdo->prepare("SELECT * FROM users WHERE email = ? LIMIT 1");
    $stmt->execute([$email]);
    $user = $stmt->fetch(PDO::FETCH_ASSOC);
    
    if (!$user) {
        $stmt = $pdo->prepare("SELECT * FROM users WHERE username = ? LIMIT 1");
        $stmt->execute([$email]);
        $user = $stmt->fetch(PDO::FETCH_ASSOC);
    }
    
    if (!$user || !password_verify($password, $user['password_hash'])) {
        jsonResponse(['success' => false, 'error' => 'Invalid credentials'], 401);
    }
    
    $stmt = $pdo->prepare("SELECT api_key FROM api_keys WHERE user_id = ? AND is_active = 1 ORDER BY id DESC LIMIT 1");
    $stmt->execute([$user['id']]);
    $key = $stmt->fetchColumn();
    if (!$key) {
        $key = generateToken();
        $stmt = $pdo->prepare("INSERT INTO api_keys (user_id, api_key) VALUES (?, ?)");
        $stmt->execute([$user['id'], $key]);
    }
    
    jsonResponse([
        'success' => true,
        'api_key' => $key,
        'subscription' => isPremium($user) ? 'premium' : 'free',
        'expires_at' => $user['subscription_expires_at']
    ]);
}

jsonResponse(['success' => false, 'error' => 'Invalid action'], 400);
?>
