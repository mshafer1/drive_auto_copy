# drive-auto-copy

A utility to move files (configurable paths and patterns) to the system whenever a removable drive is plugged in.


## Why?

I regularly take the thumb drive from my mixer, plug it in just to move the files to the system, then eject it.

This is to automate that process.

After files are moved, the app prompts to optionally eject the drive.

## Configuration

If present, configuration is loaded from:

`~/.config/drive_auto_copy/settings.yaml`

Example:

```yaml
source_pattern: "AHQU/USBREC/*.WAV"
destination_path: "~/Music/DriveAutoCopy"
move_files: true
```

Fields:

- `source_pattern`: Glob pattern resolved from the root of each removable drive.
- `destination_path`: Local folder where matching files are copied.
- `move_files`: `true` to move files (copy then remove source), `false` to only copy.

If the file is missing or invalid, built-in defaults are used.
