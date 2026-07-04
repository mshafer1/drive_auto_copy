"""Program to automate Windows setup."""

import base64
import ctypes
import os
import subprocess

_SCHEDULED_TASK_TEMPLATE = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Date>2026-06-29T20:54:05.4092301</Date>
    <URI>\Run Drive Copy</URI>
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
    <DisallowStartIfOnBatteries>true</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>true</StopIfGoingOnBatteries>
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
      <Command>C:\Program Files\Drive Auto Copy\drive-auto-copy.exe</Command>
    </Exec>
  </Actions>
</Task>"""


# check if running elevated
def _fail_if_not_elevated():
    """Fail if the script is not running with elevated privileges."""
    try:
        # Check if the user is an admin on Windows
        if ctypes.windll.shell32.IsUserAnAdmin() == 0:
            raise RuntimeError("This script must be run with elevated privileges.")
    except AttributeError:
        # Fallback for Linux/macOS: Check if running as root (UID 0)
        try:
            if os.getlogin() != "root":
                raise RuntimeError("This script must be run with elevated privileges.")
        except Exception:
            # If os.geteuid() is not available, we can't determine if we're elevated
            raise RuntimeError(
                "Cannot determine if the script is running with elevated privileges."
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
    ps_command = f"""
    $xml = $env:SchedTaskTemplate
    Register-ScheduledTask -TaskName 'Drive Auto Copy' -Xml $xml -User 'NT AUTHORITY\\SYSTEM' -Force
    """
    encoded_command = base64.b64encode(ps_command.encode("utf-16-le")).decode("utf-8")
    try:
        # Create a new scheduled task using schtasks
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
            env={**os.environ, "SchedTaskTemplate": _SCHEDULED_TASK_TEMPLATE},
        )
    except subprocess.CalledProcessError as e:
        print(f"Error registering task: {e.stderr}")
        raise RuntimeError(f"Failed to create scheduled task: {e}") from e


if __name__ == "__main__":
    enable_driver_framework_logging()
    template_and_configure_task(
        install_path="C:\\Program Files\\Drive Auto Copy\\drive-auto-copy.exe"
    )
