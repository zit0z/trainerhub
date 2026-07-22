"""Shared logging helpers for TrainerHub desktop."""
import logging
import sys
import os
from datetime import datetime


def get_logger(name='TrainerHub'):
    return logging.getLogger(name)


def setup_file_logging(path=None):
    if path is None:
        base = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'TrainerHub')
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, 'trainerhub.log')
    handler = logging.FileHandler(path, encoding='utf-8', mode='a')
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
    root = logging.getLogger()
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == path for h in root.handlers):
        root.addHandler(handler)
    return path


def log_system_info(logger):
    logger.info(f"TrainerHub system info: Python {sys.version}")
    logger.info(f"Executable: {sys.executable}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"CWD: {os.getcwd()}")
