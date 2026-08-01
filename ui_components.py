"""Modern, reusable UI components for SweetCheat."""
import tkinter as tk

try:
    from PIL import Image, ImageTk, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

class ModernStyle:
    BG = '#07080d'
    BG_CARD = '#10121a'
    BG_ELEVATED = '#161925'
    BG_INPUT = '#0c0e15'
    ACCENT = '#00f0ff'
    ACCENT_DIM = 'rgba(0,240,255,0.08)'
    ACCENT_SEC = '#ff3864'
    TEXT = '#ffffff'
    TEXT_MUTED = '#8a91a8'
    TEXT_DIM = '#5b6377'
    BORDER = '#1d2130'
    BORDER_ACTIVE = '#2a2f42'
    SUCCESS = '#00e676'
    DANGER = '#ff3864'
    WARN = '#ffab00'
    FONT_HEAD = ('Rajdhani', 26, 'bold')
    FONT_TITLE = ('Rajdhani', 18, 'bold')
    FONT_SUB = ('Rajdhani', 13, 'bold')
    FONT_BODY = ('Segoe UI', 10)
    FONT_BODY_B = ('Segoe UI', 10, 'bold')
    FONT_SMALL = ('Segoe UI', 9)

    @staticmethod
    def apply(root):
        root.configure(bg=ModernStyle.BG)


# ---- Reusable styled widgets ----

def card(parent, width=None, height=None, padx=24, pady=20):
    f = tk.Frame(parent, bg=ModernStyle.BG_CARD, highlightbackground=ModernStyle.BORDER,
                 highlightthickness=1, bd=0, padx=padx, pady=pady)
    if width:
        f.config(width=width)
    if height:
        f.config(height=height)
    return f


def section_title(parent, text, icon=''):
    txt = f"{icon}  {text}".strip()
    return tk.Label(parent, text=txt, bg=parent.cget('bg'), fg=ModernStyle.TEXT,
                    font=ModernStyle.FONT_SUB, anchor='w')


def primary_btn(parent, text, command, icon=''):
    txt = f"{icon}  {text}".strip() if icon else text
    btn = tk.Button(parent, text=txt, command=command, font=ModernStyle.FONT_BODY_B,
                    bg=ModernStyle.ACCENT, fg=ModernStyle.BG, relief='flat',
                    activebackground='#33f3ff', activeforeground=ModernStyle.BG,
                    padx=20, pady=10, cursor='hand2')
    return btn


def secondary_btn(parent, text, command, icon=''):
    txt = f"{icon}  {text}".strip() if icon else text
    btn = tk.Button(parent, text=txt, command=command, font=ModernStyle.FONT_BODY,
                    bg=ModernStyle.BG_ELEVATED, fg=ModernStyle.TEXT, relief='flat',
                    activebackground=ModernStyle.BORDER_ACTIVE, activeforeground=ModernStyle.ACCENT,
                    padx=16, pady=9, cursor='hand2',
                    highlightbackground=ModernStyle.BORDER, highlightthickness=1)
    return btn


def ghost_btn(parent, text, command, icon=''):
    txt = f"{icon}  {text}".strip() if icon else text
    btn = tk.Button(parent, text=txt, command=command, font=ModernStyle.FONT_BODY,
                    bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED, relief='flat',
                    padx=12, pady=7, activebackground=ModernStyle.BORDER_ACTIVE,
                    activeforeground=ModernStyle.TEXT, cursor='hand2')
    return btn


def input_field(parent, label=None, show=None, width=32):
    if label:
        tk.Label(parent, text=label, bg=parent.cget('bg'), fg=ModernStyle.TEXT_MUTED,
                 font=ModernStyle.FONT_BODY).pack(anchor='w', pady=(0, 5))
    entry = tk.Entry(parent, width=width, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT,
                     insertbackground=ModernStyle.ACCENT, relief='flat',
                     highlightbackground=ModernStyle.BORDER, highlightthickness=1,
                     font=ModernStyle.FONT_BODY)
    entry.pack(fill='x', ipady=7)
    if show:
        entry.config(show=show)
    return entry


def badge(parent, text, color=ModernStyle.ACCENT):
    return tk.Label(parent, text=text, bg='#08141a' if color == ModernStyle.ACCENT else '#1a0c12',
                    fg=color, font=ModernStyle.FONT_SMALL, padx=10, pady=3,
                    highlightbackground=color, highlightthickness=1)


def stat_card(parent, label, value, icon=''):
    f = card(parent, padx=18, pady=16)
    tk.Label(f, text=f"{icon}  {label}".strip(), bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_MUTED,
             font=ModernStyle.FONT_SMALL).pack(anchor='w')
    tk.Label(f, text=str(value), bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT,
             font=('Rajdhani', 22, 'bold')).pack(anchor='w', pady=(6, 0))
    return f
