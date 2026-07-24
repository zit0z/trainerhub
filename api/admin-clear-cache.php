<?php
require_once 'auth-lib.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$auth = checkAuth();
if (isset($auth['error'])) {
    jsonResponse(['success' => false, 'error' => $auth['error']], $auth['code']);
}
if (!$auth['is_admin']) {
    jsonResponse(['success' => false, 'error' => 'Admin required'], 403);
}

$pdo = getDB();
$pdo->exec("DELETE FROM api_cache");
jsonResponse(['success' => true, 'message' => 'API cache cleared']);
