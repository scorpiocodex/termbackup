"""
TermBackup Plugin: Hologram
===========================
Generates a sci-fi scanning visualization effect before running a backup.
"""

import time
import random
from rich.text import Text

from termbackup import plugins, ui

def hologram_scan(profile_name: str, **kwargs):
    """Displays a Matrix-style scanning log before the backup starts."""
    ui.info("Initializing holographic file system scan...")
    with ui.create_spinner() as progress:
        task = progress.add_task("[cyan]Quantum data stream analysis...", total=10)
        for i in range(10):
            # Matrix/hacker-style print
            hex_stream = "".join(random.choice("0123456789ABCDEF!@#$%^&*") for _ in range(40))
            ui.console.print(f"[{ui.Theme.DIM}]0x{(1000 + i*16):X}[/] [{ui.Theme.PRIMARY}]{hex_stream}[/]", highlight=False)
            time.sleep(0.1)
            progress.update(task, advance=1)
    ui.success("Scan complete. Quantum integrity verified.")

def setup() -> None:
    """Register holographic scan plugin hooks."""
    plugins.register_hook("pre_backup", hologram_scan)
