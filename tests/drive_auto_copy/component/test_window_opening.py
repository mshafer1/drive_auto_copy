from unittest.mock import Mock

import PyQt6.QtWidgets
import pytest

import drive_auto_copy._windows as windows_module


@pytest.fixture
def stub_workflow_side_effects():
    def _apply(window, *, ensure_window_visible=None, ask_to_eject_drive=None):
        ensure_mock = ensure_window_visible or Mock()
        ask_mock = ask_to_eject_drive or Mock(return_value=False)
        window._ensure_window_visible = ensure_mock
        window._emit_status = lambda _message: None
        window._ask_to_eject_drive = ask_mock
        window._highlight_files = lambda _files: None
        window._request_quit = lambda _why=None: None
        return ensure_mock, ask_mock

    return _apply


def test___first_show_signal___shows_and_activates_window(qapp, event_loop, app_config):
    window = windows_module.MainWindow(event_loop, app_config)
    show = Mock()
    raise_window = Mock()
    activate = Mock()
    window.show = show
    window.raise_ = raise_window
    window.activateWindow = activate

    window._on_show_window()

    assert show.call_count == 1
    assert raise_window.call_count == 1
    assert activate.call_count == 1
    assert window._window_shown is True
    assert window._show_event.is_set()


def test___subsequent_show_signal___does_not_show_window_again(qapp, event_loop, app_config):
    window = windows_module.MainWindow(event_loop, app_config)
    show = Mock()
    raise_window = Mock()
    activate = Mock()
    window.show = show
    window.raise_ = raise_window
    window.activateWindow = activate

    window._on_show_window()
    window._show_event.clear()
    window._on_show_window()

    assert show.call_count == 1
    assert raise_window.call_count == 1
    assert activate.call_count == 1
    assert window._show_event.is_set()


def test___ensure_window_visible_called___emits_show_signal_and_waits(qapp, event_loop, app_config):
    window = windows_module.MainWindow(event_loop, app_config)
    wait = Mock(return_value=True)
    window._show_event.wait = wait
    window.show_window.connect(lambda: window._show_event.set())

    window._ensure_window_visible()

    assert wait.call_count == 1
    assert wait.call_args.kwargs == {"timeout": 5}


def test___eject_prompt_yes_response___stores_true_answer(
    monkeypatch, qapp, event_loop, app_config
):
    window = windows_module.MainWindow(event_loop, app_config)
    monkeypatch.setattr(
        PyQt6.QtWidgets.QMessageBox,
        "question",
        lambda *_args, **_kwargs: PyQt6.QtWidgets.QMessageBox.StandardButton.Yes,
    )

    window._on_eject_prompt("E:\\", 2, "transferred")

    assert window._prompt_answer is True
    assert window._prompt_event.is_set()


def test___eject_prompt_no_response___stores_false_answer(
    monkeypatch, qapp, event_loop, app_config
):
    window = windows_module.MainWindow(event_loop, app_config)
    monkeypatch.setattr(
        PyQt6.QtWidgets.QMessageBox,
        "question",
        lambda *_args, **_kwargs: PyQt6.QtWidgets.QMessageBox.StandardButton.No,
    )

    window._on_eject_prompt("E:\\", 2, "transferred")

    assert window._prompt_answer is False
    assert window._prompt_event.is_set()


