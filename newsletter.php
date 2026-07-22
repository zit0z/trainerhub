<?php
require_once 'auth-lib.php';
require_once 'mailer.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$action = $_GET['action'] ?? '';
$pdo = getDB();

if ($action === 'subscribe') {
    $data = json_decode(file_get_contents('php://input'), true);
    $email = sanitizeEmail($data['email'] ?? '');
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        jsonResponse(['success' => false, 'error' => 'Ungültige E-Mail'], 400);
    }
    $token = bin2hex(random_bytes(24));
    try {
        $stmt = $pdo->prepare("INSERT INTO newsletter_subscribers (email, token, confirmed) VALUES (?, ?, 0)");
        $stmt->execute([$email, $token]);
    } catch (PDOException $e) {
        jsonResponse(['success' => false, 'error' => 'Bereits registriert'], 409);
    }
    $baseUrl = 'https://' . ($_SERVER['HTTP_HOST'] ?? 'sayfespace.online');
    $link = $baseUrl . '/trainerhub/verify-newsletter?token=' . urlencode($token);
    $html = "<html><body style='font-family:Inter,sans-serif; background:#050507; color:#f8fafc; padding:20px;'>"
          . "<div style='max-width:480px; margin:0 auto; background:#0f1016; border:1px solid #232333; border-radius:14px; padding:32px;'>"
          . "<h1 style='color:#00f0ff;'>SweetCheat Newsletter</h1>"
          . "<p>Klicke zum Bestätigen:</p>"
          . "<a href='{$link}' style='display:inline-block; background:#00f0ff; color:#050507; padding:14px 28px; border-radius:8px; text-decoration:none; font-weight:700;'>Bestätigen</a>"
          . "</div></body></html>";
    sendMail($email, 'Newsletter bestätigen — SweetCheat', $html, 'newsletter_confirm');
    jsonResponse(['success' => true, 'message' => 'Bestätigungs-Mail gesendet']);
}

if ($action === 'confirm') {
    $token = $_GET['token'] ?? '';
    if (!$token) {
        jsonResponse(['success' => false, 'error' => 'Token erforderlich'], 400);
    }
    $stmt = $pdo->prepare("UPDATE newsletter_subscribers SET confirmed = 1, token = NULL WHERE token = ?");
    $stmt->execute([$token]);
    if ($stmt->rowCount() > 0) {
        jsonResponse(['success' => true, 'message' => 'Newsletter erfolgreich bestätigt']);
    }
    jsonResponse(['success' => false, 'error' => 'Ungültiger Token'], 400);
}

if ($action === 'admin_send') {
    $auth = checkAuth();
    if (isset($auth['error'])) jsonResponse(['success' => false, 'error' => $auth['error']], $auth['code']);
    if (empty($auth['user']['is_admin'])) jsonResponse(['success' => false, 'error' => 'Admin required'], 403);
    
    $data = json_decode(file_get_contents('php://input'), true);
    $subject = $data['subject'] ?? '';
    $body = $data['body'] ?? '';
    if (!$subject || !$body) jsonResponse(['success' => false, 'error' => 'Betreff und Inhalt erforderlich'], 400);
    
    $stmt = $pdo->query("SELECT email FROM newsletter_subscribers WHERE confirmed = 1");
    $recipients = $stmt->fetchAll(PDO::FETCH_COLUMN);
    $sent = 0;
    foreach ($recipients as $email) {
        if (sendMail($email, $subject, $body, 'newsletter_broadcast')) $sent++;
    }
    jsonResponse(['success' => true, 'sent' => $sent]);
}

jsonResponse(['success' => false, 'error' => 'Invalid action'], 400);
