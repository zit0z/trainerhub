<?php
header('Content-Type: application/json');
echo json_encode([
    'success' => true,
    'version' => '0.9.14',
    'brand' => 'SweetCheat Engine',
    'download_url' => 'https://sayfespace.online/trainerhub/SweetCheat-windows.zip?v=0.9.14',
    'installer_url' => 'https://sayfespace.online/trainerhub/SweetCheat-v0914.exe'
]);
