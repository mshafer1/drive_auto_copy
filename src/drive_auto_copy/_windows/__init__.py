from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

import PyQt6.QtCore
import PyQt6.QtWidgets

import drive_auto_copy._drive_utils
from drive_auto_copy._config import AppConfig

_SAFE_HIGHLIGHT_PATH = re.compile(r"^[A-Za-z]:\\[A-Za-z0-9 .\\\-]+$")


class MainWindow(PyQt6.QtWidgets.QMainWindow):
    """Main application window for drive_auto_copy."""

    status_message = PyQt6.QtCore.pyqtSignal(str)
    eject_prompt = PyQt6.QtCore.pyqtSignal(str, int, str)
    show_window = PyQt6.QtCore.pyqtSignal()
    quit_app = PyQt6.QtCore.pyqtSignal()

    def __init__(self, loop: asyncio.AbstractEventLoop, config: AppConfig):
        """Initialize the main window and set up the UI components."""
        super().__init__()
        self.loop = loop
        self.config = config
        self.worker_thread = threading.Thread(target=self._run_copy_workflow, daemon=True)

        self.setWindowTitle("Thumb Drive Auto Copy")
        self.setMinimumHeight(240)
        self.setMinimumWidth(640)

        self.status_box = PyQt6.QtWidgets.QPlainTextEdit()
        self.status_box.setReadOnly(True)
        self.setCentralWidget(self.status_box)

        self.status_message.connect(self._append_status)
        self.eject_prompt.connect(self._on_eject_prompt)
        self.show_window.connect(self._on_show_window)
        self.quit_app.connect(self._on_quit_app)

        self._prompt_event = threading.Event()
        self._prompt_answer = False
        self._show_event = threading.Event()
        self._window_shown = False

        # self.worker_thread.start()

    def _emit_status(self, message: str):
        self.status_message.emit(message)

    @PyQt6.QtCore.pyqtSlot(str)
    def _append_status(self, message: str):
        self.status_box.appendPlainText(message)

    @PyQt6.QtCore.pyqtSlot()
    def _on_show_window(self):
        if self._window_shown:
            self._show_event.set()
            return

        self.show()
        self.raise_()
        self.activateWindow()
        self._window_shown = True
        self._show_event.set()

    @PyQt6.QtCore.pyqtSlot()
    def _on_quit_app(self):
        print("Quitting application...")
        app = PyQt6.QtWidgets.QApplication.instance()
        if app is not None:
            app.quit()
        self.loop.stop()
        print("Application quit successfully.")

    def _ensure_window_visible(self):
        if self._window_shown:
            return

        self._show_event.clear()
        self.show_window.emit()
        self._show_event.wait()

    def _request_quit(self, why: str | None = None):
        print("Requesting application quit...")
        if why:
            print(f"Reason: {why}")
        self.quit_app.emit()

    @PyQt6.QtCore.pyqtSlot(str, int, str)
    def _on_eject_prompt(self, drive: str, transferred_count: int, action_word: str):
        response = PyQt6.QtWidgets.QMessageBox.question(
            self,
            "Eject Drive",
            f"{action_word.capitalize()} {transferred_count} file(s) from {drive}.\n"
            "Do you want to eject this drive now?",
            PyQt6.QtWidgets.QMessageBox.StandardButton.Yes
            | PyQt6.QtWidgets.QMessageBox.StandardButton.No,
            PyQt6.QtWidgets.QMessageBox.StandardButton.Yes,
        )
        self._prompt_answer = response == PyQt6.QtWidgets.QMessageBox.StandardButton.Yes
        self._prompt_event.set()

    def _ask_to_eject_drive(self, drive: str, transferred_count: int, action_word: str) -> bool:
        self._prompt_answer = False
        self._prompt_event.clear()
        self.eject_prompt.emit(drive, transferred_count, action_word)
        self._prompt_event.wait()
        return self._prompt_answer

    @staticmethod
    def _highlight_files(files: list[Path]):
        # Highlight the copied files in File Explorer
        print(f"Highlighting copied files in File Explorer...: {files}")
        for file in files:
            if not file.exists():
                print(f"File does not exist, skipping highlight: {file}")
                continue
            resolved_file = os.path.realpath(str(file.resolve()))
            if not _SAFE_HIGHLIGHT_PATH.fullmatch(resolved_file):
                raise ValueError(f"Unsafe characters in highlight path: {resolved_file}")
            print(f"Highlighting file: {resolved_file}")
            cmd_command = f"start explorer.exe /select,{resolved_file}"
            cmd = [
                "cmd.exe",
                "/c",
                cmd_command,
            ]
            print(cmd)
            if files:
                subprocess.run(
                    cmd,
                    check=False,
                )

    def _run_copy_workflow(self):
        config = self.config
        self._emit_status("Starting thumb drive scan...")

        drives = drive_auto_copy._drive_utils.get_removable_drives()
        if not drives:
            print("No removable drives found. Exiting.")
            self._request_quit("No removable drives found.")
            return

        matched_files_by_drive = {}
        for drive in drives:
            drive_root = Path(drive)
            try:
                matched_files = [p for p in drive_root.glob(config.source_pattern) if p.is_file()]
            except (OSError, ValueError):
                continue

            if matched_files:
                matched_files_by_drive[drive] = matched_files

        print(f"Matched files by drive: {matched_files_by_drive}")

        if not matched_files_by_drive:
            self._request_quit("No files matched on any removable drives.")
            return

        self._ensure_window_visible()
        self._emit_status("Starting thumb drive scan...")
        self._emit_status(f"Found removable drive(s): {', '.join(drives)}")

        moved_count = 0
        copied_count = 0
        skipped_count = 0
        copied_not_removed_count = 0
        destination_root = config.destination_path
        destination_root.mkdir(parents=True, exist_ok=True)

        self._emit_status(f"Destination root: {destination_root}")
        self._emit_status(f"Search pattern: {config.source_pattern}")
        self._emit_status(f"Transfer mode: {'move' if config.move_files else 'copy'}")

        for drive in drives:
            self._emit_status(f"Scanning drive: {drive}")
            matched_files = matched_files_by_drive.get(drive)
            if not matched_files:
                self._emit_status(
                    f"No files matched on {drive} for pattern {config.source_pattern}"
                )
                continue

            drive_destination = destination_root
            drive_destination.mkdir(parents=True, exist_ok=True)
            drive_transferred_count = 0
            moved_files = []

            for source_file in matched_files:
                destination_file = drive_destination / source_file.name
                try:
                    if destination_file.exists():
                        skipped_count += 1
                        print(f"Skipped existing file: {destination_file.name}")
                        continue

                    shutil.copy2(source_file, destination_file)
                    moved_files.append(destination_file)

                    if config.move_files:
                        try:
                            source_file.unlink()
                            moved_count += 1
                            drive_transferred_count += 1
                            self._emit_status(f"Moved: {source_file.name}")
                        except OSError as error:
                            copied_not_removed_count += 1
                            self._emit_status(
                                f"Copied but could not remove source {source_file.name}: {error}"
                            )
                    else:
                        copied_count += 1
                        drive_transferred_count += 1
                        self._emit_status(f"Copied: {source_file.name}")
                except OSError as error:
                    self._emit_status(f"Error copying {source_file.name}: {error}")

            if drive_transferred_count > 0:
                action_word = "moved" if config.move_files else "copied"
                should_eject = self._ask_to_eject_drive(drive, drive_transferred_count, action_word)
                self._highlight_files(moved_files)
                if should_eject:
                    if self._eject_drive(drive):
                        print(f"Ejected drive: {drive}")
                    else:
                        print(f"Failed to eject drive: {drive}")
                        self._emit_status(f"Failed to eject drive: {drive}")
                        self._emit_status(f"Please manually eject the drive: {drive}")
                        return
                else:
                    self._emit_status(f"Drive not ejected: {drive}")
                    return
            else:
                self._emit_status(f"No files transferred from drive: {drive}")
                time.sleep(2)  # Allow user to read the message before quitting
                self._request_quit(f"No files to transfer from drive: {drive}")

        if config.move_files:
            self._emit_status(
                "Done. "
                f"Moved {moved_count} file(s), copied-but-not-removed {copied_not_removed_count} file(s), "
                f"skipped {skipped_count} existing file(s)."
            )
        else:
            self._emit_status(
                "Done. " f"Copied {copied_count} file(s), skipped {skipped_count} existing file(s)."
            )

        self._request_quit("Operation completed.")

    @staticmethod
    def _eject_drive(drive: str) -> bool:
        print(f"Requesting drive ({drive}) eject...")
        drive_letter = drive.rstrip(":\\")
        command = (
            "$shell = New-Object -ComObject Shell.Application; "
            f"$item = $shell.Namespace(17).ParseName('{drive_letter}:\\'); "
            "if ($item) { $item.InvokeVerb('Eject'); Start-Sleep -Seconds 2 } else { exit 1 }"
        )
        result = subprocess.run(
            [
                "conhost.exe",
                "--headless",
                "powershell.exe",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False

        for _ in range(12):
            if not Path(f"{drive_letter}:\\").exists():
                return True
            time.sleep(0.25)
        return False
