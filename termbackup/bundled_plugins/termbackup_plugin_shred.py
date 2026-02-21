"""
TermBackup Plugin: Shredder
===========================
Hook that securely overwrites and shreds temporary backup files
after the backup process completes.
"""

import os
from termbackup import config, plugins, ui

def shred_temp_files(profile_name: str, **kwargs):
    """Securely overwrites temporary files in the config temp directory."""
    tmp_dir = config.CONFIG_DIR / "tmp"
    if not tmp_dir.exists():
        return

    shredded_count = 0
    for file_path in tmp_dir.iterdir():
        if file_path.is_file():
            try:
                # Overwrite with random bytes
                size = file_path.stat().st_size
                with open(file_path, "wb") as f:
                    f.write(os.urandom(size))
                
                # Delete the file
                file_path.unlink()
                shredded_count += 1
            except Exception as e:
                ui.warning(f"Shredder failed on {file_path.name}: {e}")

    if shredded_count > 0:
        ui.success(f"Securely shredded {shredded_count} temporary files.")

def setup() -> None:
    """Register shredder plugin hooks."""
    plugins.register_hook("post_backup", shred_temp_files)
