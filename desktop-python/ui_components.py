"""Modern UI components and styles for SweetCheat desktop app."""
import tkinter as tk
from tkinter import ttk, font as tkfont

class ModernStyle:
    BG = '#0a0b10'
    BG_CARD = '#12141c'
    BG_ELEVATED = '#1a1d27'
    BORDER = '#2a2e3b'
    TEXT = '#f0f2f7'
    TEXT_MUTED = '#8b92a8'
    ACCENT = '#00d4ff'
    ACCENT_DARK = '#0099cc'
    ACCENT_2 = '#7b2cbf'
    SUCCESS = '#00e5a0'
    WARNING = '#ffb800'
    DANGER = '#ff3864'
    FONT = ('Segoe UI', 11)
    FONT_BOLD = ('Segoe UI', 11, 'bold')
    FONT_TITLE = ('Segoe UI', 24, 'bold')
    FONT_SMALL = ('Segoe UI', 9)

class ModernButton(tk.Canvas):
    """Flat modern button with hover effect."""
    def __init__(self, parent, text, command=None, variant='primary', size='normal', **kwargs):
        self.variant = variant
        self.size = size
        self.command = command
        self.hover = False
        w = kwargs.pop('width', 140 if size == 'normal' else 100)
        h = kwargs.pop('height', 38 if size == 'normal' else 32)
        super().__init__(parent, width=w, height=h, bg=kwargs.get('bg', ModernStyle.BG),
                         highlightthickness=0, cursor='hand2', **kwargs)
        self.text = text
        self.radius = 8
        self.bind('<Enter>', lambda e: self._set_hover(True))
        self.bind('<Leave>', lambda e: self._set_hover(False))
        self.bind('<Button-1>', lambda e: self._click())
        self.draw()
        
    def _set_hover(self, state):
        self.hover = state
        self.draw()
        
    def _click(self):
        if self.command:
            self.command()
            
    def draw(self):
        self.delete('all')
        color = {
            'primary': ModernStyle.ACCENT if not self.hover else '#33ddff',
            'secondary': ModernStyle.BG_ELEVATED if not self.hover else '#252a38',
            'danger': '#2a1b22' if not self.hover else '#3d252e',
        }.get(self.variant, ModernStyle.ACCENT)
        fg = ModernStyle.BG if self.variant == 'primary' else (ModernStyle.DANGER if self.variant == 'danger' else ModernStyle.TEXT)
        # Draw rounded rect
        self.create_rounded_rect(0, 0, self.winfo_reqwidth(), self.winfo_reqheight(), self.radius, fill=color, outline='')
        self.create_text(self.winfo_reqwidth()//2, self.winfo_reqheight()//2, text=self.text,
                         fill=fg, font=ModernStyle.FONT_BOLD)

    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [x1+radius, y1, x2-radius, y1, x2, y1, x2, y1+radius,
                  x2, y2-radius, x2, y2, x2-radius, y2, x1+radius, y2,
                  x1, y2, x1, y2-radius, x1, y1+radius, x1, y1]
        return self.create_polygon(points, smooth=True, **kwargs)

class ModernCard(tk.Frame):
    """Rounded card frame with border."""
    def __init__(self, parent, **kwargs):
        bg = kwargs.pop('bg', ModernStyle.BG_CARD)
        super().__init__(parent, bg=bg, **kwargs)
        self.config(highlightbackground=ModernStyle.BORDER, highlightthickness=1, bd=0)
        self.radius = kwargs.get('radius', 12)

class ModernLabel(tk.Label):
    def __init__(self, parent, text='', variant='body', **kwargs):
        styles = {
            'body': {'fg': ModernStyle.TEXT, 'font': ModernStyle.FONT},
            'muted': {'fg': ModernStyle.TEXT_MUTED, 'font': ModernStyle.FONT},
            'title': {'fg': ModernStyle.TEXT, 'font': ModernStyle.FONT_TITLE},
            'accent': {'fg': ModernStyle.ACCENT, 'font': ModernStyle.FONT_BOLD},
        }
        style = styles.get(variant, styles['body'])
        kwargs.update(style)
        kwargs.setdefault('bg', parent.cget('bg'))
        super().__init__(parent, text=text, **kwargs)

class ModernEntry(tk.Entry):
    def __init__(self, parent, **kwargs):
        kwargs.setdefault('bg', ModernStyle.BG_ELEVATED)
        kwargs.setdefault('fg', ModernStyle.TEXT)
        kwargs.setdefault('insertbackground', ModernStyle.ACCENT)
        kwargs.setdefault('relief', 'flat')
        kwargs.setdefault('font', ModernStyle.FONT)
        kwargs.setdefault('highlightthickness', 1)
        kwargs.setdefault('highlightcolor', ModernStyle.ACCENT)
        kwargs.setdefault('highlightbackground', ModernStyle.BORDER)
        super().__init__(parent, **kwargs)

class ScrollableFrame(tk.Frame):
    """Frame with canvas + scrollbar."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=kwargs.get('bg', ModernStyle.BG), **kwargs)
        self.canvas = tk.Canvas(self, bg=self['bg'], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.scrollable = tk.Frame(self.canvas, bg=self['bg'])
        self.scrollable.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.create_window((0,0), window=self.scrollable, anchor='nw', tags='frame')
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        self.scrollbar.pack(side='right', fill='y')
