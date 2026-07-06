"""drive_auto_copy: Main entry point for the application."""

import asyncio
import contextlib
import os
import sys
import tempfile

if sys.platform != "win32":
    raise SystemExit("drive-auto-copy is currently supported only on Windows.")

import click
import filelock
import PyQt6.QtCore
import PyQt6.QtWidgets
import qasync

import drive_auto_copy._windows as windows
from drive_auto_copy import _config


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


@click.command()
def main():
    """Main entry point for the drive_auto_copy application."""
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
