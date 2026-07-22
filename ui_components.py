import tkinter as tk
from tkinter import ttk, font as tkfont

class ModernStyle:
    """Centralized dark theme for SweetCheat desktop app."""
    BG = "#050507"
    BG_CARD = "#111118"
    BG_ELEVATED = "#1a1a24"
    BG_INPUT = "#0a0a10"
    BORDER = "#232333"
    BORDER_ACTIVE = "#3b3b55"
    TEXT = "#f8fafc"
    TEXT_MUTED = "#94a3b8"
    ACCENT = "#2563eb"
    ACCENT_HOVER = "#3b82f6"
    SUCCESS = "#10b981"
    WARNING = "#f59e0b"
    DANGER = "#ef4444"
    GOLD = "#fbbf24"
    ACCENT = "#00f0ff"
    ACCENT_HOVER = "#4df4ff"
    GRADIENT_START = "#00f0ff"
    GRADIENT_END = "#ff3864"

    @classmethod
    def apply(cls, root):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background=cls.BG)
        style.configure('Card.TFrame', background=cls.BG_CARD)
        style.configure('TLabel', background=cls.BG, foreground=cls.TEXT, font=('Segoe UI', 10))
        style.configure('Muted.TLabel', background=cls.BG, foreground=cls.TEXT_MUTED, font=('Segoe UI', 9))
        style.configure('Heading.TLabel', background=cls.BG, foreground=cls.TEXT, font=('Rajdhani', 18, 'bold'))
        style.configure('Title.TLabel', background=cls.BG, foreground=cls.TEXT, font=('Rajdhani', 24, 'bold'))
        style.configure('Accent.TButton', background=cls.ACCENT, foreground=cls.BG, font=('Segoe UI', 10, 'bold'), padding=8)
        style.map('Accent.TButton', background=[('active', cls.ACCENT_HOVER)], foreground=[('active', cls.BG)])
        style.configure('Secondary.TButton', background=cls.BG_CARD, foreground=cls.TEXT, font=('Segoe UI', 10), padding=8)
        style.map('Secondary.TButton', background=[('active', cls.BORDER)])
        style.configure('Danger.TButton', background=cls.DANGER, foreground='#ffffff', font=('Segoe UI', 10, 'bold'), padding=8)
        style.map('Danger.TButton', background=[('active', '#f87171')])
        style.configure('Gold.TButton', background=cls.GOLD, foreground='#000000', font=('Segoe UI', 10, 'bold'), padding=8)
        style.configure('TEntry', fieldbackground=cls.BG_INPUT, foreground=cls.TEXT, insertcolor=cls.TEXT)
        style.configure('TCombobox', fieldbackground=cls.BG_INPUT, foreground=cls.TEXT)
        style.configure('Horizontal.TProgressbar', background=cls.ACCENT, troughcolor=cls.BG_CARD, borderwidth=0)
        style.configure('Vertical.TScrollbar', background=cls.BG_CARD, troughcolor=cls.BG, borderwidth=0)
        style.map('Vertical.TScrollbar', background=[('active', cls.BORDER_ACTIVE)])

        # Load Rajdhani font via Google Fonts if possible (windows will fetch it if URL accessible, tk does not support CSS)
        # Fallback to Segoe UI if not installed
        try:
            import tkinter.font as tkfont
            fonts = tkfont.families()
            if 'Rajdhani' not in fonts:
                # Try to register from local
                pass
        except Exception:
            pass


