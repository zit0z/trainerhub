<?php
/**
 * Stripe Webhook for SweetCheat
 * Configure endpoint in Stripe Dashboard with events:
 * checkout.session.completed, invoice.payment_succeeded, customer.subscription.deleted
 */

require_once 'auth-lib.php';

$payload = @file_get_contents('php://input');
$sigHeader = $_SERVER['HTTP_STRIPE_SIGNATURE'] ?? '';
$event = null;

$cfgFile = __DIR__ . '/config/stripe.json';
$cfg = json_decode(file_get_contents($cfgFile), true);
$secretKey = $cfg['secret_key'] ?? '';
$webhookSecret = $cfg['webhook_secret'] ?? '';

// Simple signature verification
if ($webhookSecret) {
    $timestamp = null;
    $signatures = [];
    $parts = explode(',', $sigHeader);
    foreach ($parts as $part) {
        [$key, $val] = explode('=', $part, 2);
        if ($key === 't') $timestamp = $val;
        if ($key === 'v1') $signatures[] = $val;
    }
    $signedPayload = $timestamp . '.' . $payload;
    $expectedSig = hash_hmac('sha256', $signedPayload, $webhookSecret);
    if (!in_array($expectedSig, $signatures)) {
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Invalid signature']);
        exit;
    }
}

$event = json_decode($payload, true);
if (!$event) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Invalid payload']);
    exit;
}

$type = $event['type'] ?? '';
$data = $event['data']['object'] ?? [];

$pdo = getDB();

if ($type === 'checkout.session.completed') {
    $userId = (int)($data['client_reference_id'] ?? $data['metadata']['user_id'] ?? 0);
    $subId = $data['subscription'] ?? '';
    if ($userId) {
        $expires = strtotime('+1 month');
        $stmt = $pdo->prepare("UPDATE users SET subscription_status='active', subscription_expires_at=? WHERE id=?");
        $stmt->execute([$expires, $userId]);
        
        $stmt = $pdo->prepare("INSERT INTO subscriptions (user_id, provider, provider_subscription_id, status, plan, amount, currency, starts_at, ends_at) VALUES (?, 'stripe', ?, 'active', 'premium', 9.99, 'EUR', strftime('%s','now'), ?)");
        $stmt->execute([$userId, $subId, $expires]);
    }
}

if ($type === 'customer.subscription.deleted') {
    $subId = $data['id'] ?? '';
    $stmt = $pdo->prepare("SELECT user_id FROM subscriptions WHERE provider_subscription_id = ? LIMIT 1");
    $stmt->execute([$subId]);
    $userId = $stmt->fetchColumn();
    if ($userId) {
        $stmt = $pdo->prepare("UPDATE users SET subscription_status='cancelled' WHERE id=?");
        $stmt->execute([$userId]);
        $stmt = $pdo->prepare("UPDATE subscriptions SET status='cancelled' WHERE provider_subscription_id=?");
        $stmt->execute([$subId]);
    }
}

http_response_code(200);
echo json_encode(['success' => true, 'received' => $type]);
?>
