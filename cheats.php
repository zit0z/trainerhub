<?php
require_once 'auth-lib.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$auth = checkAuth();
if (isset($auth['error'])) {
    jsonResponse(['success' => false, 'error' => $auth['error']], $auth['code']);
}
$user = $auth['user'];
$pdo = getDB();
$game = $_GET['game'] ?? '';
if (!$game) {
    jsonResponse(['success' => false, 'error' => 'game slug required'], 400);
}

$stmt = $pdo->prepare("SELECT c.*, g.name as game_name, g.process_name FROM game_cheats c JOIN games g ON g.id = c.game_id WHERE g.slug = ? AND c.is_active = 1 ORDER BY c.is_premium, c.created_at");
$stmt->execute([$game]);
$cheats = $stmt->fetchAll(PDO::FETCH_ASSOC);
jsonResponse(['success' => true, 'game' => $game, 'cheats' => $cheats]);
