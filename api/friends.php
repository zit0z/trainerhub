<?php
require_once 'auth-lib.php';
header('Content-Type: application/json');
require_once 'config.php';
$auth = checkAuth();
if (!empty($auth['error'])) { http_response_code(401); echo json_encode(['success'=>false,'error'=>$auth['error']]); exit; }
$user = $auth['user'];
$pdo = getDB();
$action = $_GET['action'] ?? 'list';

try {
    switch($action) {
        case 'list':
            $stmt = $pdo->prepare("
                SELECT u.id, u.username, u.is_admin, u.reputation,
                    f1.status,
                    'outgoing' as direction
                FROM friendships f1
                JOIN users u ON u.id = f1.addressee_id
                WHERE f1.requester_id = ?
                UNION
                SELECT u.id, u.username, u.is_admin, u.reputation,
                    f2.status,
                    'incoming' as direction
                FROM friendships f2
                JOIN users u ON u.id = f2.requester_id
                WHERE f2.addressee_id = ? AND f2.status = 'pending'
            ");
            $stmt->execute([$user['id'], $user['id']]);
            echo json_encode(['success'=>true,'friends'=>$stmt->fetchAll(PDO::FETCH_ASSOC)]);
            break;
        case 'search':
            $q = trim($_GET['q'] ?? '');
            if (strlen($q) < 2) { echo json_encode(['success'=>false,'error'=>'Zu kurz']); exit; }
            $stmt = $pdo->prepare("SELECT id, username, reputation FROM users WHERE username LIKE ? AND id != ? LIMIT 10");
            $stmt->execute(["%$q%", $user['id']]);
            echo json_encode(['success'=>true,'users'=>$stmt->fetchAll(PDO::FETCH_ASSOC)]);
            break;
        case 'request':
            $input = json_decode(file_get_contents('php://input'), true) ?: [];
            $friend_id = intval($input['user_id'] ?? 0);
            if (!$friend_id || $friend_id == $user['id']) { echo json_encode(['success'=>false,'error'=>'Invalid']); exit; }
            $stmt = $pdo->prepare("INSERT OR IGNORE INTO friendships (requester_id, addressee_id, status, created_at, updated_at) VALUES (?, ?, 'pending', ?, ?)");
            $stmt->execute([$user['id'], $friend_id, time(), time()]);
            logAudit($user['id'], 'friend_request', '', "to=$friend_id");
            echo json_encode(['success'=>true]);
            break;
        case 'respond':
            $input = json_decode(file_get_contents('php://input'), true) ?: [];
            $friend_id = intval($input['user_id'] ?? 0);
            $status = in_array($input['status'] ?? '', ['accepted','rejected']) ? $input['status'] : 'rejected';
            $stmt = $pdo->prepare("UPDATE friendships SET status = ?, updated_at = ? WHERE requester_id = ? AND addressee_id = ?");
            $stmt->execute([$status, time(), $friend_id, $user['id']]);
            if ($status === 'accepted') {
                $stmt = $pdo->prepare("UPDATE users SET reputation = reputation + 5 WHERE id IN (?, ?)");
                $stmt->execute([$user['id'], $friend_id]);
            }
            echo json_encode(['success'=>true]);
            break;
        case 'remove':
            $friend_id = intval($_GET['user_id'] ?? 0);
            $stmt = $pdo->prepare("DELETE FROM friendships WHERE (requester_id = ? AND addressee_id = ?) OR (requester_id = ? AND addressee_id = ?)");
            $stmt->execute([$user['id'], $friend_id, $friend_id, $user['id']]);
            echo json_encode(['success'=>true]);
            break;
        default:
            echo json_encode(['success'=>false,'error'=>'Unknown']);
    }
} catch (Exception $e) { echo json_encode(['success'=>false,'error'=>$e->getMessage()]); }
