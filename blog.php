<?php
require_once 'auth-lib.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$action = $_GET['action'] ?? 'list';
$pdo = getDB();

if ($action === 'list') {
    $page = (int)($_GET['page'] ?? 1);
    $perPage = (int)($_GET['per_page'] ?? 10);
    $offset = ($page - 1) * $perPage;
    $stmt = $pdo->prepare("SELECT * FROM blog_posts WHERE published = 1 ORDER BY created_at DESC LIMIT ? OFFSET ?");
    $stmt->execute([$perPage, $offset]);
    jsonResponse(['success' => true, 'posts' => $stmt->fetchAll(PDO::FETCH_ASSOC)]);
}

if ($action === 'get') {
    $slug = $_GET['slug'] ?? '';
    $stmt = $pdo->prepare("SELECT * FROM blog_posts WHERE slug = ? AND published = 1 LIMIT 1");
    $stmt->execute([$slug]);
    $post = $stmt->fetch(PDO::FETCH_ASSOC);
    if (!$post) {
        jsonResponse(['success' => false, 'error' => 'Post nicht gefunden'], 404);
    }
    jsonResponse(['success' => true, 'post' => $post]);
}

if ($action === 'admin_list' || $action === 'create' || $action === 'update' || $action === 'delete') {
    $auth = checkAuth();
    if (isset($auth['error'])) jsonResponse(['success' => false, 'error' => $auth['error']], $auth['code']);
    if (empty($auth['user']['is_admin'])) jsonResponse(['success' => false, 'error' => 'Admin required'], 403);
    
    if ($action === 'admin_list') {
        $stmt = $pdo->query("SELECT * FROM blog_posts ORDER BY created_at DESC");
        jsonResponse(['success' => true, 'posts' => $stmt->fetchAll(PDO::FETCH_ASSOC)]);
    }
    
    if ($action === 'create') {
        $data = json_decode(file_get_contents('php://input'), true);
        $stmt = $pdo->prepare("
            INSERT INTO blog_posts (slug, title, excerpt, content, author, tags, published, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, strftime('%s','now'), strftime('%s','now'))
        ");
        $stmt->execute([
            $data['slug'] ?? '',
            $data['title'] ?? '',
            $data['excerpt'] ?? '',
            $data['content'] ?? '',
            $data['author'] ?? '',
            $data['tags'] ?? '',
            isset($data['published']) ? (int)$data['published'] : 1
        ]);
        jsonResponse(['success' => true, 'id' => $pdo->lastInsertId()]);
    }
    
    if ($action === 'update') {
        $data = json_decode(file_get_contents('php://input'), true);
        $id = (int)($data['id'] ?? 0);
        $stmt = $pdo->prepare("
            UPDATE blog_posts SET slug=?, title=?, excerpt=?, content=?, author=?, tags=?, published=?, updated_at=strftime('%s','now') WHERE id=?
        ");
        $stmt->execute([
            $data['slug'] ?? '',
            $data['title'] ?? '',
            $data['excerpt'] ?? '',
            $data['content'] ?? '',
            $data['author'] ?? '',
            $data['tags'] ?? '',
            isset($data['published']) ? (int)$data['published'] : 1,
            $id
        ]);
        jsonResponse(['success' => true]);
    }
    
    if ($action === 'delete') {
        $data = json_decode(file_get_contents('php://input'), true);
        $id = (int)($data['id'] ?? 0);
        $pdo->prepare("DELETE FROM blog_posts WHERE id = ?")->execute([$id]);
        jsonResponse(['success' => true]);
    }
}

jsonResponse(['success' => false, 'error' => 'Invalid action'], 400);
