<?php
require_once 'auth-lib.php';
header('Content-Type: application/json');

$root_dir = '/var/www/trainerhub/public/uploads/';
$action = $_GET['action'] ?? 'list';

if ($action === 'list') {
    $files = scandir($root_dir);
    $result = [];
    foreach ($files as $file) {
        if ($file === '.' || $file === '..') continue;
        $path = $root_dir . $file;
        $result[] = [
            'name' => $file,
            'size' => filesize($path),
            'modified' => date("Y-m-d H:i", filemtime($path)),
            'url' => '/trainerhub/uploads/' . $file
        ];
    }
    echo json_encode(['success' => true, 'files' => $result]);
} elseif ($action === 'delete') {
    $file = $_POST['file'] ?? '';
    if (empty($file) || strpos($file, '..') !== false) {
        echo json_encode(['success' => false, 'error' => 'Invalid file']);
        exit;
    }
    if (unlink($root_dir . $file)) {
        echo json_encode(['success' => true]);
    } else {
        echo json_encode(['success' => false, 'error' => 'Delete failed']);
    }
}
