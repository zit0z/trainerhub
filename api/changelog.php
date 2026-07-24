<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$versions = [
    '0.8.4' => 'Desktop: Auto-Updater, In-App-Changelog, System-Tray, Hotkeys, Prozess-Watcher. Web: Discord-Webhook, Status-Seite, Admin-Mass-Mail, 2FA, Landingpage v2 mit Video-Hero.',
    '0.8.3' => 'Hotfix: Logger-Import-Fehler in der EXE behoben.',
    '0.8.2' => 'Newsletter, Support-Widget, Blog, Game-Detail, User-Settings, Desktop-Sync.',
    '0.8.1' => 'Rebrand TrainerHub → SweetCheat.',
    '0.8.0' => 'Initiales SweetCheat-Release.',
];

$ver = '0.8.4';
$vf = __DIR__ . '/version.php';
if (file_exists($vf)) {
    $content = file_get_contents($vf);
    if (preg_match('/[\'\"](version)[\'\"]\s*\=\s*[\'\"]([0-9.]+)[\'\"]/', $content, $m)) {
        $ver = $m[2];
    }
}

echo json_encode([
    'version' => $ver,
    'title' => 'SweetCheat v' . $ver,
    'body' => $versions[$ver] ?? 'Verbesserungen und Bugfixes.',
    'history' => $versions
], JSON_PRETTY_PRINT);
