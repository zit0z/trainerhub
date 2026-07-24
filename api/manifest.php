<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$zipPath = '/var/www/sweetcheat/SweetCheat-windows.zip';
$files = [];

if (file_exists($zipPath)) {
    $zip = new ZipArchive();
    if ($zip->open($zipPath) === true) {
        for ($i = 0; $i < $zip->numFiles; $i++) {
            $name = $zip->getNameIndex($i);
            $stat = $zip->statIndex($i);
            if ($stat['size'] > 0) {
                // Compute SHA256 from zip entry
                $stream = $zip->getStream($name);
                $ctx = hash_init('sha256');
                while (!feof($stream)) {
                    hash_update($ctx, fread($stream, 65536));
                }
                fclose($stream);
                $files[$name] = [
                    'sha256' => hash_final($ctx),
                    'size' => $stat['size']
                ];
            }
        }
        $zip->close();
    }
}

echo json_encode([
    'success' => true,
    'version' => '0.5.3',
    'files' => $files
]);
