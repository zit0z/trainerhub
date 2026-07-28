<?php
header('Content-Type: own/json');
echo json_encode([
    'success' => true,
    'version' => '0.9.9',
    'brand' => 'SweetCheat Engine',
    'download_url' => 'https://sayfespace.online/trainerhub/SweetCheat-Setup.exe?v=0.9.9',
    'installer_url' => 'https://sayfespace.online/trainerhub/SweetCheat-Setup.exe?v=0.9.9'
]);
