import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import threading
import json
import os
import struct
import time
import urllib.request
import urllib.error
try:
    import sdv_savegame
    SDV_SAVE = True
except ImportError:
    SDV_SAVE = False

# Safety: refuse to attach to known multiplayer/anti-cheat processes
BLOCKED_PROCESSES = [
    'steam.exe', 'epicgameslauncher.exe', 'battleye', 'easyanticheat', 'valorant.exe',
    'cs2.exe', 'csgo.exe', 'league of legends.exe', 'overwatch.exe', 'fortnite.exe',
    'apex_legends.exe', 'rainbowsix.exe', 'call of duty.exe', 'cod.exe'
]

WINDOWS = False
try:
    import sys
    if sys.platform == 'win32':
        import pymem
        from pymem import Pymem
        import pymem.process
        import pymem.memory
        WINDOWS = True
except ImportError:
    WINDOWS = False

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

try:
    from savegame_trainers import SUPPORTED_SAVEGAME_TRAINERS
    SAVEGAME_TRAINERS = True
except ImportError:
    SAVEGAME_TRAINERS = False

API_BASE = os.environ.get('TRAINERHUB_API', 'https://sayfespace.online/trainerhub/api')
CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.trainerhub', 'config.json')

class TrainerHubGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TrainerHub — Stardew Valley")
        self.root.geometry("1100x750")
        self.root.configure(bg="#050507")
        self.api_key = None
        self.current_game_pid = None
        self.trainers = []
        self.scan_state = {}
        self.frozen_addresses = {}
        self.setup_styles()
        self.load_config()
        if self.api_key:
            self.validate_key()
        else:
            self.build_login_view()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TFrame', background='#050507')
        self.style.configure('TLabel', background='#050507', foreground='#f8fafc', font=('Segoe UI', 10))
        self.style.configure('TButton', background='#2563eb', foreground='#ffffff', font=('Segoe UI', 10, 'bold'), padding=8)
        self.style.map('TButton', background=[('active', '#3b82f6')])
        self.style.configure('TEntry', fieldbackground='#111118', foreground='#f8fafc')

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE) as f:
                    cfg = json.load(f)
                    self.api_key = cfg.get('api_key')
                    if 'email' in cfg:
                        self.email_var = tk.StringVar(value=cfg['email'])
            except Exception:
                pass

    def save_config(self):
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        cfg = {'api_key': self.api_key}
        if getattr(self, 'email_var', None):
            cfg['email'] = self.email_var.get()
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f)

    def api_call(self, endpoint, method='GET', data=None):
        headers = {}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        url = f'{API_BASE}/{endpoint}'
        try:
            if method == 'GET':
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as r:
                    return json.loads(r.read().decode('utf-8'))
            else:
                body = json.dumps(data).encode('utf-8') if data else b''
                req = urllib.request.Request(url, data=body, headers={**headers, 'Content-Type': 'application/json'}, method='POST')
                with urllib.request.urlopen(req, timeout=15) as r:
                    return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode('utf-8'))
            except Exception:
                return {'success': False, 'error': f'HTTP {e.code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def check_for_updates(self):
        try:
            req = urllib.request.Request(f'{API_BASE}/version.php', headers={'User-Agent': 'TrainerHub-Desktop'})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode('utf-8'))
            if data.get('success'):
                remote = data.get('version', '0.0.0')
                if remote != APP_VERSION:
                    return data.get('download_url')
        except Exception:
            pass
        return None

    def clear_window(self):
        for w in self.root.winfo_children():
            w.destroy()

    def build_login_view(self):
        self.clear_window()
        frame = tk.Frame(self.root, bg='#050507')
        frame.place(relx=0.5, rely=0.5, anchor='center')
        tk.Label(frame, text="TrainerHub", font=('Segoe UI', 28, 'bold'), bg='#050507', fg='#f8fafc').pack(pady=(0,10))
        tk.Label(frame, text="Singleplayer Trainer für 300+ Spiele", bg='#050507', fg='#64748b', font=('Segoe UI', 12)).pack(pady=(0,40))
        card = tk.Frame(frame, bg='#111118', highlightbackground='#232333', highlightthickness=1, padx=40, pady=40)
        card.pack()
        tk.Label(card, text="E-Mail", bg='#111118', fg='#64748b', font=('Segoe UI', 10)).pack(anchor='w', pady=(0,5))
        self.email_entry = tk.Entry(card, width=40, bg='#050507', fg='#f8fafc', insertbackground='#f8fafc', relief='flat', font=('Segoe UI', 11))
        self.email_entry.pack(pady=(0,15), ipady=6)
        tk.Label(card, text="Passwort", bg='#111118', fg='#64748b', font=('Segoe UI', 10)).pack(anchor='w', pady=(0,5))
        self.pass_entry = tk.Entry(card, width=40, show='*', bg='#050507', fg='#f8fafc', insertbackground='#f8fafc', relief='flat', font=('Segoe UI', 11))
        self.pass_entry.pack(pady=(0,25), ipady=6)
        tk.Button(card, text="Einloggen", bg='#2563eb', fg='#ffffff', font=('Segoe UI', 11, 'bold'), relief='flat', padx=20, pady=10, command=self.do_login).pack(fill='x')
        self.status_label = tk.Label(card, text="", bg='#111118', fg='#ef4444', font=('Segoe UI', 9))
        self.status_label.pack(pady=(15,0))
        tk.Label(card, text="Beta — kostenlos · sayfespace.online/trainerhub", bg='#111118', fg='#64748b', font=('Segoe UI', 9)).pack(pady=(25,0))

    def do_login(self):
        email = self.email_entry.get().strip()
        password = self.pass_entry.get()
        self.email_var = tk.StringVar(value=email)
        data = self.api_call('auth.php?action=login', 'POST', {'email': email, 'password': password})
        if data.get('success'):
            self.api_key = data['api_key']
            self.save_config()
            self.build_main_view()
            self.load_trainers()
        else:
            self.status_label.config(text=data.get('error', 'Login fehlgeschlagen'))

    def validate_key(self):
        data = self.api_call('billing.php?action=status')
        if data.get('success'):
            self.premium_data = self.api_call('premium.php?action=status')
            self.build_main_view()
            self.load_trainers()
        else:
            self.build_login_view()

    def build_main_view(self):
        self.clear_window()
        header = tk.Frame(self.root, bg='#050507', height=70)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="TrainerHub", font=('Segoe UI', 16, 'bold'), bg='#050507', fg='#f8fafc').pack(side='left', padx=25, pady=15)
        tk.Button(header, text="Account", bg='#111118', fg='#f8fafc', font=('Segoe UI', 10), relief='flat', padx=15, pady=5, command=self.show_account).pack(side='right', padx=(0,10), pady=15)
        tk.Button(header, text="Logout", bg='#111118', fg='#ef4444', font=('Segoe UI', 10), relief='flat', padx=15, pady=5, command=self.logout).pack(side='right', padx=(0,25), pady=15)
        self.sub_label = tk.Label(header, text="FREE", font=('Segoe UI', 10, 'bold'), bg='#050507', fg='#64748b')
        self.sub_label.pack(side='right', padx=15, pady=15)
        tk.Frame(self.root, bg='#232333', height=1).pack(fill='x')
        game_bar = tk.Frame(self.root, bg='#050507', padx=25, pady=15)
        game_bar.pack(fill='x')
        tk.Label(game_bar, text="Spiel:", bg='#050507', fg='#f8fafc', font=('Segoe UI', 11, 'bold')).pack(side='left', padx=(0,10))
        self.game_var = tk.StringVar(value='stardew-valley')
        self.game_combo = ttk.Combobox(game_bar, textvariable=self.game_var, values=[], state='readonly', width=30, font=('Segoe UI', 10))
        self.load_games()
        self.game_combo.pack(side='left')
        game_combo.bind('<<ComboboxSelected>>', lambda e: self.load_trainers())
        tk.Button(game_bar, text="🔍 Prozess prüfen", bg='#2563eb', fg='#ffffff', font=('Segoe UI', 10, 'bold'), relief='flat', padx=15, pady=5, command=self.check_process).pack(side='left', padx=(20,10))
        self.proc_label = tk.Label(game_bar, text="Stardew Valley nicht gestartet", bg='#050507', fg='#ef4444', font=('Segoe UI', 10))
        self.proc_label.pack(side='left')
        content = tk.Frame(self.root, bg='#050507')
        content.pack(fill='both', expand=True, padx=25, pady=(10,0))
        left = tk.Frame(content, bg='#050507')
        left.pack(side='left', fill='both', expand=True)
        tk.Label(left, text="Verfügbare Trainer", bg='#050507', fg='#f8fafc', font=('Segoe UI', 14, 'bold')).pack(anchor='w', pady=(0,10))
        canvas = tk.Canvas(left, bg='#050507', highlightthickness=0)
        scrollbar = ttk.Scrollbar(left, orient='vertical', command=canvas.yview)
        self.trainer_container = tk.Frame(canvas, bg='#050507')
        self.trainer_container.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0,0), window=self.trainer_container, anchor='nw', width=560)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        right = tk.Frame(content, bg='#050507', width=380)
        right.pack(side='right', fill='y', padx=(20,0))
        right.pack_propagate(False)
        tk.Label(right, text="Live-Log", bg='#050507', fg='#f8fafc', font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(0,10))
        self.log_box = scrolledtext.ScrolledText(right, bg='#111118', fg='#f8fafc', font=('Consolas', 9), state='disabled', wrap='word')
        self.log_box.pack(fill='both', expand=True)
        tk.Label(right, text="Gefundene Adressen", bg='#050507', fg='#f8fafc', font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(15,5))
        self.addr_list = tk.Listbox(right, bg='#111118', fg='#f8fafc', font=('Consolas', 9), height=8)
        self.addr_list.pack(fill='x')
        hint = tk.Frame(self.root, bg='#050507', padx=25, pady=10)
        hint.pack(fill='x')
        tk.Label(hint, text="Hinweis: Für präzise Scans gib deinen aktuellen Geld-/Energie-Wert ein. Bei zu vielen Treffern: Wert im Spiel ändern und erneut scannen.", bg='#050507', fg='#64748b', font=('Segoe UI', 9)).pack(anchor='w')
        
        # Hotkeys
        self.root.bind('<F5>', lambda e: self.check_process())
        self.root.bind('<F6>', lambda e: self.show_tutorial())
        self.root.bind('<F1>', lambda e: self.show_tutorial())
        
        # Tutorial button in header
        tk.Button(header, text="? Tutorial", bg='#111118', fg='#f8fafc', font=('Segoe UI', 10), relief='flat', padx=15, pady=5, command=self.show_tutorial).pack(side='right', padx=(0,10), pady=15)

    def log(self, msg):
        self.log_box.config(state='normal')
        self.log_box.insert('end', f"• {msg}\n")
        self.log_box.see('end')
        self.log_box.config(state='disabled')

    def has_feature(self, feature):
        try:
            return self.premium_data.get('features', {}).get(feature, False)
        except Exception:
            return False

    def load_games(self):
        data = self.api_call('games.php')
        if data.get('success'):
            games = data.get('games', [])
            values = [g['slug'] for g in games]
            self.game_combo.config(values=values)
            if values and not self.game_var.get():
                self.game_var.set(values[0])

    def load_trainers(self):
        slug = self.game_var.get()
        if not slug:
            return
        data = self.api_call(f'trainers.php?action=list&game={slug}')
        if not data.get('success'):
            self.log(f"Fehler: {data.get('error')}")
            return
        self.trainers = data.get('trainers', [])
        status = data.get('subscription', 'free')
        self.sub_label.config(text=status.upper(), fg='#fbbf24' if status == 'premium' else '#64748b')
        for w in self.trainer_container.winfo_children():
            w.destroy()
        if not self.trainers:
            tk.Label(self.trainer_container, text="Keine Trainer gefunden.", bg='#050507', fg='#64748b').pack(pady=20)
        else:
            # Show SMAPI bridge status for Stardew Valley
            if self.game_var.get() == 'stardew-valley' and BRIDGE:
                bridge_frame = tk.Frame(self.trainer_container, bg='#111118', highlightbackground='#10b981', highlightthickness=1, padx=15, pady=10)
                bridge_frame.pack(fill='x', pady=5)
                tk.Label(bridge_frame, text="🌉 SMAPI Bridge erkannt", bg='#111118', fg='#10b981', font=('Segoe UI', 11, 'bold')).pack(anchor='w')
                tk.Label(bridge_frame, text="Installiere den TrainerHub Bridge SMAPI-Mod für sichere, update-sichere Cheats.", bg='#111118', fg='#64748b', font=('Segoe UI', 9)).pack(anchor='w')
                tk.Button(bridge_frame, text="Mit SMAPI verbinden", bg='#10b981', fg='#ffffff', font=('Segoe UI', 9, 'bold'), relief='flat', padx=15, pady=6, command=self.connect_stardew_bridge).pack(anchor='e', pady=(10,0))

            for t in self.trainers:
                card = tk.Frame(self.trainer_container, bg='#111118', highlightbackground='#232333', highlightthickness=1, padx=15, pady=15)
                card.pack(fill='x', pady=5)
                header_frame = tk.Frame(card, bg='#111118')
                header_frame.pack(fill='x')
                title = t['name'] + (' 🔒 PREMIUM' if t.get('locked') else '')
                tk.Label(header_frame, text=title, bg='#111118', fg='#f8fafc', font=('Segoe UI', 12, 'bold')).pack(side='left')
                if self.has_feature('pattern_library'):
                    tk.Button(header_frame, text="⭐", bg='#111118', fg='#fbbf24', font=('Segoe UI', 10), relief='flat', command=lambda tr=t: self.toggle_favorite(tr['name'])).pack(side='right')
                tk.Label(card, text=t.get('description', ''), bg='#111118', fg='#64748b', font=('Segoe UI', 9)).pack(anchor='w', pady=(5,0))
                if t.get('locked'):
                    tk.Button(card, text="Premium beantragen", bg='#fbbf24', fg='#000000', font=('Segoe UI', 9, 'bold'), relief='flat', padx=15, pady=6, command=self.show_premium_dialog).pack(anchor='e', pady=(10,0))
                else:
                    btn_frame = tk.Frame(card, bg='#111118')
                    btn_frame.pack(fill='x', pady=(10,0))
                    ctype = t.get('cheat_type', '')
                    game_slug = self.game_var.get()
                    if ctype == 'smapi_set':
                        stat = t.get('name','').lower().replace('smap bridge ', '').replace('smapi ', '').split()[0]
                        tk.Button(btn_frame, text="SMAPI Set", bg='#9146FF', fg='#ffffff', font=('Segoe UI', 9, 'bold'), relief='flat', padx=15, pady=6, command=lambda tr=t, st=stat: self.smapi_set_value(st)).pack(side='right')
                    elif ctype == 'command':
                        cmd_text = t.get('description','')
                        tk.Button(btn_frame, text="In Zwischenablage", bg='#10b981', fg='#ffffff', font=('Segoe UI', 9, 'bold'), relief='flat', padx=15, pady=6, command=lambda ct=cmd_text: self.copy_to_clipboard(ct)).pack(side='right')
                    elif ctype == 'two_scan' or ctype == 'scan':
                        label = 'money' if 'geld' in t['name'].lower() or 'money' in t['name'].lower() else ('health' if 'leben' in t['name'].lower() or 'health' in t['name'].lower() or 'hp' in t['name'].lower() else 'energy')
                        vtype = 'int32' if label == 'money' or label == 'health' else 'float'
                        tk.Button(btn_frame, text="2-Scan starten", bg='#2563eb', fg='#ffffff', font=('Segoe UI', 9, 'bold'), relief='flat', padx=15, pady=6, command=lambda tr=t, vt=vtype, lb=label: self.scan_with_two_values(tr, vt, lb)).pack(side='right', padx=(0,5))
                    elif ctype == 'savegame' or (game_slug == 'stardew-valley' and 'savegame' in t['name'].lower()):
                        tk.Button(btn_frame, text="Savegame Editor", bg='#10b981', fg='#ffffff', font=('Segoe UI', 9, 'bold'), relief='flat', padx=15, pady=6, command=lambda tr=t: self.open_savegame_editor('money')).pack(side='right', padx=(0,5))
                    elif ctype == 'pattern_learner' or ctype == 'pattern':
                        tk.Button(btn_frame, text="🔍 Pattern lernen", bg='#232333', fg='#10b981', font=('Segoe UI', 9), relief='flat', padx=10, pady=6, command=lambda tr=t: self.open_pattern_learner(tr)).pack(side='left')
                    elif t.get('patterns'):
                        tk.Button(btn_frame, text="Pattern-Scan", bg='#2563eb', fg='#ffffff', font=('Segoe UI', 9, 'bold'), relief='flat', padx=15, pady=6, command=lambda tr=t: self.run_pattern_scan(tr)).pack(side='right')
                    else:
                        tk.Button(btn_frame, text="Anleitung anzeigen", bg='#2563eb', fg='#ffffff', font=('Segoe UI', 9, 'bold'), relief='flat', padx=15, pady=6, command=lambda tr=t: self.show_trainer_info(tr)).pack(side='right')
                    
                    if self.has_feature('pattern_library') and PATTERN_LEARNER:
                        tk.Button(btn_frame, text="🔍 Pattern lernen", bg='#232333', fg='#10b981', font=('Segoe UI', 9), relief='flat', padx=10, pady=6, command=lambda tr=t: self.open_pattern_learner(tr)).pack(side='left')
        
        # Official Cheats / Console Commands section
        self.load_official_cheats()
        
        # Community Patterns section
        self.load_community_patterns()

    def load_official_cheats(self):
        current = self.game_var.get()
        try:
            data = self.api_call(f'cheats.php?game={current}')
            cheats = data.get('cheats', [])
            if cheats:
                section = tk.LabelFrame(self.trainer_container, text="Offizielle Cheats / Konsolenbefehle", bg='#050507', fg='#10b981', font=('Segoe UI', 12, 'bold'), relief='solid', borderwidth=1)
                section.pack(fill='x', pady=15, padx=5)
                for c in cheats[:5]:
                    card = tk.Frame(section, bg='#111118', highlightbackground='#232333', highlightthickness=1, padx=12, pady=10)
                    card.pack(fill='x', pady=4, padx=5)
                    tk.Label(card, text=c['name'], bg='#111118', fg='#f8fafc', font=('Segoe UI', 11, 'bold')).pack(anchor='w')
                    tk.Label(card, text=c['description'], bg='#111118', fg='#64748b', font=('Segoe UI', 9)).pack(anchor='w')
                    cmd_frame = tk.Frame(card, bg='#111118')
                    cmd_frame.pack(fill='x', pady=(5,0))
                    cmd_text = c['command'] + (f" {c['params']}" if c.get('params') else '')
                    tk.Entry(cmd_frame, bg='#050507', fg='#10b981', font=('Consolas', 10), state='readonly', readonlybackground='#050507').pack(side='left', fill='x', expand=True)
                    tk.Button(cmd_frame, text="Kopieren", bg='#232333', fg='#f8fafc', font=('Segoe UI', 9), relief='flat', command=lambda ct=cmd_text: self.copy_to_clipboard(ct)).pack(side='right', padx=(5,0))
        except Exception as e:
            self.log(f"Cheats laden fehlgeschlagen: {e}")

    def load_community_patterns(self):
        if not self.has_feature('pattern_library'):
            return
        current = self.game_var.get()
        try:
            data = self.api_call(f'community-patterns.php?action=list&game={current}')
            patterns = data.get('patterns', [])
            if patterns:
                section = tk.LabelFrame(self.trainer_container, text="👥 Community Patterns", bg='#050507', fg='#9146FF', font=('Segoe UI', 12, 'bold'), relief='solid', borderwidth=1)
                section.pack(fill='x', pady=15, padx=5)
                for p in patterns[:5]:
                    card = tk.Frame(section, bg='#111118', highlightbackground='#232333', highlightthickness=1, padx=12, pady=10)
                    card.pack(fill='x', pady=4, padx=5)
                    header = tk.Frame(card, bg='#111118')
                    header.pack(fill='x')
                    tk.Label(header, text=f"{p['name']} ({p['votes']} Votes)", bg='#111118', fg='#f8fafc', font=('Segoe UI', 11, 'bold')).pack(side='left')
                    tk.Label(header, text=f"by {p['author']}", bg='#111118', fg='#64748b', font=('Segoe UI', 9)).pack(side='right')
                    tk.Label(card, text=f"Pattern: {p['pattern'][:60]}... | {p['value_type']} = {p['value']}", bg='#111118', fg='#64748b', font=('Consolas', 9)).pack(anchor='w', pady=(5,0))
                    btn_frame = tk.Frame(card, bg='#111118')
                    btn_frame.pack(fill='x', pady=(5,0))
                    tk.Button(btn_frame, text="👍", bg='#232333', fg='#10b981', font=('Segoe UI', 9), relief='flat', command=lambda pid=p['id']: self.vote_pattern(pid, 1)).pack(side='right', padx=(0,5))
                    tk.Button(btn_frame, text="👎", bg='#232333', fg='#ef4444', font=('Segoe UI', 9), relief='flat', command=lambda pid=p['id']: self.vote_pattern(pid, -1)).pack(side='right')
                    tk.Button(btn_frame, text="Pattern übernehmen", bg='#9146FF', fg='#ffffff', font=('Segoe UI', 9, 'bold'), relief='flat', command=lambda pp=p: self.use_community_pattern(pp)).pack(side='left')
        except Exception as e:
            self.log(f"Community Patterns laden fehlgeschlagen: {e}")

    def copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("Kopiert", f"{text[:50]}... kopiert!")

    def vote_pattern(self, pattern_id, vote):
        try:
            self.api_call('community-patterns.php?action=vote', 'POST', {'pattern_id': pattern_id, 'vote': vote})
            self.log(f"Pattern {pattern_id}: {'Upvote' if vote > 0 else 'Downvote'}")
            self.load_trainers()
        except Exception as e:
            self.log(f"Vote fehlgeschlagen: {e}")

    def use_community_pattern(self, pattern):
        if not self.has_feature('pattern_library'):
            self.show_premium_dialog()
            return
        self.config['active_pattern'] = pattern
        self.save_config()
        self.log(f"Community Pattern übernommen: {pattern['name']}")
        messagebox.showinfo("Pattern", f"{pattern['name']} übernommen. Klicke auf 'Pattern-Scan' zum Anwenden.")

    def open_pattern_learner(self, trainer):
        if not WINDOWS:
            messagebox.showinfo("Nur Windows", "Pattern-Lernen braucht Windows + laufendes Spiel.")
            return
        if not self.current_game_pid:
            self.check_process()
            if not self.current_game_pid:
                messagebox.showwarning("Spiel nicht gefunden", "Starte das Spiel zuerst.")
                return
        
        win = tk.Toplevel(self.root)
        win.title("Pattern Learner")
        win.geometry("500x450")
        win.configure(bg='#050507')
        
        tk.Label(win, text="Pattern Learner", bg='#050507', fg='#f8fafc', font=('Segoe UI', 14, 'bold')).pack(pady=10)
        tk.Label(win, text="Finde selbst stabile Memory-Adressen ohne fremde Cheats.", bg='#050507', fg='#64748b', font=('Segoe UI', 10)).pack(pady=(0,10))
        
        tk.Label(win, text="Aktueller Wert:", bg='#050507', fg='#f8fafc').pack(anchor='w', padx=20, pady=(10,0))
        val1 = tk.Entry(win, bg='#111118', fg='#f8fafc', font=('Segoe UI', 11))
        val1.pack(fill='x', padx=20, pady=5)
        
        tk.Label(win, text="Wert-Typ:", bg='#050507', fg='#f8fafc').pack(anchor='w', padx=20)
        vtype = ttk.Combobox(win, values=['int32', 'float', 'int64', 'int8', 'int16', 'double'], state='readonly')
        vtype.set('int32')
        vtype.pack(fill='x', padx=20, pady=5)
        
        result_label = tk.Label(win, text="Bereit.", bg='#050507', fg='#64748b', font=('Segoe UI', 10))
        result_label.pack(pady=10)
        
        def do_scan():
            try:
                learner = PatternLearner(self.current_game_pid)
                value = int(val1.get())
                addrs = learner.first_scan(value, vtype.get())
                result_label.config(text=f"Gefunden: {len(addrs)} Adressen", fg='#10b981')
                self._learner = learner
                self._learner_results = addrs
            except Exception as e:
                result_label.config(text=f"Fehler: {e}", fg='#ef4444')
        
        def do_filter():
            if not hasattr(self, '_learner') or not self._learner_results:
                result_label.config(text="Zuerst scannen.", fg='#ef4444')
                return
            try:
                value = int(val1.get())
                addrs = self._learner.next_scan(value)
                self._learner_results = addrs
                result_label.config(text=f"Nach Filter: {len(addrs)} Adressen", fg='#10b981')
                if len(addrs) <= 5:
                    for a in addrs:
                        pattern = self._learner.generate_pattern(a)
                        self.log(f"Pattern-Learner: Adresse 0x{a:X} - Pattern: {pattern[:40]}...")
            except Exception as e:
                result_label.config(text=f"Fehler: {e}", fg='#ef4444')
        
        def upload_pattern():
            if not self._learner_results or len(self._learner_results) != 1:
                result_label.config(text="Genau 1 Adresse nötig.", fg='#ef4444')
                return
            addr = self._learner_results[0]
            pattern = self._learner.generate_pattern(addr)
            name = simpledialog.askstring("Pattern hochladen", "Name für dein Pattern:")
            if not name: return
            try:
                current_game = self.game_var.get()
                # find game_id
                games = self.api_call('games.php').get('games', [])
                game_id = next((g['id'] for g in games if g['slug'] == current_game), None)
                if game_id:
                    self.api_call('community-patterns.php?action=submit', 'POST', {
                        'game_id': game_id,
                        'name': name,
                        'pattern': pattern,
                        'value_type': vtype.get(),
                        'value': val1.get(),
                        'game_version': '*'
                    })
                    result_label.config(text="Pattern eingereicht!", fg='#10b981')
                    self.log(f"Community Pattern eingereicht: {name}")
            except Exception as e:
                result_label.config(text=f"Upload fehlgeschlagen: {e}", fg='#ef4444')
        
        tk.Button(win, text="1. Scan starten", bg='#2563eb', fg='#ffffff', font=('Segoe UI', 10, 'bold'), relief='flat', command=do_scan).pack(fill='x', padx=20, pady=5)
        tk.Button(win, text="2. Filter / Pattern generieren", bg='#10b981', fg='#ffffff', font=('Segoe UI', 10, 'bold'), relief='flat', command=do_filter).pack(fill='x', padx=20, pady=5)
        if self.has_feature('pattern_library'):
            tk.Button(win, text="3. Mit Community teilen", bg='#9146FF', fg='#ffffff', font=('Segoe UI', 10, 'bold'), relief='flat', command=upload_pattern).pack(fill='x', padx=20, pady=5)

    def connect_stardew_bridge(self):
        if not BRIDGE:
            messagebox.showinfo("Nicht verfügbar", "SMAPI Bridge nur auf Windows verfügbar.")
            return
        client = stardew_bridge.StardewBridgeClient()
        if client.connect(timeout=3.0):
            self.bridge_client = client
            resp = client.get('money')
            self.log(f"SMAPI Bridge verbunden. Geld: {resp}")
            messagebox.showinfo("SMAPI Bridge", f"Verbunden! Aktuelles Geld: {resp}")
        else:
            messagebox.showwarning("SMAPI Bridge", "Verbindung fehlgeschlagen. Starte Stardew Valley über SMAPI und stelle sicher, dass der TrainerHub Bridge-Mod installiert ist.")

    def smapi_set_value(self, stat):
        if not hasattr(self, 'bridge_client') or not self.bridge_client:
            self.connect_stardew_bridge()
        if not hasattr(self, 'bridge_client') or not self.bridge_client:
            return
        val = simpledialog.askinteger("SMAPI Wert", f"Neuer Wert für {stat}:", initialvalue=999999 if stat == 'money' else 9999)
        if val is None: return
        resp = self.bridge_client.set(stat, val)
        self.log(f"SMAPI: {stat} -> {val} ({resp})")
        if resp and resp.startswith('ok'):
            messagebox.showinfo("Erfolg", f"{stat} auf {val} gesetzt!")
        else:
            messagebox.showerror("Fehler", f"SMAPI Fehler: {resp}")

    def get_process_name(self):
        try:
            current = self.game_var.get()
            if not current and self.trainers:
                return self.trainers[0].get('process_name', '')
            for t in self.trainers:
                if t.get('game_slug') == current:
                    return t.get('process_name', '')
        except Exception:
            pass
        return ''

    def check_process(self):
        if not WINDOWS:
            self.proc_label.config(text="Nur auf Windows verfügbar", fg='#ef4444')
            self.log("Windows-only: Prozess-Scan braucht Windows + pymem.")
            return
        try:
            procs = pymem.process.list_processes()
            for proc in procs:
                name = proc.sz_exeFile.decode('utf-8', errors='ignore')
                proc_filter = self.get_process_name().lower().replace('.exe','')
            if proc_filter and proc_filter in name.lower():
                    self.current_game_pid = proc.th32ProcessID
                    self.proc_label.config(text=f"Gefunden: {name} (PID {proc.th32ProcessID})", fg='#10b981')
                    self.log(f"Prozess gefunden: {name} PID {proc.th32ProcessID}")
                    return
                    
            self.proc_label.config(text="Spiel nicht gestartet", fg='#ef4444')
            self.log("Stardew Valley nicht gefunden.")
        except Exception as e:
            self.proc_label.config(text=f"Fehler: {e}", fg='#ef4444')
            self.log(f"Prozess-Fehler: {e}")

    def scan_with_two_values(self, trainer, value_type, label):
        if not WINDOWS:
            messagebox.showinfo("Demo", "Auf Windows würde jetzt gescannt und geschrieben.")
            return
        if not self.current_game_pid:
            self.check_process()
            if not self.current_game_pid:
                messagebox.showwarning("Spiel nicht gefunden", "Starte Stardew Valley zuerst.")
                return
        current = simpledialog.askinteger("Wert 1", f"Gib deinen aktuellen {label}-Wert ein:")
        if current is None: return
        messagebox.showinfo("Schritt 2", f"Ändere jetzt deinen {label}-Wert im Spiel (z.B. etwas kaufen/verkaufen), dann klicke OK.")
        changed = simpledialog.askinteger("Wert 2", f"Gib den neuen {label}-Wert ein:")
        if changed is None: return
        target = simpledialog.askinteger("Zielwert", f"Auf welchen Wert setzen?", initialvalue=999999 if label == 'money' else 9999)
        if target is None: return
        self.log(f"2-Scan {label}: {current} -> {changed} -> Ziel {target}")
        threading.Thread(target=self.two_value_scan_worker, args=(current, changed, target, value_type, label)).start()

    def two_value_scan_worker(self, val1, val2, target, value_type, label):
        try:
            pm = Pymem(self.current_game_pid)
            pack_fmt = '<i' if value_type == 'int32' else '<f'
            b1 = struct.pack(pack_fmt, val1 if value_type == 'int32' else float(val1))
            b2 = struct.pack(pack_fmt, val2 if value_type == 'int32' else float(val2))
            candidates = []
            regions = self.get_regions(pm)
            self.log(f"Scanne {len(regions)} Regionen nach Wert {val1}...")
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
                except Exception:
                    continue
                if len(candidates) > 20000: break
            self.log(f"Erster Scan: {len(candidates)} Kandidaten")
            if not candidates:
                self.log("Keine Treffer für Wert 1. Scan abgebrochen.")
                pm.close_process(); return
            # Second pass: verify changed value
            confirmed = []
            for addr in candidates[:10000]:
                try:
                    if pm.read_bytes(addr, 4) == b2:
                        confirmed.append(addr)
                except Exception:
                    pass
            self.log(f"Zweiter Scan: {len(confirmed)} Adressen mit Wert {val2}")
            if len(confirmed) > 1:
                # Third pass: ask user to change value again
                self.log("Wähle eine Adresse oder ändere den Wert ein drittes Mal.")
                self.update_addr_list(confirmed)
                self.scan_state = {'pm': pm, 'value_type': value_type, 'target': target, 'label': label, 'addresses': confirmed}
            elif len(confirmed) == 1:
                addr = confirmed[0]
                self.update_addr_list([addr])
                if self.write_value(pm, addr, target, value_type):
                    self.log(f"✅ {label} auf {target} gesetzt! ({hex(addr)})")
                    self.freeze_address(pm, addr, target, value_type, label)
                else:
                    self.log(f"❌ Schreiben fehlgeschlagen")
                    pm.close_process()
            else:
                self.log("Keine Adresse bestätigt. Bitte stärkeren Wert-Wechsel versuchen.")
                pm.close_process()
        except Exception as e:
            self.log(f"Scan-Fehler: {e}")

    def update_addr_list(self, addresses):
        self.addr_list.delete(0, tk.END)
        for addr in addresses[:50]:
            self.addr_list.insert(tk.END, hex(addr))

    def on_addr_double_click(self, event):
        self.set_selected_address()

    def set_selected_address(self):
        sel = self.addr_list.curselection()
        if not sel:
            messagebox.showinfo("Adresse wählen", "Bitte eine Adresse aus der Liste auswählen.")
            return
        idx = sel[0]
        if 'addresses' not in self.scan_state or idx >= len(self.scan_state['addresses']):
            return
        addr = self.scan_state['addresses'][idx]
        target = self.scan_state.get('target', 999999)
        value_type = self.scan_state.get('value_type', 'int32')
        label = self.scan_state.get('label', 'value')
        try:
            pm = Pymem(self.current_game_pid)
            if self.write_value(pm, addr, target, value_type):
                self.log(f"✅ {label} auf {target} an {hex(addr)} gesetzt")
                self.freeze_address(pm, addr, target, value_type, label)
            else:
                self.log("❌ Schreiben fehlgeschlagen")
                pm.close_process()
        except Exception as e:
            self.log(f"Fehler: {e}")

    def run_third_scan(self):
        if 'addresses' not in self.scan_state or not self.scan_state['addresses']:
            messagebox.showinfo("Scan", "Zuerst einen 2-Scan durchführen.")
            return
        val3 = simpledialog.askinteger("3. Wert", "Ändere den Wert im Spiel erneut und gib ihn ein:")
        if val3 is None: return
        threading.Thread(target=self.third_scan_worker, args=(val3,)).start()

    def third_scan_worker(self, val3):
        try:
            state = self.scan_state
            value_type = state['value_type']
            pack_fmt = '<i' if value_type == 'int32' else '<f'
            b3 = struct.pack(pack_fmt, val3 if value_type == 'int32' else float(val3))
            pm = Pymem(self.current_game_pid)
            confirmed = []
            for addr in state['addresses'][:5000]:
                try:
                    if pm.read_bytes(addr, 4) == b3:
                        confirmed.append(addr)
                except Exception: pass
            self.log(f"Dritter Scan: {len(confirmed)} Treffer")
            self.update_addr_list(confirmed)
            state['addresses'] = confirmed
            if len(confirmed) == 1:
                self.set_selected_address()
            elif not confirmed:
                self.log("Keine Treffer mehr. Starte neu.")
                pm.close_process()
        except Exception as e:
            self.log(f"3-Scan Fehler: {e}")

    def open_savegame_editor(self, stat):
        if not SDV_SAVE:
            messagebox.showinfo("Nicht verfügbar", "Savegame-Editor nicht geladen.")
            return
        saves = sdv_savegame.list_saves()
        if not saves:
            messagebox.showwarning("Keine Saves", "Keine Stardew Valley-Savegames gefunden.")
            return
        win = tk.Toplevel(self.root)
        win.title("Stardew Valley Savegame Editor")
        win.geometry("500x400")
        win.configure(bg='#050507')
        tk.Label(win, text="Savegame auswählen", bg='#050507', fg='#f8fafc', font=('Segoe UI', 12, 'bold')).pack(pady=10)
        listbox = tk.Listbox(win, bg='#111118', fg='#f8fafc', font=('Segoe UI', 10), height=8)
        listbox.pack(fill='x', padx=20, pady=10)
        for save in saves:
            listbox.insert(tk.END, save['name'])
        
        def load_selected():
            idx = listbox.curselection()
            if not idx: return
            path = saves[idx[0]]['path']
            info = sdv_savegame.read_save(path)
            if info:
                info_text.delete(1.0, tk.END)
                info_text.insert(tk.END, json.dumps(info, indent=2))
                win.current_path = path
            else:
                messagebox.showerror("Fehler", "Savegame konnte nicht gelesen werden.")
        
        tk.Button(win, text="Laden", bg='#2563eb', fg='#fff', font=('Segoe UI', 10, 'bold'), relief='flat', command=load_selected).pack(pady=5)
        info_text = tk.Text(win, bg='#111118', fg='#f8fafc', font=('Consolas', 9), height=8)
        info_text.pack(fill='both', expand=True, padx=20, pady=10)
        
        def set_value():
            if not hasattr(win, 'current_path'):
                messagebox.showwarning("Zuerst laden", "Bitte Savegame laden.")
                return
            val = simpledialog.askinteger("Neuer Wert", f"Neuer Wert für {stat}:", initialvalue=999999)
            if val is None: return
            if sdv_savegame.write_save(win.current_path, {stat: val}):
                messagebox.showinfo("Erfolg", f"{stat} auf {val} gesetzt! Starte Stardew Valley neu.")
                self.log(f"Savegame: {stat} auf {val} gesetzt")
            else:
                messagebox.showerror("Fehler", "Schreiben fehlgeschlagen.")
        
        tk.Button(win, text=f"{stat.title()} setzen", bg='#fbbf24', fg='#000', font=('Segoe UI', 10, 'bold'), relief='flat', command=set_value).pack(pady=10)

    def run_pattern_scan(self, trainer):
        if not WINDOWS:
            messagebox.showinfo("Demo", "Pattern-Scan nur auf Windows."); return
        if not self.current_game_pid:
            self.check_process()
            if not self.current_game_pid:
                messagebox.showwarning("Spiel nicht gefunden", "Starte Stardew Valley zuerst."); return
        patterns = trainer.get('patterns', [])
        if not patterns:
            self.log("Keine Patterns vorhanden."); return
        threading.Thread(target=self.pattern_scan_worker, args=(patterns, trainer['name'])).start()

    def pattern_scan_worker(self, patterns, trainer_name):
        try:
            pm = Pymem(self.current_game_pid)
            module = pymem.process.module_from_name(pm.process_handle, 'Stardew Valley.exe')
            base = module.lpBaseOfDll
            size = module.SizeOfImage
            data = pm.read_bytes(base, size)
            for p in patterns:
                pattern_str = p.get('pattern', '')
                bytes_pattern = self.parse_pattern(pattern_str)
                if not bytes_pattern:
                    self.log(f"Ungültiges Pattern: {pattern_str}"); continue
                found = []
                idx = 0
                while True:
                    idx = self.find_pattern(data, bytes_pattern, idx)
                    if idx == -1: break
                    found.append(base + idx + p.get('offset', 0))
                    idx += 1
                self.log(f"Pattern: {len(found)} Treffer")
                if found and p.get('value') is not None:
                    addr = found[0]
                    val = int(p['value']) if p['value_type'] == 'int32' else float(p['value'])
                    if self.write_value(pm, addr, val, p['value_type']):
                        self.log(f"✅ {trainer_name} aktiviert an {hex(addr)}")
                        self.freeze_address(pm, addr, val, p['value_type'], trainer_name)
                    else:
                        self.log(f"❌ Schreiben fehlgeschlagen")
            pm.close_process()
        except Exception as e:
            self.log(f"Pattern-Fehler: {e}")

    def parse_pattern(self, pattern_str):
        parts = pattern_str.split()
        result = []
        for p in parts:
            if p in ('??', '?'):
                result.append(None)
            else:
                try: result.append(int(p, 16))
                except ValueError: return None
        return result

    def find_pattern(self, data, pattern, start):
        for i in range(start, len(data) - len(pattern) + 1):
            match = True
            for j, byte in enumerate(pattern):
                if byte is not None and data[i + j] != byte:
                    match = False; break
            if match: return i
        return -1

    def write_value(self, pm, address, value, value_type):
        try:
            if value_type == 'int32': pm.write_int(address, int(value))
            elif value_type == 'float': pm.write_float(address, float(value))
            elif value_type == 'bytes': pm.write_bytes(address, value, len(value))
            return True
        except Exception: return False

    def freeze_address(self, pm, address, value, value_type, label):
        if label in self.frozen_addresses:
            self.frozen_addresses[label]['stop'] = True
        stop_flag = {'stop': False}
        self.frozen_addresses[label] = stop_flag
        def loop():
            while not stop_flag['stop']:
                try:
                    self.write_value(pm, address, value, value_type)
                    time.sleep(1)
                except Exception:
                    break
            try: pm.close_process()
            except Exception: pass
        threading.Thread(target=loop, daemon=True).start()
        self.log(f"🧊 {label} wird jede Sekunde neu geschrieben (Freeze).")

    def get_regions(self, pm):
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

    def show_trainer_info(self, trainer):
        messagebox.showinfo(trainer['name'], trainer.get('description', 'Keine weitere Information verfügbar.'))

    def activate_generic(self, trainer):
        self.log(f"{trainer['name']} aktiviert (noch ohne spezifische Aktion).")

    def toggle_favorite(self, trainer_name):
        if not self.has_feature('pattern_library'):
            messagebox.showinfo("Premium", "Premium erforderlich für Favoriten.")
            return
        favs = self.config.get('favorites', [])
        if trainer_name in favs:
            favs.remove(trainer_name)
            self.log(f"⭐ {trainer_name} aus Favoriten entfernt")
        else:
            favs.append(trainer_name)
            self.log(f"⭐ {trainer_name} zu Favoriten hinzugefügt")
        self.config['favorites'] = favs
        self.save_config()

    def show_premium_dialog(self):
        try:
            data = self.api_call('premium.php?action=upgrade_request', 'POST')
            msg = data.get('message', 'Anfrage gesendet')
        except Exception as e:
            msg = f"Premium beantragen. Fehler: {e}"
        messagebox.showinfo("Premium", msg)
        self.log(msg)

    def show_account(self):
        data = self.api_call('billing.php?action=status')
        msg = f"Status: {data.get('subscription', 'unknown')}\n\n{data.get('message', '')}"
        try:
            lb = self.api_call('premium.php?action=leaderboard')
            if lb.get('success'):
                email = getattr(self, 'email_var', None)
                email = email.get() if email else None
                me = next((x for x in lb['leaderboard'] if email and x['email'] == email), None)
                if me:
                    msg += f"\n\nReputation: {me['reputation']}\nApproved Patterns: {me['approved_patterns']}\nTotal Votes: {me['total_votes']}"
        except Exception:
            pass
        messagebox.showinfo("Account", msg)

    def logout(self):
        self.api_key = None
        self.save_config()
        self.build_login_view()

    def show_tutorial(self):
        win = tk.Toplevel(self.root)
        win.title("TrainerHub Tutorial")
        win.geometry("600x500")
        win.configure(bg='#050507')
        txt = scrolledtext.ScrolledText(win, bg='#111118', fg='#f8fafc', font=('Segoe UI', 10), wrap='word', padx=20, pady=20)
        txt.pack(fill='both', expand=True)
        tutorial = '''Willkommen bei TrainerHub!

So aktivierst du einen Trainer:

1. Starte dein Singleplayer-Spiel (z.B. Stardew Valley).
2. Klicke im TrainerHub auf "🔍 Prozess prüfen" (oder F5).
3. Wähle den Trainer aus (z.B. "Unendlich Geld").
4. Gib deinen aktuellen Wert ein (z.B. aktuelles Geld im Spiel).
5. Ändere den Wert im Spiel (kaufe/verkaufe etwas).
6. Gib den neuen Wert ein.
7. TrainerHub findet die Adresse und setzt sie auf deinen Zielwert.

Tastenkürzel:
• F5 = Prozess prüfen
• F1 / F6 = Tutorial öffnen

Wichtig:
• TrainerHub funktioniert NUR in Singleplayer-Spielen.
• Nutze Cheats nie in Online/Multiplayer-Modi.
• Einige Spiele aktualisieren ihre Offsets mit Updates.

Viel Spaß!
'''
        txt.insert('1.0', tutorial)
        txt.config(state='disabled')
        tk.Button(win, text="Schließen", bg='#2563eb', fg='#ffffff', font=('Segoe UI', 10, 'bold'), relief='flat', command=win.destroy).pack(pady=10)

def check_for_updates():
    try:
        r = requests.get('https://sayfespace.online/trainerhub/api/version.php', timeout=10)
        data = r.json()
        local = '0.1.0'
        if data.get('success') and data.get('version') != local:
            return data.get('download_url')
    except Exception:
        pass
    return None

def main():
    update_url = check_for_updates()
    if update_url:
        root = tk.Tk()
        root.withdraw()
        if messagebox.askyesno("Update verfügbar", "Eine neue Version ist verfügbar. Im Browser öffnen?"):
            import webbrowser
            webbrowser.open(update_url)
            root.destroy()
            return
        root.destroy()
    root = tk.Tk()
    TrainerHubGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()