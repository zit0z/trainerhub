<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$versions = [
    [
        'version' => '0.5.0',
        'date' => '2026-07-21',
        'title' => 'Das Mega-Update',
        'changes' => [
            'In-App Changelog beim Start',
            'SMAPI Live-Werte-Anzeige für Stardew Valley',
            'Trainer-Verlauf mit Diagramm im Dashboard',
            'Multi-Game Freeze-Manager',
            'Cloud-Sync für Favoriten',
            'Neues Midnight & Neon Theme',
            'Globale Hotkeys (F9 Prozess prüfen)',
            'Game Launcher im Settings-Menü'
        ]
    ],
    [
        'version' => '0.4.1',
        'date' => '2026-07-21',
        'title' => 'Settings & Hotkeys',
        'changes' => [
            'Einstellungen-Menü hinzugefügt',
            'Theme-Switcher (Dark, Midnight, Neon)',
            'Globale Hotkeys für Windows',
            'Game Launcher im Settings',
            'Trainer-Aktivierungs-Logging'
        ]
    ],
    [
        'version' => '0.4.0',
        'date' => '2026-07-21',
        'title' => 'Premium UI Redesign',
        'changes' => [
            'Modernes Dark UI mit Gradienten',
            'Dashboard mit Statistik-Karten',
            'Favoriten und zuletzt verwendete Spiele',
            'Pattern Learner für selbst gefundene Adressen',
            'Verbesserter Memory-Scanner'
        ]
    ]
];

echo json_encode(['success' => true, 'versions' => $versions]);
