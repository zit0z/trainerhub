<?php
require_once 'auth-lib.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$action = $_GET['action'] ?? 'public';
$pdo = getDB();

if ($action === 'public') {
    $id_or_name = $_GET['user'] ?? '';
    $stmt = $pdo->prepare("
        SELECT u.id, u.username, u.email, u.reputation, u.created_at,
               (SELECT COUNT(*) FROM trainer_logs WHERE user_id = u.id) as activations,
               (SELECT COUNT(*) FROM user_favorites WHERE user_id = u.id) as favorites,
               (SELECT COUNT(*) FROM followers WHERE following_id = u.id) as followers,
               (SELECT COUNT(*) FROM followers WHERE follower_id = u.id) as following
        FROM users u
        WHERE u.id = ? OR u.username = ? OR u.email = ?
    ");
    $stmt->execute([is_numeric($id_or_name) ? $id_or_name : 0, $id_or_name, $id_or_name]);
    $user = $stmt->fetch(PDO::FETCH_ASSOC);
    if (!$user) {
        jsonResponse(['success' => false, 'error' => 'Profil nicht gefunden'], 404);
    }
    unset($user['email']);
    jsonResponse(['success' => true, 'profile' => $user]);
}

if ($action === 'leaderboard') {
    $stmt = $pdo->query("
        SELECT id, username, reputation,
               (SELECT COUNT(*) FROM trainer_logs WHERE user_id = u.id) as activations
        FROM users u
        ORDER BY reputation DESC
        LIMIT 20
    ");
    jsonResponse(['success' => true, 'profiles' => $stmt->fetchAll(PDO::FETCH_ASSOC)]);
}

$auth = checkAuth();
if (isset($auth['error'])) jsonResponse(['success' => false, 'error' => $auth['error']], $auth['code']);
$user = $auth['user'];

if ($action === 'follow') {
    $target = (int)($_GET['user_id'] ?? 0);
    if ($target === $user['id']) {
        jsonResponse(['success' => false, 'error' => 'Du kannst dir nicht selbst folgen'], 400);
    }
    try {
        $pdo->prepare("INSERT OR IGNORE INTO followers (follower_id, following_id) VALUES (?, ?)")->execute([$user['id'], $target]);
        jsonResponse(['success' => true, 'message' => 'Folge jetzt']);
    } catch (PDOException $e) {
        jsonResponse(['success' => false, 'error' => 'Bereits folgend'], 400);
    }
}

if ($action === 'unfollow') {
    $target = (int)($_GET['user_id'] ?? 0);
    $pdo->prepare("DELETE FROM followers WHERE follower_id = ? AND following_id = ?")->execute([$user['id'], $target]);
    jsonResponse(['success' => true, 'message' => 'Entfolgt']);
}

if ($action === 'following') {
    $stmt = $pdo->prepare("
        SELECT u.id, u.username, u.reputation
        FROM followers f
        JOIN users u ON u.id = f.following_id
        WHERE f.follower_id = ?
    ");
    $stmt->execute([$user['id']]);
    jsonResponse(['success' => true, 'following' => $stmt->fetchAll(PDO::FETCH_ASSOC)]);
}

jsonResponse(['success' => false, 'error' => 'Ungültige Aktion'], 400);
