"""TrainerHub Desktop Application - Premium UI Edition"""
import sys
import os
import json
import time
import threading
import struct
import urllib.request
import urllib.error

# Constants
APP_VERSION = '0.5.0'
CONFIG_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'TrainerHub')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
API_BASE = os.environ.get('TRAINERHUB_API', 'https://sayfespace.online/trainerhub/api')

os.makedirs(CONFIG_DIR, exist_ok=True)

# Optional imports
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext, simpledialog
except ImportError:
    print("tkinter fehlt")
    sys.exit(1)

from ui_components import ModernStyle, RoundedFrame, AnimatedButton, StatusBadge, ModernCombobox

WINDOWS = sys.platform == 'win32'
if WINDOWS:
    try:
        import pymem
        from pymem import Pymem
        import pymem.process
        import pymem.memory
    except ImportError as e:
        print(f"pymem fehlt: {e}")
        pymem = None
else:
    pymem = None

try:
    import sdv_savegame
    SDV_SAVE = True
except ImportError:
    SDV_SAVE = False

try:
    import stardew_bridge
    BRIDGE = True
except ImportError:
    BRIDGE = False

try:
    from pattern_learner import PatternLearner
    PATTERN_LEARNER = True
except ImportError:
    PATTERN_LEARNER = False


def load_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'api_key': None, 'api_base': API_BASE, 'theme': 'dark', 'favorites': [], 'recent_games': []}


def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f)
    except Exception as e:
        print(f"Config save error: {e}")


class TrainerHubApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"TrainerHub {APP_VERSION} — Singleplayer Trainer")
        self.root.geometry("1280x820")
        self.root.minsize(1100, 700)
        self.root.configure(bg=ModernStyle.BG)
        ModernStyle.apply(self.root)
        
        self.config = load_config()
        self.api_key = self.config.get('api_key')
        self.api_base = self.config.get('api_base', API_BASE)
        self.games = []
        self.trainers = []
        self.current_game = None
        self.current_game_pid = None
        self.premium_data = {}
        self.favorites = set(self.config.get('favorites', []))
        self.recent_games = list(self.config.get('recent_games', []))
        self.freeze_threads = {}
        self.scan_state = {}
        self.log_lines = []
        self.bridge_client = None
        self.user_info = {}
        self.hotkey_manager = None
        self.theme_manager = None
        
        self.build_ui()
        if self.api_key:
            self.validate_key()
        else:
            self.show_login()
        
        self.apply_theme(self.config.get('theme', 'dark'))
        self.start_background_tasks()

    # ----------------------------- UI BUILD -----------------------------
    def build_ui(self):
        # Header
        self.header = tk.Frame(self.root, bg=ModernStyle.BG, height=64)
        self.header.pack(fill='x', padx=20, pady=(15,0))
        self.header.pack_propagate(False)
        
        self.brand = tk.Label(self.header, text="TrainerHub", font=('Segoe UI', 20, 'bold'),
                              bg=ModernStyle.BG, fg=ModernStyle.TEXT)
        self.brand.pack(side='left')
        self.brand.config(fg=ModernStyle.ACCENT)
        
        self.status_frame = tk.Frame(self.header, bg=ModernStyle.BG)
        self.status_frame.pack(side='right')
        
        self.premium_badge = StatusBadge(self.status_frame, "FREE", ModernStyle.TEXT_MUTED)
        self.premium_badge.pack(side='left', padx=(0,12))
        
        self.connection_badge = StatusBadge(self.status_frame, "● Offline", ModernStyle.DANGER)
        self.connection_badge.pack(side='left', padx=(0,12))
        
        tk.Button(self.status_frame, text="⚙ Einstellungen", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT,
                  relief='flat', font=('Segoe UI', 10), padx=15, pady=5,
                  command=self.show_settings).pack(side='left', padx=(0,8))
        tk.Button(self.status_frame, text="Account", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT,
                  relief='flat', font=('Segoe UI', 10), padx=15, pady=5,
                  command=self.show_account).pack(side='left', padx=(0,8))
        tk.Button(self.status_frame, text="Logout", bg=ModernStyle.BG_CARD, fg=ModernStyle.DANGER,
                  relief='flat', font=('Segoe UI', 10), padx=15, pady=5,
                  command=self.logout).pack(side='left')
        
        # Main content area (pages)
        self.content = tk.Frame(self.root, bg=ModernStyle.BG)
        self.content.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Bottom status bar
        self.statusbar = tk.Frame(self.root, bg=ModernStyle.BG_CARD, height=28)
        self.statusbar.pack(fill='x', side='bottom')
        self.statusbar.pack_propagate(False)
        self.status_text = tk.Label(self.statusbar, text="Bereit", bg=ModernStyle.BG_CARD,
                                    fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 9))
        self.status_text.pack(side='left', padx=12, pady=4)
        self.version_label = tk.Label(self.statusbar, text=f"v{APP_VERSION}", bg=ModernStyle.BG_CARD,
                                        fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 9))
        self.version_label.pack(side='right', padx=12, pady=4)

    def _apply_gradient(self, widget):
        # Apply gradient text effect by configuring font color via label mapping not possible in tk
        # Instead use a canvas-based approach for hero text later.
        widget.config(fg=ModernStyle.ACCENT)

    def clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def show_login(self):
        self.clear_content()
        card = RoundedFrame(self.content, radius=20, bg=ModernStyle.BG_CARD, border_color=ModernStyle.BORDER)
        card.pack(expand=True)
        inner = card.inner
        inner.configure(padx=60, pady=50)
        
        tk.Label(inner, text="Willkommen zurück", font=('Segoe UI', 24, 'bold'),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT).pack()
        tk.Label(inner, text="Singleplayer Trainer für 300+ Spiele", font=('Segoe UI', 12),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack(pady=(5,35))
        
        tk.Label(inner, text="Benutzername oder E-Mail", bg=ModernStyle.BG_CARD,
                 fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 10)).pack(anchor='w', pady=(0,5))
        self.login_user = tk.Entry(inner, width=42, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT,
                                   insertbackground=ModernStyle.TEXT, relief='flat', font=('Segoe UI', 11))
        self.login_user.pack(fill='x', ipady=7, pady=(0,15))
        
        tk.Label(inner, text="Passwort", bg=ModernStyle.BG_CARD,
                 fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 10)).pack(anchor='w', pady=(0,5))
        self.login_pass = tk.Entry(inner, width=42, show='*', bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT,
                                   insertbackground=ModernStyle.TEXT, relief='flat', font=('Segoe UI', 11))
        self.login_pass.pack(fill='x', ipady=7, pady=(0,25))
        self.login_pass.bind('<Return>', lambda e: self.do_login())
        
        btn = AnimatedButton(inner, text="Einloggen", command=self.do_login, width=360, height=44)
        btn.pack(pady=5)
        
        self.login_msg = tk.Label(inner, text="", bg=ModernStyle.BG_CARD, fg=ModernStyle.DANGER, font=('Segoe UI', 10))
        self.login_msg.pack(pady=(15,0))
        
        tk.Label(inner, text="Noch kein Account? Registriere dich auf sayfespace.online/trainerhub",
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 9)).pack(pady=(25,0))

    def do_login(self):
        user = self.login_user.get().strip()
        pw = self.login_pass.get()
        if not user or not pw:
            self.login_msg.config(text="Bitte Benutzername und Passwort eingeben.")
            return
        data = self.api_call('auth.php?action=login', 'POST', {'email': user, 'password': pw})
        if data.get('success'):
            self.api_key = data['api_key']
            self.config['api_key'] = self.api_key
            save_config(self.config)
            self.validate_key()
        else:
            self.login_msg.config(text=data.get('error', 'Login fehlgeschlagen'))

    def validate_key(self):
        data = self.api_call('billing.php?action=status')
        if data.get('success'):
            self.user_info = data
            self.premium_data = self.api_call('premium.php?action=status')
            status = 'PREMIUM' if self.is_premium() else 'FREE'
            color = ModernStyle.GOLD if self.is_premium() else ModernStyle.TEXT_MUTED
            self.premium_badge = StatusBadge(self.status_frame, status, color)
            self.premium_badge.pack(side='left', padx=(0,12), before=self.connection_badge)
            self.connection_badge = StatusBadge(self.status_frame, "● Online", ModernStyle.SUCCESS)
            self.connection_badge.pack(side='left', padx=(0,12), after=self.premium_badge)
            self.show_dashboard()
            self.init_hotkeys()
        else:
            self.api_key = None
            self.show_login()
            self.login_msg.config(text="Sitzung abgelaufen. Bitte neu einloggen.")

    def show_dashboard(self):
        self.clear_content()
        
        # Top: game selector bar
        top = tk.Frame(self.content, bg=ModernStyle.BG)
        top.pack(fill='x', pady=(0,15))
        
        tk.Label(top, text="Spiel auswählen:", bg=ModernStyle.BG, fg=ModernStyle.TEXT_MUTED,
                 font=('Segoe UI', 11)).pack(side='left', padx=(0,10))
        self.game_combo = ModernCombobox(top, values=[], command=self.on_game_selected)
        self.game_combo.pack(side='left', fill='y')
        self.load_games()
        
        AnimatedButton(top, text="🔍 Prozess prüfen", command=self.check_process, width=150, height=34,
                       bg=ModernStyle.BORDER, fg=ModernStyle.TEXT, hover_bg=ModernStyle.BORDER_ACTIVE).pack(side='left', padx=(15,0))
        
        self.proc_status = tk.Label(top, text="Kein Spiel gestartet", bg=ModernStyle.BG,
                                      fg=ModernStyle.DANGER, font=('Segoe UI', 10))
        self.proc_status.pack(side='left', padx=(15,0))
        
        # Main split
        main = tk.Frame(self.content, bg=ModernStyle.BG)
        main.pack(fill='both', expand=True)
        
        # Left: dashboard cards
        left = tk.Frame(main, bg=ModernStyle.BG)
        left.pack(side='left', fill='both', expand=True)
        
        # Stats row
        stats = tk.Frame(left, bg=ModernStyle.BG)
        stats.pack(fill='x', pady=(0,15))
        self._create_stat_card(stats, "Spiele", "0", 0)
        self._create_stat_card(stats, "Trainer", "0", 1)
        self._create_stat_card(stats, "Favoriten", str(len(self.favorites)), 2)
        self._create_stat_card(stats, "Premium", "AKTIV" if self.is_premium() else "FREE", 3)
        
        # Recently played / favorites
        recents = RoundedFrame(left, radius=16, bg=ModernStyle.BG_CARD, border_color=ModernStyle.BORDER)
        recents.pack(fill='x', pady=(0,15))
        recents.inner.configure(padx=20, pady=15)
        tk.Label(recents.inner, text="Zuletzt verwendet", bg=ModernStyle.BG_CARD,
                 fg=ModernStyle.TEXT, font=('Segoe UI', 14, 'bold')).pack(anchor='w')
        self.recent_container = tk.Frame(recents.inner, bg=ModernStyle.BG_CARD)
        self.recent_container.pack(fill='x', pady=(10,0))
        self._render_recent_games()
        
        # Trainers list
        trainers_card = RoundedFrame(left, radius=16, bg=ModernStyle.BG_CARD, border_color=ModernStyle.BORDER)
        trainers_card.pack(fill='both', expand=True)
        trainers_card.inner.configure(padx=20, pady=15)
        header = tk.Frame(trainers_card.inner, bg=ModernStyle.BG_CARD)
        header.pack(fill='x', pady=(0,10))
        tk.Label(header, text="Verfügbare Trainer", bg=ModernStyle.BG_CARD,
                 fg=ModernStyle.TEXT, font=('Segoe UI', 14, 'bold')).pack(side='left')
        self.trainer_filter = tk.Entry(header, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT,
                                       insertbackground=ModernStyle.TEXT, relief='flat', font=('Segoe UI', 10), width=25)
        self.trainer_filter.pack(side='right', ipady=4, padx=(10,0))
        self.trainer_filter.bind('<KeyRelease>', lambda e: self.render_trainers())
        tk.Label(header, text="Filter:", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED,
                 font=('Segoe UI', 10)).pack(side='right')
        
        self.trainer_canvas = tk.Canvas(trainers_card.inner, bg=ModernStyle.BG_CARD, highlightthickness=0)
        self.trainer_scroll = ttk.Scrollbar(trainers_card.inner, orient='vertical', command=self.trainer_canvas.yview)
        self.trainer_container = tk.Frame(self.trainer_canvas, bg=ModernStyle.BG_CARD)
        self.trainer_container.bind('<Configure>', lambda e: self.trainer_canvas.configure(scrollregion=self.trainer_canvas.bbox('all')))
        self.trainer_canvas.create_window((0,0), window=self.trainer_container, anchor='nw', width=560)
        self.trainer_canvas.configure(yscrollcommand=self.trainer_scroll.set)
        self.trainer_canvas.pack(side='left', fill='both', expand=True)
        self.trainer_scroll.pack(side='right', fill='y')
        
        # Right: log + tools
        right = tk.Frame(main, bg=ModernStyle.BG, width=380)
        right.pack(side='right', fill='y', padx=(20,0))
        right.pack_propagate(False)
        
        log_card = RoundedFrame(right, radius=16, bg=ModernStyle.BG_CARD, border_color=ModernStyle.BORDER)
        log_card.pack(fill='both', expand=True)
        log_card.inner.configure(padx=15, pady=15)
        tk.Label(log_card.inner, text="Live-Log", bg=ModernStyle.BG_CARD,
                 fg=ModernStyle.TEXT, font=('Segoe UI', 14, 'bold')).pack(anchor='w')
        self.log_box = scrolledtext.ScrolledText(log_card.inner, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT,
                                                 font=('Consolas', 9), wrap='word', state='disabled',
                                                 relief='flat', highlightthickness=1, highlightbackground=ModernStyle.BORDER)
        self.log_box.pack(fill='both', expand=True, pady=(10,0))
        
        # Quick tools
        tools_card = RoundedFrame(right, radius=16, bg=ModernStyle.BG_CARD, border_color=ModernStyle.BORDER)
        tools_card.pack(fill='x', pady=(15,0))
        tools_card.inner.configure(padx=15, pady=15)
        tk.Label(tools_card.inner, text="Tools", bg=ModernStyle.BG_CARD,
                 fg=ModernStyle.TEXT, font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        btn_frame = tk.Frame(tools_card.inner, bg=ModernStyle.BG_CARD)
        btn_frame.pack(fill='x', pady=(10,0))
        AnimatedButton(btn_frame, text="Changelog", command=self.show_changelog, width=110, height=34,
                         bg=ModernStyle.BORDER, fg=ModernStyle.TEXT, hover_bg=ModernStyle.BORDER_ACTIVE).pack(side='left', padx=(0,8))
        AnimatedButton(btn_frame, text="Verlauf", command=self.show_history, width=110, height=34,
                         bg=ModernStyle.BORDER, fg=ModernStyle.TEXT, hover_bg=ModernStyle.BORDER_ACTIVE).pack(side='left', padx=(0,8))
        AnimatedButton(btn_frame, text="Log speichern", command=self.export_log, width=110, height=34,
                         bg=ModernStyle.BORDER, fg=ModernStyle.TEXT, hover_bg=ModernStyle.BORDER_ACTIVE).pack(side='left')
        
        # Hotkey hint
        tk.Label(tools_card.inner, text="Hotkeys: F5 = Prozess prüfen | F1 = Tutorial | F9 = Global",
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 9)).pack(anchor='w', pady=(12,0))
        
        self.root.bind('<F5>', lambda e: self.check_process())
        self.root.bind('<F1>', lambda e: self.show_tutorial())
        
        self.load_trainers()
        self.show_changelog(first_start=True)
        self.start_smapipoll()

    def _create_stat_card(self, parent, label, value, idx):
        card = RoundedFrame(parent, radius=14, bg=ModernStyle.BG_CARD, border_color=ModernStyle.BORDER, height=80)
        card.pack(side='left', fill='x', expand=True, padx=(0 if idx==0 else 10,0))
        card.inner.configure(padx=15, pady=12)
        tk.Label(card.inner, text=label, bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED,
                 font=('Segoe UI', 10)).pack(anchor='w')
        self.stat_value_label = tk.Label(card.inner, text=value, bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT,
                                         font=('Segoe UI', 20, 'bold'))
        self.stat_value_label.pack(anchor='w', pady=(5,0))
        if label == 'Premium':
            self.stat_value_label.config(fg=ModernStyle.GOLD if value == "AKTIV" else ModernStyle.TEXT_MUTED)
        elif label == 'Spiele':
            self.games_count_label = self.stat_value_label
        elif label == 'Trainer':
            self.trainers_count_label = self.stat_value_label

    def _render_recent_games(self):
        for w in self.recent_container.winfo_children():
            w.destroy()
        if not self.recent_games:
            tk.Label(self.recent_container, text="Noch keine Spiele verwendet.", bg=ModernStyle.BG_CARD,
                     fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 10)).pack(anchor='w')
            return
        for slug in self.recent_games[:5]:
            game = next((g for g in self.games if g.get('slug') == slug), None)
            if not game:
                continue
            btn = tk.Button(self.recent_container, text=game.get('name', slug),
                            bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT, relief='flat',
                            font=('Segoe UI', 10), padx=12, pady=6,
                            command=lambda s=slug: self.select_game(s))
            btn.pack(side='left', padx=(0,8))

    # ----------------------------- API -----------------------------
    def api_call(self, endpoint, method='GET', data=None):
        headers = {'User-Agent': 'TrainerHub-Desktop/0.4.0'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        url = f'{self.api_base}/{endpoint}'
        try:
            if method == 'GET':
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as r:
                    return json.loads(r.read().decode('utf-8'))
            else:
                body = json.dumps(data).encode('utf-8') if data else b''
                req = urllib.request.Request(url, data=body,
                                            headers={**headers, 'Content-Type': 'application/json'},
                                            method='POST')
                with urllib.request.urlopen(req, timeout=15) as r:
                    return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode('utf-8'))
            except Exception:
                return {'success': False, 'error': f'HTTP {e.code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def is_premium(self):
        try:
            return self.premium_data.get('subscription') == 'premium' or self.premium_data.get('features', {}).get('advanced_scans', False)
        except Exception:
            return False

    def has_feature(self, feature):
        try:
            return self.premium_data.get('features', {}).get(feature, False)
        except Exception:
            return False

    # ----------------------------- GAME LOADING -----------------------------
    def load_games(self):
        data = self.api_call('games.php')
        if data.get('success'):
            self.games = data.get('games', [])
            values = [g.get('name', '') for g in self.games]
            self.game_combo.set_values(values)
            if values:
                self.select_game(self.games[0].get('slug'))
            if hasattr(self, 'games_count_label'):
                self.games_count_label.config(text=str(len(self.games)))

    def on_game_selected(self):
        name = self.game_combo.get()
        game = next((g for g in self.games if g.get('name') == name), None)
        if game:
            self.select_game(game.get('slug'))

    def select_game(self, slug):
        self.current_game = slug
        if slug in self.recent_games:
            self.recent_games.remove(slug)
        self.recent_games.insert(0, slug)
        self.recent_games = self.recent_games[:10]
        self.config['recent_games'] = self.recent_games
        save_config(self.config)
        self._render_recent_games()
        game = next((g for g in self.games if g.get('slug') == slug), None)
        if game and hasattr(self, 'game_combo'):
            self.game_combo.set(game.get('name', ''))
        self.load_trainers()

    def load_trainers(self):
        if not self.current_game:
            return
        data = self.api_call(f'trainers.php?action=list&game={self.current_game}')
        if data.get('success'):
            self.trainers = data.get('trainers', [])
            if hasattr(self, 'trainers_count_label'):
                self.trainers_count_label.config(text=str(len(self.trainers)))
            self.render_trainers()
            self.log(f"Trainer für {self.current_game} geladen: {len(self.trainers)}")
        else:
            self.log(f"Fehler beim Laden der Trainer: {data.get('error')}")

    def render_trainers(self):
        if not hasattr(self, 'trainer_container'):
            return
        for w in self.trainer_container.winfo_children():
            w.destroy()
        
        filt = getattr(self, 'trainer_filter', None)
        text = filt.get().lower() if filt else ''
        
        shown = [t for t in self.trainers if not text or text in t.get('name','').lower()]
        if not shown:
            tk.Label(self.trainer_container, text="Keine Trainer gefunden.", bg=ModernStyle.BG_CARD,
                     fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 11)).pack(pady=20)
            return
        
        for t in shown:
            card = RoundedFrame(self.trainer_container, radius=12, bg=ModernStyle.BG_CARD, border_color=ModernStyle.BORDER)
            card.pack(fill='x', pady=6)
            inner = card.inner
            inner.configure(padx=15, pady=12)
            
            head = tk.Frame(inner, bg=ModernStyle.BG_CARD)
            head.pack(fill='x')
            title = t.get('name', 'Unbenannt')
            if t.get('locked'):
                title += ' 🔒'
            tk.Label(head, text=title, bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT,
                     font=('Segoe UI', 12, 'bold')).pack(side='left')
            
            if t.get('locked'):
                StatusBadge(head, "PREMIUM", ModernStyle.GOLD).pack(side='right')
            else:
                StatusBadge(head, "AKTIV", ModernStyle.SUCCESS).pack(side='right')
            
            desc = t.get('description', '')
            tk.Label(inner, text=desc, bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED,
                     font=('Segoe UI', 9), wraplength=520, justify='left').pack(anchor='w', pady=(6,0))
            
            btn_row = tk.Frame(inner, bg=ModernStyle.BG_CARD)
            btn_row.pack(fill='x', pady=(12,0))
            
            ctype = t.get('cheat_type', '')
            if t.get('locked'):
                AnimatedButton(btn_row, text="Premium aktivieren", command=self.show_premium_dialog,
                               width=160, height=32, bg=ModernStyle.GOLD, fg='#000000').pack(side='right')
            else:
                if ctype in ('smapi_set',):
                    AnimatedButton(btn_row, text="SMAPI Set", command=lambda tr=t: self.smapi_set(tr),
                                   width=110, height=32, bg=ModernStyle.PURPLE).pack(side='right', padx=(8,0))
                elif ctype in ('two_scan', 'scan', 'memory'):
                    AnimatedButton(btn_row, text="2-Scan starten", command=lambda tr=t: self.scan_with_two_values(tr),
                                   width=120, height=32).pack(side='right', padx=(8,0))
                elif ctype in ('savegame',):
                    AnimatedButton(btn_row, text="Savegame", command=lambda tr=t: self.open_savegame_editor(tr),
                                   width=110, height=32, bg=ModernStyle.SUCCESS).pack(side='right', padx=(8,0))
                elif ctype in ('pattern_learner', 'pattern'):
                    AnimatedButton(btn_row, text="Pattern lernen", command=lambda tr=t: self.open_pattern_learner(tr),
                                   width=130, height=32, bg=ModernStyle.CYAN, fg='#000000').pack(side='right', padx=(8,0))
                else:
                    AnimatedButton(btn_row, text="Aktivieren", command=lambda tr=t: self.activate_generic(tr),
                                   width=110, height=32).pack(side='right', padx=(8,0))
                
                AnimatedButton(btn_row, text="Info", command=lambda tr=t: self.show_trainer_info(tr),
                               width=70, height=32, bg=ModernStyle.BORDER, fg=ModernStyle.TEXT,
                               hover_bg=ModernStyle.BORDER_ACTIVE).pack(side='right', padx=(8,0))
            
            # Favorite star
            fav_text = "★" if title in self.favorites else "☆"
            star = tk.Label(btn_row, text=fav_text, bg=ModernStyle.BG_CARD, fg=ModernStyle.GOLD,
                            font=('Segoe UI', 14), cursor='hand2')
            star.pack(side='left')
            star.bind('<Button-1>', lambda e, n=title: self.toggle_favorite(n))
        
        # Load official cheats section
        self.load_official_cheats()

    def load_official_cheats(self):
        if not self.current_game:
            return
        try:
            data = self.api_call(f'cheats.php?game={self.current_game}')
            cheats = data.get('cheats', [])
            if cheats:
                section = tk.LabelFrame(self.trainer_container, text="Offizielle Cheats / Konsole",
                                        bg=ModernStyle.BG_CARD, fg=ModernStyle.SUCCESS,
                                        font=('Segoe UI', 12, 'bold'), relief='solid', borderwidth=1)
                section.pack(fill='x', pady=15, padx=5)
                for c in cheats[:8]:
                    card = tk.Frame(section, bg=ModernStyle.BG_CARD, highlightbackground=ModernStyle.BORDER,
                                    highlightthickness=1, padx=12, pady=10)
                    card.pack(fill='x', pady=4, padx=5)
                    tk.Label(card, text=c.get('name',''), bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT,
                             font=('Segoe UI', 11, 'bold')).pack(anchor='w')
                    tk.Label(card, text=c.get('description',''), bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED,
                             font=('Segoe UI', 9), wraplength=500, justify='left').pack(anchor='w')
                    cmd_text = c.get('command', '') + (f" {c.get('params','')}" if c.get('params') else '')
                    if cmd_text.strip():
                        row = tk.Frame(card, bg=ModernStyle.BG_CARD)
                        row.pack(fill='x', pady=(6,0))
                        entry = tk.Entry(row, bg=ModernStyle.BG_INPUT, fg=ModernStyle.SUCCESS,
                                         font=('Consolas', 10), state='readonly', readonlybackground=ModernStyle.BG_INPUT,
                                         relief='flat')
                        entry.pack(side='left', fill='x', expand=True, ipady=4)
                        entry.insert(0, cmd_text)
                        tk.Button(row, text="Kopieren", bg=ModernStyle.BORDER, fg=ModernStyle.TEXT,
                                  relief='flat', font=('Segoe UI', 9), padx=10,
                                  command=lambda ct=cmd_text: self.copy_to_clipboard(ct)).pack(side='right', padx=(8,0))
        except Exception as e:
            self.log(f"Cheats laden fehlgeschlagen: {e}")

    # ----------------------------- ACTIONS -----------------------------
    def check_process(self):
        if not WINDOWS or not pymem:
            self.proc_status.config(text="Nur auf Windows verfügbar", fg=ModernStyle.DANGER)
            self.log("Prozess-Scan nur auf Windows verfügbar.")
            return
        game = next((g for g in self.games if g.get('slug') == self.current_game), None)
        if not game:
            self.proc_status.config(text="Kein Spiel ausgewählt", fg=ModernStyle.WARNING)
            return
        proc_name = game.get('process_name', '').lower().replace('.exe', '')
        if not proc_name:
            self.proc_status.config(text="Kein Prozessname bekannt", fg=ModernStyle.WARNING)
            return
        try:
            procs = pymem.process.list_processes()
            for proc in procs:
                name = proc.sz_exeFile.decode('utf-8', errors='ignore').lower()
                if proc_name in name:
                    self.current_game_pid = proc.th32ProcessID
                    self.proc_status.config(text=f"✓ {name} (PID {proc.th32ProcessID})", fg=ModernStyle.SUCCESS)
                    self.log(f"Prozess gefunden: {name} PID {proc.th32ProcessID}")
                    return
            self.current_game_pid = None
            self.proc_status.config(text="Spiel nicht gestartet", fg=ModernStyle.DANGER)
            self.log(f"{proc_name}.exe nicht gefunden.")
        except Exception as e:
            self.proc_status.config(text=f"Fehler: {e}", fg=ModernStyle.DANGER)
            self.log(f"Prozess-Fehler: {e}")

    def copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.log(f"In Zwischenablage kopiert: {text[:50]}...")

    def log(self, msg, level='info'):
        ts = time.strftime('%H:%M:%S')
        colors = {'info': ModernStyle.TEXT, 'success': ModernStyle.SUCCESS, 'warning': ModernStyle.WARNING, 'error': ModernStyle.DANGER}
        color = colors.get(level, ModernStyle.TEXT)
        line = f"[{ts}] {msg}"
        self.log_lines.append(line)
        self.log_box.config(state='normal')
        self.log_box.insert('end', line + '\n')
        self.log_box.tag_config(level, foreground=color)
        # apply tag to last line
        start = self.log_box.index('end -2 lines linestart')
        end = self.log_box.index('end -1 lines')
        self.log_box.tag_add(level, start, end)
        self.log_box.see('end')
        self.log_box.config(state='disabled')
        self.status_text.config(text=msg[:80])

    def export_log(self):
        path = os.path.join(CONFIG_DIR, 'trainerhub_log.txt')
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.log_lines))
            self.log(f"Log gespeichert: {path}", 'success')
        except Exception as e:
            self.log(f"Log-Export fehlgeschlagen: {e}", 'error')

    # ----------------------------- TRAINER ACTIONS -----------------------------
    def activate_generic(self, trainer):
        self.log(f"{trainer.get('name')} aktiviert (generisch).", 'info')
        self.log_activation(trainer.get('name', 'generic'), success=True)

    def show_trainer_info(self, trainer):
        win = tk.Toplevel(self.root)
        win.title(trainer.get('name', 'Info'))
        win.geometry("500x350")
        win.configure(bg=ModernStyle.BG)
        card = RoundedFrame(win, radius=16, bg=ModernStyle.BG_CARD, border_color=ModernStyle.BORDER)
        card.pack(fill='both', expand=True, padx=20, pady=20)
        inner = card.inner
        inner.configure(padx=20, pady=20)
        tk.Label(inner, text=trainer.get('name',''), bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT,
                 font=('Segoe UI', 16, 'bold')).pack(anchor='w')
        tk.Label(inner, text=trainer.get('description',''), bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED,
                 font=('Segoe UI', 10), wraplength=420, justify='left').pack(anchor='w', pady=(10,0))
        tk.Label(inner, text=f"Typ: {trainer.get('cheat_type','memory')}", bg=ModernStyle.BG_CARD,
                 fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 10)).pack(anchor='w', pady=(15,0))
        tk.Button(inner, text="Schließen", bg=ModernStyle.ACCENT, fg='#fff', relief='flat',
                  font=('Segoe UI', 10, 'bold'), padx=20, pady=6, command=win.destroy).pack(anchor='e', pady=(20,0))

    def toggle_favorite(self, name):
        if name in self.favorites:
            self.favorites.discard(name)
            self.log(f"{name} aus Favoriten entfernt")
        else:
            self.favorites.add(name)
            self.log(f"{name} zu Favoriten hinzugefügt", 'success')
        self.config['favorites'] = list(self.favorites)
        save_config(self.config)
        self.render_trainers()
        self.sync_favorites()

    def show_premium_dialog(self):
        try:
            data = self.api_call('premium.php?action=upgrade_request', 'POST')
            msg = data.get('message', 'Premium-Anfrage gesendet.')
        except Exception as e:
            msg = f"Fehler: {e}"
        messagebox.showinfo("Premium", msg)

    def show_account(self):
        win = tk.Toplevel(self.root)
        win.title("Account")
        win.geometry("450x480")
        win.configure(bg=ModernStyle.BG)
        card = RoundedFrame(win, radius=16, bg=ModernStyle.BG_CARD, border_color=ModernStyle.BORDER)
        card.pack(fill='both', expand=True, padx=20, pady=20)
        inner = card.inner
        inner.configure(padx=25, pady=25)
        tk.Label(inner, text="Account", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT,
                 font=('Segoe UI', 18, 'bold')).pack(anchor='w')
        
        status = "PREMIUM" if self.is_premium() else "FREE"
        tk.Label(inner, text=f"Status: {status}", bg=ModernStyle.BG_CARD,
                 fg=ModernStyle.GOLD if self.is_premium() else ModernStyle.TEXT_MUTED,
                 font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(15,5))
        
        # Load stats
        stats = self.api_call('trainer-logs.php?action=stats')
        if stats.get('success'):
            tk.Label(inner, text=f"Gesamte Aktivierungen: {stats.get('total_activations', 0)}",
                     bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 10)).pack(anchor='w', pady=2)
            tk.Label(inner, text=f"Erfolgreich: {stats.get('successful', 0)}",
                     bg=ModernStyle.BG_CARD, fg=ModernStyle.SUCCESS, font=('Segoe UI', 10)).pack(anchor='w', pady=2)
            tk.Label(inner, text=f"Fehlgeschlagen: {stats.get('failed', 0)}",
                     bg=ModernStyle.BG_CARD, fg=ModernStyle.DANGER, font=('Segoe UI', 10)).pack(anchor='w', pady=2)
        
        # Leaderboard position
        lb = self.api_call('premium.php?action=leaderboard')
        if lb.get('success') and self.user_info.get('email'):
            me = next((x for x in lb.get('leaderboard', []) if x.get('email') == self.user_info.get('email')), None)
            if me:
                tk.Label(inner, text=f"Reputation: {me.get('reputation', 0)}",
                         bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 10)).pack(anchor='w', pady=(15,2))
                tk.Label(inner, text=f"Approved Patterns: {me.get('approved_patterns', 0)}",
                         bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 10)).pack(anchor='w', pady=2)
        
        tk.Label(inner, text=f"API-Key:\n{self.api_key or 'Nicht eingeloggt'}", bg=ModernStyle.BG_CARD,
                 fg=ModernStyle.TEXT_MUTED, font=('Consolas', 9), wraplength=380).pack(anchor='w', pady=(15,0))
        
        tk.Button(inner, text="Schließen", bg=ModernStyle.ACCENT, fg='#fff', relief='flat',
                  font=('Segoe UI', 10, 'bold'), padx=20, pady=6, command=win.destroy).pack(anchor='e', pady=(20,0))

    def show_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Einstellungen")
        win.geometry("520x540")
        win.configure(bg=ModernStyle.BG)
        card = RoundedFrame(win, radius=16, bg=ModernStyle.BG_CARD, border_color=ModernStyle.BORDER)
        card.pack(fill='both', expand=True, padx=20, pady=20)
        inner = card.inner
        inner.configure(padx=25, pady=25)
        
        tk.Label(inner, text="⚙ Einstellungen", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT,
                 font=('Segoe UI', 18, 'bold')).pack(anchor='w')
        
        # API Base
        tk.Label(inner, text="API Base URL:", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED,
                 font=('Segoe UI', 10)).pack(anchor='w', pady=(20,5))
        api_entry = tk.Entry(inner, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT, relief='flat', font=('Segoe UI', 11))
        api_entry.insert(0, self.api_base)
        api_entry.pack(fill='x', ipady=5)
        
        # Theme
        tk.Label(inner, text="Theme:", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED,
                 font=('Segoe UI', 10)).pack(anchor='w', pady=(20,5))
        from features import ThemeManager
        theme_var = tk.StringVar(value=self.config.get('theme', 'dark'))
        theme_combo = ttk.Combobox(inner, values=['dark', 'midnight', 'neon'], textvariable=theme_var, state='readonly')
        theme_combo.pack(fill='x', ipady=3)
        
        # Global hotkeys
        tk.Label(inner, text="Globale Hotkeys:", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED,
                 font=('Segoe UI', 10)).pack(anchor='w', pady=(20,5))
        hotkey_var = tk.BooleanVar(value=self.config.get('global_hotkeys', False))
        tk.Checkbutton(inner, text="Hotkeys aktivieren (nur Windows)", variable=hotkey_var,
                       bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT, selectcolor=ModernStyle.BG_INPUT,
                       activebackground=ModernStyle.BG_CARD, activeforeground=ModernStyle.TEXT).pack(anchor='w')
        
        # Auto update
        tk.Label(inner, text="Updates:", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED,
                 font=('Segoe UI', 10)).pack(anchor='w', pady=(20,5))
        update_var = tk.BooleanVar(value=self.config.get('auto_update_check', True))
        tk.Checkbutton(inner, text="Beim Start auf Updates prüfen", variable=update_var,
                       bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT, selectcolor=ModernStyle.BG_INPUT,
                       activebackground=ModernStyle.BG_CARD, activeforeground=ModernStyle.TEXT).pack(anchor='w')
        
        # Game Launcher section
        tk.Label(inner, text="Spiel-Launcher:", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED,
                 font=('Segoe UI', 10)).pack(anchor='w', pady=(20,5))
        launcher_frame = tk.Frame(inner, bg=ModernStyle.BG_CARD)
        launcher_frame.pack(fill='x', pady=(5,0))
        launch_label = tk.Label(launcher_frame, text="Spiel auswählen und starten", bg=ModernStyle.BG_CARD,
                                fg=ModernStyle.TEXT, font=('Segoe UI', 10))
        launch_label.pack(side='left')
        
        def launch_current_game():
            from features import GameLauncher
            game = next((g for g in self.games if g.get('slug') == self.current_game), None)
            if not game:
                messagebox.showwarning("Kein Spiel", "Bitte ein Spiel auswählen.")
                return
            exe = game.get('process_name', '')
            launcher = GameLauncher(self.log)
            path = launcher.find_game_exe(exe)
            if path:
                launcher.launch(path)
                launch_label.config(text=f"Gestartet: {exe}", fg=ModernStyle.SUCCESS)
            else:
                launch_label.config(text=f"{exe} nicht gefunden", fg=ModernStyle.DANGER)
        
        AnimatedButton(launcher_frame, text="Spiel starten", command=launch_current_game,
                       width=120, height=30, bg=ModernStyle.SUCCESS).pack(side='right')
        
        def save():
            self.api_base = api_entry.get().strip() or API_BASE
            self.config['api_base'] = self.api_base
            self.config['theme'] = theme_var.get()
            self.config['global_hotkeys'] = hotkey_var.get()
            self.config['auto_update_check'] = update_var.get()
            save_config(self.config)
            self.log("Einstellungen gespeichert.", 'success')
            win.destroy()
        
        AnimatedButton(inner, text="Speichern", command=save, width=120, height=36).pack(anchor='e', pady=(25,0))

    def show_tutorial(self):
        win = tk.Toplevel(self.root)
        win.title("TrainerHub Tutorial")
        win.geometry("650x500")
        win.configure(bg=ModernStyle.BG)
        txt = scrolledtext.ScrolledText(win, bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT,
                                        font=('Segoe UI', 11), wrap='word', padx=20, pady=20,
                                        relief='flat')
        txt.pack(fill='both', expand=True, padx=20, pady=20)
        tutorial = """Willkommen bei TrainerHub!

So aktivierst du einen Trainer:
1. Starte dein Singleplayer-Spiel.
2. Wähle das Spiel im Dropdown oben aus.
3. Klicke auf '🔍 Prozess prüfen' (F5).
4. Wähle einen Trainer aus der Liste.
5. Klicke auf '2-Scan starten' und gib deinen aktuellen Wert ein.
6. Ändere den Wert im Spiel (z.B. etwas kaufen).
7. Gib den neuen Wert ein.
8. TrainerHub findet die Adresse und setzt sie auf deinen Zielwert.

SMAPI Bridge (Stardew Valley):
- Installiere SMAPI und den TrainerHub Bridge Mod.
- Cheats funktionieren dann direkt über die Konsole.

Regeln:
• Nur Singleplayer verwenden.
• Niemals in Online/Multiplayer-Cheats nutzen.
• Vor Savegame-Editoren immer ein Backup erstellen.

Tastenkürzel:
• F5 = Prozess prüfen
• F1 = Tutorial öffnen
"""
        txt.insert('1.0', tutorial)
        txt.config(state='disabled')

    def logout(self):
        self.api_key = None
        self.config['api_key'] = None
        save_config(self.config)
        self.premium_data = {}
        self.user_info = {}
        self.show_login()

    # ----------------------------- SCAN / MEMORY -----------------------------
    def scan_with_two_values(self, trainer):
        if not WINDOWS or not pymem:
            messagebox.showinfo("Nur Windows", "Memory-Scan braucht Windows.")
            return
        if not self.current_game_pid:
            self.check_process()
            if not self.current_game_pid:
                messagebox.showwarning("Spiel nicht gefunden", "Starte das Spiel zuerst.")
                return
        label = trainer.get('name', 'Wert')
        vt = 'float' if any(x in label.lower() for x in ['energie','ausdauer','sauerstoff','health','hp','stamina']) else 'int32'
        win = tk.Toplevel(self.root)
        win.title(f"2-Scan: {label}")
        win.geometry("420x360")
        win.configure(bg=ModernStyle.BG)
        card = RoundedFrame(win, radius=16, bg=ModernStyle.BG_CARD, border_color=ModernStyle.BORDER)
        card.pack(fill='both', expand=True, padx=20, pady=20)
        inner = card.inner
        inner.configure(padx=20, pady=20)
        
        tk.Label(inner, text=f"2-Scan: {label}", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT,
                 font=('Segoe UI', 16, 'bold')).pack(anchor='w')
        
        tk.Label(inner, text="1. Aktueller Wert:", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED,
                 font=('Segoe UI', 10)).pack(anchor='w', pady=(15,5))
        val1 = tk.Entry(inner, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT, relief='flat', font=('Segoe UI', 11))
        val1.pack(fill='x', ipady=5)
        
        tk.Label(inner, text="2. Neuer Wert nach Änderung im Spiel:", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED,
                 font=('Segoe UI', 10)).pack(anchor='w', pady=(15,5))
        val2 = tk.Entry(inner, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT, relief='flat', font=('Segoe UI', 11))
        val2.pack(fill='x', ipady=5)
        
        tk.Label(inner, text="Zielwert:", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED,
                 font=('Segoe UI', 10)).pack(anchor='w', pady=(15,5))
        target = tk.Entry(inner, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT, relief='flat', font=('Segoe UI', 11))
        target.insert(0, '999999')
        target.pack(fill='x', ipady=5)
        
        result = tk.Label(inner, text="Bereit.", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED,
                          font=('Segoe UI', 10))
        result.pack(anchor='w', pady=(15,0))
        
        def start():
            try:
                v1 = int(val1.get())
                v2 = int(val2.get())
                vtarg = int(target.get())
                threading.Thread(target=self._two_value_worker, args=(v1, v2, vtarg, vt, label, result)).start()
                result.config(text="Scan läuft...", fg=ModernStyle.WARNING)
            except ValueError:
                result.config(text="Bitte gültige Zahlen eingeben.", fg=ModernStyle.DANGER)
        
        AnimatedButton(inner, text="Scan starten", command=start, width=160, height=36).pack(anchor='e', pady=(15,0))

    def _two_value_worker(self, v1, v2, target, value_type, label, result_label):
        try:
            pm = Pymem(self.current_game_pid)
            pack_fmt = '<i' if value_type == 'int32' else '<f'
            b1 = struct.pack(pack_fmt, v1 if value_type == 'int32' else float(v1))
            b2 = struct.pack(pack_fmt, v2 if value_type == 'int32' else float(v2))
            candidates = []
            regions = self._get_regions(pm)
            self.log(f"Scanne {len(regions)} Regionen nach {v1}...")
            for start, end in regions:
                try:
                    size = min(end - start, 0x10000000)
                    data = pm.read_bytes(start, size)
                    idx = 0
                    while True:
                        idx = data.find(b1, idx)
                        if idx == -1: break
                        candidates.append(start + idx)
                        idx += 1
                        if len(candidates) > 20000: break
                except Exception: continue
                if len(candidates) > 20000: break
            self.log(f"Erster Scan: {len(candidates)} Kandidaten")
            if not candidates:
                result_label.config(text="Keine Treffer. Wert im Spiel geändert?", fg=ModernStyle.DANGER)
                pm.close_process(); return
            confirmed = []
            for addr in candidates[:10000]:
                try:
                    if pm.read_bytes(addr, 4) == b2:
                        confirmed.append(addr)
                except Exception: pass
            self.log(f"Zweiter Scan: {len(confirmed)} Adressen")
            if len(confirmed) == 1:
                addr = confirmed[0]
                if self._write_value(pm, addr, target, value_type):
                    self.log(f"✅ {label} auf {target} gesetzt! ({hex(addr)})", 'success')
                    result_label.config(text=f"✅ Gesetzt: {hex(addr)}", fg=ModernStyle.SUCCESS)
                    self._freeze_address(pm, addr, target, value_type, label)
                    self.log_activation(label, success=True)
                else:
                    result_label.config(text="Schreiben fehlgeschlagen", fg=ModernStyle.DANGER)
                    self.log_activation(label, success=False)
                    pm.close_process()
            elif len(confirmed) > 1:
                self.log(f"{len(confirmed)} Adressen gefunden. Ändere den Wert erneut für einen 3-Scan.")
                result_label.config(text=f"{len(confirmed)} Treffer. 3-Scan nötig.", fg=ModernStyle.WARNING)
                self.scan_state = {'pm': pm, 'value_type': value_type, 'target': target, 'label': label, 'addresses': confirmed}
            else:
                result_label.config(text="Keine Adresse bestätigt.", fg=ModernStyle.DANGER)
                pm.close_process()
        except Exception as e:
            self.log(f"Scan-Fehler: {e}", 'error')
            result_label.config(text=f"Fehler: {e}", fg=ModernStyle.DANGER)

    def _get_regions(self, pm):
        regions = []
        addr = 0x10000
        while True:
            try:
                mbi = pymem.memory.virtual_query(pm.process_handle, addr)
                if mbi.State == 0x1000 and mbi.Protect in (0x04, 0x20, 0x40, 0x02):
                    regions.append((mbi.BaseAddress, mbi.BaseAddress + mbi.RegionSize))
                addr = mbi.BaseAddress + mbi.RegionSize
                if addr > 0x7FFF00000000: break
            except Exception: break
        return regions

    def _write_value(self, pm, address, value, value_type):
        try:
            if value_type == 'int32': pm.write_int(address, int(value))
            elif value_type == 'float': pm.write_float(address, float(value))
            elif value_type == 'bytes': pm.write_bytes(address, value, len(value))
            return True
        except Exception: return False

    def _freeze_address(self, pm, address, value, value_type, label):
        if label in self.freeze_threads:
            self.freeze_threads[label]['stop'] = True
        stop_flag = {'stop': False}
        self.freeze_threads[label] = stop_flag
        def loop():
            while not stop_flag['stop']:
                try:
                    self._write_value(pm, address, value, value_type)
                    time.sleep(0.5)
                except Exception: break
            try: pm.close_process()
            except Exception: pass
        threading.Thread(target=loop, daemon=True).start()
        self.log(f"🧊 {label} freeze aktiviert.", 'success')

    # ----------------------------- SAVEGAME / SMAPI -----------------------------
    def open_savegame_editor(self, trainer):
        if not SDV_SAVE:
            messagebox.showinfo("Nicht verfügbar", "Savegame-Editor nicht geladen.")
            return
        saves = sdv_savegame.list_saves()
        if not saves:
            messagebox.showwarning("Keine Saves", "Keine Stardew Valley-Savegames gefunden.")
            return
        win = tk.Toplevel(self.root)
        win.title("Savegame Editor")
        win.geometry("520x440")
        win.configure(bg=ModernStyle.BG)
        card = RoundedFrame(win, radius=16, bg=ModernStyle.BG_CARD, border_color=ModernStyle.BORDER)
        card.pack(fill='both', expand=True, padx=20, pady=20)
        inner = card.inner
        inner.configure(padx=20, pady=20)
        tk.Label(inner, text="Savegame auswählen", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT,
                 font=('Segoe UI', 14, 'bold')).pack(anchor='w')
        listbox = tk.Listbox(inner, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT, font=('Segoe UI', 10), height=8)
        listbox.pack(fill='x', pady=(15,10))
        for save in saves:
            listbox.insert(tk.END, save['name'])
        info_text = scrolledtext.ScrolledText(inner, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT,
                                              font=('Consolas', 9), height=8, relief='flat')
        info_text.pack(fill='both', expand=True)
        
        def load():
            idx = listbox.curselection()
            if not idx: return
            path = saves[idx[0]]['path']
            info = sdv_savegame.read_save(path)
            if info:
                info_text.delete(1.0, tk.END)
                info_text.insert(tk.END, json.dumps(info, indent=2))
                win.current_path = path
        
        def set_val():
            if not hasattr(win, 'current_path'):
                messagebox.showwarning("Zuerst laden", "Bitte Savegame laden.")
                return
            val = simpledialog.askinteger("Neuer Wert", "Wert:", initialvalue=999999)
            if val is None: return
            if sdv_savegame.write_save(win.current_path, {'money': val}):
                self.log(f"Savegame: money auf {val} gesetzt", 'success')
                messagebox.showinfo("Erfolg", f"money auf {val} gesetzt!")
            else:
                messagebox.showerror("Fehler", "Schreiben fehlgeschlagen.")
        
        tk.Button(inner, text="Laden", bg=ModernStyle.ACCENT, fg='#fff', relief='flat',
                  font=('Segoe UI', 10, 'bold'), command=load).pack(side='left', pady=(10,0))
        tk.Button(inner, text="Money setzen", bg=ModernStyle.GOLD, fg='#000', relief='flat',
                  font=('Segoe UI', 10, 'bold'), command=set_val).pack(side='right', pady=(10,0))

    def smapi_set(self, trainer):
        if not BRIDGE:
            messagebox.showinfo("Nicht verfügbar", "SMAPI Bridge nicht geladen.")
            return
        name = trainer.get('name', '').lower()
        stat = 'money'
        if 'health' in name: stat = 'health'
        elif 'stamina' in name or 'energy' in name: stat = 'stamina'
        if not self.bridge_client:
            client = stardew_bridge.StardewBridgeClient()
            if client.connect(timeout=3.0):
                self.bridge_client = client
                self.log("SMAPI Bridge verbunden.", 'success')
            else:
                messagebox.showwarning("SMAPI Bridge", "Verbindung fehlgeschlagen. SMAPI + Mod installiert?")
                self.log_activation(f"SMAPI {stat}", success=False)
                return
        init = 999999 if stat == 'money' else 9999
        val = simpledialog.askinteger("SMAPI Wert", f"Neuer Wert für {stat}:", initialvalue=init)
        if val is None: return
        resp = self.bridge_client.set(stat, val)
        self.log(f"SMAPI: {stat} -> {val} ({resp})")
        if resp and resp.startswith('ok'):
            messagebox.showinfo("Erfolg", f"{stat} auf {val} gesetzt!")
            self.log_activation(f"SMAPI {stat}", success=True)
        else:
            messagebox.showerror("Fehler", f"SMAPI Fehler: {resp}")
            self.log_activation(f"SMAPI {stat}", success=False)

    def open_savegame_editor(self, trainer):
        if not SDV_SAVE:
            messagebox.showinfo("Nicht verfügbar", "Savegame-Editor nicht geladen.")
            return
        saves = sdv_savegame.list_saves()
        if not saves:
            messagebox.showwarning("Keine Saves", "Keine Stardew Valley-Savegames gefunden.")
            return
        win = tk.Toplevel(self.root)
        win.title("Savegame Editor")
        win.geometry("520x440")
        win.configure(bg=ModernStyle.BG)
        card = RoundedFrame(win, radius=16, bg=ModernStyle.BG_CARD, border_color=ModernStyle.BORDER)
        card.pack(fill='both', expand=True, padx=20, pady=20)
        inner = card.inner
        inner.configure(padx=20, pady=20)
        tk.Label(inner, text="Savegame auswählen", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT,
                 font=('Segoe UI', 14, 'bold')).pack(anchor='w')
        listbox = tk.Listbox(inner, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT, font=('Segoe UI', 10), height=8)
        listbox.pack(fill='x', pady=(15,10))
        for save in saves:
            listbox.insert(tk.END, save['name'])
        info_text = scrolledtext.ScrolledText(inner, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT,
                                              font=('Consolas', 9), height=8, relief='flat')
        info_text.pack(fill='both', expand=True, padx=20, pady=10)
        
        def load():
            idx = listbox.curselection()
            if not idx: return
            path = saves[idx[0]]['path']
            info = sdv_savegame.read_save(path)
            if info:
                info_text.delete(1.0, tk.END)
                info_text.insert(tk.END, json.dumps(info, indent=2))
                win.current_path = path
        
        def set_val():
            if not hasattr(win, 'current_path'):
                messagebox.showwarning("Zuerst laden", "Bitte Savegame laden.")
                return
            val = simpledialog.askinteger("Neuer Wert", "Wert:", initialvalue=999999)
            if val is None: return
            if sdv_savegame.write_save(win.current_path, {'money': val}):
                self.log(f"Savegame: money auf {val} gesetzt", 'success')
                self.log_activation("Savegame money", success=True)
                messagebox.showinfo("Erfolg", f"money auf {val} gesetzt!")
            else:
                self.log_activation("Savegame money", success=False)
                messagebox.showerror("Fehler", "Schreiben fehlgeschlagen.")
        
        tk.Button(inner, text="Laden", bg=ModernStyle.ACCENT, fg='#fff', relief='flat',
                  font=('Segoe UI', 10, 'bold'), command=load).pack(side='left', pady=(10,0))
        tk.Button(inner, text="Money setzen", bg=ModernStyle.GOLD, fg='#000', relief='flat',
                  font=('Segoe UI', 10, 'bold'), command=set_val).pack(side='right', pady=(10,0))

    def open_pattern_learner(self, trainer):
        if not WINDOWS or not pymem:
            messagebox.showinfo("Nur Windows", "Pattern-Lernen braucht Windows.")
            return
        if not self.current_game_pid:
            self.check_process()
            if not self.current_game_pid:
                messagebox.showwarning("Spiel nicht gefunden", "Starte das Spiel zuerst.")
                return
        if not PATTERN_LEARNER:
            messagebox.showinfo("Nicht verfügbar", "Pattern-Learner Modul fehlt.")
            return
        
        win = tk.Toplevel(self.root)
        win.title("Pattern Learner")
        win.geometry("520x480")
        win.configure(bg=ModernStyle.BG)
        card = RoundedFrame(win, radius=16, bg=ModernStyle.BG_CARD, border_color=ModernStyle.BORDER)
        card.pack(fill='both', expand=True, padx=20, pady=20)
        inner = card.inner
        inner.configure(padx=20, pady=20)
        tk.Label(inner, text="Pattern Learner", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT,
                 font=('Segoe UI', 16, 'bold')).pack(anchor='w')
        tk.Label(inner, text="Finde stabile Memory-Adressen selbst.", bg=ModernStyle.BG_CARD,
                 fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 10)).pack(anchor='w', pady=(5,0))
        
        tk.Label(inner, text="Aktueller Wert:", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED,
                 font=('Segoe UI', 10)).pack(anchor='w', pady=(20,5))
        val1 = tk.Entry(inner, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT, relief='flat', font=('Segoe UI', 11))
        val1.pack(fill='x', ipady=5)
        
        tk.Label(inner, text="Wert-Typ:", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED,
                 font=('Segoe UI', 10)).pack(anchor='w', pady=(15,5))
        vtype = ttk.Combobox(inner, values=['int32','float','int64','int8','int16','double'], state='readonly')
        vtype.set('int32')
        vtype.pack(fill='x')
        
        result = tk.Label(inner, text="Bereit.", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 10))
        result.pack(anchor='w', pady=(15,0))
        
        learner = None
        addrs = []
        
        def do_scan():
            nonlocal learner, addrs
            try:
                learner = PatternLearner(self.current_game_pid)
                value = int(val1.get())
                addrs = learner.first_scan(value, vtype.get())
                result.config(text=f"Gefunden: {len(addrs)} Adressen", fg=ModernStyle.SUCCESS)
            except Exception as e:
                result.config(text=f"Fehler: {e}", fg=ModernStyle.DANGER)
        
        def do_filter():
            nonlocal addrs
            if not learner or not addrs:
                result.config(text="Zuerst scannen.", fg=ModernStyle.DANGER); return
            try:
                value = int(val1.get())
                addrs = learner.next_scan(value)
                result.config(text=f"Nach Filter: {len(addrs)} Adressen", fg=ModernStyle.SUCCESS)
                if len(addrs) <= 5:
                    for a in addrs:
                        pattern = learner.generate_pattern(a)
                        self.log(f"Pattern: {hex(a)} - {pattern[:50]}...")
            except Exception as e:
                result.config(text=f"Fehler: {e}", fg=ModernStyle.DANGER)
        
        AnimatedButton(inner, text="1. Scan starten", command=do_scan, width=160, height=36).pack(anchor='w', pady=(20,8))
        AnimatedButton(inner, text="2. Filter / Pattern", command=do_filter, width=160, height=36,
                       bg=ModernStyle.SUCCESS).pack(anchor='w')

    # ----------------------------- BACKGROUND -----------------------------
    def start_background_tasks(self):
        def heartbeat():
            while True:
                time.sleep(60)
                if self.api_key:
                    self.api_call('billing.php?action=status')
        threading.Thread(target=heartbeat, daemon=True).start()
        
        def update_check():
            if not self.config.get('auto_update_check', True):
                return
            try:
                from features import UpdateNotifier
                notifier = UpdateNotifier(APP_VERSION, self.api_base, self.log)
                new_ver, url = notifier.check()
                if new_ver:
                    self.log(f"Update verfügbar: {new_ver} → {url}", 'warning')
            except Exception:
                pass
        threading.Thread(target=update_check, daemon=True).start()

    def apply_theme(self, theme_name):
        from features import ThemeManager
        self.theme_manager = ThemeManager()
        theme = self.theme_manager.apply(theme_name)
        # Apply colors to main window
        self.root.configure(bg=theme['bg'])
        # Note: full dynamic theme switching with ttk requires rebuilding styles
        # For now we store and apply on next restart, plus update header
        if hasattr(self, 'header'):
            self.header.config(bg=theme['bg'])
            self.brand.config(bg=theme['bg'])
            self.status_frame.config(bg=theme['bg'])

    def init_hotkeys(self):
        if not self.config.get('global_hotkeys', False):
            return
        try:
            from features import HotkeyManager
            self.hotkey_manager = HotkeyManager(self.log)
            self.hotkey_manager.register('f9', self.check_process, 'Prozess prüfen')
            self.hotkey_manager.start()
            self.log("Globale Hotkeys aktiviert (F9 = Prozess prüfen).")
        except Exception as e:
            self.log(f"Hotkey-Init fehlgeschlagen: {e}")

    def log_activation(self, trainer_name, success=True):
        try:
            from features import ConfigSync
            sync = ConfigSync(self.api_base, self.api_key, self.log)
            sync.log_history(trainer_name, self.current_game or '', success)
        except Exception as e:
            self.log(f"Log-Aktivierung fehlgeschlagen: {e}")

    def sync_favorites(self):
        try:
            from features import ConfigSync
            sync = ConfigSync(self.api_base, self.api_key, self.log)
            # Upload
            resp = sync.upload_favorites(self.favorites)
            if resp.get('success'):
                self.log("Favoriten in Cloud gespeichert.", 'success')
            # Download
            down = sync.download_favorites()
            if down.get('success') and 'favorites' in down.get('config', {}):
                cloud = set(down['config']['favorites'])
                if cloud != self.favorites:
                    self.favorites = cloud
                    self.config['favorites'] = list(cloud)
                    save_config(self.config)
                    self.log(f"{len(cloud)} Favoriten aus Cloud geladen.", 'success')
                    if hasattr(self, 'stat_value_label'):
                        self.render_trainers()
        except Exception as e:
            self.log(f"Cloud-Sync fehlgeschlagen: {e}")

    def show_changelog(self, first_start=False):
        data = self.api_call('changelog.php')
        if not data.get('success'):
            if not first_start:
                messagebox.showerror("Fehler", "Changelog konnte nicht geladen werden.")
            return
        versions = data.get('versions', [])
        if first_start and versions:
            last_seen = self.config.get('last_seen_changelog', '')
            if last_seen == versions[0].get('version'):
                return
        
        win = tk.Toplevel(self.root)
        win.title("Changelog")
        win.geometry("520x600")
        win.configure(bg=ModernStyle.BG)
        card = RoundedFrame(win, radius=16, bg=ModernStyle.BG_CARD, border_color=ModernStyle.BORDER)
        card.pack(fill='both', expand=True, padx=20, pady=20)
        inner = card.inner
        inner.configure(padx=25, pady=25)
        tk.Label(inner, text="Was ist neu?", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT,
                 font=('Segoe UI', 18, 'bold')).pack(anchor='w')
        tk.Label(inner, text="TrainerHub Updates", bg=ModernStyle.BG_CARD,
                 fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 10)).pack(anchor='w', pady=(5,15))
        
        container = tk.Frame(inner, bg=ModernStyle.BG_CARD)
        container.pack(fill='both', expand=True)
        for v in versions[:5]:
            vcard = tk.Frame(container, bg=ModernStyle.BG_CARD, highlightbackground=ModernStyle.BORDER, highlightthickness=1, bd=0)
            vcard.pack(fill='x', pady=(0,10))
            tk.Label(vcard, text=f"v{v.get('version')} — {v.get('date')}", bg=ModernStyle.BG_CARD,
                     fg=ModernStyle.ACCENT, font=('Segoe UI', 11, 'bold')).pack(anchor='w', padx=15, pady=(10,0))
            tk.Label(vcard, text=v.get('title', ''), bg=ModernStyle.BG_CARD,
                     fg=ModernStyle.TEXT, font=('Segoe UI', 10, 'bold')).pack(anchor='w', padx=15, pady=(5,0))
            for c in v.get('changes', []):
                tk.Label(vcard, text=f"• {c}", bg=ModernStyle.BG_CARD,
                         fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 9), wraplength=400).pack(anchor='w', padx=15, pady=(2,0))
            tk.Label(vcard, text='', bg=ModernStyle.BG_CARD).pack(pady=(5,0))
        
        if versions:
            self.config['last_seen_changelog'] = versions[0].get('version')
            save_config(self.config)
        
        AnimatedButton(inner, text="Schließen", command=win.destroy, width=120, height=36).pack(anchor='e', pady=(15,0))

    def show_history(self):
        data = self.api_call('trainer-logs.php?action=list&limit=100')
        stats = self.api_call('trainer-logs.php?action=stats')
        
        win = tk.Toplevel(self.root)
        win.title("Trainer-Verlauf")
        win.geometry("640x520")
        win.configure(bg=ModernStyle.BG)
        card = RoundedFrame(win, radius=16, bg=ModernStyle.BG_CARD, border_color=ModernStyle.BORDER)
        card.pack(fill='both', expand=True, padx=20, pady=20)
        inner = card.inner
        inner.configure(padx=25, pady=25)
        tk.Label(inner, text="Dein Trainer-Verlauf", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT,
                 font=('Segoe UI', 18, 'bold')).pack(anchor='w')
        
        # Mini chart from log counts per day
        if data.get('success') and data.get('logs'):
            from collections import Counter
            days = Counter()
            for l in data['logs']:
                day = time.strftime('%d.%m', time.localtime(l.get('created_at', 0)))
                days[day] += 1
            labels = list(days.keys())[:14][::-1]
            values = [days.get(d, 0) for d in labels]
            max_v = max(values) if values else 1
            chart_frame = tk.Frame(inner, bg=ModernStyle.BG_CARD)
            chart_frame.pack(fill='x', pady=(15,0))
            tk.Label(chart_frame, text="Aktivierungen/Tag", bg=ModernStyle.BG_CARD,
                     fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 10)).pack(anchor='w')
            bars = tk.Frame(chart_frame, bg=ModernStyle.BG_CARD)
            bars.pack(fill='x', pady=(10,0))
            for d, v in zip(labels, values):
                col = tk.Frame(bars, bg=ModernStyle.BG_CARD)
                col.pack(side='left', expand=True)
                h = max(20, int((v / max_v) * 80))
                bar = tk.Frame(col, bg=ModernStyle.ACCENT, width=30, height=h)
                bar.pack()
                tk.Label(col, text=str(v), bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED,
                         font=('Segoe UI', 8)).pack()
                tk.Label(col, text=d, bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED,
                         font=('Segoe UI', 7)).pack()
        
        # Stats
        if stats.get('success'):
            sf = tk.Frame(inner, bg=ModernStyle.BG_CARD)
            sf.pack(fill='x', pady=(20,0))
            for lbl, val, col in [
                ('Gesamt', stats.get('total_activations', 0), ModernStyle.TEXT),
                ('Erfolgreich', stats.get('successful', 0), ModernStyle.SUCCESS),
                ('Fehler', stats.get('failed', 0), ModernStyle.DANGER)
            ]:
                c = tk.Frame(sf, bg=ModernStyle.BG_CARD)
                c.pack(side='left', expand=True)
                tk.Label(c, text=str(val), bg=ModernStyle.BG_CARD, fg=col, font=('Segoe UI', 20, 'bold')).pack()
                tk.Label(c, text=lbl, bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 9)).pack()
        
        listbox = scrolledtext.ScrolledText(inner, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT,
                                            font=('Consolas', 9), height=12, relief='flat')
        listbox.pack(fill='both', expand=True, pady=(15,0))
        for l in data.get('logs', [])[:50]:
            t = time.strftime('%d.%m.%Y %H:%M', time.localtime(l.get('created_at', 0)))
            s = '✅' if l.get('success') else '❌'
            listbox.insert(tk.END, f"{t} {s} {l.get('action', '?')} ({l.get('game_name', '?')} / {l.get('trainer_name', '?')})\n")

    def start_smapipoll(self):
        if not BRIDGE:
            return
        self.smapipoll_active = False
        def poll():
            last_values = {}
            while True:
                time.sleep(5)
                if self.current_game == 'stardew-valley':
                    try:
                        if not self.bridge_client:
                            client = stardew_bridge.StardewBridgeClient()
                            if client.connect(timeout=1.0):
                                self.bridge_client = client
                                self.log("SMAPI Bridge verbunden.", 'success')
                        if self.bridge_client:
                            vals = {}
                            for stat in ['money', 'health', 'stamina']:
                                vals[stat] = self.bridge_client.get(stat)
                            if vals != last_values:
                                last_values = vals
                                self.log(f"SMAPI Live | ${vals.get('money','?')} | HP {vals.get('health','?')} | Energy {vals.get('stamina','?')}", 'info')
                    except Exception:
                        pass
        threading.Thread(target=poll, daemon=True).start()

    def open_multi_freeze_manager(self):
        win = tk.Toplevel(self.root)
        win.title("Multi-Game Freeze Manager")
        win.geometry("580x480")
        win.configure(bg=ModernStyle.BG)
        card = RoundedFrame(win, radius=16, bg=ModernStyle.BG_CARD, border_color=ModernStyle.BORDER)
        card.pack(fill='both', expand=True, padx=20, pady=20)
        inner = card.inner
        inner.configure(padx=20, pady=20)
        tk.Label(inner, text="Freeze Manager", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT,
                 font=('Segoe UI', 16, 'bold')).pack(anchor='w')
        tk.Label(inner, text="Aktive Freeze-Threads und Adressen", bg=ModernStyle.BG_CARD,
                 fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 10)).pack(anchor='w', pady=(5,0))
        
        listbox = tk.Listbox(inner, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT, font=('Consolas', 10), height=12)
        listbox.pack(fill='both', expand=True, pady=(15,0))
        
        def refresh():
            listbox.delete(0, tk.END)
            for key, t in list(self.freeze_threads.items()):
                status = 'läuft' if t.is_alive() else 'gestoppt'
                listbox.insert(tk.END, f"{key} — {status}")
        
        AnimatedButton(inner, text="Aktualisieren", command=refresh, width=120, height=34).pack(anchor='w', pady=(10,0))
        refresh()



def check_for_updates_gui():
    try:
        r = urllib.request.urlopen('https://sayfespace.online/trainerhub/api/version.php', timeout=10)
        data = json.loads(r.read().decode('utf-8'))
        if data.get('success') and data.get('version') != APP_VERSION:
            return data.get('download_url')
    except Exception:
        pass
    return None


def main():
    update_url = check_for_updates_gui()
    root = tk.Tk()
    if update_url:
        root.withdraw()
        if messagebox.askyesno("Update verfügbar", "Eine neue Version ist verfügbar. Im Browser öffnen?"):
            import webbrowser
            webbrowser.open(update_url)
            return
    TrainerHubApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
