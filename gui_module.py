"""TrainerHub Desktop Application — Modern Cyan UI v0.6.0"""
import sys
import os
import json
import time
import threading
import urllib.request
import urllib.error
import logging

APP_VERSION = '0.6.8'
logger = logging.getLogger('TrainerHub.GUI')
CONFIG_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'TrainerHub')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
API_BASE = os.environ.get('TRAINERHUB_API', 'https://sayfespace.online/trainerhub/api')

os.makedirs(CONFIG_DIR, exist_ok=True)

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext, simpledialog
except ImportError:
    logger.error("tkinter fehlt")
    sys.exit(1)

from ui_components import ModernStyle, StatusBadge, AnimatedButton, ToggleSwitch

WINDOWS = sys.platform == 'win32'


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
        logger.error(f"Config save error: {e}")


class TrainerHubApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"TrainerHub {APP_VERSION}")
        self.root.geometry("1366x900")
        self.root.minsize(1200, 750)
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
        self.search_var = tk.StringVar()
        self.user_info = {}
        self.toast_after = None

        self.engine = None
        try:
            from cheat_engine import CheatEngine
            self.engine = CheatEngine()
        except Exception as e:
            logger.exception("Cheat engine load error")

        self.build_ui()
        self.premium_badge = None
        if self.api_key:
            self._on_login_success()
        else:
            self.show_login()
        self.start_background_tasks()

    # ----------------------------- UI BUILD -----------------------------
    def build_ui(self):
        # Top title bar
        self.titlebar = tk.Frame(self.root, bg=ModernStyle.BG, height=70)
        self.titlebar.pack(fill='x', side='top')
        self.titlebar.pack_propagate(False)

        brand = tk.Label(self.titlebar, text="◆ TrainerHub", font=('Rajdhani', 22, 'bold'),
                         bg=ModernStyle.BG, fg=ModernStyle.TEXT)
        brand.pack(side='left', padx=(25, 0), pady=(10, 0))
        sub = tk.Label(self.titlebar, text="SINGLEPLAYER TRAINER", font=('Rajdhani', 10),
                       bg=ModernStyle.BG, fg=ModernStyle.ACCENT)
        sub.place(x=160, y=38)

        self.status_frame = tk.Frame(self.titlebar, bg=ModernStyle.BG)
        self.status_frame.pack(side='right', padx=25, pady=(15, 0))

        self.page_title = tk.Label(self.titlebar, text="", font=('Rajdhani', 18, 'bold'),
                                   bg=ModernStyle.BG, fg=ModernStyle.TEXT)
        self.page_title.place(relx=0.5, y=35, anchor='center')

        # Main frame
        self.main_frame = tk.Frame(self.root, bg=ModernStyle.BG)
        self.main_frame.pack(fill='both', expand=True)

        # Sidebar
        self.sidebar = tk.Frame(self.main_frame, bg=ModernStyle.BG_CARD, width=260)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)

        self._sidebar_profile()
        self._sidebar_sep()
        self.nav_buttons = []
        self._nav_btn("⌂ Dashboard", self.show_dashboard, active=True)
        self._nav_btn("🎮 Spiele", self.show_games_library)
        self._nav_btn("★ Favoriten", lambda: self.show_games_library(filter_favorites=True))
        self._nav_btn("⎋ Account", self.show_account)
        self._nav_btn("⚙ Einstellungen", self.show_settings)

        # Content
        self.content = tk.Frame(self.main_frame, bg=ModernStyle.BG)
        self.content.pack(side='left', fill='both', expand=True, padx=25, pady=20)

        # Toast
        self.toast = tk.Label(self.root, text="", font=('Segoe UI', 10, 'bold'),
                              bg=ModernStyle.ACCENT, fg=ModernStyle.BG, padx=20, pady=10)

        # Statusbar
        self.statusbar = tk.Frame(self.root, bg=ModernStyle.BG_CARD, height=32)
        self.statusbar.pack(fill='x', side='bottom')
        self.statusbar.pack_propagate(False)
        self.status_text = tk.Label(self.statusbar, text="Bereit", bg=ModernStyle.BG_CARD,
                                    fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 9))
        self.status_text.pack(side='left', padx=20, pady=5)
        self.version_label = tk.Label(self.statusbar, text=f"v{APP_VERSION}", bg=ModernStyle.BG_CARD,
                                      fg=ModernStyle.ACCENT, font=('Segoe UI', 9))
        self.version_label.pack(side='right', padx=20, pady=5)

    def _sidebar_profile(self):
        self.profile_card = tk.Frame(self.sidebar, bg=ModernStyle.BG_ELEVATED, padx=20, pady=20)
        self.profile_card.pack(fill='x', padx=15, pady=(20, 10))
        self.profile_card.configure(highlightbackground=ModernStyle.BORDER, highlightthickness=1)

        self.profile_name = tk.Label(self.profile_card, text="Gast", font=('Segoe UI', 14, 'bold'),
                                     bg=ModernStyle.BG_ELEVATED, fg=ModernStyle.TEXT)
        self.profile_name.pack(anchor='w')
        self.profile_status = tk.Label(self.profile_card, text="● Offline", font=('Segoe UI', 9),
                                       bg=ModernStyle.BG_ELEVATED, fg=ModernStyle.DANGER)
        self.profile_status.pack(anchor='w', pady=(5, 0))

    def _sidebar_sep(self):
        tk.Frame(self.sidebar, bg=ModernStyle.BORDER, height=1).pack(fill='x', padx=20, pady=10)

    def _nav_btn(self, text, command, active=False):
        bg = ModernStyle.ACCENT if active else ModernStyle.BG_CARD
        fg = ModernStyle.BG if active else ModernStyle.TEXT
        btn = tk.Button(self.sidebar, text=text, font=('Segoe UI', 12), bg=bg, fg=fg,
                        relief='flat', anchor='w', padx=20, pady=12,
                        activebackground=ModernStyle.BORDER_ACTIVE, activeforeground=ModernStyle.TEXT,
                        command=lambda: (self._set_active_nav(btn), command()))
        btn.pack(fill='x', padx=15, pady=(0, 6))
        self.nav_buttons.append(btn)
        if active:
            self.active_nav = btn

    def _set_active_nav(self, active_btn):
        for btn in self.nav_buttons:
            btn.config(bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT)
        active_btn.config(bg=ModernStyle.ACCENT, fg=ModernStyle.BG)
        self.active_nav = active_btn

    def clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def set_title(self, title):
        self.page_title.config(text=title)

    def show_toast(self, message, color=None, duration=3000):
        color = color or ModernStyle.ACCENT
        self.toast.config(text=message, bg=color, fg=ModernStyle.BG)
        self.toast.place(relx=0.5, y=40, anchor='n')
        if self.toast_after:
            self.root.after_cancel(self.toast_after)
        self.toast_after = self.root.after(duration, self.toast.place_forget)

    # ----------------------------- LOGIN -----------------------------
    def show_login(self):
        self.clear_content()
        self.set_title("Anmelden")
        self._set_active_nav(self.nav_buttons[0])

        wrapper = tk.Frame(self.content, bg=ModernStyle.BG)
        wrapper.place(relx=0.5, rely=0.5, anchor='center')

        card = self._card(wrapper, width=420)
        card.pack(padx=40, pady=40)
        inner = tk.Frame(card, bg=ModernStyle.BG_CARD)
        inner.pack(padx=40, pady=40)

        tk.Label(inner, text="Willkommen zurück", font=('Rajdhani', 26, 'bold'),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT).pack()
        tk.Label(inner, text="Singleplayer Trainer für 300+ Spiele", font=('Segoe UI', 11),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack(pady=(5, 30))

        self._form_input(inner, "Benutzername oder E-Mail", 'login_user')
        self._form_input(inner, "Passwort", 'login_pass', password=True)

        self.login_msg = tk.Label(inner, text="", bg=ModernStyle.BG_CARD, fg=ModernStyle.DANGER, font=('Segoe UI', 10))
        self.login_msg.pack(pady=(5, 15))

        AnimatedButton(inner, text="Einloggen →", command=self.do_login, width=340, height=44).pack()
        tk.Label(inner, text="Registriere dich auf sayfespace.online/trainerhub", font=('Segoe UI', 9),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack(pady=(25, 0))

        self.login_user.focus_set()

    def _card(self, parent, width=None, height=None):
        card = tk.Frame(parent, bg=ModernStyle.BG_CARD, highlightbackground=ModernStyle.BORDER,
                        highlightthickness=1, bd=0)
        if width:
            card.config(width=width)
        if height:
            card.config(height=height)
        return card

    def _form_input(self, parent, label, attr, password=False):
        tk.Label(parent, text=label, bg=ModernStyle.BG_CARD,
                 fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 10)).pack(anchor='w', pady=(0, 5))
        entry = tk.Entry(parent, width=40, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT,
                         insertbackground=ModernStyle.TEXT, relief='flat', font=('Segoe UI', 11),
                         highlightbackground=ModernStyle.BORDER, highlightthickness=1)
        if password:
            entry.config(show='•')
        entry.pack(fill='x', ipady=8, pady=(0, 18))
        setattr(self, attr, entry)

    def do_login(self):
        user = self.login_user.get().strip()
        pw = self.login_pass.get()
        if not user or not pw:
            self.login_msg.config(text="Bitte beide Felder ausfüllen.")
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
        if not data.get('success'):
            self.api_key = None
            self.show_login()
            self.login_msg.config(text="Sitzung ungültig.", fg=ModernStyle.DANGER)
            return
        self.user_info = data
        self.premium_data = self.api_call('premium.php?action=status')

        self.profile_name.config(text=self.user_info.get('username', 'User').upper())
        self.profile_status.config(text="● Online", fg=ModernStyle.SUCCESS)
        self.status_text.config(text=f"Angemeldet als {self.user_info.get('username', 'User')}")
        self._refresh_premium_badge()

        if not self.games:
            threading.Thread(target=self.load_games, daemon=True).start()
        self.show_dashboard()

    def _refresh_premium_badge(self):
        for w in self.status_frame.winfo_children():
            w.destroy()
        is_premium = self.is_premium()
        status = 'PREMIUM' if is_premium else 'FREE'
        color = ModernStyle.ACCENT if is_premium else ModernStyle.TEXT_MUTED
        self.premium_badge = StatusBadge(self.status_frame, status, color)
        self.premium_badge.pack(side='left', padx=(0, 12))
        tk.Button(self.status_frame, text="Logout", bg=ModernStyle.BG_CARD, fg=ModernStyle.DANGER,
                  relief='flat', font=('Segoe UI', 10), padx=18, pady=6,
                  command=self.logout).pack(side='left')

    # ----------------------------- DASHBOARD -----------------------------
    def show_dashboard(self):
        self.clear_content()
        self.set_title("Dashboard")
        self._set_active_nav(self.nav_buttons[0])

        # Stats
        stats_frame = tk.Frame(self.content, bg=ModernStyle.BG)
        stats_frame.pack(fill='x', pady=(0, 25))
        vals = [
            ("Spiele", str(len(self.games)) if self.games else "…", ModernStyle.ACCENT),
            ("Trainer", str(len(self.trainers)), ModernStyle.TEXT),
            ("Favoriten", str(len(self.favorites)), ModernStyle.GOLD),
            ("Status", "PREMIUM" if self.is_premium() else "FREE", ModernStyle.ACCENT if self.is_premium() else ModernStyle.TEXT_MUTED)
        ]
        for label, val, col in vals:
            card = self._card(stats_frame, width=200, height=110)
            card.pack(side='left', padx=(0, 18))
            card.pack_propagate(False)
            tk.Label(card, text=val, font=('Rajdhani', 26, 'bold'),
                     bg=ModernStyle.BG_CARD, fg=col).pack(pady=(25, 0))
            tk.Label(card, text=label, font=('Segoe UI', 10),
                     bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack()

        # Recent + quick actions
        row = tk.Frame(self.content, bg=ModernStyle.BG)
        row.pack(fill='both', expand=True)

        left = self._card(row)
        left.pack(side='left', fill='both', expand=True, padx=(0, 20))
        linner = tk.Frame(left, bg=ModernStyle.BG_CARD, padx=25, pady=25)
        linner.pack(fill='both', expand=True)
        tk.Label(linner, text="Zuletzt verwendet", font=('Rajdhani', 16, 'bold'),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT).pack(anchor='w')
        recent_box = tk.Frame(linner, bg=ModernStyle.BG_CARD)
        recent_box.pack(fill='x', pady=(20, 0))
        if self.recent_games:
            for slug in self.recent_games[:6]:
                game = next((g for g in self.games if g.get('slug') == slug), None)
                if game:
                    self._game_chip(recent_box, game)
        else:
            tk.Label(recent_box, text="Noch keine Spiele", bg=ModernStyle.BG_CARD,
                     fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 11)).pack()

        right = self._card(row, width=320)
        right.pack(side='right', fill='y')
        rinner = tk.Frame(right, bg=ModernStyle.BG_CARD, padx=25, pady=25)
        rinner.pack(fill='both', expand=True)
        tk.Label(rinner, text="Schnellzugriff", font=('Rajdhani', 16, 'bold'),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT).pack(anchor='w', pady=(0, 20))
        AnimatedButton(rinner, text="🎮 Spielebibliothek", command=self.show_games_library,
                       width=260, height=42).pack(pady=(0, 12))
        AnimatedButton(rinner, text="🔄 Update prüfen", command=self.check_for_update,
                       width=260, height=42, bg=ModernStyle.BORDER, hover_bg=ModernStyle.BORDER_ACTIVE).pack()

    def _game_chip(self, parent, game):
        chip = tk.Frame(parent, bg=ModernStyle.BG_ELEVATED, highlightbackground=ModernStyle.BORDER,
                        highlightthickness=1, cursor='hand2')
        chip.pack(side='left', padx=(0, 12), pady=5)
        tk.Label(chip, text=game.get('name', ''), bg=ModernStyle.BG_ELEVATED,
                 fg=ModernStyle.TEXT, font=('Segoe UI', 10), padx=15, pady=8).pack()
        chip.bind('<Button-1>', lambda e, g=game: self.select_game(g.get('slug')))
        for c in chip.winfo_children():
            c.bind('<Button-1>', lambda e, g=game: self.select_game(g.get('slug')))

    # ----------------------------- GAMES LIBRARY -----------------------------
    def show_games_library(self, filter_favorites=False):
        self.clear_content()
        self.set_title("Favoriten" if filter_favorites else "Spielebibliothek")
        self._set_active_nav(self.nav_buttons[2] if filter_favorites else self.nav_buttons[1])
        self._filter_favorites = filter_favorites

        search_frame = tk.Frame(self.content, bg=ModernStyle.BG)
        search_frame.pack(fill='x', pady=(0, 20))
        tk.Entry(search_frame, textvariable=self.search_var, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT,
                 insertbackground=ModernStyle.TEXT, relief='flat', font=('Segoe UI', 12),
                 highlightbackground=ModernStyle.BORDER, highlightthickness=1).pack(side='left', fill='x', expand=True, ipady=10, padx=(0, 12))
        AnimatedButton(search_frame, text="Suchen", command=self._render_game_grid, width=110, height=42).pack(side='left')
        self.search_var.trace('w', lambda *args: self._render_game_grid())

        # Canvas + scroll
        canvas_frame = tk.Frame(self.content, bg=ModernStyle.BG)
        canvas_frame.pack(fill='both', expand=True)
        self.games_canvas = tk.Canvas(canvas_frame, bg=ModernStyle.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical', command=self.games_canvas.yview)
        self.games_grid = tk.Frame(self.games_canvas, bg=ModernStyle.BG)
        self.games_grid.bind('<Configure>', lambda e: self.games_canvas.configure(scrollregion=self.games_canvas.bbox('all')))
        self.games_canvas.create_window((0, 0), window=self.games_grid, anchor='nw')
        self.games_canvas.configure(yscrollcommand=scrollbar.set)
        self.games_canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        self._render_game_grid()
        if not self.games:
            threading.Thread(target=self.load_games, daemon=True).start()

    def _render_game_grid(self):
        for w in self.games_grid.winfo_children():
            w.destroy()
        q = self.search_var.get().lower()
        games = [g for g in self.games if q in g.get('name', '').lower() or q in (g.get('genre') or '').lower()]
        if self._filter_favorites:
            games = [g for g in games if g.get('name') in self.favorites]

        if not games:
            tk.Label(self.games_grid, text="Keine Spiele gefunden", bg=ModernStyle.BG,
                     fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 13)).pack(pady=50)
            return

        col = 0
        row = 0
        for game in games:
            card = self._game_card(game)
            card.grid(row=row, column=col, padx=(0, 18), pady=(0, 18), sticky='nw')
            col += 1
            if col >= 4:
                col = 0
                row += 1

    def _game_card(self, game):
        card = tk.Frame(self.games_grid, bg=ModernStyle.BG_CARD, highlightbackground=ModernStyle.BORDER,
                        highlightthickness=1, width=270, height=150, cursor='hand2')
        card.grid_propagate(False)
        card.pack_propagate(False)

        name = game.get('name', 'Unbekannt')
        tk.Label(card, text=name[:28] + ('...' if len(name) > 28 else ''), font=('Segoe UI', 13, 'bold'),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT).pack(anchor='w', padx=18, pady=(18, 4))
        tk.Label(card, text=f"{game.get('trainer_count', 0)} Trainer", font=('Segoe UI', 10),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack(anchor='w', padx=18)
        tk.Label(card, text=game.get('genre') or 'Singleplayer', font=('Segoe UI', 9),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.ACCENT).pack(anchor='w', padx=18, pady=(8, 0))

        fav = "★" if name in self.favorites else "☆"
        fav_lbl = tk.Label(card, text=fav, font=('Segoe UI', 16),
                           bg=ModernStyle.BG_CARD, fg=ModernStyle.ACCENT if name in self.favorites else ModernStyle.TEXT_MUTED)
        fav_lbl.place(relx=0.9, rely=0.18, anchor='center')
        fav_lbl.bind('<Button-1>', lambda e, g=game: self._toggle_favorite(g))

        card.bind('<Button-1>', lambda e, g=game: self.select_game(g.get('slug')))
        for c in card.winfo_children():
            c.bind('<Button-1>', lambda e, g=game: self.select_game(g.get('slug')))
        return card

    def _toggle_favorite(self, game):
        name = game.get('name')
        if name in self.favorites:
            self.favorites.discard(name)
        else:
            self.favorites.add(name)
        self.config['favorites'] = list(self.favorites)
        save_config(self.config)
        self.sync_favorites()
        self._render_game_grid()

    # ----------------------------- GAME DETAIL -----------------------------
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

        header = tk.Frame(self.content, bg=ModernStyle.BG)
        header.pack(fill='x', pady=(0, 20))
        tk.Label(header, text=game.get('name', ''), font=('Rajdhani', 24, 'bold'),
                 bg=ModernStyle.BG, fg=ModernStyle.TEXT).pack(side='left')
        self.proc_status = tk.Label(header, text="● Nicht gestartet", font=('Segoe UI', 11),
                                    bg=ModernStyle.BG, fg=ModernStyle.DANGER)
        self.proc_status.pack(side='left', padx=(20, 0), pady=(8, 0))
        AnimatedButton(header, text="🔄 Prozess prüfen", command=self.check_process,
                       width=160, height=36, bg=ModernStyle.BORDER, hover_bg=ModernStyle.BORDER_ACTIVE).pack(side='right')

        # Tabs
        self.detail_tabs = tk.Frame(self.content, bg=ModernStyle.BG)
        self.detail_tabs.pack(fill='x', pady=(0, 15))
        self.tab_trainers = self._tab_btn("Trainer", active=True)
        self.tab_cheats = self._tab_btn("Offizielle Cheats")
        self.tab_info = self._tab_btn("Info")

        # Scrollable trainer area using ttk Scrollbar + Canvas
        self.detail_canvas = tk.Canvas(self.content, bg=ModernStyle.BG, highlightthickness=0)
        self.detail_scrollbar = ttk.Scrollbar(self.content, orient='vertical', command=self.detail_canvas.yview)
        self.detail_scrollable_frame = tk.Frame(self.detail_canvas, bg=ModernStyle.BG)
        self.detail_canvas.create_window((0, 0), window=self.detail_scrollable_frame, anchor='nw', tags='inner')
        self.detail_canvas.configure(yscrollcommand=self.detail_scrollbar.set)
        self.detail_canvas.pack(side='left', fill='both', expand=True)
        self.detail_scrollbar.pack(side='right', fill='y')
        self.detail_scrollable_frame.bind('<Configure>', self._on_inner_configure)
        self.content.bind('<Configure>', self._on_content_configure)
        self.detail_canvas.bind_all('<MouseWheel>', self._on_mousewheel)

        self.detail_state = 'trainers'
        self._show_trainers_tab()

        # Attach engine
        if self.engine:
            self.engine.set_process(game.get('process_name'))

        # Load trainers synchronously first (fast path) then fallback
        self.trainers_data = None
        self.trainers = []
        threading.Thread(target=lambda: self.load_trainers(slug), daemon=True).start()

    def _on_content_configure(self, event):
        try:
            self.detail_canvas.itemconfig('inner', width=event.width - self.detail_scrollbar.winfo_width() - 10)
        except Exception:
            pass

    def _on_inner_configure(self, event):
        self.detail_canvas.configure(scrollregion=self.detail_canvas.bbox('all'))

    def _on_mousewheel(self, event):
        try:
            self.detail_canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        except Exception:
            pass

    def _tab_btn(self, text, active=False):
        bg = ModernStyle.BG_CARD if active else ModernStyle.BG
        fg = ModernStyle.ACCENT if active else ModernStyle.TEXT_MUTED
        btn = tk.Label(self.detail_tabs, text=text, font=('Segoe UI', 11, 'bold'),
                       bg=bg, fg=fg, padx=20, pady=10, cursor='hand2')
        btn.pack(side='left', padx=(0, 8))
        btn.bind('<Button-1>', lambda e, t=text: self._switch_tab(t))
        return btn

    def _switch_tab(self, name):
        for btn in [self.tab_trainers, self.tab_cheats, self.tab_info]:
            btn.config(bg=ModernStyle.BG, fg=ModernStyle.TEXT_MUTED)
        # Reset scroll
        self.detail_canvas.yview_moveto(0)
        if name == 'Trainer':
            self.tab_trainers.config(bg=ModernStyle.BG_CARD, fg=ModernStyle.ACCENT)
            self.detail_state = 'trainers'
            self._show_trainers_tab()
        elif name == 'Offizielle Cheats':
            self.tab_cheats.config(bg=ModernStyle.BG_CARD, fg=ModernStyle.ACCENT)
            self.detail_state = 'cheats'
            self._show_cheats_tab()
        else:
            self.tab_info.config(bg=ModernStyle.BG_CARD, fg=ModernStyle.ACCENT)
            self.detail_state = 'info'
            self._show_info_tab()

    def _clear_scrollable(self):
        for w in self.detail_scrollable_frame.winfo_children():
            w.destroy()

    def _show_trainers_tab(self):
        self._clear_scrollable()
        self.trainer_loading = tk.Label(self.detail_scrollable_frame, text="Lade Trainer...", font=('Segoe UI', 13),
                                        bg=ModernStyle.BG, fg=ModernStyle.TEXT_MUTED)
        self.trainer_loading.pack(pady=60)
        self.reload_btn = tk.Label(self.detail_scrollable_frame, text="↻ Neu laden", font=('Segoe UI', 10),
                                   bg=ModernStyle.BORDER, fg=ModernStyle.TEXT, padx=15, pady=6, cursor='hand2')
        self.reload_btn.pack(pady=10)
        self.reload_btn.bind('<Button-1>', lambda e: self._manual_reload_trainers())
        if self.trainers_data:
            self._render_trainers()

    def _show_cheats_tab(self):
        self._clear_scrollable()
        if not self.trainers_data:
            tk.Label(self.detail_scrollable_frame, text="Lade Cheats...", font=('Segoe UI', 13),
                     bg=ModernStyle.BG, fg=ModernStyle.TEXT_MUTED).pack(pady=60)
            return
        cheats = []
        for t in self.trainers_data.get('trainers', []):
            cheats.extend(t.get('game_cheats', []))
        if not cheats:
            tk.Label(self.detail_scrollable_frame, text="Keine offiziellen Cheats verfügbar", font=('Segoe UI', 13),
                     bg=ModernStyle.BG, fg=ModernStyle.TEXT_MUTED).pack(pady=60)
            return
        for c in cheats:
            self._cheat_card(self.detail_scrollable_frame, c)
        self.detail_scrollable_frame.update_idletasks()
        self.detail_canvas.configure(scrollregion=self.detail_canvas.bbox('all'))

    def _show_info_tab(self):
        self._clear_scrollable()
        g = self.current_game or {}
        info = "Spiel: %s\nProzess: %s\nGenre: %s\nSlug: %s" % (
            g.get('name', '-'), g.get('process_name', '-'), g.get('genre', '-'), g.get('slug', '-')
        )
        tk.Label(self.detail_scrollable_frame, text=info, font=('Segoe UI', 11), justify='left',
                 bg=ModernStyle.BG, fg=ModernStyle.TEXT_MUTED).pack(anchor='nw', pady=20)

    def _manual_reload_trainers(self):
        if self.current_game:
            self.trainers_data = None
            self.trainers = []
            self._show_trainers_tab()
            threading.Thread(target=lambda: self.load_trainers(self.current_game.get('slug')), daemon=True).start()

    def load_trainers(self, slug):
        print(f"[TrainerHub] load_trainers started for {slug}")
        try:
            data = self.api_call(f'trainers.php?game={slug}')
            print(f"[TrainerHub] load_trainers API response: success={data.get('success')}, trainers={len(data.get('trainers', []))}")
            self.trainers_data = data
            if hasattr(self, 'root') and self.root.winfo_exists():
                self.root.after(0, self._on_trainers_loaded)
            else:
                print("[TrainerHub] root destroyed, cannot schedule _on_trainers_loaded")
        except Exception as e:
            print(f"[TrainerHub] load_trainers exception: {e}")
            import traceback
            traceback.print_exc()

    def _on_trainers_loaded(self):
        try:
            if not hasattr(self, 'detail_scrollable_frame') or not self.detail_scrollable_frame.winfo_exists():
                return
            if self.detail_state == 'trainers' or (hasattr(self, 'tab_trainers') and self.tab_trainers.cget('bg') == ModernStyle.BG_CARD):
                self._render_trainers()
            elif self.detail_state == 'cheats':
                self._show_cheats_tab()
        except Exception as e:
            print(f"_on_trainers_loaded error: {e}")
            import traceback
            traceback.print_exc()

    def _render_trainers(self):
        try:
            if hasattr(self, 'trainer_loading') and self.trainer_loading.winfo_exists():
                self.trainer_loading.destroy()
            self._clear_scrollable()

            data = self.trainers_data or {}
            if not data.get('success'):
                err = data.get('error', 'Unbekannter Fehler')
                tk.Label(self.detail_scrollable_frame, text=f"Fehler: {err}",
                         font=('Segoe UI', 13), bg=ModernStyle.BG, fg=ModernStyle.DANGER).pack(pady=60)
                return

            self.trainers = data.get('trainers', [])
            sub = data.get('subscription', 'free')
            tk.Label(self.detail_scrollable_frame, text=f"Abonnement: {sub.upper()}", font=('Segoe UI', 10, 'bold'),
                     bg=ModernStyle.BG, fg=ModernStyle.ACCENT if sub == 'premium' else ModernStyle.TEXT_MUTED).pack(anchor='w', pady=(0, 15))

            if not self.trainers:
                tk.Label(self.detail_scrollable_frame, text="Keine Trainer verfügbar", font=('Segoe UI', 13),
                         bg=ModernStyle.BG, fg=ModernStyle.TEXT_MUTED).pack(pady=60)
                return

            for trainer in self.trainers:
                self._trainer_card(self.detail_scrollable_frame, trainer)

            self.detail_scrollable_frame.update_idletasks()
            self.detail_canvas.configure(scrollregion=self.detail_canvas.bbox('all'))
        except Exception as e:
            print(f"_render_trainers error: {e}")
            import traceback
            traceback.print_exc()
            try:
                self._clear_scrollable()
                tk.Label(self.detail_scrollable_frame, text=f"Fehler beim Laden: {str(e)[:200]}",
                         font=('Segoe UI', 13), bg=ModernStyle.BG, fg=ModernStyle.DANGER).pack(pady=60)
            except Exception:
                pass

    def _trainer_card(self, parent, trainer):
        card = tk.Frame(parent, bg=ModernStyle.BG_CARD, highlightbackground=ModernStyle.BORDER,
                        highlightthickness=1)
        card.pack(fill='x', pady=(0, 14), ipady=14)

        top = tk.Frame(card, bg=ModernStyle.BG_CARD)
        top.pack(fill='x', padx=22, pady=(14, 8))
        tk.Label(top, text=trainer.get('title', 'Trainer'), font=('Segoe UI', 14, 'bold'),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT).pack(side='left')
        locked = trainer.get('locked', False)
        if trainer.get('premium') or trainer.get('is_premium'):
            badge_color = ModernStyle.ACCENT if not locked else ModernStyle.TEXT_MUTED
            tk.Label(top, text="PREMIUM" if not locked else "🔒 PREMIUM", font=('Segoe UI', 8, 'bold'),
                     bg=badge_color, fg=ModernStyle.BG if not locked else ModernStyle.TEXT,
                     padx=10, pady=3).pack(side='left', padx=(12, 0))

        desc = trainer.get('description', '')
        if desc:
            tk.Label(card, text=desc, font=('Segoe UI', 10),
                     bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack(anchor='w', padx=22)

        bottom = tk.Frame(card, bg=ModernStyle.BG_CARD)
        bottom.pack(fill='x', padx=22, pady=(12, 0))

        if locked:
            tk.Label(bottom, text="Upgrade auf Premium erforderlich", font=('Segoe UI', 10),
                     bg=ModernStyle.BG_CARD, fg=ModernStyle.ACCENT).pack(side='left')
        else:
            self._toggle_switch(bottom, trainer)

    def _toggle_switch(self, parent, trainer):
        name = trainer.get('title', '')
        active = self.engine and self.engine.active_cheats.get(name, False)
        container = tk.Frame(parent, bg=ModernStyle.BG_CARD)
        container.pack(side='left')
        status_lbl = tk.Label(container, text="AUS", font=('Segoe UI', 9, 'bold'),
                              bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED)
        status_lbl.pack(side='left', padx=(0, 10))

        def toggle(state):
            if not self.engine:
                self.show_toast("Cheat-Engine nicht verfügbar", ModernStyle.DANGER)
                sw.set(False)
                return
            if state:
                ctype = trainer.get('cheat_type', 'memory')
                if ctype == 'two_scan':
                    self._open_two_scan_dialog(trainer)
                    sw.set(False)
                    return
                res = self.engine.activate(trainer, self.current_game)
                if res.get('success'):
                    self.engine.active_cheats[name] = True
                    status_lbl.config(text="AN", fg=ModernStyle.ACCENT)
                    self.show_toast(res.get('message', 'Aktiviert'), ModernStyle.ACCENT)
                else:
                    sw.set(False)
                    msg = res.get('message', '')
                    if '2-Werte-Scan' in msg or 'SMAPI' in msg or 'Prozess' in msg:
                        self._open_cheat_config(trainer, msg)
                    else:
                        self.show_toast(msg, ModernStyle.DANGER)
            else:
                res = self.engine.deactivate(trainer)
                status_lbl.config(text="AUS", fg=ModernStyle.TEXT_MUTED)
                self.show_toast(res.get('message', 'Deaktiviert'), ModernStyle.TEXT_MUTED)

        sw = ToggleSwitch(container, command=toggle, initial=active, bg=ModernStyle.BG_CARD)
        sw.pack(side='left')
        if active:
            status_lbl.config(text="AN", fg=ModernStyle.ACCENT)

    def _open_two_scan_dialog(self, trainer):
        d = tk.Toplevel(self.root)
        d.title(f"2-Werte-Scan: {trainer.get('title', '')}")
        d.configure(bg=ModernStyle.BG_CARD)
        d.geometry("400x300")
        d.transient(self.root)
        d.grab_set()
        tk.Label(d, text="Aktueller Wert im Spiel", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack(pady=(20, 5))
        e1 = tk.Entry(d, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT, relief='flat', font=('Segoe UI', 11))
        e1.pack(fill='x', padx=20, ipady=6)
        tk.Label(d, text="Neuer Wert nach Änderung", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack(pady=(15, 5))
        e2 = tk.Entry(d, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT, relief='flat', font=('Segoe UI', 11))
        e2.pack(fill='x', padx=20, ipady=6)
        tk.Label(d, text="Gewünschter Wert", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack(pady=(15, 5))
        e3 = tk.Entry(d, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT, relief='flat', font=('Segoe UI', 11))
        e3.pack(fill='x', padx=20, ipady=6)
        e3.insert(0, '999')
        def run():
            try:
                v1 = int(e1.get())
                v2 = int(e2.get())
                v3 = int(e3.get())
                label = trainer.get('title', 'scan')
                res = self.engine.two_scan_dialog_values(self.current_game.get('name', ''), label, v1, v2, v3)
                if res.get('success'):
                    self.engine.active_cheats[label] = True
                    self.show_toast(res.get('message'), ModernStyle.ACCENT)
                    d.destroy()
                else:
                    self.show_toast(res.get('message'), ModernStyle.DANGER)
            except ValueError:
                self.show_toast("Bitte Zahlen eingeben", ModernStyle.DANGER)
        AnimatedButton(d, text="Scannen & Setzen", command=run, width=200, height=40).pack(pady=20)

    def _open_cheat_config(self, trainer, error_msg):
        d = tk.Toplevel(self.root)
        d.title(trainer.get('title', 'Cheat Config'))
        d.configure(bg=ModernStyle.BG_CARD)
        d.geometry("420x260")
        d.transient(self.root)
        d.grab_set()
        tk.Label(d, text=error_msg, bg=ModernStyle.BG_CARD, fg=ModernStyle.DANGER, wraplength=380).pack(pady=(15, 15))
        tk.Label(d, text="Wert (z.B. 999999)", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack()
        e_val = tk.Entry(d, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT, relief='flat', font=('Segoe UI', 11))
        e_val.pack(fill='x', padx=20, ipady=6)
        e_val.insert(0, '999999')

        def try_again():
            val = e_val.get().strip()
            # Inject value into trainer dict for this run
            patched = dict(trainer)
            patched['effect'] = f"set money = {val}"
            res = self.engine.activate(patched, self.current_game)
            if res.get('success'):
                self.engine.active_cheats[trainer.get('title', '')] = True
                self.show_toast(res.get('message', 'Aktiviert'), ModernStyle.ACCENT)
                d.destroy()
            else:
                self.show_toast(res.get('message', 'Fehler'), ModernStyle.DANGER)

        AnimatedButton(d, text="Mit Wert versuchen", command=try_again, width=200, height=40).pack(pady=20)
        tk.Label(d, text="Hinweis: Für SMAPI-Cheats muss SMAPI installiert sein.",
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 9)).pack()

    def _cheat_card(self, parent, cheat):
        card = tk.Frame(parent, bg=ModernStyle.BG_CARD, highlightbackground=ModernStyle.BORDER,
                        highlightthickness=1)
        card.pack(fill='x', pady=(0, 10), ipady=10)
        top = tk.Frame(card, bg=ModernStyle.BG_CARD)
        top.pack(fill='x', padx=18, pady=(10, 4))
        tk.Label(top, text=cheat.get('name', 'Cheat'), font=('Segoe UI', 12, 'bold'),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT).pack(side='left')
        if cheat.get('locked'):
            tk.Label(top, text="🔒 PREMIUM", font=('Segoe UI', 8, 'bold'),
                     bg=ModernStyle.TEXT_MUTED, fg=ModernStyle.TEXT, padx=8, pady=2).pack(side='left', padx=(8, 0))
        tk.Label(card, text=cheat.get('effect') or cheat.get('command') or '', font=('Segoe UI', 9),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack(anchor='w', padx=18)

    def check_process(self):
        if not self.current_game:
            self.show_toast("Bitte zuerst ein Spiel auswählen", ModernStyle.WARNING)
            return
        pnames = []
        if self.current_game.get('process_name'):
            pnames.append(self.current_game['process_name'])
        if self.current_game.get('launcher_processes'):
            pnames.extend([p.strip() for p in self.current_game['launcher_processes'].split(',') if p.strip()])
        if not pnames:
            self.proc_status.config(text="● Kein Prozess bekannt", fg=ModernStyle.WARNING)
            return
        if not WINDOWS or not self.engine or not self.engine.memory:
            self.proc_status.config(text="● Nur unter Windows verfügbar", fg=ModernStyle.WARNING)
            return

        found = False
        for pname in pnames:
            ok = self.engine.set_process(pname)
            if ok:
                found = True
                self.process_name = pname
                break
        if found:
            self.proc_status.config(text=f"● Prozess aktiv (PID {self.engine.memory.pid})", fg=ModernStyle.SUCCESS)
            self.show_toast("Prozess verbunden", ModernStyle.SUCCESS)
        else:
            tried = ', '.join(pnames)
            self.proc_status.config(text=f"● Nicht gestartet", fg=ModernStyle.DANGER)
            self.show_toast(f"Kein Prozess gefunden: {tried}", ModernStyle.DANGER)

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
            self.set_status(f"{len(self.games)} Spiele geladen")
            self.root.after(0, self._refresh_after_games_load)
        else:
            self.set_status("Spiele laden fehlgeschlagen")

    def _refresh_after_games_load(self):
        if hasattr(self, '_render_game_grid'):
            self._render_game_grid()
        if hasattr(self, 'show_dashboard'):
            self.show_dashboard()

    def set_status(self, msg):
        self.root.after(0, lambda: self.status_text.config(text=msg))

    # ----------------------------- PREMIUM -----------------------------
    def is_premium(self):
        try:
            return (self.premium_data.get('subscription') == 'premium' or
                    self.user_info.get('subscription') == 'premium' or
                    self.user_info.get('subscription_status') == 'premium')
        except Exception:
            return False

    # ----------------------------- ACCOUNT / SETTINGS -----------------------------
    def show_account(self):
        self.clear_content()
        self.set_title("Account")
        self._set_active_nav(self.nav_buttons[3])
        card = self._card(self.content)
        card.pack(fill='both', expand=True)
        inner = tk.Frame(card, bg=ModernStyle.BG_CARD, padx=40, pady=40)
        inner.pack(fill='both', expand=True)
        tk.Label(inner, text="Account", font=('Rajdhani', 20, 'bold'),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT).pack(anchor='w', pady=(0, 20))
        for label, val in [
            ("Benutzer", self.user_info.get('username', '-')),
            ("E-Mail", self.user_info.get('email', '-')),
            ("Premium", 'Ja' if self.is_premium() else 'Nein'),
        ]:
            tk.Label(inner, text=f"{label}: {val}", font=('Segoe UI', 12),
                     bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack(anchor='w', pady=5)

    def show_settings(self):
        self.clear_content()
        self.set_title("Einstellungen")
        self._set_active_nav(self.nav_buttons[4])
        card = self._card(self.content)
        card.pack(fill='both', expand=True)
        inner = tk.Frame(card, bg=ModernStyle.BG_CARD, padx=40, pady=40)
        inner.pack(fill='both', expand=True)
        tk.Label(inner, text="Einstellungen", font=('Rajdhani', 20, 'bold'),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT).pack(anchor='w', pady=(0, 20))
        tk.Label(inner, text="API-Key", font=('Segoe UI', 10),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack(anchor='w')
        key_entry = tk.Entry(inner, width=60, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT,
                             insertbackground=ModernStyle.TEXT, relief='flat', font=('Segoe UI', 10))
        key_entry.insert(0, self.api_key or '')
        key_entry.pack(anchor='w', pady=(5, 20), ipady=6)
        AnimatedButton(inner, text="Speichern", command=lambda: self._save_settings(key_entry.get()),
                       width=120, height=36).pack(anchor='w')

    def _save_settings(self, key):
        self.api_key = key.strip() or None
        self.config['api_key'] = self.api_key
        save_config(self.config)
        self.show_toast("Einstellungen gespeichert", ModernStyle.SUCCESS)

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

    def sync_favorites(self):
        try:
            self.api_call('config-sync.php', 'POST', {'favorites': list(self.favorites)})
        except Exception as e:
            print(f"Favorites sync error: {e}")

    def logout(self):
        self.api_key = None
        self.config['api_key'] = None
        save_config(self.config)
        self.user_info = {}
        self.premium_data = {}
        self.profile_name.config(text="GAST")
        self.profile_status.config(text="● Offline", fg=ModernStyle.DANGER)
        if self.premium_badge:
            self.premium_badge.destroy()
        self.show_login()


def main():
    root = tk.Tk()
    app = TrainerHubApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
