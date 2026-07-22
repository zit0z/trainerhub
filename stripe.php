<?php
/**
 * TrainerHub Stripe Subscription Integration
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

$cfgFile = __DIR__ . '/config/stripe.json';
$cfg = json_decode(file_get_contents($cfgFile), true);
$secretKey = $cfg['secret_key'] ?? '';
$priceId = $cfg['price_id'] ?? '';

if (!$secretKey || !$priceId) {
    jsonResponse(['success' => false, 'error' => 'Stripe not configured'], 500);
}

$action = $_GET['action'] ?? '';

if ($action === 'checkout') {
    $baseUrl = 'https://' . ($_SERVER['HTTP_HOST'] ?? 'sayfespace.online');
    $successUrl = $baseUrl . '/trainerhub/?checkout=success&session_id={CHECKOUT_SESSION_ID}';
    $cancelUrl = $baseUrl . '/trainerhub/?checkout=cancel';
    
    $payload = [
        'mode' => 'subscription',
        'line_items' => [['price' => $priceId, 'quantity' => 1]],
        'success_url' => $successUrl,
        'cancel_url' => $cancelUrl,
        'client_reference_id' => (string)$user['id'],
        'customer_email' => $user['email'],
        'metadata' => ['user_id' => $user['id'], 'platform' => 'trainerhub']
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
        'expires_at' => $user['subscription_expires_at']
    ]);
}

jsonResponse(['success' => false, 'error' => 'Invalid action'], 400);
?>
