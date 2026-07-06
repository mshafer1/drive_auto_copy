from pathlib import Path
from unittest.mock import Mock

import drive_auto_copy._windows as windows_module


def _build_window(qapp, event_loop, config):
    window = windows_module.MainWindow(event_loop, config)
    statuses: list[str] = []
    quit_reasons: list[str | None] = []
    window._emit_status = statuses.append
    window._ensure_window_visible = lambda: None
    window._highlight_files = lambda files: None
    window._request_quit = lambda why=None: quit_reasons.append(why)
    window._ask_to_eject_drive = Mock(return_value=False)

    return window, statuses, quit_reasons


def test___copy_mode_enabled___copies_files_without_removing_source(
    tmp_path, qapp, event_loop, app_config_factory, fake__get_removable_drives
):
    drive_root = tmp_path / "drive"
    drive_root.mkdir()
    source_file = drive_root / "take1.WAV"
    source_file.write_text("audio", encoding="utf-8")
    config = app_config_factory(
        move_files=False,
        source_pattern="*.WAV",
        destination_path=tmp_path / "dest",
    )
    window, statuses, _ = _build_window(qapp, event_loop, config)
    fake__get_removable_drives.set_result([str(drive_root)])

    window._run_copy_workflow()

    assert source_file.exists()
    assert (config.destination_path / "take1.WAV").exists()
    assert any("Copied: take1.WAV" in message for message in statuses)
    assert any(
        "Done. Copied 1 file(s), skipped 0 existing file(s)." in message for message in statuses
    )


def test___move_mode_enabled___copies_and_removes_source(
    tmp_path, monkeypatch, qapp, event_loop, app_config_factory, fake__get_removable_drives
):
    drive_root = tmp_path / "drive"
    drive_root.mkdir()
    source_file = drive_root / "take2.WAV"
    source_file.write_text("audio", encoding="utf-8")
    config = app_config_factory(
        move_files=True,
        source_pattern="*.WAV",
        destination_path=tmp_path / "dest",
    )
    window, statuses, _ = _build_window(qapp, event_loop, config)
    fake__get_removable_drives.set_result([str(drive_root)])

    window._run_copy_workflow()

    assert not source_file.exists()
    assert (config.destination_path / "take2.WAV").exists()
    assert any("Moved: take2.WAV" in message for message in statuses)
    assert any(
        "Done. Moved 1 file(s), copied-but-not-removed 0 file(s), skipped 0 existing file(s)."
        in message
        for message in statuses
    )


def test___move_mode_unlink_fails___counts_as_copied_but_not_removed(
    tmp_path, monkeypatch, qapp, event_loop, app_config_factory, fake__get_removable_drives
):
    drive_root = tmp_path / "drive"
    drive_root.mkdir()
    source_file = drive_root / "take3.WAV"
    source_file.write_text("audio", encoding="utf-8")
    config = app_config_factory(
        move_files=True,
        source_pattern="*.WAV",
        destination_path=tmp_path / "dest",
    )
    window, statuses, _ = _build_window(qapp, event_loop, config)
    fake__get_removable_drives.set_result([str(drive_root)])

    original_unlink = Path.unlink

    def _fail_unlink(path_obj: Path, *args, **kwargs):
        if path_obj == source_file:
            raise OSError("permission denied")
        return original_unlink(path_obj, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", _fail_unlink)

    window._run_copy_workflow()

    assert source_file.exists()
    assert (config.destination_path / "take3.WAV").exists()
    assert any("Copied but could not remove source take3.WAV" in message for message in statuses)
    assert any(
        "Done. Moved 0 file(s), copied-but-not-removed 1 file(s), skipped 0 existing file(s)."
        in message
        for message in statuses
    )


def test___copy_operation_fails___does_not_remove_source(
    tmp_path, monkeypatch, qapp, event_loop, app_config_factory, fake__get_removable_drives
):
    drive_root = tmp_path / "drive"
    drive_root.mkdir()
    source_file = drive_root / "take4.WAV"
    source_file.write_text("audio", encoding="utf-8")
    config = app_config_factory(
        move_files=True,
        source_pattern="*.WAV",
        destination_path=tmp_path / "dest",
    )
    window, statuses, _ = _build_window(qapp, event_loop, config)
    fake__get_removable_drives.set_result([str(drive_root)])
    monkeypatch.setattr(
        windows_module.shutil,
        "copy2",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("copy failed")),
    )

    window._run_copy_workflow()

    assert source_file.exists()
    assert not (config.destination_path / "take4.WAV").exists()
    assert any("Error copying take4.WAV: copy failed" in message for message in statuses)
    assert any(
        "Done. Moved 0 file(s), copied-but-not-removed 0 file(s), skipped 0 existing file(s)."
        in message
        for message in statuses
    )


def test___mixed_outcomes___reports_expected_counts(
    tmp_path, monkeypatch, qapp, event_loop, app_config_factory, fake__get_removable_drives
):
    drive_root = tmp_path / "drive"
    drive_root.mkdir()
    (drive_root / "ok.WAV").write_text("ok", encoding="utf-8")
    (drive_root / "existing.WAV").write_text("exists", encoding="utf-8")
    (drive_root / "broken.WAV").write_text("broken", encoding="utf-8")

    config = app_config_factory(
        move_files=False,
        source_pattern="*.WAV",
        destination_path=tmp_path / "dest",
    )
    config.destination_path.mkdir(parents=True, exist_ok=True)
    (config.destination_path / "existing.WAV").write_text("dest", encoding="utf-8")

    window, statuses, _ = _build_window(qapp, event_loop, config)
    fake__get_removable_drives.set_result([str(drive_root)])

    original_copy2 = windows_module.shutil.copy2

    def _copy_with_failure(source: Path, destination: Path):
        if source.name == "broken.WAV":
            raise OSError("disk full")
        return original_copy2(source, destination)

    monkeypatch.setattr(windows_module.shutil, "copy2", _copy_with_failure)

    window._run_copy_workflow()

    assert (config.destination_path / "ok.WAV").exists()
    assert (drive_root / "ok.WAV").exists()
    assert any("Error copying broken.WAV: disk full" in message for message in statuses)
    assert any(
        "Done. Copied 1 file(s), skipped 1 existing file(s)." in message for message in statuses
    )
