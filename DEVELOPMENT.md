# Development Guide

This document describes how to build the Windows executables and MSI installer for this project.

## Prerequisites

Install the following tools:

- Python 3.11+
- Poetry
- WiX Toolset v4 CLI (`wix` command)

Optional install examples on Windows:

```powershell
winget install Python.Python.3.11
winget install Python.Poetry
winget install WiXToolset.WiXToolset
```

## Project Setup

From the repository root, install dependencies including the installer tool group:

```powershell
poetry install --with installer
```

## Build Executables

Build both EXEs into the `dist/` folder:

```powershell
poetry run poe build-exe
poetry run poe build-first-launch
```

Expected outputs:

- `dist/drive-auto-copy.exe`
- `dist/drive-auto-copy-first-launch.exe`

## Build MSI Installer

The WiX configuration is in `installer/Package.wxs` and installs to:

`C:\Program Files\Drive Auto Copy\`

Build the MSI:

```powershell
wix build installer\Package.wxs -arch x64 -out dist\DriveAutoCopy.msi
```

Expected output:

- `dist/DriveAutoCopy.msi`

## Install For Testing

```powershell
msiexec /i dist\DriveAutoCopy.msi
```

To uninstall:

```powershell
msiexec /x dist\DriveAutoCopy.msi
```

## Full Build Sequence

Run all steps in order:

```powershell
poetry install --with installer
poetry run poe build-exe
poetry run poe build-first-launch
poetry run poe build-installer
```

## Troubleshooting

- If `wix` is not found, reopen terminal after installing WiX, then run `wix --version`.
- If `wix` errors with "You must accept the Open Source Maintenance Fee (OSMF) EULA", see `https://wixtoolset.org/osmf/`
- If EXEs are missing, rerun both `poetry run poe` build commands and check `dist/`.
- If WiX reports missing source files, verify both EXE filenames in `dist/` match the `Source` entries in `installer/Package.wxs`.
