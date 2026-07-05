import dataclasses
import datetime
import logging
import pathlib

import decouple
import yaml

_logger = logging.getLogger(__name__)

_config = decouple.AutoConfig(search_path=pathlib.Path.cwd())


@dataclasses.dataclass(frozen=True)
class AppConfig:
    """Data class to hold application configuration."""

    source_pattern: str
    destination_path: pathlib.Path
    move_files: bool


def _get_config_path() -> pathlib.Path:
    config_path = _config(
        "TDAC_DESTINATION",
        default="~/.config/drive_auto_copy/settings.yaml",
        cast=pathlib.Path,
    )
    return pathlib.Path(config_path).expanduser()


def load_config() -> AppConfig:
    """Load the application configuration from a YAML file."""
    default = AppConfig(
        source_pattern="AHQU/USBREC/*.WAV",
        destination_path=pathlib.Path.home() / "Documents" / "ThumbDriveBackups",
        move_files=True,
    )

    _config_path = _get_config_path()
    if not _config_path.exists():
        _logger.debug(f"Config not found at {_config_path}; using defaults.")
        _config_path.parent.mkdir(parents=True, exist_ok=True)
        with _config_path.open("w", encoding="utf-8") as fout:
            yaml.safe_dump(
                {
                    **dataclasses.asdict(default),
                    "destination_path": str(default.destination_path),
                },
                fout,
            )
        return default

    try:
        with _config_path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
    except OSError as error:
        _logger.debug(f"Failed to read config at {_config_path}: {error}; using defaults.")
        return default
    except yaml.YAMLError as error:
        _logger.debug(f"Invalid YAML in {_config_path}: {error}; using defaults.")
        return default

    if not isinstance(loaded, dict):
        _logger.debug(f"Config in {_config_path} must be a mapping; using defaults.")
        return default

    source_pattern = loaded.get("source_pattern", default.source_pattern).replace(
        "**", "*"
    )  # recursive glob intentionally not supported
    destination_value = loaded.get("destination_path", str(default.destination_path))
    move_files_value = loaded.get("move_files", default.move_files)

    source_pattern = str(source_pattern).strip() or default.source_pattern
    destination_path = (
        pathlib.Path(
            str(destination_value).replace(
                "{TIMESTAMP}", datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            )
        )
        .expanduser()
        .resolve()
    )

    if isinstance(move_files_value, bool):
        move_files = move_files_value
    else:
        move_files = decouple.strtobool(str(move_files_value))

    _logger.debug(f"Loaded config from {_config_path}")
    return AppConfig(
        source_pattern=source_pattern,
        destination_path=destination_path,
        move_files=move_files,
    )
