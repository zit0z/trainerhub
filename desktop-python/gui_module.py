# VERSION_ULTIMATE_SLA_SAYFE_SURE_0.9.14_CONFIRMED_BY_HERMES
import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import threading
import os
from activation_engine import ActivationEngine

class SweetCheatGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SweetCheat Engine v0.9.14")
        self.root.geometry("900x600")
        self.root.configure(bg="#0B0B0B")
        
        self.engine = ActivationEngine()
        self.setup_ui()

    def setup_ui(self):
        # Placeholder for the actual complex UI logic
        # This is a simplified version to ensure the build works first
        self.label = tk.Label(self.root, text="Slayer Edition v0.9.14", fg="#00FFFF", bg="#0B0B0B", font=("Rajdhani", 20))
        self.label.pack(pady=20)

    def run(self):
        self.root.mainloop()