def test___shutdown_already_requested___ask_to_eject_drive_returns_false(
    monkeypatch, qapp, event_loop, app_config
):
    window = windows_module.MainWindow(event_loop, app_config)
    window._shutdown_requested.set()
    question = Mock(return_value=PyQt6.QtWidgets.QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(PyQt6.QtWidgets.QMessageBox, "question", question)

    result = window._ask_to_eject_drive("E:\\", 1, "transferred")

    assert result is False
    assert question.call_count == 0


def test___shutdown_requested_while_waiting___ask_to_eject_drive_unblocks(
    monkeypatch, qapp, event_loop, app_config
):
    window = windows_module.MainWindow(event_loop, app_config)
    monkeypatch.setattr(
        PyQt6.QtWidgets.QMessageBox,
        "question",
        lambda *_args, **_kwargs: PyQt6.QtWidgets.QMessageBox.StandardButton.No,
    )

    def _wait(timeout=None):
        window._shutdown_requested.set()
        return False

    window._prompt_event.wait = _wait

    result = window._ask_to_eject_drive("E:\\", 1, "transferred")

    assert result is False


def test___quit_app_called___sets_shutdown_and_unblocks_prompt(qapp, event_loop, app_config):
    window = windows_module.MainWindow(event_loop, app_config)
    window._shutdown_requested.clear()
    window._prompt_event.clear()

    window._on_quit_app()

    assert window._shutdown_requested.is_set()
    assert window._prompt_event.is_set()


def test___no_files_transferred___does_not_prompt_for_eject(
    tmp_path,
    qapp,
    event_loop,
    copy_mode_app_config,
    stub_workflow_side_effects,
    fake__get_removable_drives,
):
    drive_root = tmp_path / "drive"
    drive_root.mkdir()
    config = copy_mode_app_config
    window = windows_module.MainWindow(event_loop, config)
    _, prompt = stub_workflow_side_effects(window)
    fake__get_removable_drives.set_result([str(drive_root)])

    window._run_copy_workflow()

    assert prompt.call_count == 0


def test___files_transferred___prompts_for_eject_once(
    tmp_path,
    qapp,
    event_loop,
    copy_mode_app_config,
    stub_workflow_side_effects,
    fake__get_removable_drives,
):
    drive_root = tmp_path / "drive"
    drive_root.mkdir()
    source_file = drive_root / "take.WAV"
    source_file.write_text("audio", encoding="utf-8")
    config = copy_mode_app_config
    window = windows_module.MainWindow(event_loop, config)
    _, prompt = stub_workflow_side_effects(window)
    fake__get_removable_drives.set_result([str(drive_root)])

    window._run_copy_workflow()

    assert (config.destination_path / source_file.name).exists()
    assert prompt.call_count == 1


def test___no_removable_drives___window_show_not_called(
    qapp,
    event_loop,
    copy_mode_app_config,
    stub_workflow_side_effects,
    fake__get_removable_drives,
):
    config = copy_mode_app_config
    window = windows_module.MainWindow(event_loop, config)
    ensure_window_visible, _ = stub_workflow_side_effects(window)
    fake__get_removable_drives.set_result([])

    window._run_copy_workflow()

    assert ensure_window_visible.call_count == 0


def test___removable_drives_but_no_matching_files___window_show_not_called(
    tmp_path,
    qapp,
    event_loop,
    copy_mode_app_config,
    stub_workflow_side_effects,
    fake__get_removable_drives,
):
    drive_root = tmp_path / "drive"
    drive_root.mkdir()
    config = copy_mode_app_config
    window = windows_module.MainWindow(event_loop, config)
    ensure_window_visible, _ = stub_workflow_side_effects(window)
    fake__get_removable_drives.set_result([str(drive_root)])

    window._run_copy_workflow()

    assert ensure_window_visible.call_count == 0


def test___removable_drives_and_matching_files___window_show_called(
    tmp_path,
    qapp,
    event_loop,
    copy_mode_app_config,
    stub_workflow_side_effects,
    fake__get_removable_drives,
):
    drive_root = tmp_path / "drive"
    drive_root.mkdir()
    (drive_root / "take.WAV").write_text("audio", encoding="utf-8")
    config = copy_mode_app_config
    window = windows_module.MainWindow(event_loop, config)
    ensure_window_visible, _ = stub_workflow_side_effects(window)
    fake__get_removable_drives.set_result([str(drive_root)])

    window._run_copy_workflow()

    assert ensure_window_visible.call_count == 1
