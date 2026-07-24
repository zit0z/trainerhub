<?php
require_once 'auth-lib.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');

function getDiscordWebhook() {
    $path = __DIR__ . '/config/discord.json';
    if (!file_exists($path)) return null;
    $cfg = json_decode(file_get_contents($path), true);
    return $cfg['webhook_url'] ?? null;
}

function discordNotify($title, $description, $color = 0x00f0ff, $fields = []) {
    $url = getDiscordWebhook();
    if (!$url) return false;

    $payload = [
        'embeds' => [[
            'title' => $title,
            'description' => $description,
            'color' => $color,
            'fields' => $fields,
            'timestamp' => gmdate('c'),
            'footer' => ['text' => 'SweetCheat Community']
        ]]
    ];

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 5);
    $res = curl_exec($ch);
    curl_close($ch);
    return $res !== false;
}

$action = $_GET['action'] ?? 'test';
if ($action === 'test') {
    $ok = discordNotify('SweetCheat ist live 🚀', 'Ein neuer Build wurde deployed. Probiere die aktuelle Version aus.');
    jsonResponse(['success' => (bool)$ok, 'message' => $ok ? 'Webhook versendet' : 'Webhook nicht konfiguriert']);
}
jsonResponse(['success' => false, 'error' => 'Ungültige Aktion'], 400);
