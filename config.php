<?php
/**
 * SweetCheat Centralized Config Loader
 */

function loadEnvConfig() {
    static $config = null;
    if ($config !== null) return $config;

    $envFile = __DIR__ . '/config/.env';
    if (file_exists($envFile)) {
        $lines = file($envFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
        foreach ($lines as $line) {
            if (strpos($line, '=') === false || strpos($line, '#') === 0) continue;
            list($key, $value) = array_map('trim', explode('=', $line, 2));
            if (!isset($_ENV[$key])) {
                $_ENV[$key] = trim($value, '\'"');
            }
        }
    }

    $config = array(
        'app_name'    => $_ENV['APP_NAME']    ?? 'SweetCheat',
        'app_url'     => $_ENV['APP_URL']     ?? 'https://sayfespace.online',
        'admin_email' => $_ENV['ADMIN_EMAIL'] ?? 'admin@sayfespace.online',
        'admin_pass'  => $_ENV['ADMIN_PASSWORD'] ?? 'sayfehub2026',
        'db_path'     => $_ENV['DB_PATH']     ?? __DIR__ . '/../database/sweetcheat.db',
        'jwt_secret'  => $_ENV['JWT_SECRET']  ?? bin2hex(random_bytes(32)),
        'stripe' => array(
            'secret_key'     => $_ENV['STRIPE_SECRET_KEY'] ?? '',
            'price_id'       => $_ENV['STRIPE_PRICE_ID']   ?? '',
            'webhook_secret' => $_ENV['STRIPE_WEBHOOK_SECRET'] ?? '',
        ),
        'mail' => array(
            'from'     => $_ENV['MAIL_FROM']     ?? 'SweetCheat <noreply@sayfespace.online>',
            'reply_to' => $_ENV['MAIL_REPLY_TO'] ?? 'SweetCheat <noreply@sayfespace.online>',
        ),
        'security' => array(
            'rate_limit'   => (int)($_ENV['RATE_LIMIT']  ?? 100),
            'rate_window'  => (int)($_ENV['RATE_WINDOW'] ?? 60),
            'password_min' => (int)($_ENV['PASSWORD_MIN'] ?? 8),
            'session_ttl'  => (int)($_ENV['SESSION_TTL'] ?? 86400 * 30),
        )
    );
    return $config;
}

function env($key, $default = null) {
    $cfg = loadEnvConfig();
    $parts = explode('.', $key);
    $val = $cfg;
    foreach ($parts as $p) {
        if (!isset($val[$p])) return $default;
        $val = $val[$p];
    }
    return $val;
}
