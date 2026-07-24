<?php
require_once 'auth-lib.php';
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$status = [
    'brand' => 'SweetCheat',
    'version' => getApiVersion(),
    'database' => isDBHealthy() ? 'ok' : 'error',
    'timestamp' => time(),
    'regions' => [
        ['name' => 'EU-West', 'status' => 'operational'],
        ['name' => 'US-East', 'status' => 'operational']
    ]
];

echo json_encode($status);

function getApiVersion() {
    $vp = __DIR__ . '/version.php';
    if (!file_exists($vp)) return '0.8.3';
    $data = json_decode(file_get_contents($vp), true);
    return $data['version'] ?? '0.8.3';
}

function isDBHealthy() {
    try {
        $pdo = getDB();
        $pdo->query("SELECT 1");
        return true;
    } catch (Exception $e) {
        return false;
    }
}
