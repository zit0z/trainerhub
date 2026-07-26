<?php
require_once 'auth-lib.php';
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

$auth = checkAuth();
if (isset($auth['error'])) {
    jsonResponse(['success' => false, 'error' => $auth['error']], $auth['code']);
}
$user = $auth['user'];
if (empty($user['is_admin'])) {
    jsonResponse(['success' => false, 'error' => 'Admin erforderlich'], 403);
}

$pdo = getDB();
$action = $_GET['action'] ?? 'dashboard';
$method = $_SERVER['REQUEST_METHOD'];

function audit($pdo, $email, $action, $target, $details = '') {
    $stmt = $pdo->prepare("INSERT INTO admin_audit (admin_email, action, target, details) VALUES (?,?,?,?)");
    $stmt->execute([$email, $action, $target, $details]);
}

function editable($pdo, $section, $content = null) {
    if ($content !== null) {
        $stmt = $pdo->prepare("INSERT INTO admin_editable (section, content) VALUES (?,?) ON CONFLICT(section) DO UPDATE SET content=excluded.content, updated_at=CURRENT_TIMESTAMP");
        $stmt->execute([$section, $content]);
    }
    $stmt = $pdo->prepare("SELECT content FROM admin_editable WHERE section=?");
    $stmt->execute([$section]);
    $row = $stmt->fetch(PDO::FETCH_ASSOC);
    return $row ? $row['content'] : '';
}

function setting($pdo, $key, $value = null) {
    if ($value !== null) {
        $stmt = $pdo->prepare("INSERT INTO site_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP");
        $stmt->execute([$key, $value]);
    }
    $stmt = $pdo->prepare("SELECT value FROM site_settings WHERE key=?");
    $stmt->execute([$key]);
    $row = $stmt->fetch(PDO::FETCH_ASSOC);
    return $row ? $row['value'] : '';
}

// GET endpoints
if ($method === 'GET') {
    switch ($action) {
        case 'dashboard':
            $stats = [
                'users' => $pdo->query("SELECT COUNT(*) FROM users")->fetchColumn(),
                'games' => $pdo->query("SELECT COUNT(*) FROM games")->fetchColumn(),
                'trainers' => $pdo->query("SELECT COUNT(*) FROM trainers")->fetchColumn(),
                'forum_threads' => $pdo->query("SELECT COUNT(*) FROM forum_threads")->fetchColumn(),
                'revenue' => 0,
            ];
            jsonResponse(['success' => true, 'stats' => $stats, 'admin' => $user]);
            break;

        case 'tables':
            $tables = $pdo->query("SELECT name FROM sqlite_master WHERE type='table'")->fetchAll(PDO::FETCH_COLUMN);
            jsonResponse(['success' => true, 'tables' => $tables]);
            break;

        case 'table':
            $table = $_GET['table'] ?? '';
            if (!preg_match('/^[a-z0-9_]+$/i', $table)) jsonResponse(['success' => false, 'error' => 'Invalid table'], 400);
            $limit = min((int)($_GET['limit'] ?? 50), 200);
            $offset = (int)($_GET['offset'] ?? 0);
            $rows = $pdo->query("SELECT * FROM $table LIMIT $limit OFFSET $offset")->fetchAll(PDO::FETCH_ASSOC);
            $cols = $pdo->query("PRAGMA table_info($table)")->fetchAll(PDO::FETCH_ASSOC);
            $total = $pdo->query("SELECT COUNT(*) FROM $table")->fetchColumn();
            jsonResponse(['success' => true, 'table' => $table, 'columns' => $cols, 'rows' => $rows, 'total' => $total]);
            break;

        case 'users':
            $rows = $pdo->query("SELECT id, email, username, is_admin, role, subscription, created_at FROM users ORDER BY id DESC")->fetchAll(PDO::FETCH_ASSOC);
            jsonResponse(['success' => true, 'users' => $rows]);
            break;

        case 'games':
            $rows = $pdo->query("SELECT id, name, slug, genre, platform, is_active, trainer_count, metadata FROM games ORDER BY id DESC")->fetchAll(PDO::FETCH_ASSOC);
            jsonResponse(['success' => true, 'games' => $rows]);
            break;

        case 'trainers':
            $game = $_GET['game_id'] ?? null;
            if ($game) {
                $stmt = $pdo->prepare("SELECT * FROM trainers WHERE game_id=? ORDER BY id DESC");
                $stmt->execute([$game]);
            } else {
                $stmt = $pdo->query("SELECT t.*, g.name as game_name FROM trainers t JOIN games g ON g.id=t.game_id ORDER BY t.id DESC");
            }
            jsonResponse(['success' => true, 'trainers' => $stmt->fetchAll(PDO::FETCH_ASSOC)]);
            break;

        case 'editable':
            $section = $_GET['section'] ?? 'home_hero';
            jsonResponse(['success' => true, 'section' => $section, 'content' => editable($pdo, $section)]);
            break;

        case 'settings':
            $stmt = $pdo->query("SELECT * FROM site_settings");
            $settings = [];
            foreach ($stmt->fetchAll(PDO::FETCH_ASSOC) as $row) $settings[$row['key']] = $row['value'];
            jsonResponse(['success' => true, 'settings' => $settings]);
            break;

        case 'audit':
            $rows = $pdo->query("SELECT * FROM admin_audit ORDER BY id DESC LIMIT 100")->fetchAll(PDO::FETCH_ASSOC);
            jsonResponse(['success' => true, 'audit' => $rows]);
            break;

        default:
            jsonResponse(['success' => false, 'error' => 'Unknown action'], 400);
    }
}

