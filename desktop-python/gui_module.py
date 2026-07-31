"""SweetCheat Engine Application — Modern Cyan UI"""
import sys
import os
import json
import time
import threading
import urllib.request
import urllib.error
import logging

APP_VERSION = '0.9.1'
logger = logging.getLogger('SweetCheat.GUI')
CONFIG_DIR = os.path.join(os.eniron.get('APPDATA', os.path.expanduser('~')), 'SweetCheat')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
API_BASE = os.eniron.get('TRAINERHUB_API', 'https://sayfespace.online/trainerhub/api')

os.makedirs(CONFIG_DIR, exist_ok=True)

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext, simpledialog
except ImportError:
    logger.error("tkinter fehlt")
    sys.exit(1)

from ui_components import ModernStyle, StatusBadge, AnimatedButton, ToggleSwitch, card, primary_btn, secondary_btn, section_title, badge, stat_card, card, primary_btn, secondary_btn, section_title, badge
from desktop_api import SweetCheatAPI
from process_scanner import ProcessScanner
from actiation_engine import ActiationEngine

WINDOWS = sys.platform == 'win32'


def load_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'api_key': None, 'api_base': API_BASE, 'theme': 'dark', 'faorites': [], 'recent_games': []}


def sae_config(cfg):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f)
    except Exception as e:
        logger.error(f"Config sae error: {e}")


class SweetCheatApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"SweetCheat Engine {APP_VERSION}")
        try:
            from PIL import Image, ImageTk
            if os.path.exists(LOGO_PATH):
                icon = Image.open(LOGO_PATH)
                photo = ImageTk.PhotoImage(icon.resize((64, 64)))
                self.root.iconphoto(True, photo)
        except Exception as e:
            logger.warning(f"Could not set window icon: {e}")
        self.root.geometry("1366x900")
        self.root.minsize(1200, 750)
        self.root.configure(bg=ModernStyle.BG)
        ModernStyle.apply(self.root)

        self.config = load_config()
        self.api_key = self.config.get('api_key')
        self.api_base = self.config.get('api_base', API_BASE)
        self.api = SweetCheatAPI(self.api_base, self.api_key)
        self.scanner = ProcessScanner()
        self.actiation_engine = ActiationEngine(self.api)
        self.games = []
        self.trainers = []
        self.current_game = None
        self.current_game_pid = None
        self.premium_data = {}
        self.faorites = set(self.config.get('faorites', []))
        self.recent_games = list(self.config.get('recent_games', []))
        self.search_ar = tk.StringVar()
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

    # ----------------------------- MODERN UI BUILD -----------------------------
    def build_ui(self):
        # Top title bar with logo
        self.titlebar = tk.Frame(self.root, bg=ModernStyle.BG, height=72)
        self.titlebar.pack(fill='x', side='top')
        self.titlebar.pack_propagate(False)

        logo_frame = tk.Frame(self.titlebar, bg=ModernStyle.BG)
        logo_frame.pack(side='left', padx=22, pady=14)
        try:
            from PIL import Image, ImageTk
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'logo.png')
            if os.path.exists(logo_path):
                logo_img = Image.open(logo_path).resize((170, 34), Image.Resampling.LANCZOS)
                self.logo_tk = ImageTk.PhotoImage(logo_img)
                logo_label = tk.Label(logo_frame, image=self.logo_tk, bg=ModernStyle.BG, cursor='hand2')
                logo_label.bind('<Button-1>', lambda e: self.show_dashboard())
            else:
                logo_label = tk.Label(logo_frame, text="SweetCheat Engine", font=('Rajdhani', 24, 'bold'),
                                      bg=ModernStyle.BG, fg=ModernStyle.ACCENT, cursor='hand2')
                logo_label.bind('<Button-1>', lambda e: self.show_dashboard())
        except Exception:
            logo_label = tk.Label(logo_frame, text="SweetCheat Engine", font=('Rajdhani', 24, 'bold'),
                                  bg=ModernStyle.BG, fg=ModernStyle.ACCENT, cursor='hand2')
            logo_label.bind('<Button-1>', lambda e: self.show_dashboard())
        logo_label.pack(side='left')

        # Center page title
        self.page_title = tk.Label(self.titlebar, text="Dashboard", font=('Rajdhani', 17, 'bold'),
                                   bg=ModernStyle.BG, fg=ModernStyle.TEXT)
        self.page_title.place(relx=0.5, y=36, anchor='center')

        # Right status + user pill
        self.status_frame = tk.Frame(self.titlebar, bg=ModernStyle.BG)
        self.status_frame.pack(side='right', padx=22, pady=14)
        self.user_pill = tk.Frame(self.status_frame, bg=ModernStyle.BG_ELEVATED,
                                  highlightbackground=ModernStyle.BORDER, highlightthickness=1)
        self.user_pill.pack(side='right')
        self.user_menu_btn = tk.Label(self.user_pill, text="👤  Gast  ▾", font=('Segoe UI', 11),
                                      bg=ModernStyle.BG_ELEVATED, fg=ModernStyle.TEXT, padx=14, pady=7,
                                      cursor='hand2')
        self.user_menu_btn.pack()
        self.user_menu_btn.bind('<Button-1>', self._show_user_menu)

        # Main frame
        self.main_frame = tk.Frame(self.root, bg=ModernStyle.BG)
        self.main_frame.pack(fill='both', expand=True)

        # Modern Sidebar
        self.sidebar = tk.Frame(self.main_frame, bg=ModernStyle.BG_CARD, width=260)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)

        self._sidebar_profile()
        self._sidebar_sep()
        self.na_buttons = []
        self._na_btn("⌂  Dashboard", self.show_dashboard, actie=True)
        self._na_btn("🎮  Spiele", self.show_games_library)
        self._na_btn("⭐  Faoriten", lambda: self.show_games_library(filter_faorites=True))
        self._na_btn("⎋  Account", self.show_account)
        self._na_btn("⚙  Einstellungen", self.show_settings)

        # Content area
        self.content = tk.Frame(self.main_frame, bg=ModernStyle.BG)
        self.content.pack(side='left', fill='both', expand=True, padx=24, pady=18)

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

    def _show_user_menu(self, eent=None):
        menu = tk.Menu(self.root, tearoff=0, bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT,
                       actiebackground=ModernStyle.BORDER_ACTIVE, actieforeground=ModernStyle.TEXT,
                       font=('Segoe UI', 10))
        menu.add_command(label="Profil", command=self.show_account)
        menu.add_command(label="Einstellungen", command=self.show_settings)
        menu.add_separator()
        menu.add_command(label="Abmelden", command=self.logout)
        menu.post(self.user_menu_btn.winfo_rootx(), self.user_menu_btn.winfo_rooty() + self.user_menu_btn.winfo_height())

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

    def _na_btn(self, text, command, actie=False):
        bg = ModernStyle.ACCENT if actie else ModernStyle.BG_CARD
        fg = ModernStyle.BG if actie else ModernStyle.TEXT
        btn = tk.Button(self.sidebar, text=text, font=('Segoe UI', 12), bg=bg, fg=fg,
                        relief='flat', anchor='w', padx=20, pady=12,
                        actiebackground=ModernStyle.BORDER_ACTIVE if not actie else '#33f3ff',
                        actieforeground=ModernStyle.BG if actie else ModernStyle.TEXT,
                        command=lambda: (self._set_actie_na(btn), command()), cursor='hand2')
        btn.pack(fill='x', padx=15, pady=(0, 6))
        self.na_buttons.append(btn)

    def _set_actie_na(self, actie_btn):
        for btn in self.na_buttons:
            btn.config(bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT, actiebackground=ModernStyle.BORDER_ACTIVE)
        actie_btn.config(bg=ModernStyle.ACCENT, fg=ModernStyle.BG, actiebackground='#33f3ff')
        if actie:
            self.actie_na = btn

    def _set_actie_na(self, actie_btn):
        for btn in self.na_buttons:
            btn.config(bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT)
        actie_btn.config(bg=ModernStyle.ACCENT, fg=ModernStyle.BG)
        self.actie_na = actie_btn

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
        self._set_actie_na(self.na_buttons[0])

        wrapper = tk.Frame(self.content, bg=ModernStyle.BG)
        wrapper.place(relx=0.5, rely=0.45, anchor='center')

        # Modern card container
        card = tk.Frame(wrapper, bg=ModernStyle.BG_CARD, highlightbackground=ModernStyle.BORDER,
                        highlightthickness=1, bd=0, padx=40, pady=36)
        card.pack()

        # Logo area
        logo_text = tk.Label(card, text="SweetCheat Engine", font=('Rajdhani', 32, 'bold'),
                             bg=ModernStyle.BG_CARD, fg=ModernStyle.ACCENT)
        logo_text.pack(pady=(0, 4))
        tk.Label(card, text="SWEETCHEAT ENGINE", font=('Rajdhani', 10),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack(pady=(0, 24))

        email_ar = tk.StringVar(alue=self.config.get('last_email', ''))
        pass_ar = tk.StringVar()

        def do_login():
            email = email_ar.get().strip()
            password = pass_ar.get()
            if not email or not password:
                self.show_toast("E-Mail und Passwort erforderlich", ModernStyle.DANGER)
                return
            self.show_toast("Anmeldung läuft...")
            def run():
                result = self.api.login(email, password)
                if result.get('success'):
                    self.api_key = self.api.api_key
                    self.config['api_key'] = self.api_key
                    self.config['last_email'] = email
                    sae_config(self.config)
                    self.root.after(0, lambda: self._on_login_success())
                    self.root.after(0, lambda: self.show_toast(f"Willkommen, {result.get('user',{}).get('username','User')}"))
                else:
                    err = result.get('error', 'Anmeldung fehlgeschlagen')
                    self.root.after(0, lambda: self.show_toast(err, ModernStyle.DANGER))
            threading.Thread(target=run, daemon=True).start()

        tk.Label(card, text="E-Mail", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 10)).pack(anchor='w')
        email_entry = tk.Entry(card, textariable=email_ar, font=('Segoe UI', 12), bg=ModernStyle.BG_INPUT,
                             fg=ModernStyle.TEXT, insertbackground=ModernStyle.ACCENT, relief='flat',
                             highlightthickness=1, highlightcolor=ModernStyle.ACCENT, width=32)
        email_entry.pack(pady=(4, 14), ipady=7)

        tk.Label(card, text="Passwort", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 10)).pack(anchor='w')
        pass_entry = tk.Entry(card, textariable=pass_ar, show='•', font=('Segoe UI', 12), bg=ModernStyle.BG_INPUT,
                            fg=ModernStyle.TEXT, insertbackground=ModernStyle.ACCENT, relief='flat',
                            highlightthickness=1, highlightcolor=ModernStyle.ACCENT, width=32)
        pass_entry.pack(pady=(4, 22), ipady=7)

        tk.Button(card, text="Einloggen", command=do_login, font=('Segoe UI', 12, 'bold'),
                  bg=ModernStyle.ACCENT, fg=ModernStyle.BG, relief='flat', padx=30, pady=11, cursor='hand2').pack(fill='x')

        tk.Label(card, text="oder", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 9)).pack(pady=14)

        tk.Button(card, text="API-Key manuell eingeben", command=self._show_api_key_input,
                  font=('Segoe UI', 10), bg=ModernStyle.BG_ELEVATED, fg=ModernStyle.TEXT, relief='flat',
                  highlightbackground=ModernStyle.BORDER, highlightthickness=1,
                  padx=20, pady=9, cursor='hand2').pack(fill='x')

        pass_entry.bind('<Return>', lambda e: do_login())

    def _show_api_key_input(self):
        from tkinter import simpledialog
        key = simpledialog.askstring("API-Key", "Gib deinen API-Key ein:", show='•')
        if key:
            self.api.set_key(key)
            self.api_key = key
            self.config['api_key'] = key
            sae_config(self.config)
            self._on_login_success()


    def _card(self, parent, width=None, height=None):
        return card(parent, width, height)

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
                sae_config(self.config)
                self.root.after(0, self._on_login_success)
            else:
                self.root.after(0, lambda: self.login_msg.config(
                    text=data.get('error', 'Login fehlgeschlagen'), fg=ModernStyle.DANGER))
        except Exception as e:
            self.root.after(0, lambda err=str(e): self.login_msg.config(
                text=f"Netzwerkfehler: {err[:80]}", fg=ModernStyle.DANGER))

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def on_close(self):
        try:
            if hasattr(self, 'tray') and self.tray:
                self.tray.stop()
        except Exception:
            pass
        try:
            if hasattr(self, 'watcher') and self.watcher:
                self.watcher.stop()
        except Exception:
            pass
        try:
            if hasattr(self, 'hotkeys') and self.hotkeys:
                self.hotkeys.stop()
        except Exception:
            pass
        self.root.destroy()

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
        self._set_actie_na(self.na_buttons[0])

        # Welcome banner
        welcome = tk.Frame(self.content, bg=ModernStyle.BG_ELEVATED, highlightbackground=ModernStyle.BORDER,
                           highlightthickness=1, padx=28, pady=22)
        welcome.pack(fill='x', pady=(0, 22))
        uname = self.config.get('last_email', '').split('@')[0] or 'Player'
        tk.Label(welcome, text=f"Willkommen zurück, {uname}", font=ModernStyle.FONT_TITLE,
                 bg=ModernStyle.BG_ELEVATED, fg=ModernStyle.TEXT).pack(anchor='w')
        tk.Label(welcome, text="Deine Singleplayer-Trainer-Plattform. Wähle ein Spiel oder checke deine Faoriten.",
                 font=ModernStyle.FONT_BODY, bg=ModernStyle.BG_ELEVATED, fg=ModernStyle.TEXT_MUTED).pack(anchor='w', pady=(6, 0))

        # Stats row
        stats_frame = tk.Frame(self.content, bg=ModernStyle.BG)
        stats_frame.pack(fill='x', pady=(0, 22))
        als = [
            ("Spiele", str(len(self.games)) if self.games else "…", ModernStyle.ACCENT, "🎮"),
            ("Trainer", str(len(self.trainers)), ModernStyle.TEXT, "⚡"),
            ("Faoriten", str(len(self.faorites)), ModernStyle.ACCENT_SEC, "★"),
            ("Status", "PREMIUM" if self.is_premium() else "FREE", ModernStyle.ACCENT if self.is_premium() else ModernStyle.TEXT_MUTED, "◆")
        ]
        for label, al, col, icon in als:
            c = self._card(stats_frame, padx=18, pady=16)
            c.pack(side='left', fill='both', expand=True, padx=(0, 14))
            tk.Label(c, text=f"{icon}  {label}", font=ModernStyle.FONT_SMALL,
                     bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack(anchor='w')
            tk.Label(c, text=al, font=('Rajdhani', 24, 'bold'),
                     bg=ModernStyle.BG_CARD, fg=col).pack(anchor='w', pady=(8, 0))

        # Recent + quick actions
        row = tk.Frame(self.content, bg=ModernStyle.BG)
        row.pack(fill='both', expand=True)

        left = self._card(row, padx=22, pady=20)
        left.pack(side='left', fill='both', expand=True, padx=(0, 18))
        tk.Label(left, text="Zuletzt erwendet", font=ModernStyle.FONT_SUB,
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT).pack(anchor='w', pady=(0, 16))
        recent_box = tk.Frame(left, bg=ModernStyle.BG_CARD)
        recent_box.pack(fill='x')
        if self.recent_games:
            for slug in self.recent_games[:6]:
                game = next((g for g in self.games if g.get('slug') == slug), None)
                if game:
                    self._game_chip(recent_box, game)
        else:
            tk.Label(recent_box, text="Noch keine Spiele", bg=ModernStyle.BG_CARD,
                     fg=ModernStyle.TEXT_MUTED, font=ModernStyle.FONT_BODY).pack()

        right = self._card(row, width=300, padx=22, pady=20)
        right.pack(side='right', fill='y')
        tk.Label(right, text="Schnellzugriff", font=ModernStyle.FONT_SUB,
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT).pack(anchor='w', pady=(0, 16))
        secondary_btn(right, "Spielebibliothek", self.show_games_library, "🎮").pack(fill='x', pady=(0, 10))
        secondary_btn(right, "Faoriten", lambda: self.show_games_library(filter_faorites=True), "★").pack(fill='x', pady=(0, 10))
        secondary_btn(right, "Update prüfen", self.check_for_update, "🔄").pack(fill='x')

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
    def show_games_library(self, filter_faorites=False):
        self.clear_content()
        self.set_title("Faoriten" if filter_faorites else "Spiele-Bibliothek")

        # Header
        header = tk.Frame(self.content, bg=ModernStyle.BG)
        header.pack(fill='x', pady=(0, 15))
        search = tk.Entry(header, font=('Segoe UI', 11), bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT,
                          insertbackground=ModernStyle.TEXT, relief='flat', highlightthickness=1,
                          highlightcolor=ModernStyle.ACCENT)
        search.pack(side='left', fill='x', expand=True, ipady=6)
        search.insert(0, "Spiel suchen...")
        search.bind('<FocusIn>', lambda e: search.delete(0, 'end') if search.get() == "Spiel suchen..." else None)
        search.bind('<FocusOut>', lambda e: search.insert(0, "Spiel suchen...") if not search.get() else None)

        refresh_btn = tk.Button(header, text="↻ Aktualisieren", font=('Segoe UI', 10), bg=ModernStyle.BG_CARD,
                                fg=ModernStyle.TEXT, relief='flat', command=lambda: self._load_games_list(filter_faorites, search.get()))
        refresh_btn.pack(side='right', padx=(10, 0))

        scan_btn = tk.Button(header, text="🔍 Prozesse scannen", font=('Segoe UI', 10), bg=ModernStyle.ACCENT,
                             fg=ModernStyle.BG, relief='flat', command=self._scan_processes)
        scan_btn.pack(side='right', padx=(10, 0))

        # Running games banner
        self.running_banner = tk.Frame(self.content, bg=ModernStyle.BG_ELEVATED, padx=15, pady=12)
        self.running_banner.pack(fill='x', pady=(0, 15))
        self.running_banner.pack_forget()

        # Games grid
        self.games_canas = tk.Canas(self.content, bg=ModernStyle.BG, highlightthickness=0)
        self.games_scroll = tk.Scrollbar(self.content, orient='ertical', command=self.games_canas.yiew)
        self.games_frame = tk.Frame(self.games_canas, bg=ModernStyle.BG)
        self.games_canas.configure(yscrollcommand=self.games_scroll.set)
        self.games_canas.pack(side='left', fill='both', expand=True)
        self.games_scroll.pack(side='right', fill='y')
        self.games_canas_window = self.games_canas.create_window((0, 0), window=self.games_frame, anchor='nw')
        self.games_frame.bind('<Configure>', lambda e: self.games_canas.configure(scrollregion=self.games_canas.bbox('all')))

        self._load_games_list(filter_faorites)

    def _load_games_list(self, filter_faorites=False, search=None):
        for w in self.games_frame.winfo_children():
            w.destroy()
        self.set_status("Lade Spiele...")
        def load():
            result = self.api.games(search=search, per_page=100)
            if not result.get('success'):
                self.root.after(0, lambda: self.show_toast("Spiele konnten nicht geladen werden", ModernStyle.DANGER))
                self.root.after(0, lambda: self.set_status("Fehler beim Laden"))
                return
            games = result.get('games', [])
            if filter_faorites:
                games = [g for g in games if g.get('is_faorite')]
            self.games = games
            self.root.after(0, lambda: self._render_game_cards(games))
        threading.Thread(target=load, daemon=True).start()

    def _render_game_cards(self, games):
        for w in self.games_frame.winfo_children():
            w.destroy()
        if not games:
            tk.Label(self.games_frame, text="Keine Spiele gefunden", bg=ModernStyle.BG, fg=ModernStyle.TEXT_MUTED,
                     font=ModernStyle.FONT_BODY).pack(pady=40)
            return
        for g in games:
            c = self._card(self.games_frame, padx=20, pady=18)
            c.pack(fill='x', pady=8)
            top = tk.Frame(c, bg=ModernStyle.BG_CARD)
            top.pack(fill='x')
            title = tk.Label(top, text=g.get('name', 'Unbekannt'), font=('Rajdhani', 16, 'bold'),
                             bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT)
            title.pack(side='left')
            if g.get('is_faorite'):
                tk.Label(top, text="★", bg=ModernStyle.BG_CARD, fg='#ffd700', font=('Segoe UI', 14)).pack(side='left', padx=(8, 0))
            meta = tk.Label(c, text=f"{g.get('genre','?')}  •  {g.get('trainer_count',0)} Trainer  •  {g.get('platform','PC')}",
                            font=ModernStyle.FONT_SMALL, bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED)
            meta.pack(anchor='w', pady=(8, 14))
            actions = tk.Frame(c, bg=ModernStyle.BG_CARD)
            actions.pack(fill='x')
            secondary_btn(actions, "Trainer anzeigen", lambda slug=g.get('slug'): self._show_trainers_for_game(slug), "⚡").pack(side='right')
            ghost_btn(actions, "Faorit", lambda gid=g['id']: self._toggle_game_fa(gid), "★" if not g.get('is_faorite') else "Entfernen").pack(side='left')
        self.set_status(f"{len(games)} Spiele geladen")

    def _toggle_game_fa(self, game_id):
        def do():
            fas = self.api.faorites()
            is_fa = any(f.get('game_id') == game_id and not f.get('trainer_id') for f in fas.get('faorites', []))
            result = self.api.remoe_faorite(game_id=game_id) if is_fa else self.api.add_faorite(game_id=game_id)
            if result.get('success'):
                self.root.after(0, lambda: self.show_toast("Faorit aktualisiert"))
                self.root.after(0, lambda: self._load_games_list())
        threading.Thread(target=do, daemon=True).start()

    def _scan_processes(self):
        found = self.scanner.scan()
        for w in self.running_banner.winfo_children():
            w.destroy()
        if not found:
            self.running_banner.pack_forget()
            self.show_toast("Keine bekannten Spieleprozesse gefunden", ModernStyle.DANGER)
            return
        self.running_banner.pack(fill='x', pady=(0, 15), before=self.games_canas)
        tk.Label(self.running_banner, text="🎮 Laufende Spiele erkannt:", bg=ModernStyle.BG_ELEVATED,
                 fg=ModernStyle.ACCENT, font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        for info in found:
            row = tk.Frame(self.running_banner, bg=ModernStyle.BG_ELEVATED)
            row.pack(fill='x', pady=2)
            tk.Label(row, text=f"{info['name']} (PID {info['pid']})", bg=ModernStyle.BG_ELEVATED,
                     fg=ModernStyle.TEXT).pack(side='left')
            tk.Button(row, text="Trainer", bg=ModernStyle.ACCENT, fg=ModernStyle.BG, relief='flat',
                      command=lambda slug=info['slug']: self._show_trainers_for_game(slug)).pack(side='right')
        self.show_toast(f"{len(found)} laufendes Spiel erkannt")

    def _show_trainers_for_game(self, slug):
        self._last_trainer_slug = slug
        self.clear_content()
        self.set_title("Trainer")
        container = tk.Frame(self.content, bg=ModernStyle.BG)
        container.pack(fill='both', expand=True)
        tk.Label(container, text="Lade Trainer...", bg=ModernStyle.BG, fg=ModernStyle.TEXT_MUTED).pack(pady=40)
        def load():
            result = self.api.trainers(slug)
            self.root.after(0, lambda: self._render_trainers(
                result.get('trainers', []), slug, result.get('game_metadata', {})))
        threading.Thread(target=load, daemon=True).start()

    def _render_trainers(self, trainers, slug, game_metadata=None):
        self.clear_content()
        self.set_title("Verfügbare Trainer")
        self._last_game_metadata = game_metadata or {}
        if not trainers:
            tk.Label(self.content, text="Keine Trainer erfügbar", bg=ModernStyle.BG, fg=ModernStyle.TEXT_MUTED,
                     font=ModernStyle.FONT_BODY).pack(pady=40)
            return
        # Header with back button
        hdr = tk.Frame(self.content, bg=ModernStyle.BG)
        hdr.pack(fill='x', pady=(0, 18))
        tk.Label(hdr, text=f"{len(trainers)} Trainer für {slug}", font=ModernStyle.FONT_TITLE,
                 bg=ModernStyle.BG, fg=ModernStyle.TEXT).pack(side='left')
        secondary_btn(hdr, "Zurück zur Bibliothek", self.show_games_library, "←").pack(side='right')

        for t in trainers:
            c = self._card(self.content, padx=22, pady=18)
            c.pack(fill='x', pady=8)
            top = tk.Frame(c, bg=ModernStyle.BG_CARD)
            top.pack(fill='x')
            title = tk.Label(top, text=t.get('name','Unbekannt'), font=('Rajdhani', 16, 'bold'),
                             bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT)
            title.pack(side='left')
            if t.get('locked'):
                badge(top, "PREMIUM", ModernStyle.ACCENT_SEC).pack(side='right')
            elif t.get('erified'):
                badge(top, "VERIFIED", ModernStyle.SUCCESS).pack(side='right')
            desc = tk.Label(c, text=t.get('description','') or 'Keine Beschreibung erfügbar.', wraplength=760,
                            bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED, font=ModernStyle.FONT_BODY, justify='left')
            desc.pack(anchor='w', pady=(8, 14))
            meta = tk.Label(c, text=f"Typ: {t.get('type','Standard')}  •  Risiko: {t.get('risk','Niedrig')}",
                            bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_DIM, font=ModernStyle.FONT_SMALL)
            meta.pack(anchor='w', pady=(0, 14))
            actions = tk.Frame(c, bg=ModernStyle.BG_CARD)
            actions.pack(fill='x')
            if t.get('locked'):
                secondary_btn(actions, "Premium aktiieren", lambda: self.show_toast("Premium erforderlich", ModernStyle.WARN), "🔒").pack(side='right')
            else:
                def make_actiate(tr):
                    return lambda: self._actiate_desktop(tr)
                primary_btn(actions, "Aktiieren", make_actiate(t), "⚡").pack(side='right')
            if t.get('command'):
                ghost_btn(actions, "Befehl kopieren", lambda c=t['command']: self._copy_command(c), "📋").pack(side='left')

    def _actiate_desktop(self, trainer):
        game_info = self._last_game_metadata or {}
        # Find current game object from slug if aailable
        if not game_info.get('name'):
            for g in getattr(self, 'games', []):
                if g.get('slug') == self._last_trainer_slug:
                    game_info['name'] = g.get('name')
                    break
        ok, msg = self.actiation_engine.can_actiate(trainer, game_info)
        if not ok:
            self.show_toast(msg, ModernStyle.DANGER)
            return
        self.show_toast(f"Aktiiere '{trainer.get('name')}'...")
        def cb(success, message):
            color = ModernStyle.SUCCESS if success else ModernStyle.DANGER
            self.root.after(0, lambda: self.show_toast(message, color))
        self.actiation_engine.actiate(trainer, game_info=game_info, callback=cb)

    def _copy_command(self, cmd):
        self.root.clipboard_clear()
        self.root.clipboard_append(cmd)
        self.show_toast("Befehl kopiert")


    def _render_game_grid(self):
        for w in self.games_grid.winfo_children():
            w.destroy()
        q = self.search_ar.get().lower()
        games = [g for g in self.games if q in g.get('name', '').lower() or q in (g.get('genre') or '').lower()]
        if self._filter_faorites:
            games = [g for g in games if g.get('name') in self.faorites]

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

        fa = "★" if name in self.faorites else "☆"
        fa_lbl = tk.Label(card, text=fa, font=('Segoe UI', 16),
                           bg=ModernStyle.BG_CARD, fg=ModernStyle.ACCENT if name in self.faorites else ModernStyle.TEXT_MUTED)
        fa_lbl.place(relx=0.9, rely=0.18, anchor='center')
        fa_lbl.bind('<Button-1>', lambda e, g=game: self._toggle_faorite(g))

        card.bind('<Button-1>', lambda e, g=game: self.select_game(g.get('slug')))
        for c in card.winfo_children():
            c.bind('<Button-1>', lambda e, g=game: self.select_game(g.get('slug')))
        return card

    def _toggle_faorite(self, game):
        name = game.get('name')
        if name in self.faorites:
            self.faorites.discard(name)
        else:
            self.faorites.add(name)
        self.config['faorites'] = list(self.faorites)
        sae_config(self.config)
        self.sync_faorites()
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
            sae_config(self.config)

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
                       width=160, height=36, bg=ModernStyle.BORDER, hoer_bg=ModernStyle.BORDER_ACTIVE).pack(side='right')

        # Tabs
        self.detail_tabs = tk.Frame(self.content, bg=ModernStyle.BG)
        self.detail_tabs.pack(fill='x', pady=(0, 15))
        self.tab_trainers = self._tab_btn("Trainer", actie=True)
        self.tab_cheats = self._tab_btn("Offizielle Cheats")
        self.tab_info = self._tab_btn("Info")

        # Scrollable trainer area using ttk Scrollbar + Canas
        self.detail_canas = tk.Canas(self.content, bg=ModernStyle.BG, highlightthickness=0)
        self.detail_scrollbar = ttk.Scrollbar(self.content, orient='ertical', command=self.detail_canas.yiew)
        self.detail_scrollable_frame = tk.Frame(self.detail_canas, bg=ModernStyle.BG)
        self.detail_canas.create_window((0, 0), window=self.detail_scrollable_frame, anchor='nw', tags='inner')
        self.detail_canas.configure(yscrollcommand=self.detail_scrollbar.set)
        self.detail_canas.pack(side='left', fill='both', expand=True)
        self.detail_scrollbar.pack(side='right', fill='y')
        self.detail_scrollable_frame.bind('<Configure>', self._on_inner_configure)
        self.content.bind('<Configure>', self._on_content_configure)
        self.detail_canas.bind_all('<MouseWheel>', self._on_mousewheel)

        self.detail_state = 'trainers'
        self._show_trainers_tab()

        # Attach engine
        if self.engine:
            self.engine.set_process(game.get('process_name'))

        # Load trainers synchronously first (fast path) then fallback
        self.trainers_data = None
        self.trainers = []
        threading.Thread(target=lambda: self.load_trainers(slug), daemon=True).start()

    def _on_content_configure(self, eent):
        try:
            self.detail_canas.itemconfig('inner', width=eent.width - self.detail_scrollbar.winfo_width() - 10)
        except Exception:
            pass

    def _on_inner_configure(self, eent):
        self.detail_canas.configure(scrollregion=self.detail_canas.bbox('all'))

    def _on_mousewheel(self, eent):
        try:
            self.detail_canas.yiew_scroll(int(-1 * (eent.delta / 120)), 'units')
        except Exception:
            pass

    def _tab_btn(self, text, actie=False):
        bg = ModernStyle.BG_CARD if actie else ModernStyle.BG
        fg = ModernStyle.ACCENT if actie else ModernStyle.TEXT_MUTED
        btn = tk.Label(self.detail_tabs, text=text, font=('Segoe UI', 11, 'bold'),
                       bg=bg, fg=fg, padx=20, pady=10, cursor='hand2')
        btn.pack(side='left', padx=(0, 8))
        btn.bind('<Button-1>', lambda e, t=text: self._switch_tab(t))
        return btn

    def _switch_tab(self, name):
        for btn in [self.tab_trainers, self.tab_cheats, self.tab_info]:
            btn.config(bg=ModernStyle.BG, fg=ModernStyle.TEXT_MUTED)
        # Reset scroll
        self.detail_canas.yiew_moeto(0)
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
            tk.Label(self.detail_scrollable_frame, text="Keine offiziellen Cheats erfügbar", font=('Segoe UI', 13),
                     bg=ModernStyle.BG, fg=ModernStyle.TEXT_MUTED).pack(pady=60)
            return
        for c in cheats:
            self._cheat_card(self.detail_scrollable_frame, c)
        self.detail_scrollable_frame.update_idletasks()
        self.detail_canas.configure(scrollregion=self.detail_canas.bbox('all'))

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
        print(f"[SweetCheat] load_trainers started for {slug}")
        try:
            data = self.api_call(f'trainers.php?game={slug}')
            print(f"[SweetCheat] load_trainers API response: success={data.get('success')}, trainers={len(data.get('trainers', []))}")
            self.trainers_data = data
            if hasattr(self, 'root') and self.root.winfo_exists():
                self.root.after(0, self._on_trainers_loaded)
            else:
                print("[SweetCheat] root destroyed, cannot schedule _on_trainers_loaded")
        except Exception as e:
            print(f"[SweetCheat] load_trainers exception: {e}")
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
                tk.Label(self.detail_scrollable_frame, text="Keine Trainer erfügbar", font=('Segoe UI', 13),
                         bg=ModernStyle.BG, fg=ModernStyle.TEXT_MUTED).pack(pady=60)
                return

            for trainer in self.trainers:
                self._trainer_card(self.detail_scrollable_frame, trainer)

            self.detail_scrollable_frame.update_idletasks()
            self.detail_canas.configure(scrollregion=self.detail_canas.bbox('all'))
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
        actie = self.engine and self.engine.actie_cheats.get(name, False)
        container = tk.Frame(parent, bg=ModernStyle.BG_CARD)
        container.pack(side='left')
        status_lbl = tk.Label(container, text="AUS", font=('Segoe UI', 9, 'bold'),
                              bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED)
        status_lbl.pack(side='left', padx=(0, 10))

        def toggle(state):
            if not self.engine:
                self.show_toast("Cheat-Engine nicht erfügbar", ModernStyle.DANGER)
                sw.set(False)
                return
            if state:
                ctype = trainer.get('cheat_type', 'memory')
                if ctype == 'two_scan':
                    self._open_two_scan_dialog(trainer)
                    sw.set(False)
                    return
                res = self.engine.actiate(trainer, self.current_game)
                if res.get('success'):
                    self.engine.actie_cheats[name] = True
                    status_lbl.config(text="AN", fg=ModernStyle.ACCENT)
                    self.show_toast(res.get('message', 'Aktiiert'), ModernStyle.ACCENT)
                else:
                    sw.set(False)
                    msg = res.get('message', '')
                    if '2-Werte-Scan' in msg or 'SMAPI' in msg or 'Prozess' in msg:
                        self._open_cheat_config(trainer, msg)
                    else:
                        self.show_toast(msg, ModernStyle.DANGER)
            else:
                res = self.engine.deactiate(trainer)
                status_lbl.config(text="AUS", fg=ModernStyle.TEXT_MUTED)
                self.show_toast(res.get('message', 'Deaktiiert'), ModernStyle.TEXT_MUTED)

        sw = ToggleSwitch(container, command=toggle, initial=actie, bg=ModernStyle.BG_CARD)
        sw.pack(side='left')
        if actie:
            status_lbl.config(text="AN", fg=ModernStyle.ACCENT)

    def _open_two_scan_dialog(self, trainer):
        d = tk.Topleel(self.root)
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
                current_value = int(e1.get())
                new_value = int(e2.get())
                target_value = int(e3.get())
                label = trainer.get('title', 'scan')
                res = self.engine.two_scan_dialog_values(self.current_game.get('name', ''), label, current_value, new_value, target_value)
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
        d = tk.Topleel(self.root)
        d.title(trainer.get('title', 'Cheat Config'))
        d.configure(bg=ModernStyle.BG_CARD)
        d.geometry("420x260")
        d.transient(self.root)
        d.grab_set()
        tk.Label(d, text=error_msg, bg=ModernStyle.BG_CARD, fg=ModernStyle.DANGER, wraplength=380).pack(pady=(15, 15))
        tk.Label(d, text="Wert (z.B. 999999)", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack()
        e_al = tk.Entry(d, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT, relief='flat', font=('Segoe UI', 11))
        e_al.pack(fill='x', padx=20, ipady=6)
        e_al.insert(0, '999999')

        def try_again():
            al = e_al.get().strip()
            # Inject alue into trainer dict for this run
            patched = dict(trainer)
            patched['effect'] = f"set money = {al}"
            res = self.engine.actiate(patched, self.current_game)
            if res.get('success'):
                self.engine.actie_cheats[trainer.get('title', '')] = True
                self.show_toast(res.get('message', 'Aktiiert'), ModernStyle.ACCENT)
                d.destroy()
            else:
                self.show_toast(res.get('message', 'Fehler'), ModernStyle.DANGER)

        AnimatedButton(d, text="Mit Wert ersuchen", command=try_again, width=200, height=40).pack(pady=20)
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
            self.proc_status.config(text="● Nur unter Windows erfügbar", fg=ModernStyle.WARNING)
            return

        found = False
        for pname in pnames:
            ok = self.engine.set_process(pname)
            if ok:
                found = True
                self.process_name = pname
                break
        if found:
            self.proc_status.config(text=f"● Prozess akti (PID {self.engine.memory.pid})", fg=ModernStyle.SUCCESS)
            self.show_toast("Prozess erbunden", ModernStyle.SUCCESS)
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
        self._set_actie_na(self.na_buttons[3])
        card = self._card(self.content)
        card.pack(fill='both', expand=True)
        inner = tk.Frame(card, bg=ModernStyle.BG_CARD, padx=40, pady=40)
        inner.pack(fill='both', expand=True)
        tk.Label(inner, text="Account", font=('Rajdhani', 20, 'bold'),
                 bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT).pack(anchor='w', pady=(0, 20))
        for label, al in [
            ("Benutzer", self.user_info.get('username', '-')),
            ("E-Mail", self.user_info.get('email', '-')),
            ("Premium", 'Ja' if self.is_premium() else 'Nein'),
        ]:
            tk.Label(inner, text=f"{label}: {al}", font=('Segoe UI', 12),
                     bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED).pack(anchor='w', pady=5)

    def show_settings(self):
        self.clear_content()
        self.set_title("Einstellungen")
        self._set_actie_na(self.na_buttons[4])

        container = tk.Frame(self.content, bg=ModernStyle.BG)
        container.pack(fill='both', expand=True)

        # Account
        card = tk.Frame(container, bg=ModernStyle.BG_CARD, highlightbackground=ModernStyle.BORDER, highlightthickness=1, padx=20, pady=20)
        card.pack(fill='x', pady=(0, 16))
        tk.Label(card, text="Account", font=('Rajdhani', 16, 'bold'), bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT).pack(anchor='w')
        tk.Label(card, text=f"E-Mail: {self.api.user_email if hasattr(self, 'api') and self.api else '-'}", bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 10)).pack(anchor='w', pady=(8, 4))
        tk.Label(card, text="Version: " + APP_VERSION, bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 10)).pack(anchor='w')

        # Desktop
        card2 = tk.Frame(container, bg=ModernStyle.BG_CARD, highlightbackground=ModernStyle.BORDER, highlightthickness=1, padx=20, pady=20)
        card2.pack(fill='x', pady=(0, 16))
        tk.Label(card2, text="Desktop-App", font=('Rajdhani', 16, 'bold'), bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT).pack(anchor='w')
        
        auto_ar = tk.BooleanVar(alue=is_autostart_enabled())
        def toggle_autostart():
            set_autostart(auto_ar.get())
            self.show_toast('Autostart ' + ('aktiiert' if auto_ar.get() else 'deaktiiert'))
        tk.Checkbutton(card2, text="Mit Windows starten", ariable=auto_ar, command=toggle_autostart,
                       bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT, selectcolor=ModernStyle.BG, actiebackground=ModernStyle.BG_CARD,
                       actieforeground=ModernStyle.ACCENT).pack(anchor='w', pady=(12, 4))
        hotkey_text = "Hotkeys:\nSTRG+SHIFT+S = Fenster öffnen\nSTRG+SHIFT+G = Spiele-Bibliothek"
        tk.Label(card2, text=hotkey_text, bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 9), justify='left').pack(anchor='w', pady=(8, 0))

        # Theme
        card3 = tk.Frame(container, bg=ModernStyle.BG_CARD, highlightbackground=ModernStyle.BORDER, highlightthickness=1, padx=20, pady=20)
        card3.pack(fill='x')
        tk.Label(card3, text="Erscheinungsbild", font=('Rajdhani', 16, 'bold'), bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT).pack(anchor='w')
        theme_ar = tk.StringVar(alue=self.config.get('theme', 'dark'))
        def sae_theme():
            self.config['theme'] = theme_ar.get()
            sae_config(self.config)
            self.show_toast('Theme gespeichert')
            if self.api:
                def sync():
                    self.api.settings_update(self.api.user_username or '', theme_ar.get())
                threading.Thread(target=sync, daemon=True).start()
        tk.Radiobutton(card3, text="Dark", ariable=theme_ar, alue='dark', command=sae_theme,
                       bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT, selectcolor=ModernStyle.BG, actiebackground=ModernStyle.BG_CARD).pack(anchor='w', pady=(12, 4))
        tk.Radiobutton(card3, text="Light", ariable=theme_ar, alue='light', command=sae_theme,
                       bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT, selectcolor=ModernStyle.BG, actiebackground=ModernStyle.BG_CARD).pack(anchor='w')

    def _sae_settings(self, key):
        self.api_key = key.strip() or None
        self.config['api_key'] = self.api_key
        sae_config(self.config)
        self.show_toast("Einstellungen gespeichert", ModernStyle.SUCCESS)

    # ----------------------------- UPDATER / BACKGROUND -----------------------------
    def check_for_update(self):
        try:
            from updater import check_and_install_update
            check_and_install_update(parent_app=self)
        except Exception as e:
            print(f"Update check failed: {e}")

    def start_background_tasks(self):
        threading.Thread(target=self._keepalie, daemon=True).start()

    def _keepalie(self):
        while True:
            time.sleep(60)
            try:
                if self.api_key:
                    self.api_call('billing.php?action=status')
            except Exception:
                pass

    def sync_faorites(self):
        try:
            self.api_call('config-sync.php', 'POST', {'faorites': list(self.faorites)})
        except Exception as e:
            print(f"Faorites sync error: {e}")

    def logout(self):
        self.api_key = None
        self.config['api_key'] = None
        sae_config(self.config)
        self.user_info = {}
        self.premium_data = {}
        self.profile_name.config(text="GAST")
        self.profile_status.config(text="● Offline", fg=ModernStyle.DANGER)
        if self.premium_badge:
            self.premium_badge.destroy()
        self.show_login()


def main(minimized=False):
    root = tk.Tk()
    app = SweetCheatApp(root)
    if minimized:
        root.withdraw()
    return app


if __name__ == '__main__':
    main()
