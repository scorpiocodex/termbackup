"""Profile management CLI with export/import support."""

import json
from pathlib import Path

import typer

from termbackup import config, ui
from termbackup.models import ProfileConfig

app = typer.Typer(name="profile", help="Manage backup profiles.")


@app.command("create")
def create_profile(
    name: str = typer.Argument(..., help="The name of the profile."),
    source_dir: str = typer.Option(
        ..., "--source", "-s", help="The directory to back up."
    ),
    repo: str = typer.Option(
        None, "--repo", "-r", help="The GitHub repository (user/repo). Uses default repo if omitted."
    ),
    excludes: list[str] = typer.Option(
        None, "--exclude", "-e", help="Patterns to exclude (repeatable)."
    ),
    compression_level: int = typer.Option(
        6, "--compression-level", "-c", min=0, max=9,
        help="Gzip compression level (0=none, 9=max).",
    ),
    max_backups: int = typer.Option(
        None, "--max-backups", help="Maximum number of backups to keep.",
    ),
    retention_days: int = typer.Option(
        None, "--retention-days", help="Maximum age of backups in days.",
    ),
    backup_mode: str = typer.Option(
        "full", "--backup-mode", help="Backup mode: 'full' or 'incremental'.",
    ),
    webhook_url: str = typer.Option(
        None, "--webhook-url", help="Webhook URL for backup notifications.",
    ),
):
    """Creates a new backup profile."""
    ui.print_header("Profile Creation", icon=ui.Icons.GEAR)

    # Resolve repo: use explicit flag, fall back to default_repo from config
    if repo is None:
        app_config = config.get_config()
        if app_config.default_repo:
            ui.info(f"Using default repository: [{ui.Theme.ACCENT}]{app_config.default_repo}[/{ui.Theme.ACCENT}]")
            repo = app_config.default_repo
        else:
            ui.error("No repository specified. Use --repo/-r or run 'termbackup init' to set up a default repo.")
            raise SystemExit(1)

    config.create_profile(
        name, source_dir, repo, excludes, compression_level,
        max_backups, retention_days, backup_mode, webhook_url,
    )
    ui.print_footer()


@app.command("list")
def list_profiles():
    """Lists all available profiles."""
    ui.print_header("Profiles", icon=ui.Icons.GEAR)

    profiles = config.get_all_profiles()
    if not profiles:
        ui.print_empty(
            "No profiles configured.",
            suggestion="Create one with 'termbackup profile create'.",
        )
        return

    table = ui.create_table("Name", "Source Directory", "Repository", "Mode", "Excludes")
    for profile in profiles:
        excludes = ", ".join(profile.excludes) if profile.excludes else "-"
        table.add_row(
            profile.name,
            profile.source_dir,
            profile.repo,
            profile.backup_mode.value,
            excludes,
        )
    ui.print_table(table)
    ui.info(f"Total: {len(profiles)} profile(s)")
    ui.print_footer()


@app.command("show")
def show_profile(
    name: str = typer.Argument(..., help="The name of the profile to show."),
):
    """Shows the details of a specific profile."""
    ui.print_header("Profile Details", icon=ui.Icons.GEAR)

    profile = config.get_profile(name)

    excludes = ", ".join(profile.excludes) if profile.excludes else "-"
    ui.print_kv_list(
        [
            ("Name", profile.name),
            ("Source Directory", profile.source_dir),
            ("Repository", profile.repo),
            ("Excludes", excludes),
            ("Compression Level", str(profile.compression_level)),
            ("Backup Mode", profile.backup_mode.value),
            ("Max Backups", str(profile.max_backups or "-")),
            ("Retention Days", str(profile.retention_days or "-")),
            ("Webhook URL", profile.webhook_url or "-"),
        ],
        border=True,
        title=f"Profile: {name}",
    )
    ui.print_footer()


@app.command("delete")
def delete_profile(
    name: str = typer.Argument(..., help="The name of the profile to delete."),
):
    """Deletes a backup profile."""
    ui.print_header("Profile Deletion")

    # Validate profile exists before asking for confirmation
    config.get_profile(name)

    if not ui.confirm(f"Delete profile '{name}'?"):
        ui.warning("Cancelled.")
        return

    config.delete_profile(name)
    ui.print_footer()


@app.command("export")
def export_profile(
    name: str = typer.Argument(..., help="The name of the profile to export."),
    output: str = typer.Option(
        None, "--output", "-o", help="Output file path (default: <name>.profile.json)."
    ),
):
    """Exports a profile to a JSON file."""
    ui.print_header("Profile Export")

    profile = config.get_profile(name)

    # Replace source_dir with placeholder for portability
    export_data = profile.model_dump(mode="json")
    export_data["source_dir"] = "<SET_SOURCE_DIR>"

    output_path = Path(output) if output else Path(f"{name}.profile.json")

    with open(output_path, "w") as f:
        json.dump(export_data, f, indent=4)

    ui.success(f"Profile '{name}' exported to {output_path}")
    ui.print_footer()


@app.command("import")
def import_profile(
    input_file: str = typer.Argument(..., help="Path to the profile JSON file."),
    source_dir: str = typer.Option(
        None, "--source", "-s", help="Source directory to use (overrides placeholder)."
    ),
):
    """Imports a profile from a JSON file."""
    ui.print_header("Profile Import")

    input_path = Path(input_file)
    if not input_path.exists():
        ui.error(f"File not found: {input_file}")
        raise SystemExit(1)

    with open(input_path) as f:
        data = json.load(f)

    # Override source_dir if placeholder or provided
    if source_dir:
        data["source_dir"] = str(Path(source_dir).resolve())
    elif data.get("source_dir") == "<SET_SOURCE_DIR>":
        ui.error("Source directory is a placeholder. Provide --source/-s.")
        raise SystemExit(1)

    # Validate with Pydantic
    try:
        profile = ProfileConfig.model_validate(data)
    except Exception as e:
        ui.error(f"Invalid profile data: {e}")
        raise SystemExit(1)

    config.create_profile(
        profile.name,
        profile.source_dir,
        profile.repo,
        profile.excludes,
        profile.compression_level,
        profile.max_backups,
        profile.retention_days,
        profile.backup_mode.value,
        profile.webhook_url,
    )
    ui.print_footer()
