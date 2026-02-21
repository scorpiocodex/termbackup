"""
TermBackup Plugin: Export
=========================
Exports the backup history for a given profile to a JSON file for external analysis.
"""

import json
from pathlib import Path
from termbackup import plugins, ui, config, github

def setup():
    from termbackup.cli import plugins_app
    import typer

    @plugins_app.command("export")
    def export_history(
        profile_name: str = typer.Argument(..., help="The profile name to export.")
    ):
        """Export backup history to a JSON log file."""
        ui.print_header("Exporting Backup History", icon=ui.Icons.FOLDER)
        
        try:
            config.get_config()
            profile = config.get_profile(profile_name)
            
            content, _ = github.get_metadata_content(profile.repo)
            
            if not content:
                ui.warning("No backups found to export.")
                raise typer.Exit(code=1)
                
            ledger_data = json.loads(content)
            backups = ledger_data.get("backups", [])
            
            if not backups:
                ui.warning("No backups found to export.")
                raise typer.Exit(code=1)
                
            export_path = Path(f"{profile_name}_export.json")
            
            data = []
            for b in backups:
                data.append({
                    "id": b.get("id"),
                    "timestamp": b.get("created_at"),
                    "total_files": b.get("file_count"),
                    "total_size": b.get("size"),
                    "encrypted": True
                })
                
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
                
            ui.success(f"Successfully exported {len(backups)} backup entries.")
            ui.detail("Export Location", str(export_path.resolve()))
            
        except Exception as e:
            ui.error(f"Failed to export history: {e}")
            raise typer.Exit(code=1)
            
        ui.print_footer()
