<?php
require_once 'auth-lib.php';
header('Content-Type: application/json');
require_once 'config.php';
$pdo = getDB();
$action = $_GET['action'] ?? 'list';

try {
    if ($action === 'list') {
        $stmt = $pdo->prepare("SELECT * FROM achievements ORDER BY points");
        $stmt->execute();
        echo json_encode(['success'=>true,'achievements'=>$stmt->fetchAll(PDO::FETCH_ASSOC)]);
    } else {
        $auth = checkAuth();
        if (!empty($auth['error'])) { http_response_code(401); echo json_encode(['success'=>false,'error'=>$auth['error']]); exit; }
        $user = $auth['user'];
        if ($action === 'mine') {
            $stmt = $pdo->prepare("
                SELECT a.*, ua.unlocked_at
                FROM achievements a
                LEFT JOIN user_achievements ua ON ua.achievement_id = a.id AND ua.user_id = ?
                ORDER BY a.points
            ");
            $stmt->execute([$user['id']]);
            echo json_encode(['success'=>true,'achievements'=>$stmt->fetchAll(PDO::FETCH_ASSOC)]);
        } elseif ($action === 'check') {
            checkAndUnlockAchievements($user['id']);
            echo json_encode(['success'=>true]);
        }
    }
} catch (Exception $e) { echo json_encode(['success'=>false,'error'=>$e->getMessage()]); }

function checkAndUnlockAchievements($user_id) {
    global $pdo;
    $stmt = $pdo->prepare("SELECT * FROM achievements");
    $stmt->execute();
    $achievements = $stmt->fetchAll(PDO::FETCH_ASSOC);

    $stmt = $pdo->prepare("SELECT COUNT(*) FROM user_favorites WHERE user_id = ?");
    $stmt->execute([$user_id]);
    $favorites = $stmt->fetchColumn();

    $stmt = $pdo->prepare("SELECT COUNT(*) FROM forum_threads WHERE user_id = ?");
    $stmt->execute([$user_id]);
    $threads = $stmt->fetchColumn();

    $stmt = $pdo->prepare("SELECT COUNT(*) FROM user_challenges WHERE user_id = ? AND status = 'completed'");
    $stmt->execute([$user_id]);
    $challenges = $stmt->fetchColumn();

    $stmt = $pdo->prepare("SELECT created_at FROM users WHERE id = ?");
    $stmt->execute([$user_id]);
    $memberDays = (time() - ($stmt->fetchColumn() ?: time())) / 86400;

    foreach ($achievements as $a) {
        $unlock = false;
        switch ($a['condition_type']) {
            case 'favorite': $unlock = $favorites >= $a['condition_value']; break;
            case 'thread': $unlock = $threads >= $a['condition_value']; break;
            case 'challenges': $unlock = $challenges >= $a['condition_value']; break;
            case 'days_member': $unlock = $memberDays >= $a['condition_value']; break;
        }
        if ($unlock) {
            $stmt = $pdo->prepare("INSERT OR IGNORE INTO user_achievements (user_id, achievement_id, unlocked_at) VALUES (?, ?, ?)");
            $stmt->execute([$user_id, $a['id'], time()]);
        }
    }
}
