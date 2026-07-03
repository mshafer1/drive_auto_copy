
import contextlib
import sys
import tempfile
import time

import click
import qasync
import asyncio
import PyQt6.QtWidgets
import PyQt6.QtCore

from thumb_drive_auto_copy import _config
import thumb_drive_auto_copy._windows as windows

import filelock
import os

@contextlib.contextmanager
def _single_shot_lock():
    try:
        with filelock.FileLock(os.path.join(tempfile.gettempdir(), "thumb_drive_auto_copy.lock"), timeout=.5):
            yield
    except filelock.Timeout:
        print("Another instance of the application is already running. Exiting.")
        sys.exit(0)
        
    except Exception as e:
        print(f"An unexpected error occurred while acquiring the lock: {e}")
        sys.exit(0)

@contextlib.contextmanager
def _mutex_lock():
    try:
        with filelock.FileLock(os.path.join(tempfile.gettempdir(), "thumb_drive_auto_copy_running.lock"), timeout=30):
            time.sleep(1)  # Ensure the lock is held for a short duration to prevent
            yield
    except filelock.Timeout:
        print("Another instance of the application is already running. Exiting.")
        sys.exit(0)
        
    except Exception as e:
        print(f"An unexpected error occurred while acquiring the lock: {e}")
        sys.exit(0)


@click.command()
def main():
    """Main entry point for the thumb_drive_auto_copy application."""
    with _single_shot_lock():
        with _mutex_lock():
            click.echo("Thumb Drive Auto Copy Application is running...")

            config = _config.load_config()
            print("Loaded configuration:", config)

            app = PyQt6.QtWidgets.QApplication([])
            loop = qasync.QEventLoop(app)
            asyncio.set_event_loop(loop)

            window = windows.MainWindow(loop, config)
            PyQt6.QtCore.QTimer.singleShot(0, window.worker_thread.start)
            print("Window initialized. Starting event loop...")
            with loop:
                loop.run_forever()

if __name__ == "__main__":
    main()
