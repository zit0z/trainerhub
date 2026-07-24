<?php
/**
 * SweetCheat Stripe Subscription Integration
 * Requires STRIPE_SECRET_KEY in config/stripe.json
 */

require_once 'auth-lib.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$auth = checkAuth();
if (isset($auth['error'])) {
    jsonResponse(['success' => false, 'error' => $auth['error']], $auth['code']);
}
$user = $auth['user'];
requireVerified($user);

$cfgFile = __DIR__ . '/config/stripe.json';
$cfg = json_decode(@file_get_contents($cfgFile) ?: '{}', true);
$secretKey = $cfg['secret_key'] ?? '';
$priceId = $cfg['price_id'] ?? '';

$action = $_GET['action'] ?? '';
$pdo = getDB();

if ($action === 'checkout') {
    if (!$secretKey || !$priceId) {
        jsonResponse(['success' => false, 'error' => 'Stripe not configured'], 500);
    }
    $baseUrl = 'https://' . ($_SERVER['HTTP_HOST'] ?? 'sayfespace.online');
    $successUrl = $baseUrl . '/sweetcheat/?checkout=success&session_id={CHECKOUT_SESSION_ID}';
    $cancelUrl = $baseUrl . '/sweetcheat/?checkout=cancel';
    
    $payload = [
        'mode' => 'subscription',
        'line_items' => [['price' => $priceId, 'quantity' => 1]],
        'success_url' => $successUrl,
        'cancel_url' => $cancelUrl,
        'client_reference_id' => (string)$user['id'],
        'customer_email' => $user['email'],
        'metadata' => ['user_id' => $user['id'], 'platform' => 'sweetcheat']
    ];
    
    $ch = curl_init('https://api.stripe.com/v1/checkout/sessions');
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($payload));
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Authorization: Bearer ' . $secretKey, 'Content-Type: application/x-www-form-urlencoded']);
    $resp = curl_exec($ch);
    curl_close($ch);
    $session = json_decode($resp, true);
    
    if (isset($session['url'])) {
        jsonResponse(['success' => true, 'checkout_url' => $session['url'], 'session_id' => $session['id']]);
    } else {
        jsonResponse(['success' => false, 'error' => $session['error']['message'] ?? 'Stripe error'], 500);
    }
}

if ($action === 'status') {
    jsonResponse([
        'success' => true,
        'subscription' => isPremium($user) ? 'premium' : 'free',
        'expires_at' => $user['subscription_expires_at'],
        'stripe_configured' => !empty($secretKey) && !empty($priceId)
    ]);
}

// Create a payment/subscription record table entry placeholder
// Table: user_subscriptions could be added here for full history


if ($action === 'test_checkout') {
    // Simulate a successful subscription for 30 days
    $expires = time() + 30 * 86400;
    $stmt = $pdo->prepare("UPDATE users SET subscription_status = 'active', subscription_expires_at = ? WHERE id = ?");
    $stmt->execute([$expires, $user['id']]);
    $stmt = $pdo->prepare("INSERT INTO user_subscriptions (user_id, status, amount, currency, provider, expires_at) VALUES (?, 'active', 999, 'eur', 'test', ?)");
    $stmt->execute([$user['id'], $expires]);
    logAudit($user['id'], 'test_checkout', 'stripe.php', ['expires_at' => $expires]);
    jsonResponse(['success' => true, 'message' => 'Premium für 30 Tage aktiviert (Test)']);
}

if ($action === 'webhook') {
    $payload = file_get_contents('php://input');
    $sig_header = $_SERVER['HTTP_STRIPE_SIGNATURE'] ?? '';
    $event = null;
    
    $cfg = json_decode(file_get_contents(__DIR__ . '/config/stripe.json'), true);
    $endpoint_secret = $cfg['webhook_secret'] ?? '';
    
    if ($endpoint_secret) {
        // Simple signature verification (production should use Stripe SDK)
        $timestamp = strtok($sig_header, ',');
        $signature = substr(strtok(','), 4);
        $signed_payload = sprintf('%s.%s', substr($timestamp, 2), $payload);
        $expected = hash_hmac('sha256', $signed_payload, $endpoint_secret);
        if (!hash_equals($expected, $signature)) {
            jsonResponse(['success' => false, 'error' => 'Invalid signature'], 400);
        }
    }
    
    $event = json_decode($payload, true);
    if (!$event) {
        jsonResponse(['success' => false, 'error' => 'Invalid payload'], 400);
    }
    
    if ($event['type'] === 'checkout.session.completed') {
        $session = $event['data']['object'];
        $userId = (int)($session['client_reference_id'] ?? $session['metadata']['user_id'] ?? 0);
        $sessionId = $session['id'] ?? '';
        if ($userId) {
            $expires = time() + 30 * 86400;
            $stmt = $pdo->prepare("UPDATE users SET subscription_status = 'active', subscription_expires_at = ? WHERE id = ?");
            $stmt->execute([$expires, $userId]);
            $stmt = $pdo->prepare("INSERT INTO user_subscriptions (user_id, status, amount, currency, provider, provider_session_id, expires_at) VALUES (?, 'active', 999, 'eur', 'stripe', ?, ?)");
            $stmt->execute([$userId, $sessionId, $expires]);
            logAudit($userId, 'stripe_checkout_completed', 'stripe.php', ['session_id' => $sessionId]);
        }
    }
    
    jsonResponse(['success' => true, 'received' => true]);
}

jsonResponse(['success' => false, 'error' => 'Invalid action'], 400);
?>
