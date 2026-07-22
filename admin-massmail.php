<?php
require_once 'auth-lib.php';
require_once 'mailer.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$auth = checkAuth();
if (isset($auth['error'])) jsonResponse(['success' => false, 'error' => $auth['error']], $auth['code']);
if (!$auth['user']['is_admin']) jsonResponse(['success' => false, 'error' => 'Forbidden'], 403);

$data = json_decode(file_get_contents('php://input'), true);
$subject = trim($data['subject'] ?? '');
$body = trim($data['body'] ?? '');
$audience = $data['audience'] ?? 'all';

if (!$subject || !$body) {
    jsonResponse(['success' => false, 'error' => 'Betreff und Inhalt erforderlich'], 400);
}

$pdo = getDB();
if ($audience === 'newsletter') {
    $stmt = $pdo->query("SELECT email FROM newsletter_subscribers WHERE confirmed = 1");
} elseif ($audience === 'premium') {
    $stmt = $pdo->query("
        SELECT DISTINCT u.email FROM users u
        JOIN user_subscriptions us ON us.user_id = u.id
        WHERE us.status = 'active' AND us.expires_at > strftime('%s','now')
    ");
} else {
    $stmt = $pdo->query("SELECT email FROM users");
}

$recipients = $stmt->fetchAll(PDO::FETCH_COLUMN);
$sent = 0;
$failed = 0;
foreach ($recipients as $email) {
    $html = getEmailTemplate('welcome', ['username' => $email]);
    // Override welcome template with custom body for mass mail
    $html = preg_replace('/Hallo.*?<\/p>/s', $body, $html, 1) ?: $html;
    if (sendMail($email, $subject, $html, 'massmail')) {
        $sent++;
    } else {
        $failed++;
    }
}
jsonResponse(['success' => true, 'sent' => $sent, 'failed' => $failed, 'total' => count($recipients)]);
