<?php
header('Content-Type: application/json');
echo json_encode([
    'success' => true,
    'version' => '0.9.8',
    'brand' => 'SweetCheat Engine',
    'download_url' => 'https://sayfespace.online/trainerhub/SweetCheat-Setup.exe?v=0.9.8',
    'installer_url' => 'https://sayfespace.online/trainerhub/SweetCheat-Setup.exe?v=0.9.8'
]);
