import datetime
from pathlib import Path

import yaml

import drive_auto_copy._config as config_module


def test___missing_config_file___returns_defaults_and_writes_template(tmp_path, monkeypatch):
    config_path = tmp_path / "settings.yaml"
    monkeypatch.setenv("DAC_CONFIG_PATH", str(config_path))

    config = config_module.load_config()

    assert config[0].source_pattern == "AHQU/USBREC/*.WAV"
    assert config[0].destination_path == Path.home() / "Documents" / "DriveBackups"
    assert config[0].move_files is True
    assert config_path.exists()
    written = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert written[0]["source_pattern"] == "AHQU/USBREC/*.WAV"
    assert written[0]["destination_path"] == str(Path.home() / "Documents" / "DriveBackups")
    assert written[0]["move_files"] is True


def test___invalid_yaml___returns_defaults(tmp_path, monkeypatch):
    config_path = tmp_path / "settings.yaml"
    config_path.write_text("source_pattern: [", encoding="utf-8")
    monkeypatch.setenv("DAC_CONFIG_PATH", str(config_path))

    config = config_module.load_config()

    assert config[0].source_pattern == "AHQU/USBREC/*.WAV"
    assert config[0].destination_path == Path.home() / "Documents" / "DriveBackups"
    assert config[0].move_files is True


def test___non_mapping_yaml___returns_defaults(tmp_path, monkeypatch):
    config_path = tmp_path / "settings.yaml"
    config_path.write_text("- one\n- two\n", encoding="utf-8")
    monkeypatch.setenv("DAC_CONFIG_PATH", str(config_path))

    config = config_module.load_config()

    assert config[0].source_pattern == "AHQU/USBREC/*.WAV"
    assert config[0].destination_path == Path.home() / "Documents" / "DriveBackups"
    assert config[0].move_files is True


def test___config_values_present___normalizes_and_coerces_values(tmp_path, monkeypatch):
    class _FixedDateTime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 1, 2, 3, 4, 5, tzinfo=tz)

    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        "- source_pattern: '  **/*.WAV  '\n"
        "  destination_path: '~/Backup_{TIMESTAMP}'\n"
        "  move_files: 'false'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DAC_CONFIG_PATH", str(config_path))
    monkeypatch.setattr(config_module.datetime, "datetime", _FixedDateTime)

    config = config_module.load_config()

    assert config[0].source_pattern == "*/*.WAV"
    assert config[0].destination_path == Path("~/Backup_2026-01-02_03-04-05").expanduser().resolve()
    assert config[0].move_files is False


def test___invalid_move_files_value___falls_back_to_default_true(tmp_path, monkeypatch):
    config_path = tmp_path / "settings.yaml"
    config_path.write_text("- move_files: not-a-bool\n", encoding="utf-8")
    monkeypatch.setenv("DAC_CONFIG_PATH", str(config_path))

    config = config_module.load_config()

    assert config[0].move_files is True


def test___multiple_configurations___returns_each_rule(tmp_path, monkeypatch):
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        "- source_pattern: '*.WAV'\n"
        "  destination_path: '~/Wav'\n"
        "  move_files: true\n"
        "- source_pattern: '*.MP3'\n"
        "  destination_path: '~/Mp3'\n"
        "  move_files: false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DAC_CONFIG_PATH", str(config_path))

    config = config_module.load_config()

    assert len(config) == 2
    assert config[0].source_pattern == "*.WAV"
    assert config[0].move_files is True
    assert config[1].source_pattern == "*.MP3"
    assert config[1].move_files is False
