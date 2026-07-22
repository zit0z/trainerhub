"""Thread-safe Tkinter helpers."""
import tkinter as tk
import threading
import queue
import logging

logger = logging.getLogger('TrainerHub.ThreadUtils')


class TkExecutor:
    """Execute callbacks on the main Tkinter thread safely."""
    def __init__(self, root):
        self.root = root
        self._queue = queue.Queue()
        self._after_id = None
        self._running = True
        self._schedule_poll()

    def _schedule_poll(self):
        if self._running and self.root.winfo_exists():
            try:
                self._after_id = self.root.after(100, self._poll)
            except tk.TclError as e:
                logger.debug(f"Scheduler stopped: {e}")
                self._running = False

    def _poll(self):
        try:
            while True:
                fn, args, kwargs = self._queue.get_nowait()
                try:
                    if self.root.winfo_exists():
                        fn(*args, **kwargs)
                except Exception as e:
                    logger.exception(f"Error executing queued UI update: {e}")
        except queue.Empty:
            pass
        finally:
            self._schedule_poll()

    def run(self, fn, *args, **kwargs):
        if threading.current_thread() is threading.main_thread():
            try:
                fn(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Error in main-thread UI update: {e}")
        else:
            self._queue.put((fn, args, kwargs))

    def destroy(self):
        self._running = False
        if self._after_id:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass


def safe_after(root, ms, callback):
    """Schedule an after callback only if root still exists."""
    try:
        if root.winfo_exists():
            return root.after(ms, callback)
    except tk.TclError as e:
        logger.debug(f"safe_after ignored: {e}")
    return None


def safe_destroy(widget):
    """Destroy a widget if it still exists."""
    try:
        if widget.winfo_exists():
            widget.destroy()
    except tk.TclError as e:
        logger.debug(f"safe_destroy ignored: {e}")