class RoundedFrame(tk.Canvas):
    """Rounded rectangle frame with optional gradient border."""
    def __init__(self, parent, radius=16, bg=None, border_color=None, border_width=1, **kwargs):
        self.bg = bg or ModernStyle.BG_CARD
        self.border_color = border_color or ModernStyle.BORDER
        self.border_width = border_width
        self.radius = radius
        super().__init__(parent, bg=ModernStyle.BG, highlightthickness=0, **kwargs)
        self.bind('<Configure>', self._draw)
        self.inner = tk.Frame(self, bg=self.bg)
        self.create_window(0, 0, window=self.inner, anchor='nw', tags='inner')
        self._draw()

    def _draw(self, event=None):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        self.delete('bg')
        self.create_rounded_rect(0, 0, w, h, self.radius, fill=self.bg, outline=self.border_color, width=self.border_width, tags='bg')
        self.lower('bg')
        self.itemconfig('inner', width=max(w - self.border_width*2 - 4, 1), height=max(h - self.border_width*2 - 4, 1))
        self.coords('inner', self.border_width + 2, self.border_width + 2)

    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1+radius, y1, x2-radius, y1, x2, y1,
            x2, y1+radius, x2, y2-radius, x2, y2,
            x2-radius, y2, x1+radius, y2, x1, y2,
            x1, y2-radius, x1, y1+radius, x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)


