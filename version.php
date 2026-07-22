<?php
header('Content-Type: application/json');
echo json_encode([
    'success' => true,
    'version' => '0.8.2',
    'brand' => 'SweetCheat',
    'download_url' => 'https://sayfespace.online/trainerhub/SweetCheat-windows.zip',
    'installer_url' => 'https://sayfespace.online/trainerhub/SweetCheat-Setup.exe'
]);
