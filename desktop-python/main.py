# VERSION_ULTIMATE_SLA_SAYFE_SURE_0.9.14_CONFIRMED_BY_HERMES
import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import requests
import json
import logging
from gui_module import SweetCheatGUI
from tray_module import SweetCheatTray
from activation_engine import ActivationEngine

# Application Constants
VERSION = "0.9.14_FINAL"
APP_NAME = "SweetCheat Engine"

def main():
    # Initialize GUI
    gui = SweetCheatGUI()
    # Initialize Tray
    tray = SweetCheatTray(gui)
    
    # Start Tray
    tray.start()
    
    # Start GUI
    gui.run()

if __name__ == "__main__":
    main()
