<?php
require_once __DIR__ . '/auth-lib.php';
// auth-lib.php exposes getDB()
header('Content-Type: application/json');
header('Cache-Control: public, max-age=300');

$slug = $_GET['game'] ?? null;
$search = $_GET['search'] ?? null;
$genre = $_GET['genre'] ?? null;
$page = max(1, intval($_GET['page'] ?? 1));
$per_page = min(100, max(10, intval($_GET['per_page'] ?? 60)));

try {
    $pdo = getDB();
    $params = [];
    $where = ['is_active = 1'];
    
    if ($slug) {
        $where[] = 'slug = ?';
        $params[] = $slug;
    }
    if ($search) {
        $where[] = '(name LIKE ? OR tags LIKE ?)';
        $params[] = "%$search%";
        $params[] = "%$search%";
    }
    if ($genre) {
        $where[] = '(genre LIKE ? OR tags LIKE ?)';
        $params[] = "%$genre%";
        $params[] = "%$genre%";
    }
    
    $where_sql = implode(' AND ', $where);
    
    // Count total
    $count_stmt = $pdo->prepare("SELECT COUNT(*) FROM games WHERE $where_sql");
    $count_stmt->execute($params);
    $total = (int)$count_stmt->fetchColumn();
    
    // Fetch paginated games
    $offset = ($page - 1) * $per_page;
    $sql = "SELECT g.id, g.name, g.slug, g.genre, g.release_year, g.tags, g.popularity_score, g.process_name,
                   (SELECT COUNT(*) FROM trainers t WHERE t.game_id = g.id AND t.is_active = 1) as trainer_count
            FROM games g WHERE $where_sql 
            ORDER BY g.popularity_score DESC, g.name ASC 
            LIMIT $per_page OFFSET $offset";
    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    $games = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    echo json_encode([
        'success' => true,
        'games' => $games,
        'page' => $page,
        'per_page' => $per_page,
        'total' => $total,
        'pages' => ceil($total / $per_page)
    ], JSON_PARTIAL_OUTPUT_ON_ERROR);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => $e->getMessage()]);
}
