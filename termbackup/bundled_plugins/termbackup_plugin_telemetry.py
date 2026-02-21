"""
TermBackup Plugin: Telemetry
============================
Hooks into the pre_backup and post_backup phases to display
holographic-style system RAM and CPU usage metrics.
"""

import time
import psutil
from rich.panel import Panel
from rich.table import Table

from termbackup import plugins, ui

def telemetry_pre_backup(profile_name: str, **kwargs):
    """Shows pre-backup system telemetry."""
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    
    table = ui.create_table("Resource", "Utilization", "Status", title="System Telemetry")
    
    cpu_styled = f"[{ui.Theme.SUCCESS}]{cpu}%[/]" if cpu < 80 else f"[{ui.Theme.WARNING}]{cpu}%[/]"
    mem_styled = f"[{ui.Theme.SUCCESS}]{mem.percent}%[/]" if mem.percent < 85 else f"[{ui.Theme.ERROR}]{mem.percent}%[/]"
    
    table.add_row("CPU Load", cpu_styled, "OPTIMAL" if cpu < 80 else "HEAVY")
    table.add_row("RAM Usage", mem_styled, "OPTIMAL" if mem.percent < 85 else "CRITICAL")
    
    ui.print_table(table)

def telemetry_cli(app):
    """Registers the telemetry command."""
    import typer
    @app.command("telemetry")
    def show_telemetry():
        """Show full live system telemetry."""
        ui.print_header("Holographic Telemetry", icon=ui.Icons.PULSE)
        telemetry_pre_backup("manual")
        ui.print_footer()

def setup() -> None:
    """Register telemetry plugin hooks."""
    plugins.register_hook("pre_backup", telemetry_pre_backup)
    plugins.register_hook("cli_commands", telemetry_cli)
