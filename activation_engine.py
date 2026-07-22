"""Desktop trainer activation engine."""
import os
import sys
import json
import time
import logging
import threading

logger = logging.getLogger('TrainerHub.Activation')
WINDOWS = sys.platform == 'win32'

class ActivationEngine:
    def __init__(self, api_client=None):
        self.api = api_client
        self.active_trainers = {}
        self._lock = threading.Lock()

    def can_activate(self, trainer):
        """Check if trainer can be activated on this system."""
        if trainer.get('locked'):
            return False, 'Premium-Trainer erfordert Abonnement'
        return True, 'OK'

    def activate(self, trainer, game_info=None, callback=None):
        """Run trainer activation in background thread."""
        def _run():
            try:
                tid = trainer.get('trainer_id')
                name = trainer.get('name', 'Unbekannt')
                logger.info(f"Activating trainer {tid}: {name}")

                # Log attempt
                if self.api:
                    try:
                        self.api.activate_log(tid, success=1, action='desktop_activate')
                    except Exception as e:
                        logger.error(f"Activation log failed: {e}")

                # Mark active
                with self._lock:
                    self.active_trainers[tid] = {'name': name, 'activated_at': time.time(), 'game': game_info}

                if callback:
                    callback(True, f"'{name}' aktiviert")
            except Exception as e:
                logger.exception(f"Activation error: {e}")
                if callback:
                    callback(False, str(e))

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t

    def deactivate(self, trainer_id):
        with self._lock:
            if trainer_id in self.active_trainers:
                del self.active_trainers[trainer_id]
                return True
        return False

    def is_active(self, trainer_id):
        with self._lock:
            return trainer_id in self.active_trainers

    def list_active(self):
        with self._lock:
            return list(self.active_trainers.values())
