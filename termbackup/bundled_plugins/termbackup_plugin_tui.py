"""
TermBackup Plugin: TUI Dashboard
================================
Launch a sleek interactive terminal dashboard showing system status.
"""

import json
from termbackup import plugins, ui, config, github
from rich.panel import Panel
from rich.layout import Layout
from rich import box
from termbackup.ui import Theme, Icons

def setup():
    from termbackup.cli import plugins_app
    
    @plugins_app.command("tui")
    def run_tui():
        """Launch the holographic Nexus TUI dashboard."""
        ui.print_header("Nexus Holographic TUI", icon=Icons.ROCKET)
        
        try:
            config.get_config()
            profiles = config.get_all_profiles()
            
            layout = Layout()
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="main"),
            )
            layout["main"].split_row(
                Layout(name="profiles", ratio=1),
                Layout(name="stats", ratio=1)
            )
            
            # Header
            layout["header"].update(Panel(f"[{Theme.PRIMARY}]TermBackup Nexus Uplink Active[/{Theme.PRIMARY}]", style=Theme.PRIMARY))
            
            # Profiles
            prof_text = ""
            total_backups = 0
            for p in profiles:
                content, _ = github.get_metadata_content(p.repo)
                count = 0
                if content:
                    ledger_data = json.loads(content)
                    backups = ledger_data.get("backups", [])
                    count = len(backups)
                    total_backups += count
                prof_text += f"\n[{Theme.ACCENT}]◈ {p.name}[/{Theme.ACCENT}]\n"
                prof_text += f"   Source: {p.source_dir}\n"
                prof_text += f"   Backups: {count}\n"
                
            layout["profiles"].update(Panel(prof_text if prof_text else "No profiles found.", title="Active Profiles", border_style=Theme.ACCENT, box=box.ROUNDED))
            
            # Stats
            stat_text = f"\nTotal Discovered Profiles: {len(profiles)}\n"
            stat_text += f"Total Encrypted Backups: {total_backups}\n"
            stat_text += f"System Status: [{Theme.SUCCESS}]OPTIMAL[/{Theme.SUCCESS}]\n"
            layout["stats"].update(Panel(stat_text, title="Global Telemetry", border_style=Theme.SUCCESS, box=box.ROUNDED))
            
            ui.console.print(layout)
            ui.print_footer()
            
        except Exception as e:
            ui.error(f"Failed to launch TUI: {e}")
