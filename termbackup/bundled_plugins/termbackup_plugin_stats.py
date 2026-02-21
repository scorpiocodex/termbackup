"""
TermBackup Plugin: Advanced Stats
=================================
Provides real-time, real-world storage analytics by parsing the ledger.
"""

import json
from termbackup import plugins, ui, config, github

def post_backup_stats(profile_name: str, backup_id: str, **kwargs):
    ui.info(f"[{ui.Theme.SUCCESS}]◈ Stats Engine[/{ui.Theme.SUCCESS}] Processing metrics for {backup_id}...")
    
def setup():
    """Register the plugin hooks."""
    plugins.register_hook("post_backup", post_backup_stats)
    
    from termbackup.cli import plugins_app
    import typer
    
    @plugins_app.command("stats")
    def run_stats(
        profile_name: str = typer.Argument(None, help="The profile to compute stats for.")
    ):
        """Display advanced storage analytics."""
        from termbackup.utils import format_size
        
        ui.print_header("Telemetry & Analytics", icon="📊")
        
        try:
            config.get_config()
            profiles = [config.get_profile(profile_name)] if profile_name else config.get_all_profiles()
            
            if not profiles:
                ui.warning("No profiles configured.")
                raise typer.Exit()
                
            for p in profiles:
                # ui.section is not confirmed to exist, using info
                ui.info(f"[{ui.Theme.PRIMARY}]Profile: {p.name}[/{ui.Theme.PRIMARY}]")
                content, _ = github.get_metadata_content(p.repo)
                if not content:
                    ui.detail("Total Backups", "0")
                    continue
                    
                ledger_data = json.loads(content)
                backups = ledger_data.get("backups", [])
                
                if not backups:
                    ui.detail("Total Backups", "0")
                    continue
                    
                total_size = sum(b.get("size", 0) for b in backups)
                avg_size = total_size / len(backups)
                total_files = sum(b.get("file_count", 0) for b in backups)
                avg_files = total_files / len(backups)
                
                table = ui.create_table("Metric", "Value")
                table.add_row("Total Backups", str(len(backups)))
                table.add_row("Total Storage", format_size(total_size))
                table.add_row("Avg Storage/Run", format_size(int(avg_size)))
                table.add_row("Avg Files/Run", str(int(avg_files)))
                table.add_row("First Backup", backups[-1].get("created_at", "N/A"))
                table.add_row("Latest Backup", backups[0].get("created_at", "N/A"))
                
                ui.print_table(table)
                
        except Exception as e:
            ui.error(f"Failed to load analytics: {e}")
            
        ui.print_footer()
