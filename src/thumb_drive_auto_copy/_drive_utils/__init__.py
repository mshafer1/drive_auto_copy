import string
import ctypes
import functools

@functools.lru_cache(maxsize=1)
def get_removable_drives():
    removable_drives = []
    
    # Get a bitmask of all connected drive letters (e.g., 29 means A, C, D, E)
    drive_bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    # print(f"Drive bitmask: {drive_bitmask:b} (binary), {drive_bitmask} (decimal)")
    
    # Iterate through all possible uppercase letters
    for letter in string.ascii_uppercase:
        if drive_bitmask & 1:
            drive_path = f"{letter}:\\"
            # print(f"Checking drive: {drive_path}")
            # Check the drive type (Type 2 = DRIVE_REMOVABLE)
            # (Type 3 is Fixed/HDD, Type 5 is CD-ROM)
            if ctypes.windll.kernel32.GetDriveTypeW(drive_path) == 2:
                removable_drives.append(drive_path)
                
        # Shift the bitmask to check the next letter
        drive_bitmask >>= 1
        
    return removable_drives
