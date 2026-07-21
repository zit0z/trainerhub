"""TrainerHub Desktop Application - Modern Sidebar UI Edition"""
import sys
import os
import json
import time
import threading
import struct
import urllib.request
import urllib.error

APP_VERSION = '0.5.6'
CONFIG_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'TrainerHub')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
API_BASE = os.environ.get('TRAINERHUB_API', 'https://sayfespace.online/trainerhub/api')

os.makedirs(CONFIG_DIR, exist_ok=True)

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext, simpledialog
except ImportError:
    print("tkinter fehlt")
    sys.exit(1)

from ui_components import ModernStyle, StatusBadge, AnimatedButton

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
        self.root.title(f"TrainerHub {APP_VERSION}")
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
        self.search_var = tk.StringVar()

        self.build_ui()
        if self.api_key:
            self.validate_key()
        else:
            self.show_login()
        self.apply_theme(self.config.get('theme', 'dark'))
        self.start_background_tasks()

    # ----------------------------- UI BUILD -----------------------------
    def build_ui(self):
        # Main container with sidebar + content
        self.main_frame = tk.Frame(self.root, bg=ModernStyle.BG)
        self.main_frame.pack(fill='both', expand=True)

        # Sidebar
        self.sidebar = tk.Frame(self.main_frame, bg=ModernStyle.BG_CARD, width=240)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="TRAINERHUB", font=('Segoe UI', 16, 'bold'),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.ACCENT).pack(pady=(20, 30))

        self.nav_buttons = []
        self._nav_btn("Dashboard", self.show_dashboard, active=True)
        self._nav_btn("Spielebibliothek", self.show_games_library)
        self._nav_btn("Favoriten", lambda: self.show_games_library(filter_favorites=True))
        self._nav_btn("Account", self.show_account)
        self._nav_btn("Einstellungen", self.show_settings)

        self.sidebar_status = tk.Label(self.sidebar, text="● Offline", font=('Segoe UI', 9),
                                       bg=ModernStyle.BG_CARD, fg=ModernStyle.DANGER)
        self.sidebar_status.pack(side='bottom', pady=15)

        # Header
        self.header = tk.Frame(self.main_frame, bg=ModernStyle.BG, height=64)
        self.header.pack(side='top', fill='x', padx=25, pady=(15, 0))
        self.header.pack_propagate(False)

        self.page_title = tk.Label(self.header, text="Dashboard", font=('Segoe UI', 20, 'bold'),
                                   bg=ModernStyle.BG, fg=ModernStyle.TEXT)
        self.page_title.pack(side='left')

        self.status_frame = tk.Frame(self.header, bg=ModernStyle.BG)
        self.status_frame.pack(side='right')

        self.premium_badge = StatusBadge(self.status_frame, "FREE", ModernStyle.TEXT_MUTED)
        self.premium_badge.pack(side='left', padx=(0, 12))

        tk.Button(self.status_frame, text="Logout", bg=ModernStyle.BG_CARD, fg=ModernStyle.DANGER,
                  relief='flat', font=('Segoe UI', 10), padx=15, pady=5,
                  command=self.logout).pack(side='left')

        # Content area
        self.content = tk.Frame(self.main_frame, bg=ModernStyle.BG)
        self.content.pack(side='top', fill='both', expand=True, padx=25, pady=15)

        # Statusbar
        self.statusbar = tk.Frame(self.root, bg=ModernStyle.BG_CARD, height=28)
        self.statusbar.pack(fill='x', side='bottom')
        self.statusbar.pack_propagate(False)
        self.status_text = tk.Label(self.statusbar, text="Bereit", bg=ModernStyle.BG_CARD,
                                    fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 9))
        self.status_text.pack(side='left', padx=12, pady=4)
        self.version_label = tk.Label(self.statusbar, text=f"v{APP_VERSION}", bg=ModernStyle.BG_CARD,
                                      fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 9))
        self.version_label.pack(side='right', padx=12, pady=4)

    def _nav_btn(self, text, command, active=False):
        bg = ModernStyle.ACCENT if active else ModernStyle.BG_CARD
        fg = '#ffffff' if active else ModernStyle.TEXT
        btn = tk.Button(self.sidebar, text=text, font=('Segoe UI', 11), bg=bg, fg=fg,
                        relief='flat', anchor='w', padx=20, pady=10,
                        activebackground=ModernStyle.BORDER_ACTIVE, activeforeground=ModernStyle.TEXT,
                        command=lambda: (self._set_active_nav(btn), command()))
        btn.pack(fill='x', pady=(0, 4))
        self.nav_buttons.append(btn)
        if active:
            self.active_nav = btn

    def _set_active_nav(self, active_btn):
        for btn in self.nav_buttons:
            btn.config(bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT)
        active_btn.config(bg=ModernStyle.ACCENT, fg='#ffffff')
        self.active_nav = active_btn

    def clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def set_title(self, title):
        self.page_title.config(text=title)

    # ----------------------------- LOGIN -----------------------------
    def show_login(self):
        self.clear_content()
        self.set_title("Anmelden")
        wrapper = tk.Frame(self.content, bg=ModernStyle.BG)
        wrapper.place(relx=0.5, rely=0.5, anchor='center')

        card = tk.Frame(wrapper, bg=ModernStyle.BG_CARD, highlightbackground=ModernStyle.BORDER,
                        highlightthickness=1, bd=0)
        card.pack(padx=60, pady=50)
        inner = tk.Frame(card, bg=ModernStyle.BG_CARD)
        inner.pack(padx=50, pady=40)

        tk.Label(inner, text="Willkommen zurück", font=('Segoe UI', 24, 'bold'),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT).pack()
        tk.Label(inner, text="Singleplayer Trainer für 300+ Spiele", font=('Segoe UI', 12),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack(pady=(5, 35))

        self._form_row(inner, "Benutzername oder E-Mail", 'login_user', False)
        self._form_row(inner, "Passwort", 'login_pass', True)

        AnimatedButton(inner, text="Einloggen", command=self.do_login, width=360, height=44).pack(pady=5)

        self.login_msg = tk.Label(inner, text="", bg=ModernStyle.BG_CARD, fg=ModernStyle.DANGER, font=('Segoe UI', 10))
        self.login_msg.pack(pady=(15, 0))

        tk.Label(inner, text="Noch kein Account? sayfespace.online/trainerhub",
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 9)).pack(pady=(25, 0))

        self.login_user.focus_set()

    def _form_row(self, parent, label, attr, password):
        tk.Label(parent, text=label, bg=ModernStyle.BG_CARD,
                 fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 10)).pack(anchor='w', pady=(0, 5))
        entry = tk.Entry(parent, width=42, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT,
                         insertbackground=ModernStyle.TEXT, relief='flat', font=('Segoe UI', 11))
        if password:
            entry.config(show='*')
        entry.pack(fill='x', ipady=7, pady=(0, 15))
        setattr(self, attr, entry)

    def do_login(self):
        user = self.login_user.get().strip()
        pw = self.login_pass.get()
        if not user or not pw:
            self.login_msg.config(text="Bitte Benutzername und Passwort eingeben.")
            return
        self.login_msg.config(text="Anmelden...", fg=ModernStyle.TEXT_MUTED)
        threading.Thread(target=lambda: self._perform_login(user, pw), daemon=True).start()

    def _perform_login(self, user, pw):
        try:
            data = self.api_call('auth.php?action=login', 'POST', {'email': user, 'password': pw})
            if data.get('success'):
                self.api_key = data['api_key']
                self.config['api_key'] = self.api_key
                save_config(self.config)
                self.root.after(0, self._on_login_success)
            else:
                self.root.after(0, lambda: self.login_msg.config(
                    text=data.get('error', 'Login fehlgeschlagen'), fg=ModernStyle.DANGER))
        except Exception as e:
            self.root.after(0, lambda err=str(e): self.login_msg.config(
                text=f"Netzwerkfehler: {err[:80]}", fg=ModernStyle.DANGER))

    def _on_login_success(self):
        data = self.api_call('billing.php?action=status')
        if data.get('success'):
            self.user_info = data
            self.premium_data = self.api_call('premium.php?action=status')
            status = 'PREMIUM' if self.is_premium() else 'FREE'
            color = ModernStyle.GOLD if self.is_premium() else ModernStyle.TEXT_MUTED
            self.premium_badge = StatusBadge(self.status_frame, status, color)
            self.premium_badge.pack(side='left', padx=(0, 12))
            self.sidebar_status.config(text="● Online", fg=ModernStyle.SUCCESS)
            self.show_dashboard()
            self.init_hotkeys()
            self.check_for_update()
        else:
            self.api_key = None
            self.show_login()
            self.login_msg.config(text="Sitzung abgelaufen. Bitte neu einloggen.", fg=ModernStyle.DANGER)

    # ----------------------------- DASHBOARD -----------------------------
    def show_dashboard(self):
        self.clear_content()
        self.set_title("Dashboard")
        self._set_active_nav(self.nav_buttons[0])

        top = tk.Frame(self.content, bg=ModernStyle.BG)
        top.pack(fill='x', pady=(0, 20))

        stats = [
            ("Spiele", str(len(self.games)) if self.games else "..."),
            ("Trainer", str(len(self.trainers))),
            ("Favoriten", str(len(self.favorites))),
            ("Premium", "AKTIV" if self.is_premium() else "FREE")
        ]
        for label, value in stats:
            card = tk.Frame(top, bg=ModernStyle.BG_CARD, highlightbackground=ModernStyle.BORDER,
                            highlightthickness=1, width=180, height=90)
            card.pack(side='left', padx=(0, 15))
            card.pack_propagate(False)
            tk.Label(card, text=value, font=('Segoe UI', 20, 'bold'),
                     bg=ModernStyle.BG_CARD, fg=ModernStyle.ACCENT).pack(pady=(18, 0))
            tk.Label(card, text=label, font=('Segoe UI', 10),
                     bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack()

        if not self.games:
            self.load_games()

        # Recent games
        recents = tk.Frame(self.content, bg=ModernStyle.BG_CARD, highlightbackground=ModernStyle.BORDER,
                           highlightthickness=1)
        recents.pack(fill='x', pady=(0, 20), ipady=15, ipadx=20)
        tk.Label(recents, text="Zuletzt verwendet", font=('Segoe UI', 14, 'bold'),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT).pack(anchor='w', padx=20, pady=(15, 10))
        recent_container = tk.Frame(recents, bg=ModernStyle.BG_CARD)
        recent_container.pack(fill='x', padx=20, pady=(0, 10))
        if self.recent_games:
            for slug in self.recent_games[:5]:
                game = next((g for g in self.games if g.get('slug') == slug), None)
                if game:
                    self._game_chip(recent_container, game)
        else:
            tk.Label(recent_container, text="Noch keine Spiele ausgewählt", bg=ModernStyle.BG_CARD,
                     fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 10)).pack()

        # Quick actions
        actions = tk.Frame(self.content, bg=ModernStyle.BG)
        actions.pack(fill='x')
        tk.Label(actions, text="Schnellzugriff", font=('Segoe UI', 14, 'bold'),
                 bg=ModernStyle.BG, fg=ModernStyle.TEXT).pack(anchor='w', pady=(0, 10))
        btn_row = tk.Frame(actions, bg=ModernStyle.BG)
        btn_row.pack(fill='x')
        AnimatedButton(btn_row, text="Spielebibliothek öffnen", command=self.show_games_library,
                       width=200, height=40).pack(side='left', padx=(0, 10))
        AnimatedButton(btn_row, text="Prozess prüfen", command=self.check_process,
                       width=160, height=40, bg=ModernStyle.BORDER, hover_bg=ModernStyle.BORDER_ACTIVE).pack(side='left', padx=(0, 10))

    def _game_chip(self, parent, game):
        chip = tk.Frame(parent, bg=ModernStyle.BG_ELEVATED if hasattr(ModernStyle, 'BG_ELEVATED') else '#1a1a24',
                        highlightbackground=ModernStyle.BORDER, highlightthickness=1)
        chip.pack(side='left', padx=(0, 10), pady=5)
        tk.Label(chip, text=game.get('name', 'Unbekannt'), bg=chip.cget('bg'),
                 fg=ModernStyle.TEXT, font=('Segoe UI', 10, 'bold'), padx=15, pady=8).pack()
        chip.bind('<Button-1>', lambda e, g=game: self.select_game(g.get('slug')))
        for child in chip.winfo_children():
            child.bind('<Button-1>', lambda e, g=game: self.select_game(g.get('slug')))

    # ----------------------------- GAMES LIBRARY -----------------------------
    def show_games_library(self, filter_favorites=False):
        self.clear_content()
        self.set_title("Favoriten" if filter_favorites else "Spielebibliothek")
        self._set_active_nav(self.nav_buttons[2] if filter_favorites else self.nav_buttons[1])

        # Search bar
        search_frame = tk.Frame(self.content, bg=ModernStyle.BG)
        search_frame.pack(fill='x', pady=(0, 15))
        tk.Entry(search_frame, textvariable=self.search_var, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT,
                 insertbackground=ModernStyle.TEXT, relief='flat', font=('Segoe UI', 12),
                 highlightbackground=ModernStyle.BORDER, highlightthickness=1).pack(side='left', fill='x', expand=True, ipady=8, padx=(0, 10))
        AnimatedButton(search_frame, text="🔍 Suchen", command=self._render_game_list, width=120, height=38).pack(side='left')
        self.search_var.trace('w', lambda *args: self._render_game_list())

        # Games grid
        self.games_canvas = tk.Canvas(self.content, bg=ModernStyle.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content, orient='vertical', command=self.games_canvas.yview)
        self.games_frame = tk.Frame(self.games_canvas, bg=ModernStyle.BG)
        self.games_frame.bind('<Configure>', lambda e: self.games_canvas.configure(scrollregion=self.games_canvas.bbox('all')))
        self.games_canvas.create_window((0, 0), window=self.games_frame, anchor='nw')
        self.games_canvas.configure(yscrollcommand=scrollbar.set)
        self.games_canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        self._filter_favorites = filter_favorites
        self._render_game_list()

        if not self.games:
            threading.Thread(target=self.load_games, daemon=True).start()

    def _render_game_list(self):
        for w in self.games_frame.winfo_children():
            w.destroy()
        q = self.search_var.get().lower()
        games = self.games
        if self._filter_favorites:
            games = [g for g in games if g.get('name') in self.favorites]
        if q:
            games = [g for g in games if q in g.get('name', '').lower() or q in (g.get('genre') or '').lower()]

        if not games:
            tk.Label(self.games_frame, text="Keine Spiele gefunden", bg=ModernStyle.BG,
                     fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 12)).pack(pady=30)
            return

        for game in games:
            card = tk.Frame(self.games_frame, bg=ModernStyle.BG_CARD, highlightbackground=ModernStyle.BORDER,
                            highlightthickness=1, width=260, height=120)
            card.grid_propagate(False)
            card.pack(side='left', padx=(0, 15), pady=(0, 15))
            card.pack_propagate(False)

            name = game.get('name', 'Unbekannt')
            tk.Label(card, text=name[:30] + ('...' if len(name) > 30 else ''), font=('Segoe UI', 12, 'bold'),
                     bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT).pack(anchor='w', padx=15, pady=(15, 5))
            tk.Label(card, text=f"{game.get('trainer_count', 0)} Trainer", font=('Segoe UI', 10),
                     bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack(anchor='w', padx=15)
            genre = game.get('genre') or 'Singleplayer'
            tk.Label(card, text=genre, font=('Segoe UI', 9),
                     bg=ModernStyle.BG_CARD, fg=ModernStyle.ACCENT).pack(anchor='w', padx=15, pady=(5, 0))

            fav_text = "★" if name in self.favorites else "☆"
            fav_btn = tk.Label(card, text=fav_text, font=('Segoe UI', 14),
                               bg=ModernStyle.BG_CARD, fg=ModernStyle.GOLD if name in self.favorites else ModernStyle.TEXT_MUTED)
            fav_btn.place(relx=0.9, rely=0.2, anchor='center')
            fav_btn.bind('<Button-1>', lambda e, g=game: self._toggle_favorite_game(g))

            card.bind('<Button-1>', lambda e, g=game: self.select_game(g.get('slug')))
            for child in card.winfo_children():
                child.bind('<Button-1>', lambda e, g=game: self.select_game(g.get('slug')))

        self.games_frame.update_idletasks()
        self.games_canvas.configure(scrollregion=self.games_canvas.bbox('all'))

    def _toggle_favorite_game(self, game):
        name = game.get('name')
        if name in self.favorites:
            self.favorites.discard(name)
        else:
            self.favorites.add(name)
        self.config['favorites'] = list(self.favorites)
        save_config(self.config)
        self.sync_favorites()
        self._render_game_list()

    # ----------------------------- GAME DETAIL / TRAINERS -----------------------------
    def select_game(self, slug):
        game = next((g for g in self.games if g.get('slug') == slug), None)
        if not game:
            return
        self.current_game = game
        if slug not in self.recent_games:
            self.recent_games.insert(0, slug)
            self.recent_games = self.recent_games[:10]
            self.config['recent_games'] = self.recent_games
            save_config(self.config)

        self.clear_content()
        self.set_title(game.get('name', 'Spiel'))

        top = tk.Frame(self.content, bg=ModernStyle.BG)
        top.pack(fill='x', pady=(0, 20))
        tk.Label(top, text=game.get('name', ''), font=('Segoe UI', 22, 'bold'),
                 bg=ModernStyle.BG, fg=ModernStyle.TEXT).pack(side='left')
        self.proc_status = tk.Label(top, text="Nicht gestartet", font=('Segoe UI', 10),
                                    bg=ModernStyle.BG, fg=ModernStyle.DANGER)
        self.proc_status.pack(side='left', padx=(20, 0))
        AnimatedButton(top, text="🔍 Prozess prüfen", command=self.check_process,
                       width=150, height=34, bg=ModernStyle.BORDER, hover_bg=ModernStyle.BORDER_ACTIVE).pack(side='right')

        threading.Thread(target=lambda: self.load_trainers(slug), daemon=True).start()

    def load_trainers(self, slug=None):
        if slug is None:
            slug = self.current_game.get('slug') if self.current_game else None
        if not slug:
            return
        data = self.api_call(f'trainers.php?game={slug}')
        self.trainers = data.get('trainers', [])
        self.root.after(0, self.render_trainers)

    def render_trainers(self):
        if hasattr(self, 'trainer_container'):
            for w in self.trainer_container.winfo_children():
                w.destroy()
        else:
            self.trainer_container = tk.Frame(self.content, bg=ModernStyle.BG)
            self.trainer_container.pack(fill='both', expand=True)

        if not self.trainers:
            tk.Label(self.trainer_container, text="Keine Trainer für dieses Spiel verfügbar",
                     bg=ModernStyle.BG, fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 12)).pack(pady=30)
            return

        for trainer in self.trainers:
            card = tk.Frame(self.trainer_container, bg=ModernStyle.BG_CARD, highlightbackground=ModernStyle.BORDER,
                            highlightthickness=1)
            card.pack(fill='x', pady=(0, 10), ipady=12)
            header = tk.Frame(card, bg=ModernStyle.BG_CARD)
            header.pack(fill='x', padx=20, pady=(12, 8))
            tk.Label(header, text=trainer.get('title', 'Trainer'), font=('Segoe UI', 13, 'bold'),
                     bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT).pack(side='left')
            premium = trainer.get('premium', False)
            if premium:
                tk.Label(header, text="PREMIUM", font=('Segoe UI', 8, 'bold'),
                         bg=ModernStyle.GOLD, fg='#000000', padx=8, pady=2).pack(side='left', padx=(10, 0))
            desc = trainer.get('description', '')
            if desc:
                tk.Label(card, text=desc, font=('Segoe UI', 10),
                         bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack(anchor='w', padx=20)

            btn_frame = tk.Frame(card, bg=ModernStyle.BG_CARD)
            btn_frame.pack(fill='x', padx=20, pady=(10, 0))
            AnimatedButton(btn_frame, text="Aktivieren", command=lambda t=trainer: self.activate_trainer(t),
                           width=130, height=34).pack(side='left', padx=(0, 10))
            AnimatedButton(btn_frame, text="Info", command=lambda t=trainer: self.show_trainer_info(t),
                           width=80, height=34, bg=ModernStyle.BORDER, hover_bg=ModernStyle.BORDER_ACTIVE).pack(side='left')

    def activate_trainer(self, trainer):
        ttype = trainer.get('type', 'generic')
        try:
            if ttype == 'memory':
                self.activate_generic(trainer)
            elif ttype == 'savegame':
                self.open_savegame_editor(trainer)
            elif ttype == 'smapi':
                self.smapi_set(trainer)
            elif ttype == 'pattern':
                self.open_pattern_learner(trainer)
            else:
                self.activate_generic(trainer)
        except Exception as e:
            self.log(f"Fehler bei {trainer.get('title')}: {e}", 'error')

    # ----------------------------- API -----------------------------
    def api_call(self, endpoint, method='GET', data=None):
        url = f"{self.api_base}/{endpoint}"
        try:
            if method == 'POST' and data:
                body = json.dumps(data).encode('utf-8')
                req = urllib.request.Request(url, data=body, method='POST',
                                             headers={'Content-Type': 'application/json'})
            else:
                req = urllib.request.Request(url)
            if self.api_key:
                req.add_header('Authorization', f'Bearer {self.api_key}')
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode('utf-8'))
            except Exception:
                return {'success': False, 'error': f'HTTP {e.code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def load_games(self):
        self.set_status("Lade Spiele...")
        data = self.api_call('games.php?per_page=1000')
        if data.get('success'):
            self.games = data.get('games', [])
            self.root.after(0, self._on_games_loaded)
        else:
            self.root.after(0, lambda: self.set_status("Spiele konnten nicht geladen werden"))

    def _on_games_loaded(self):
        self.set_status(f"{len(self.games)} Spiele geladen")
        if hasattr(self, '_render_game_list'):
            self._render_game_list()
        if hasattr(self, 'games_count_label'):
            self.games_count_label.config(text=str(len(self.games)))
        if self.content.winfo_children():
            current = self.content.winfo_children()[0]
            if isinstance(current, tk.Canvas):
                pass

    # ----------------------------- STATUS -----------------------------
    def set_status(self, msg):
        self.root.after(0, lambda: self.status_text.config(text=msg))

    # ----------------------------- PREMIUM -----------------------------
    def is_premium(self):
        try:
            return self.premium_data.get('is_premium', False) or self.user_info.get('subscription_status') == 'premium'
        except Exception:
            return False

    def has_feature(self, feature):
        try:
            return self.premium_data.get('features', {}).get(feature, False)
        except Exception:
            return False

    # ----------------------------- MEMORY / TRAINER ACTIONS -----------------------------
    def check_process(self):
        if not self.current_game:
            messagebox.showinfo("Hinweis", "Bitte zuerst ein Spiel auswählen.")
            return
        pname = self.current_game.get('process_name', '')
        if not pname:
            self.proc_status.config(text="Kein Prozess bekannt", fg=ModernStyle.WARNING)
            return
        if not WINDOWS or not pymem:
            self.proc_status.config(text="Nur unter Windows verfügbar", fg=ModernStyle.WARNING)
            return
        try:
            pm = Pymem(pname)
            self.current_game_pid = pm.process_id
            self.proc_status.config(text=f"Prozess aktiv (PID {pm.process_id})", fg=ModernStyle.SUCCESS)
        except Exception:
            self.proc_status.config(text=f"{pname} nicht gestartet", fg=ModernStyle.DANGER)

    def activate_generic(self, trainer):
        if not self.current_game:
            messagebox.showwarning("Hinweis", "Bitte zuerst ein Spiel auswählen.")
            return
        # Placeholder for real memory writing
        self.log(f"Aktiviert: {trainer.get('title')}")
        self.log_activation(trainer.get('title', 'Unbekannt'), True)

    def open_savegame_editor(self, trainer):
        if SDV_SAVE:
            messagebox.showinfo("Savegame Editor", "Savegame Editor wird geöffnet...")
        else:
            messagebox.showinfo("Savegame Editor", "Savegame-Modul nicht verfügbar.")

    def smapi_set(self, trainer):
        if BRIDGE:
            messagebox.showinfo("SMAPI", "SMAPI-Bridge aktiviert.")
        else:
            messagebox.showinfo("SMAPI", "SMAPI-Bridge nicht verfügbar.")

    def open_pattern_learner(self, trainer):
        if PATTERN_LEARNER:
            messagebox.showinfo("Pattern Learner", "Pattern Learner geöffnet.")
        else:
            messagebox.showinfo("Pattern Learner", "Nicht verfügbar.")

    def show_trainer_info(self, trainer):
        info = trainer.get('description') or "Keine Beschreibung."
        messagebox.showinfo(trainer.get('title', 'Trainer'), info)

    # ----------------------------- LOG -----------------------------
    def log(self, msg, level='info'):
        self.log_lines.append((time.strftime('%H:%M:%S'), level, msg))
        self.set_status(msg)

    def log_activation(self, trainer_name, success=True):
        try:
            self.api_call('trainer-logs.php?action=log', 'POST', {
                'trainer_name': trainer_name,
                'success': success,
                'game': self.current_game.get('name') if self.current_game else 'unknown'
            })
        except Exception as e:
            print(f"Log error: {e}")

    # ----------------------------- ACCOUNT / SETTINGS -----------------------------
    def show_account(self):
        self.clear_content()
        self.set_title("Account")
        self._set_active_nav(self.nav_buttons[3])
        card = tk.Frame(self.content, bg=ModernStyle.BG_CARD, highlightbackground=ModernStyle.BORDER,
                        highlightthickness=1, padx=40, pady=30)
        card.pack(fill='both', expand=True)
        email = self.user_info.get('email', 'Unbekannt')
        username = self.user_info.get('username', 'Unbekannt')
        tk.Label(card, text=f"Benutzer: {username}", font=('Segoe UI', 14),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT).pack(anchor='w', pady=5)
        tk.Label(card, text=f"E-Mail: {email}", font=('Segoe UI', 12),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack(anchor='w', pady=5)
        tk.Label(card, text=f"Premium: {'Ja' if self.is_premium() else 'Nein'}", font=('Segoe UI', 12),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.GOLD if self.is_premium() else ModernStyle.TEXT_MUTED).pack(anchor='w', pady=5)

    def show_settings(self):
        self.clear_content()
        self.set_title("Einstellungen")
        self._set_active_nav(self.nav_buttons[4])
        card = tk.Frame(self.content, bg=ModernStyle.BG_CARD, highlightbackground=ModernStyle.BORDER,
                        highlightthickness=1, padx=40, pady=30)
        card.pack(fill='both', expand=True)
        tk.Label(card, text="Einstellungen", font=('Segoe UI', 16, 'bold'),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT).pack(anchor='w', pady=(0, 20))
        tk.Label(card, text="API-Key:", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack(anchor='w')
        key_entry = tk.Entry(card, width=50, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT,
                             insertbackground=ModernStyle.TEXT, relief='flat', font=('Segoe UI', 10))
        key_entry.insert(0, self.api_key or '')
        key_entry.pack(anchor='w', pady=(5, 15), ipady=5)
        AnimatedButton(card, text="Speichern", command=lambda: self._save_settings(key_entry.get()),
                       width=120, height=36).pack(anchor='w')

    def _save_settings(self, key):
        self.api_key = key.strip() or None
        self.config['api_key'] = self.api_key
        save_config(self.config)
        self.set_status("Einstellungen gespeichert")

    # ----------------------------- UPDATER / BACKGROUND -----------------------------
    def check_for_update(self):
        try:
            from updater import check_and_install_update
            check_and_install_update(parent_app=self)
        except Exception as e:
            print(f"Update check failed: {e}")

    def start_background_tasks(self):
        threading.Thread(target=self._keepalive, daemon=True).start()

    def _keepalive(self):
        while True:
            time.sleep(60)
            try:
                if self.api_key:
                    self.api_call('billing.php?action=status')
            except Exception:
                pass

    def apply_theme(self, theme_name):
        pass

    def init_hotkeys(self):
        pass

    def sync_favorites(self):
        try:
            self.api_call('config-sync.php', 'POST', {'favorites': list(self.favorites)})
        except Exception as e:
            print(f"Favorites sync error: {e}")

    def logout(self):
        self.api_key = None
        self.config['api_key'] = None
        save_config(self.config)
        self.premium_badge = StatusBadge(self.status_frame, "FREE", ModernStyle.TEXT_MUTED)
        self.sidebar_status.config(text="● Offline", fg=ModernStyle.DANGER)
        self.show_login()


def main():
    root = tk.Tk()
    app = TrainerHubApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
