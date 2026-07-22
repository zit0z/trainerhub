"""Shared logging helpers for SweetCheat desktop."""
import logging
import sys
import os
from datetime import datetime


def _default_log_path():
    base = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'SweetCheat')
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, 'sweetcheat.log')

LOG_FILE = _default_log_path()


def setup_root_logging(level=logging.INFO, path=None):
    global LOG_FILE
    if path is None:
        path = _default_log_path()
    LOG_FILE = path
    root = logging.getLogger()
    root.setLevel(level)
    if not any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', '') == path for h in root.handlers):
        fh = logging.FileHandler(path, encoding='utf-8', mode='a')
        fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
        root.addHandler(fh)
    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in root.handlers):
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        root.addHandler(sh)


def get_logger(name='SweetCheat'):
    return logging.getLogger(name)


def setup_file_logging(path=None):
    if path is None:
        path = _default_log_path()
    return setup_root_logging(path=path)


def log_system_info(logger):
    logger.info(f"SweetCheat system info: Python {sys.version}")
    logger.info(f"Executable: {sys.executable}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"CWD: {os.getcwd()}")
