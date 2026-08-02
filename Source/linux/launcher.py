import subprocess
import os
import hashlib


def get_short_hash(text):
    m = hashlib.md5((text + "\n").encode('utf-8'))
    return m.hexdigest()[:8]


def launch_dayz(dayz_path, ip, port, profile_name, mods=None, disable_battleye=False):
    mod_param = ""
    if mods:
        short_mod_names = []
        for mod_path in mods:
            if not os.path.exists(mod_path):
                continue

            mod_folder_name = os.path.basename(mod_path)
            short_name = f"@{get_short_hash(mod_folder_name)}"
            symlink_path = os.path.join(dayz_path, short_name)

            try:
                if os.path.islink(symlink_path):
                    if os.path.realpath(symlink_path) != os.path.realpath(mod_path):
                        os.unlink(symlink_path)
                        os.symlink(mod_path, symlink_path)
                else:
                    if os.path.exists(symlink_path):
                        short_mod_names.append(mod_path)
                        continue
                    os.symlink(mod_path, symlink_path)

                short_mod_names.append(short_name)
            except Exception as e:
                print(f"Failed to create/update symlink {symlink_path}: {e}")
                short_mod_names.append(mod_path)

        if short_mod_names:
            joined = ";".join(short_mod_names)
            mod_param = f"-mod={joined}"

    cmd = [
        "steam",
        "-applaunch", "221100",
        f"-connect={ip}",
        f"-port={port}",
        f"-name={profile_name}",
        "-nolauncher",
        "-nosplash",
        "-skipintro"
    ]

    if mod_param:
        cmd.append(mod_param)

    try:
        subprocess.Popen(cmd, start_new_session=True)
        return True
    except Exception as e:
        print(f"Error launching: {e}")
        return False
