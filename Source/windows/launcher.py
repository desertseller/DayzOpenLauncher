import subprocess
import os
import platform

def launch_dayz(dayz_path, ip, port, profile_name, mods=None):
    if not os.path.exists(dayz_path):
        return False

    be_exe = os.path.join(dayz_path, "DayZ_BE.exe")
    dayz_exe = "DayZ_x64.exe"
    
    if not os.path.exists(os.path.join(dayz_path, dayz_exe)):
         dayz_exe = "DayZ.exe"

    if not os.path.exists(be_exe):
        be_exe = os.path.join(dayz_path, dayz_exe) 
    
    if not os.path.exists(be_exe):
        return False

    cmd = [
        be_exe,
        "0", "1", "1",
        "-exe", dayz_exe,
        f"-connect={ip}",
        f"-port={port}",
        f"-name={profile_name}",
        "-nolauncher",
        "-nosplash",
        "-skipintro"
    ]
    
    if mods:
        mod_str = ";".join(mods)
        cmd.append(f"-mod={mod_str}")

    try:
        flags = 0x00000008 | 0x00000200
        proc = subprocess.Popen(cmd, cwd=dayz_path, creationflags=flags, close_fds=True)
        proc.poll()
        return True
    except Exception as e:
        return False
