<?php
require_once 'auth-lib.php';
require_once 'mailer.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$action = $_GET['action'] ?? 'create';
$pdo = getDB();

if ($action === 'create') {
    $data = json_decode(file_get_contents('php://input'), true);
    $email = sanitizeEmail($data['email'] ?? '');
    $subject = $data['subject'] ?? '';
    $message = $data['message'] ?? '';
    
    if (!$email || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
        jsonResponse(['success' => false, 'error' => 'Ungültige E-Mail'], 400);
    }
    if (!$subject || !$message) {
        jsonResponse(['success' => false, 'error' => 'Betreff und Nachricht erforderlich'], 400);
    }
    
    $userId = null;
    try {
        $auth = checkAuth();
        if (!isset($auth['error'])) $userId = $auth['user']['id'];
    } catch(Exception $e) {}
    
    $stmt = $pdo->prepare("INSERT INTO support_tickets (user_id, email, subject, message) VALUES (?, ?, ?, ?)");
    $stmt->execute([$userId, $email, $subject, $message]);
    
    $adminEmail = 'admin@sayfespace.online';
    $html = "<html><body style='font-family:Inter,sans-serif;'><p>Neues Support-Ticket von {$email}:</p><p><strong>{$subject}</strong></p><p>{$message}</p></body></html>";
    sendMail($adminEmail, 'Support-Ticket: ' . $subject, $html, 'support_ticket');
    
    jsonResponse(['success' => true, 'ticket_id' => $pdo->lastInsertId()]);
}

if ($action === 'list') {
    $auth = checkAuth();
    if (isset($auth['error'])) jsonResponse(['success' => false, 'error' => $auth['error']], $auth['code']);
    $user = $auth['user'];
    if (!empty($user['is_admin'])) {
        $stmt = $pdo->query("SELECT * FROM support_tickets ORDER BY created_at DESC LIMIT 100");
    } else {
        $stmt = $pdo->prepare("SELECT * FROM support_tickets WHERE user_id = ? ORDER BY created_at DESC LIMIT 50");
        $stmt->execute([$user['id']]);
    }
    jsonResponse(['success' => true, 'tickets' => $stmt->fetchAll(PDO::FETCH_ASSOC)]);
}

if ($action === 'update') {
    $auth = checkAuth();
    if (isset($auth['error'])) jsonResponse(['success' => false, 'error' => $auth['error']], $auth['code']);
    if (empty($auth['user']['is_admin'])) jsonResponse(['success' => false, 'error' => 'Admin required'], 403);
    
    $data = json_decode(file_get_contents('php://input'), true);
    $id = (int)($data['id'] ?? 0);
    $status = $data['status'] ?? '';
    if (!$id || !in_array($status, ['open','pending','closed'])) {
        jsonResponse(['success' => false, 'error' => 'Ungültige Daten'], 400);
    }
    $stmt = $pdo->prepare("UPDATE support_tickets SET status = ?, updated_at = strftime('%s','now') WHERE id = ?");
    $stmt->execute([$status, $id]);
    jsonResponse(['success' => true]);
}

jsonResponse(['success' => false, 'error' => 'Invalid action'], 400);
