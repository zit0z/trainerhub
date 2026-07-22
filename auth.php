<?php
require_once 'auth-lib.php';
require_once 'mailer.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$action = $_GET['action'] ?? '';
$pdo = getDB();

if ($action === 'register') {
    $data = json_decode(file_get_contents('php://input'), true);
    $email = strtolower(trim($data['email'] ?? ''));
    $username = trim($data['username'] ?? '');
    $password = $data['password'] ?? '';
    
    if (!filter_var($email, FILTER_VALIDATE_EMAIL) || strlen($password) < 6) {
        jsonResponse(['success' => false, 'error' => 'Invalid email or password too short'], 400);
    }
    
    $hash = password_hash($password, PASSWORD_BCRYPT);
    $apiKey = generateToken();
    $verifyToken = bin2hex(random_bytes(24));
    
    try {
        $stmt = $pdo->prepare("
            INSERT INTO users (email, username, password_hash, subscription_status, email_verified, verification_token, created_at)
            VALUES (?, ?, ?, 'free', 0, ?, strftime('%s','now'))
        ");
        $stmt->execute([$email, $username, $hash, $verifyToken]);
        $userId = $pdo->lastInsertId();
        
        $stmt = $pdo->prepare("INSERT INTO api_keys (user_id, api_key) VALUES (?, ?)");
        $stmt->execute([$userId, $apiKey]);
        
        $html = getEmailTemplate('verify', ['token' => $verifyToken]);
        sendMail($email, 'Bitte bestätige deine E-Mail-Adresse', $html, 'verify');
        
        jsonResponse([
            'success' => true,
            'api_key' => $apiKey,
            'email_verified' => false,
            'message' => 'Account erstellt. Bitte bestätige deine E-Mail-Adresse.'
        ]);
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
    
    // Auto-verify existing users from before this feature; new users must verify
    if (empty($user['email_verified'])) {
        jsonResponse([
            'success' => false,
            'error' => 'E-Mail nicht bestätigt',
            'needs_verification' => true,
            'api_key' => null
        ], 403);
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
        'user' => ['id' => $user['id'], 'email' => $user['email'], 'username' => $user['username']],
        'subscription' => isPremium($user) ? 'premium' : 'free',
        'expires_at' => $user['subscription_expires_at']
    ]);
}

jsonResponse(['success' => false, 'error' => 'Invalid action'], 400);
?>
