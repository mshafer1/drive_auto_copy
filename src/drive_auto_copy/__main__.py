"""drive_auto_copy: Main entry point for the application."""

import asyncio
import contextlib
import os
import sys
import tempfile
import logging
import logging.handlers
if sys.platform != "win32":
    raise SystemExit("drive-auto-copy is currently supported only on Windows.")

import click
import filelock
import PyQt6.QtCore
import PyQt6.QtWidgets
import qasync

import drive_auto_copy._windows as windows
from drive_auto_copy import _config

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())

@contextlib.contextmanager
def _mutex_lock():
    try:
        with filelock.FileLock(
            os.path.join(tempfile.gettempdir(), "drive_auto_copy.lock"), timeout=0.5
        ):
            yield
    except filelock.Timeout:
        print("Another instance of the application is already running. Exiting.")
        sys.exit(0)

    except Exception as e:
        print(f"An unexpected error occurred while acquiring the lock: {e}")
        sys.exit(1)

def _setup_logging() -> None:
    """Set up logging for the application."""
    log_file = os.path.join(tempfile.gettempdir(), "drive_auto_copy.log")
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] - %(name)s - %(message)s")

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if any(
        h.name in {"drive_auto_copy_file", "drive_auto_copy_console"}
        for h in root_logger.handlers
    ):
        return

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        encoding="utf-8",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    file_handler.name = "drive_auto_copy_file"
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.name = "drive_auto_copy_console"
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
@click.command()
def main():
    """Main entry point for the drive_auto_copy application."""
    with _mutex_lock():
        _setup_logging()
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