class AnimatedButton(tk.Canvas):
    """Button with hover animation and gradient text."""
    def __init__(self, parent, text, command=None, width=120, height=38, bg=ModernStyle.ACCENT, fg='#ffffff', hover_bg=ModernStyle.ACCENT_HOVER, font=('Segoe UI', 10, 'bold'), **kwargs):
        super().__init__(parent, width=width, height=height, bg=ModernStyle.BG, highlightthickness=0, cursor='hand2', **kwargs)
        self.text = text
        self.command = command
        self.bg = bg
        self.hover_bg = hover_bg
        self.fg = fg
        self.font = font
        self.radius = 10
        self.bind('<Enter>', self._hover_in)
        self.bind('<Leave>', self._hover_out)
        self.bind('<Button-1>', self._click)
        self.current_bg = bg
        self._draw()

    def _draw(self):
        self.delete('all')
        w = self.winfo_width()
        h = self.winfo_height()
        if not w or not h:
            w, h = 120, 38
        self.create_rounded_rect(2, 2, w-2, h-2, self.radius, fill=self.current_bg, outline='', tags='btn')
        self.create_text(w//2, h//2, text=self.text, fill=self.fg, font=self.font, tags='txt')

    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [x1+radius,y1,x2-radius,y1,x2,y1,x2,y1+radius,x2,y2-radius,x2,y2,x2-radius,y2,x1+radius,y2,x1,y2,x1,y2-radius,x1,y1+radius,x1,y1]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _hover_in(self, e):
        self.current_bg = self.hover_bg
        self._draw()

    def _hover_out(self, e):
        self.current_bg = self.bg
        self._draw()

    def _click(self, e):
        if self.command:
            self.command()


class StatusBadge(tk.Canvas):
    """Small colored badge with rounded corners."""
    def __init__(self, parent, text, color=ModernStyle.SUCCESS, **kwargs):
        super().__init__(parent, bg=ModernStyle.BG, highlightthickness=0, height=22, **kwargs)
        self.text = text
        self.color = color
        self.radius = 11
        self._draw()

    def _draw(self):
        self.delete('all')
        temp = tk.Label(self, text=self.text, font=('Segoe UI', 8, 'bold'))
        temp.update_idletasks()
        w = max(temp.winfo_reqwidth() + 20, 60)
        self.config(width=w)
        self.create_rounded_rect(1, 1, w-1, 21, 10, fill=self.color, outline='', tags='bg')
        self.create_text(w//2, 11, text=self.text, fill='#ffffff', font=('Segoe UI', 8, 'bold'), tags='txt')

    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [x1+radius,y1,x2-radius,y1,x2,y1,x2,y1+radius,x2,y2-radius,x2,y2,x2-radius,y2,x1+radius,y2,x1,y2,x1,y2-radius,x1,y1+radius,x1,y1]
        return self.create_polygon(points, smooth=True, **kwargs)


class ModernCombobox(tk.Frame):
    """Searchable combobox with icon and clear button."""
    def __init__(self, parent, values=None, command=None, **kwargs):
        super().__init__(parent, bg=ModernStyle.BG, **kwargs)
        self.values = values or []
        self.command = command
        self.var = tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.var, bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT, insertbackground=ModernStyle.TEXT,
                               relief='flat', font=('Segoe UI', 10))
        self.entry.pack(side='left', fill='both', expand=True, padx=(10,0), pady=6, ipady=4)
        self.entry.bind('<KeyRelease>', self._on_type)
        self.entry.bind('<FocusIn>', self._show_list)
        self.entry.bind('<FocusOut>', lambda e: self.after(200, self._hide_list))
        self.btn = tk.Label(self, text='▼', bg=ModernStyle.BG_INPUT, fg=ModernStyle.TEXT_MUTED, font=('Segoe UI', 8), width=3)
        self.btn.pack(side='right', fill='y', padx=(0,1), pady=1)
        self.btn.bind('<Button-1>', self._toggle_list)
        self.listbox = tk.Listbox(self, bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT, font=('Segoe UI', 10),
                                  selectbackground=ModernStyle.ACCENT, selectforeground='#ffffff', relief='flat',
                                  highlightthickness=1, highlightbackground=ModernStyle.BORDER)
        self.listbox.bind('<<ListboxSelect>>', self._on_select)
        self._filter('')
        self.configure(highlightbackground=ModernStyle.BORDER, highlightthickness=1)

    def _filter(self, text):
        text = text.lower()
        self.filtered = [v for v in self.values if text in v.lower()]
        self.listbox.delete(0, tk.END)
        for v in self.filtered[:20]:
            self.listbox.insert(tk.END, v)

    def _on_type(self, e):
        self._filter(self.var.get())
        self._show_list()

    def _show_list(self, e=None):
        if not self.filtered:
            return
        self.listbox.place(in_=self, x=0, y=self.winfo_height(), relwidth=1.0, height=min(len(self.filtered), 10)*24+4)
        self.listbox.lift()

    def _hide_list(self):
        try:
            self.listbox.place_forget()
        except Exception:
            pass

    def _toggle_list(self, e):
        if self.listbox.winfo_ismapped():
            self._hide_list()
        else:
            self._show_list()

    def _on_select(self, e):
        sel = self.listbox.curselection()
        if sel:
            self.var.set(self.filtered[sel[0]])
            self._hide_list()
            if self.command:
                self.command()

    def set_values(self, values):
        self.values = values
        self._filter(self.var.get() or '')

    def get(self):
        return self.var.get()

    def set(self, value):
        self.var.set(value)


class GradientLabel(tk.Label):
    """Label with gradient text effect using multiple offsets."""
    def __init__(self, parent, text, font=None, **kw):
        super().__init__(parent, text=text, font=font, **kw)

class ToggleSwitch(tk.Canvas):
    """Animated toggle switch for cheat cards."""
    WIDTH = 44
    HEIGHT = 24
    def __init__(self, parent, command=None, initial=False, **kw):
        bg = kw.pop('bg', ModernStyle.BG_CARD)
        super().__init__(parent, width=self.WIDTH, height=self.HEIGHT, bg=bg, highlightthickness=0, **kw)
        self.command = command
        self.state = initial
        self.r = self.HEIGHT // 2
        self.draw()
        self.bind('<Button-1>', self._toggle)
        self.bind('<Enter>', lambda e: self.config(cursor='hand2'))

    def draw(self):
        self.delete('all')
        color = ModernStyle.ACCENT if self.state else ModernStyle.BORDER
        # Rounded track
        self.create_oval(2, 2, self.HEIGHT-2, self.HEIGHT-2, fill=color, outline='')
        self.create_oval(self.WIDTH-self.HEIGHT+2, 2, self.WIDTH-2, self.HEIGHT-2, fill=color, outline='')
        self.create_rectangle(self.r, 2, self.WIDTH-self.r, self.HEIGHT-2, fill=color, outline='')
        # Knob
        x = self.WIDTH - self.r - 2 if self.state else self.r + 2
        self.create_oval(x-self.r+4, 4, x+self.r-4, self.HEIGHT-4, fill=ModernStyle.TEXT, outline='')

    def _toggle(self, event=None):
        self.state = not self.state
        self.draw()
        if self.command:
            self.command(self.state)

    def set(self, value):
        self.state = bool(value)
        self.draw()
