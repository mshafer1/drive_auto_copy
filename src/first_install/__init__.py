"""Program to automate Windows setup."""

import base64
import ctypes
import os
import subprocess
import sys
import xml.sax.saxutils

_SCHEDULED_TASK_TEMPLATE = r"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Date>2026-06-29T20:54:05.4092301</Date>
    <URI>\Drive Auto Copy</URI>
  </RegistrationInfo>
  <Triggers>
    <EventTrigger>
      <Enabled>true</Enabled>
      <Subscription>&lt;QueryList&gt;&lt;Query Id="0" Path="Microsoft-Windows-DriverFrameworks-UserMode/Operational"&gt;&lt;Select Path="Microsoft-Windows-DriverFrameworks-UserMode/Operational"&gt;*[System[Provider[@Name='Microsoft-Windows-DriverFrameworks-UserMode'] and EventID=2003]]&lt;/Select&gt;&lt;/Query&gt;&lt;/QueryList&gt;</Subscription>
    </EventTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>StopExisting</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>false</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>true</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <DisallowStartOnRemoteAppSession>false</DisallowStartOnRemoteAppSession>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT72H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command><SCRIPT_PATH></Command>
    </Exec>
  </Actions>
</Task>"""


# check if running elevated
def _is_elevated():
    """Check if the script is running with elevated privileges."""
    try:
        # Check if the user is an admin on Windows
        # Returns 1 if elevated (Admin), 0 if not
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except (AttributeError, OSError):
        if hasattr(os, "geteuid"):
            return os.geteuid() == 0
        raise RuntimeError("Cannot determine if the script is running with elevated privileges.")


def _fail_if_not_elevated():
    if not _is_elevated():
        raise RuntimeError("This script must be run with elevated privileges.")


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
    ps_command = f"""
    $xml = $env:SchedTaskTemplate
    Register-ScheduledTask -TaskName 'Drive Auto Copy' -Xml $xml -Force
    """
    encoded_command = base64.b64encode(ps_command.encode("utf-16-le")).decode("utf-8")
    try:
        # Create a new scheduled task using powershell
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-EncodedCommand",
                encoded_command,
            ],
            check=True,
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "SchedTaskTemplate": _SCHEDULED_TASK_TEMPLATE.replace(
                    "<SCRIPT_PATH>", xml.sax.saxutils.escape(install_path)
                ),
            },
        )
    except subprocess.CalledProcessError as e:
        print(f"Error registering task: {e.stderr}")
        raise RuntimeError(f"Failed to create scheduled task: {e}") from e


def _run_as_admin():
    if not _is_elevated():
        # Re-run the script with admin arguments
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, subprocess.list2cmdline(sys.argv), None, 1
        )
        if result <= 32:
            raise RuntimeError(f"Failed to relaunch as admin (ShellExecuteW returned {result}).")
        sys.exit(0)


if __name__ == "__main__":
    _run_as_admin()
    print("Running first-time setup...")
    try:
        enable_driver_framework_logging()
        template_and_configure_task(
            install_path="C:\\Program Files\\Drive Auto Copy\\drive-auto-copy.exe"
        )
        print("First-time setup completed successfully.")
    except RuntimeError as e:
        print(f"Error during first-time setup: {e}")
    if sys.stdin is not None and sys.stdin.isatty():
        input("Press Enter to exit...")
