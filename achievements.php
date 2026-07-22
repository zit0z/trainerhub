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

$achievements = [
    ['id' => 'first_login', 'name' => 'Erster Login', 'description' => 'Melde dich zum ersten Mal an', 'icon' => 'fa-sign-in-alt'],
    ['id' => 'first_favorite', 'name' => 'Erster Favorit', 'description' => 'Favorisiere ein Spiel oder einen Trainer', 'icon' => 'fa-star'],
    ['id' => 'first_activation', 'name' => 'Erste Aktivierung', 'description' => 'Aktiviere deinen ersten Trainer', 'icon' => 'fa-bolt'],
    ['id' => 'ten_activations', 'name' => 'Aktivierungs-Profi', 'description' => 'Aktiviere 10 Trainer', 'icon' => 'fa-fire'],
    ['id' => 'premium_user', 'name' => 'Premium-Mitglied', 'description' => 'Werde Premium-Nutzer', 'icon' => 'fa-crown'],
];

$stmt = $pdo->prepare("SELECT achievement_id FROM user_achievements WHERE user_id = ?");
$stmt->execute([$user['id']]);
$unlocked = array_flip($stmt->fetchAll(PDO::FETCH_COLUMN));

foreach ($achievements as &$a) {
    $a['unlocked'] = isset($unlocked[$a['id']]) ? 1 : 0;
}

// Auto-unlock first_login if this is a real request
if (!isset($unlocked['first_login'])) {
    $stmt = $pdo->prepare("INSERT OR IGNORE INTO user_achievements (user_id, achievement_id) VALUES (?, 'first_login')");
    $stmt->execute([$user['id']]);
    foreach ($achievements as &$a) { if ($a['id'] === 'first_login') $a['unlocked'] = 1; }
}

jsonResponse(['success' => true, 'achievements' => $achievements]);
