"""Program to automate Windows setup."""

import os
import subprocess


# check if running elevated
def _fail_if_not_elevated():
    try:
        is_admin = (
            subprocess.check_output("net session", shell=True, stderr=subprocess.DEVNULL) == b""
        )
    except subprocess.CalledProcessError:
        is_admin = False

    if not is_admin:
        raise PermissionError(
            "This script must be run with elevated privileges (as Administrator)."
        )


# enable Windows DriverFramework operational event logging
def enable_driver_framework_logging():
    """Enable Windows DriverFramework operational event logging."""
    _fail_if_not_elevated()
    try:
        subprocess.run(
            [
                "wevtutil",
                "sl",
                "Microsoft-Windows-DriverFrameworks-UserMode/Operational",
                "/e:true",
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to enable DriverFramework logging: {e}") from e


def template_and_configure_task(install_path: str):
    """Create and configure a scheduled task for the application."""
    _fail_if_not_elevated()
    try:
        # Create a new scheduled task using schtasks
        subprocess.run(
            [
                "schtasks",
                "/Create",
                "/TN",
                "ThumbDriveAutoCopyTask",
                "/TR",
                f'"{subprocess.list2cmdline([os.path.realpath(install_path)])}"',
                "/SC",
                "ONLOGON",
                "/RL",
                "HIGHEST",
                "/F",  # Force creation if it already exists
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to create scheduled task: {e}") from e


if __name__ == "__main__":
    enable_driver_framework_logging()
    template_and_configure_task(
        install_path="C:\\Program Files\\ThumbDriveAutoCopy\\drive_auto_copy.exe"
    )
