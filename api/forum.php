<?php
require_once 'auth-lib.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Authorization, Content-Type');
header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

require_once 'config.php';

$token = getBearerToken();
$user = null;
$isAdmin = false;
if ($token) {
    $auth = checkAuth();
    if (empty($auth['error'])) {
        $user = $auth['user'];
        $isAdmin = !empty($user['is_admin']);
    }
}

$pdo = getDB();
$action = $_GET['action'] ?? 'categories';

try {
    switch ($action) {
        case 'categories':
            $stmt = $pdo->query("SELECT c.*, COUNT(DISTINCT t.id) as thread_count, COUNT(p.id) as post_count FROM forum_categories c LEFT JOIN forum_threads t ON t.category_id = c.id LEFT JOIN forum_posts p ON p.thread_id = t.id GROUP BY c.id ORDER BY c.sort_order");
            echo json_encode(['success' => true, 'categories' => $stmt->fetchAll(PDO::FETCH_ASSOC)]);
            break;

        case 'threads':
            $category_id = intval($_GET['category_id'] ?? 0);
            $page = max(1, intval($_GET['page'] ?? 1));
            $per_page = 20;
            $offset = ($page - 1) * $per_page;
            $stmt = $pdo->prepare("SELECT t.*, u.username, u.is_admin, (SELECT COUNT(*) FROM forum_posts WHERE thread_id = t.id) - 1 as reply_count, (SELECT MAX(created_at) FROM forum_posts WHERE thread_id = t.id) as last_post_at, (SELECT u2.username FROM forum_posts p2 JOIN users u2 ON u2.id = p2.user_id WHERE p2.thread_id = t.id ORDER BY p2.created_at DESC LIMIT 1) as last_poster FROM forum_threads t JOIN users u ON u.id = t.user_id WHERE t.category_id = ? ORDER BY t.is_pinned DESC, t.updated_at DESC LIMIT ? OFFSET ?");
            $stmt->execute([$category_id, $per_page, $offset]);
            echo json_encode(['success' => true, 'threads' => $stmt->fetchAll(PDO::FETCH_ASSOC)]);
            break;

        case 'thread':
            $thread_id = intval($_GET['thread_id'] ?? 0);
            $stmt = $pdo->prepare("UPDATE forum_threads SET view_count = view_count + 1 WHERE id = ?");
            $stmt->execute([$thread_id]);
            $stmt = $pdo->prepare("SELECT t.*, c.name as category_name, c.slug as category_slug, u.username as author FROM forum_threads t JOIN users u ON u.id = t.user_id JOIN forum_categories c ON c.id = t.category_id WHERE t.id = ?");
            $stmt->execute([$thread_id]);
            $thread = $stmt->fetch(PDO::FETCH_ASSOC);
            if (!$thread) {
                echo json_encode(['success' => false, 'error' => 'Thread not found']);
                exit;
            }
            $stmt = $pdo->prepare("SELECT p.*, u.username, u.is_admin, COUNT(r.id) as like_count, (SELECT reaction FROM forum_reactions WHERE post_id = p.id AND user_id = ? LIMIT 1) as user_reaction FROM forum_posts p JOIN users u ON u.id = p.user_id LEFT JOIN forum_reactions r ON r.post_id = p.id WHERE p.thread_id = ? GROUP BY p.id ORDER BY p.created_at");
            $stmt->execute([$user ? $user['id'] : 0, $thread_id]);
            $posts = $stmt->fetchAll(PDO::FETCH_ASSOC);
            echo json_encode(['success' => true, 'thread' => $thread, 'posts' => $posts, 'is_admin' => $isAdmin]);
            break;

        case 'create_thread':
            requireAuthOrFail($user);
            $input = json_decode(file_get_contents('php://input'), true) ?: [];
            $category_id = intval($input['category_id'] ?? 0);
            $title = trim($input['title'] ?? '');
            $content = trim($input['content'] ?? '');
            if (!$category_id || !$title || !$content) {
                echo json_encode(['success' => false, 'error' => 'category_id, title and content required']);
                exit;
            }
            $slug = preg_replace('/[^a-z0-9-]+/', '-', strtolower($title));
            $slug = trim($slug, '-') . '-' . substr(md5(uniqid()), 0, 6);
            $now = time();
            $stmt = $pdo->prepare("INSERT INTO forum_threads (category_id, user_id, title, slug, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)");
            $stmt->execute([$category_id, $user['id'], $title, $slug, $now, $now]);
            $thread_id = $pdo->lastInsertId();
            $stmt = $pdo->prepare("INSERT INTO forum_posts (thread_id, user_id, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?)");
            $stmt->execute([$thread_id, $user['id'], $content, $now, $now]);
            $stmt = $pdo->prepare("INSERT OR IGNORE INTO forum_subscriptions (user_id, thread_id, created_at) VALUES (?, ?, ?)");
            $stmt->execute([$user['id'], $thread_id, $now]);
            logAudit($user['id'], 'forum_create_thread', $_SERVER['REMOTE_ADDR'] ?? '', "thread_id=$thread_id");
            echo json_encode(['success' => true, 'thread_id' => $thread_id, 'slug' => $slug]);
            break;

        case 'create_post':
            requireAuthOrFail($user);
            $input = json_decode(file_get_contents('php://input'), true) ?: [];
            $thread_id = intval($input['thread_id'] ?? 0);
            $content = trim($input['content'] ?? '');
            if (!$thread_id || !$content) {
                echo json_encode(['success' => false, 'error' => 'thread_id and content required']);
                exit;
            }
            $stmt = $pdo->prepare("SELECT is_locked FROM forum_threads WHERE id = ?");
            $stmt->execute([$thread_id]);
            $locked = $stmt->fetchColumn();
            if ($locked && !$isAdmin) {
                echo json_encode(['success' => false, 'error' => 'Thread is locked']);
                exit;
            }
            $now = time();
            $stmt = $pdo->prepare("INSERT INTO forum_posts (thread_id, user_id, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?)");
            $stmt->execute([$thread_id, $user['id'], $content, $now, $now]);
            $stmt = $pdo->prepare("INSERT OR IGNORE INTO forum_subscriptions (user_id, thread_id, created_at) VALUES (?, ?, ?)");
            $stmt->execute([$user['id'], $thread_id, $now]);
            $stmt = $pdo->prepare("UPDATE forum_threads SET updated_at = ? WHERE id = ?");
            $stmt->execute([$now, $thread_id]);

            // Notify subscribers
            $stmt = $pdo->prepare("SELECT DISTINCT user_id FROM forum_subscriptions WHERE thread_id = ? AND user_id != ?");
            $stmt->execute([$thread_id, $user['id']]);
            $subs = $stmt->fetchAll(PDO::FETCH_COLUMN);
            if ($subs) {
                $msg = 'Neue Antwort im Thema: ' . $thread_title;
                $stmt = $pdo->prepare("INSERT INTO inbox_messages (user_id, type, title, body, link, is_read, created_at) VALUES (?, 'forum_reply', ?, ?, ?, 0, ?)");
                foreach ($subs as $uid) {
                    $stmt->execute([$uid, 'Forum-Antwort', $msg, '/trainerhub/forum', $now]);
                }
            }

            logAudit($user['id'], 'forum_create_post', $_SERVER['REMOTE_ADDR'] ?? '', "thread_id=$thread_id");
            echo json_encode(['success' => true, 'post_id' => $pdo->lastInsertId()]);
            break;

        case 'react':
            requireAuthOrFail($user);
            $input = json_decode(file_get_contents('php://input'), true) ?: [];
            $post_id = intval($input['post_id'] ?? 0);
            $reaction = $input['reaction'] ?? 'like';
            if (!$post_id) {
                echo json_encode(['success' => false, 'error' => 'post_id required']);
                exit;
            }
            $stmt = $pdo->prepare("DELETE FROM forum_reactions WHERE post_id = ? AND user_id = ?");
            $stmt->execute([$post_id, $user['id']]);
            $stmt = $pdo->prepare("INSERT INTO forum_reactions (post_id, user_id, reaction, created_at) VALUES (?, ?, ?, ?)");
            $stmt->execute([$post_id, $user['id'], $reaction, time()]);
            echo json_encode(['success' => true]);
            break;

        case 'moderate':
            requireAuthOrFail($user);
            if (!$isAdmin) {
                echo json_encode(['success' => false, 'error' => 'Admin only']);
                exit;
            }
            $input = json_decode(file_get_contents('php://input'), true) ?: [];
            $thread_id = intval($input['thread_id'] ?? 0);
            $field = in_array($input['field'] ?? '', ['is_pinned', 'is_locked']) ? $input['field'] : null;
            $value = intval($input['value'] ?? 0);
            if (!$thread_id || !$field) {
                echo json_encode(['success' => false, 'error' => 'Invalid']);
                exit;
            }
            $stmt = $pdo->prepare("UPDATE forum_threads SET $field = ? WHERE id = ?");
            $stmt->execute([$value, $thread_id]);
            echo json_encode(['success' => true]);
            break;

        default:
            echo json_encode(['success' => false, 'error' => 'Unknown action']);
    }
} catch (Exception $e) {
    echo json_encode(['success' => false, 'error' => $e->getMessage()]);
}

function requireAuthOrFail($user) {
    if (!$user) {
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'Login required']);
        exit;
    }
    if (empty($user['email_verified'])) {
        http_response_code(403);
        echo json_encode(['success' => false, 'error' => 'E-Mail not verified']);
        exit;
    }
}
