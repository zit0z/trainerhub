<?php
require_once 'auth-lib.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$auth = checkAuth();
if (isset($auth['error'])) {
    jsonResponse(['success' => false, 'error' => $auth['error']], $auth['code']);
}
$user = $auth['user'];
if (empty($user['is_admin'])) {
    jsonResponse(['success' => false, 'error' => 'Admin required'], 403);
}

$pdo = getDB();
$action = $_GET['action'] ?? 'list';

if ($action === 'csv') {
    $token = $_GET['token'] ?? getBearerToken();
    $stmt = $pdo->prepare("
        SELECT a.*, u.email, u.username
        FROM audit_log a
        LEFT JOIN users u ON u.id = a.user_id
        ORDER BY a.created_at DESC
        LIMIT 5000
    ");
    $stmt->execute();
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);

    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename=audit-log.csv');
    $out = fopen('php://output', 'w');
    fputcsv($out, ['Time', 'User ID', 'Email', 'Username', 'Action', 'Endpoint', 'IP', 'User Agent', 'Details'], ';');
    foreach ($rows as $r) {
        fputcsv($out, [
            date('Y-m-d H:i:s', $r['created_at']),
            $r['user_id'],
            $r['email'],
            $r['username'],
            $r['action'],
            $r['endpoint'],
            $r['ip'],
            $r['user_agent'],
            $r['details']
        ], ';');
    }
    fclose($out);
    exit;
}

if ($action === 'purge') {
    $pdo->exec("DELETE FROM audit_log");
    jsonResponse(['success' => true, 'message' => 'Audit-Log geleert']);
}

// Default list
$page = (int)($_GET['page'] ?? 1);
$perPage = (int)($_GET['per_page'] ?? 200);
$offset = ($page - 1) * $perPage;

$stmt = $pdo->prepare("
    SELECT a.*, u.email, u.username
    FROM audit_log a
    LEFT JOIN users u ON u.id = a.user_id
    ORDER BY a.created_at DESC
    LIMIT ? OFFSET ?
");
$stmt->execute([$perPage, $offset]);
$logs = $stmt->fetchAll(PDO::FETCH_ASSOC);

$total = (int)$pdo->query("SELECT COUNT(*) FROM audit_log")->fetchColumn();
jsonResponse(['success' => true, 'logs' => $logs, 'total' => $total]);