// POST / PUT / DELETE
if ($method === 'POST' || $method === 'PUT' || $method === 'DELETE') {
    $input = json_decode(file_get_contents('php://input'), true) ?: $_POST;
    switch ($action) {
        case 'table_row':
            $table = $input['table'] ?? '';
            if (!preg_match('/^[a-z0-9_]+$/i', $table)) jsonResponse(['success' => false, 'error' => 'Invalid table'], 400);
            if ($method === 'DELETE') {
                $id = $input['id'] ?? null;
                $pk = $input['pk'] ?? 'id';
                $stmt = $pdo->prepare("DELETE FROM $table WHERE $pk=?");
                $stmt->execute([$id]);
                audit($pdo, $user['email'], 'delete_row', "$table.$id", '');
                jsonResponse(['success' => true]);
            }
            $data = $input['data'] ?? [];
            $pk = $input['pk'] ?? 'id';
            if (empty($data[$pk])) {
                // insert
                $cols = array_keys($data);
                $vals = array_values($data);
                $placeholders = implode(',', array_fill(0, count($cols), '?'));
                $stmt = $pdo->prepare("INSERT INTO $table (" . implode(',', $cols) . ") VALUES ($placeholders)");
                $stmt->execute($vals);
                audit($pdo, $user['email'], 'insert_row', $table, json_encode($data));
                jsonResponse(['success' => true, 'id' => $pdo->lastInsertId()]);
            } else {
                // update
                $id = $data[$pk];
                unset($data[$pk]);
                $sets = [];
                $vals = [];
                foreach ($data as $k => $v) { $sets[] = "$k=?"; $vals[] = $v; }
                $vals[] = $id;
                $stmt = $pdo->prepare("UPDATE $table SET " . implode(',', $sets) . " WHERE $pk=?");
                $stmt->execute($vals);
                audit($pdo, $user['email'], 'update_row', "$table.$id", json_encode($data));
                jsonResponse(['success' => true]);
            }
            break;

        case 'editable':
            $section = $input['section'] ?? 'home_hero';
            $content = $input['content'] ?? '';
            editable($pdo, $section, $content);
            audit($pdo, $user['email'], 'editable', $section, substr($content, 0, 200));
            jsonResponse(['success' => true]);
            break;

        case 'settings':
            foreach (($input['settings'] ?? []) as $k => $v) {
                setting($pdo, $k, $v);
            }
            audit($pdo, $user['email'], 'settings', 'site', json_encode($input['settings'] ?? []));
            jsonResponse(['success' => true]);
            break;

        case 'make_admin':
            $id = $input['user_id'] ?? null;
            $role = $input['role'] ?? 'admin';
            $stmt = $pdo->prepare("UPDATE users SET is_admin=1, role=? WHERE id=?");
            $stmt->execute([$role, $id]);
            audit($pdo, $user['email'], 'make_admin', "user.$id", $role);
            jsonResponse(['success' => true]);
            break;

        case 'upload':
            if (empty($_FILES['file'])) jsonResponse(['success' => false, 'error' => 'No file'], 400);
            $dir = $input['dir'] ?? 'uploads';
            $target = "/var/www/trainerhub/public/$dir/";
            if (!is_dir($target)) mkdir($target, 0775, true);
            $name = preg_replace('/[^a-z0-9._-]/i', '_', $_FILES['file']['name']);
            move_uploaded_file($_FILES['file']['tmp_name'], $target . $name);
            audit($pdo, $user['email'], 'upload', "$dir/$name", '');
            jsonResponse(['success' => true, 'url' => "/trainerhub/$dir/$name"]);
            break;

        default:
            jsonResponse(['success' => false, 'error' => 'Unknown action'], 400);
    }
}

jsonResponse(['success' => false, 'error' => 'Method not allowed'], 405);
