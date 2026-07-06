"""Shared config for tests."""

import asyncio
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication

import drive_auto_copy._drive_utils as drive_utils
from drive_auto_copy._config import AppConfig


@pytest.fixture
def qapp(monkeypatch):
    """Create a QApplication instance for testing."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    return app


@pytest.fixture
def event_loop():
    """Create a new event loop for each test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def app_config_factory(tmp_path):
    """Factory fixture to create AppConfig instances with custom parameters."""

    def _factory(
        *,
        move_files: bool = True,
        source_pattern: str = "*.WAV",
        destination_path: Path | None = None,
    ) -> AppConfig:
        destination = Path(destination_path or (tmp_path / "destination"))
        return AppConfig(
            source_pattern=source_pattern,
            destination_path=destination,
            move_files=move_files,
        )

    return _factory


@pytest.fixture
def app_config(tmp_path, app_config_factory):
    """Fixture to create a default AppConfig instance."""
    return app_config_factory(destination_path=tmp_path / "destination")


@pytest.fixture
def copy_mode_app_config(tmp_path, app_config_factory):
    """Fixture to create an AppConfig instance with copy mode enabled."""
    return app_config_factory(
        move_files=False,
        source_pattern="*.WAV",
        destination_path=tmp_path / "dest",
    )


@pytest.fixture
def fake__get_removable_drives(mocker):
    """Patch removable drive discovery with configurable side effect."""

    class _FakeGetRemovableDrives:
        def __init__(self):
            self._side_effect = []

        def set_result(self, side_effect):
            self._side_effect = side_effect

        def __call__(self):
            if callable(self._side_effect):
                return self._side_effect()
            if isinstance(self._side_effect, Exception):
                raise self._side_effect
            return self._side_effect

    fake = _FakeGetRemovableDrives()
    mocker.patch.object(drive_utils, drive_utils.get_removable_drives.__name__, side_effect=fake)
    return fake
