CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    username TEXT,
    password_hash TEXT,
    twitch_id TEXT,
    avatar TEXT,
    subscription_status TEXT DEFAULT 'free',
    subscription_expires_at INTEGER,
    created_at INTEGER DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    provider TEXT,
    provider_subscription_id TEXT,
    status TEXT,
    plan TEXT,
    amount REAL,
    currency TEXT,
    starts_at INTEGER,
    ends_at INTEGER,
    created_at INTEGER DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    platform TEXT,
    process_name TEXT,
    cover_url TEXT,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS trainers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    cheat_type TEXT,
    is_premium INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    version TEXT,
    created_at INTEGER DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    api_key TEXT UNIQUE NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at INTEGER DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS trainer_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    trainer_id INTEGER NOT NULL,
    action TEXT,
    ip TEXT,
    created_at INTEGER DEFAULT (strftime('%s','now'))
);

-- Sample games
INSERT OR IGNORE INTO games (id, name, slug, platform, process_name) VALUES
(1, 'Stardew Valley', 'stardew-valley', 'PC', 'Stardew Valley.exe'),
(2, 'Cities: Skylines', 'cities-skylines', 'PC', 'Cities.exe'),
(3, 'Subnautica', 'subnautica', 'PC', 'Subnautica.exe');

-- Sample trainers
INSERT OR IGNORE INTO trainers (id, game_id, name, description, cheat_type, is_premium) VALUES
(1, 1, 'Unendlich Geld', 'Setzt dein Geld auf 999.999', 'memory', 0),
(2, 1, 'Unendlich Energie', 'Energie sinkt nie', 'memory', 0),
(3, 1, 'Instant Crop Growth', 'Pflanzen wachsen sofort', 'memory', 1),
(4, 2, 'Unendliches Geld', 'Setzt Stadtbudget auf Max', 'memory', 1),
(5, 3, 'Unendlich Sauerstoff', 'Sauerstoff sinkt nie', 'memory', 1);

-- Trainer patterns table (version independent memory scanning)
CREATE TABLE IF NOT EXISTS trainer_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trainer_id INTEGER NOT NULL,
    game_version TEXT,
    pattern TEXT NOT NULL,
    offset INTEGER DEFAULT 0,
    value_type TEXT NOT NULL,
    value TEXT,
    scan_module TEXT,
    created_at INTEGER DEFAULT (strftime('%s','now')),
    FOREIGN KEY (trainer_id) REFERENCES trainers(id)
);

-- Insert Stardew Valley trainer patterns (placeholders, need real scans)
INSERT OR IGNORE INTO trainer_patterns (id, trainer_id, game_version, pattern, offset, value_type, value, scan_module) VALUES
(1, 1, '*', '89 7D ?? 8B 45 ?? 89 45 ?? 8B 4D ?? 89 4D ?? 8B 55 ?? 89 55 ??', 0, 'int32', '999999', 'Stardew Valley.exe'),
(2, 2, '*', 'F3 0F 11 4D ?? F3 0F 11 45 ?? F3 0F 11 55 ??', 0, 'float', '9999', 'Stardew Valley.exe'),
(3, 3, '*', '89 45 ?? 89 4D ?? 89 55 ?? 8B 45 ??', 0, 'int32', '999', 'Stardew Valley.exe');
