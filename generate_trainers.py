"""Generate trainers for all active games in the SweetCheat database."""
import sqlite3
import re
from pathlib import Path

DB = Path('/var/www/sweetcheat/database/sweetcheat.db')

GENERIC_CHEATS = {
    'rpg': [
        ('Unendlich Leben', 'God Mode: Gesundheit wird auf maximal gehalten.', 'memory', 1),
        ('Unendlich Geld / Ressourcen', 'Setzt Primärwährung auf maximalen Wert.', 'memory', 1),
        ('Erfahrung x10', 'XP-Multiplikator auf 10.', 'memory', 1),
        ('Max Level', 'Setzt Spielerlevel auf Maximum.', 'savegame', 1),
        ('Schnelles Laufen', 'Bewegungsgeschwindigkeit erhöht.', 'memory', 0),
    ],
    'shooter': [
        ('Unendlich Munition', 'Munition sinkt nie.', 'memory', 1),
        ('Kein Nachladen', 'Waffen müssen nicht nachgeladen werden.', 'memory', 1),
        ('Unendlich Leben', 'God Mode: Gesundheit wird auf maximal gehalten.', 'memory', 1),
        ('One-Hit Kill', 'Gegner sterben mit einem Treffer.', 'memory', 1),
        ('No Recoil', 'Kein Rückstoß.', 'memory', 0),
    ],
    'strategy': [
        ('Unendlich Ressourcen', 'Holz, Stein, Nahrung, Gold etc. auf Maximum.', 'memory', 1),
        ('Schneller Bau', 'Bauzeiten auf 0.', 'memory', 1),
        ('Keine Nebel des Krieges', 'Map vollständig sichtbar.', 'memory', 0),
        ('Maximale Bevölkerung', 'Bevölkerungslimit aufgehoben.', 'savegame', 1),
    ],
    'simulation': [
        ('Unendlich Geld', 'Geld auf Maximum.', 'savegame', 1),
        ('Max Stats', 'Alle Stats auf Maximum.', 'savegame', 1),
        ('Keine Müdigkeit', 'Energie/Müdigkeit optimal.', 'memory', 0),
    ],
    'platformer': [
        ('Unendlich Leben', 'Leben wird auf Maximum gehalten.', 'memory', 1),
        ('99 Continues', 'Continues auf 99.', 'savegame', 0),
        ('Alle Powerups', 'Aktiviert alle Powerups.', 'memory', 1),
    ],
    'sports': [
        ('Max Stats Spieler', 'Alle Spielerstats auf 99.', 'savegame', 1),
        ('Unendlich Ausdauer', 'Ausdauer sinkt nie.', 'memory', 0),
        ('Perfekte Schüsse', 'Jeder Schuss/Torwurf trifft.', 'memory', 1),
    ],
    'puzzle': [
        ('Unendliche Züge', 'Zuglimit aufgehoben.', 'memory', 1),
        ('Max Punkte', 'Punktestand auf Maximum.', 'memory', 0),
        ('Zeit eingefroren', 'Timer stoppt.', 'memory', 1),
    ],
    'default': [
        ('Unendlich Leben / Gesundheit', 'God Mode: Gesundheit wird auf maximal gehalten.', 'memory', 1),
        ('Unendlich Geld / Ressourcen', 'Setzt Primärwährung auf maximalen Wert.', 'memory', 1),
        ('Einfrieren Zeit / Timer', 'Timer stoppt oder wird auf 0 gesetzt.', 'memory', 0),
        ('Maximale Werte', 'Alle wichtigen Werte auf Maximum.', 'savegame', 1),
        ('Schnelles Bewegen', 'Bewegungsgeschwindigkeit erhöht.', 'memory', 0),
    ]
}

GENRE_MAP = {
    'rpg': ['rpg', 'action rpg', 'mmorpg', 'jrpg'],
    'shooter': ['shooter', 'fps', 'tps', 'first-person shooter', 'third-person shooter', 'battle royale'],
    'strategy': ['strategy', 'rts', 'turn-based strategy', 'city builder', '4x', 'tower defense'],
    'simulation': ['simulation', 'sim', 'life sim', 'farming sim', 'management'],
    'platformer': ['platformer', 'metroidvania', 'action platformer'],
    'sports': ['sports', 'racing', 'football', 'basketball', 'soccer'],
    'puzzle': ['puzzle', 'casual'],
}

KNOWN_COMMANDS = {
    'stardew-valley': [
        ('/money 999999', 'Geld'), ('/health 999', 'Leben'), ('/stamina 999', 'Energie'),
        ('/backpack 36', 'Rucksack'), ('/item 74 999', 'Item Spawn'),
    ],
    'minecraft': [
        ('/gamemode creative', 'Creative Mode'), ('/give @p diamond 64', 'Diamanten'),
        ('/effect give @p minecraft:health_boost 99999 99', 'God Mode'),
    ],
    'skyrim': [
        ('player.additem 0000000f 999999', 'Gold'), ('tgm', 'God Mode'),
        ('player.advlevel', 'Level Up'), ('player.modav carryweight 9999', 'Tragkraft'),
    ],
    'fallout-4': [
        ('player.additem 0000000f 999999', 'Kronkorken'), ('tgm', 'God Mode'),
        ('player.advlevel', 'Level Up'),
    ],
    'witcher-3': [
        ('addmoney(999999)', 'Geld'), ('god', 'God Mode'), ('additem(gwint_card_geralt,1)', 'Gwent'),
    ],
    'gtav': [
        ('MONEY', 'Geld'), ('TOOLUP', 'Waffen'), ('TURTLE', 'Rüstung'),
        ('POWERUP', 'Fähigkeiten'), ('CATCHME', 'Schnelllaufen'),
    ],
}


def classify_genre(genre):
    if not genre:
        return 'default'
    g = genre.lower()
    for bucket, names in GENRE_MAP.items():
        if any(n in g for n in names):
            return bucket
    return 'default'


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id, name, slug, genre FROM games WHERE is_active = 1")
    games = cur.fetchall()
    added = 0

    for game_id, name, slug, genre in games:
        bucket = classify_genre(genre)
        cheats = GENERIC_CHEATS[bucket]

        for cmd, cname in KNOWN_COMMANDS.get(slug, []):
            cur.execute("""
                INSERT OR IGNORE INTO trainers (game_id, name, description, cheat_type, command, is_premium, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (game_id, f"{cname} Befehl", f"Offizieller Konsolenbefehl: {cmd}", 'console', cmd, 0))
            added += cur.rowcount

        for title, desc, ctype, premium in cheats:
            cur.execute("""
                INSERT OR IGNORE INTO trainers (game_id, name, description, cheat_type, is_premium, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (game_id, title, desc, ctype, premium))
            added += cur.rowcount

        cur.execute("""
            INSERT OR IGNORE INTO trainers (game_id, name, description, cheat_type, is_premium, is_active)
            VALUES (?, 'Werte scannen', 'Suche einen Wert im Speicher und setze ihn auf Maximum.', 'two_scan', 0, 1)
        """, (game_id,))
        added += cur.rowcount

        cur.execute("""
            INSERT OR IGNORE INTO trainers (game_id, name, description, cheat_type, is_premium, is_active)
            VALUES (?, 'Pattern lernen', 'Generiere ein Memory-Pattern aus einer gefundenen Adresse.', 'pattern_learner', 0, 1)
        """, (game_id,))
        added += cur.rowcount

    conn.commit()
    conn.close()
    print(f"Added {added} trainers across {len(games)} games")


if __name__ == '__main__':
    main()
