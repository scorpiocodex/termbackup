"""Backup listing with enhanced UI."""

import json

from termbackup import config, github, ui
from termbackup.utils import format_size, format_timestamp


def list_backups(profile_name: str):
    """Lists all backups for a given profile."""
    ui.print_header("Backup Ledger", icon=ui.Icons.SHIELD)

    profile = config.get_profile(profile_name)
    repo_name = profile.repo

    ui.info(f"Profile: [bold]{profile_name}[/bold]")
    ui.detail("Repository", repo_name)

    content, _ = github.get_metadata_content(repo_name)

    if not content:
        ui.print_empty(
            f"No backups found for profile '{profile_name}'.",
            suggestion=f"Run 'termbackup run {profile_name}' to create your first backup.",
        )
        return

    ledger_data = json.loads(content)
    backups = ledger_data.get("backups", [])

    if not backups:
        ui.print_empty(
            f"No backups found for profile '{profile_name}'.",
            suggestion=f"Run 'termbackup run {profile_name}' to create your first backup.",
        )
        return

    table = ui.create_table("ID", "Filename", "Created", "Size", "Files", "Status")
    for backup in backups:
        if backup.get("verified"):
            status = ui.status_badge("VERIFIED", "success")
        else:
            status = ui.status_badge("PENDING", "warning")

        table.add_row(
            backup["id"][:12],
            backup["filename"],
            format_timestamp(backup["created_at"]),
            format_size(backup["size"]),
            str(backup.get("file_count", "-")),
            status,
        )

    ui.print_table(table)
    ui.info(f"Total: {len(backups)} backup(s)")
    ui.print_footer()
