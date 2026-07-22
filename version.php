<?php
header('Content-Type: application/json');
echo json_encode([
    'success' => true,
    'version' => '0.6.9',
    'download_url' => 'https://sayfespace.online/trainerhub/TrainerHub-windows.zip',
    'installer_url' => 'https://sayfespace.online/trainerhub/TrainerHub-Setup.exe',
    'changelog_url' => 'https://sayfespace.online/trainerhub/api/changelog.php',
    'manifest_url' => 'https://sayfespace.online/trainerhub/api/manifest.php'
]);
