"""Typer CLI entrypoint for TermBackup.

Modern, professional CLI with beautiful Rich UI.
"""

import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from . import __version__
from .backup import BackupError, run_backup
from .config import (
    Config,
    ConfigError,
    Profile,
    create_profile,
    delete_profile,
    get_profile,
    is_initialized,
    list_profiles,
    load_config,
    require_initialized,
    save_config,
    ensure_config_dir,
)
from .github import GitHubClient, GitHubError
from .restore import RestoreError, get_restore_preview, restore_backup
from .ui import (
    BackupProgressManager,
    Icons,
    RestoreProgressManager,
    confirm_action,
    console,
    create_backup_table,
    create_profile_table,
    print_backup_preview,
    print_backup_summary,
    print_error,
    print_header,
    print_info,
    print_init_success,
    print_no_backups,
    print_no_profiles,
    print_profile_details,
    print_restore_preview,
    print_restore_summary,
    print_step,
    print_subheader,
    print_success,
    print_verify_result,
    print_warning,
    print_welcome,
    progress_spinner,
    prompt_input,
    prompt_password,
)
from .utils import format_size, normalize_backup_id, parse_backup_name, validate_backup_id
from .verify import VerifyError, verify_backup


app = typer.Typer(
    name="termbackup",
    help="Secure cloud-backed backup CLI using GitHub as encrypted storage.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=False,
)

profile_app = typer.Typer(
    help="Manage backup profiles.",
    no_args_is_help=True,
)
app.add_typer(profile_app, name="profile")


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print()
        console.print(f"[bold cyan]TERM[/bold cyan][bold white]BACKUP[/bold white] [dim]v{__version__}[/dim]")
        console.print("[dim]Secure cloud-backed backup CLI[/dim]")
        console.print()
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """TermBackup - Secure cloud-backed backup CLI using GitHub."""
    pass


@app.command()
def init() -> None:
    """Initialize TermBackup with GitHub configuration."""
    print_welcome()

    if is_initialized():
        if not confirm_action(
            "TermBackup is already configured. Reconfigure?",
            warning="This will overwrite your existing configuration.",
        ):
            raise typer.Exit()

    print_subheader("GitHub Configuration")

    # Get GitHub username
    github_username = prompt_input("GitHub username")
    if not github_username:
        print_error("GitHub username is required")
        raise typer.Exit(1)

    # Get repository name
    github_repo = prompt_input("Repository name", default="termbackup-storage")
    if not github_repo:
        print_error("Repository name is required")
        raise typer.Exit(1)

    console.print()
    print_info("A GitHub Personal Access Token (PAT) with 'repo' scope is required.")
    print_info("Create one at: [link]https://github.com/settings/tokens[/link]")
    console.print()

    # Token storage preference
    use_env_var = confirm_action(
        "Store token in environment variable instead of config file?",
        default=False,
    )

    if use_env_var:
        env_var_name = prompt_input("Environment variable name", default="TERMBACKUP_GITHUB_TOKEN")
        github_token = os.environ.get(env_var_name, "")
        if not github_token:
            print_warning(f"Environment variable {env_var_name} is not set.")
            github_token = prompt_password("GitHub PAT")
            console.print()
            print_info(f"Remember to set {env_var_name} in your shell profile.")
    else:
        env_var_name = None
        github_token = prompt_password("GitHub PAT")

    if not github_token:
        print_error("GitHub token is required")
        raise typer.Exit(1)

    # Create config
    config = Config(
        github_username=github_username,
        github_repo=github_repo,
        github_token="" if use_env_var else github_token,
        github_token_env_var=env_var_name if use_env_var else None,
        initialized=False,
    )

    # Temporarily set env var for validation
    if use_env_var and not os.environ.get(env_var_name):
        os.environ[env_var_name] = github_token

    # Validate token
    console.print()
    with progress_spinner("Validating GitHub token..."):
        try:
            client = GitHubClient(config)
            client.validate_token()
        except GitHubError as e:
            print_error("Token validation failed", str(e))
            raise typer.Exit(1)

    print_step(Icons.SUCCESS, "Token validated", status="success")

    # Check/create repository
    with progress_spinner("Checking repository..."):
        repo_exists = client.repo_exists()

    if repo_exists:
        print_step(Icons.SUCCESS, f"Repository {github_username}/{github_repo} exists", status="success")
    else:
        console.print()
        if confirm_action(f"Create repository {github_username}/{github_repo}?", default=True):
            private = confirm_action("Make repository private?", default=True)

            with progress_spinner("Creating repository..."):
                try:
                    client.create_repo(private=private)
                except GitHubError as e:
                    print_error("Failed to create repository", str(e))
                    raise typer.Exit(1)

            print_step(Icons.SUCCESS, "Repository created", status="success")

            with progress_spinner("Initializing repository..."):
                try:
                    client.initialize_repo()
                except GitHubError as e:
                    print_error("Failed to initialize repository", str(e))
                    raise typer.Exit(1)

            print_step(Icons.SUCCESS, "Repository initialized", status="success")
        else:
            print_error("Repository is required", "Create it manually and run init again.")
            raise typer.Exit(1)

    # Save config
    config.initialized = True
    ensure_config_dir()
    save_config(config)

    print_init_success(github_username, github_repo)


@profile_app.command("create")
def profile_create() -> None:
    """Create a new backup profile interactively."""
    try:
        require_initialized()
    except ConfigError as e:
        print_error(str(e))
        raise typer.Exit(1)

    print_header("Create Backup Profile", "Define a new backup source")

    # Get profile name
    name = prompt_input("Profile name")
    if not name:
        print_error("Profile name is required")
        raise typer.Exit(1)

    if not name.replace("_", "").replace("-", "").isalnum():
        print_error("Profile name must contain only letters, numbers, underscores, or hyphens")
        raise typer.Exit(1)

    # Get source directory
    console.print()
    source_dir = prompt_input("Source directory to backup")
    if not source_dir:
        print_error("Source directory is required")
        raise typer.Exit(1)

    source_path = Path(source_dir).expanduser().resolve()
    if not source_path.exists():
        print_error(f"Directory does not exist: {source_path}")
        raise typer.Exit(1)

    if not source_path.is_dir():
        print_error(f"Not a directory: {source_path}")
        raise typer.Exit(1)

    # Get exclusion patterns
    console.print()
    print_info("Enter glob patterns to exclude (e.g., *.log, temp/)")
    exclude_input = prompt_input("Exclusion patterns (comma-separated)", default="")
    exclude_patterns = []
    if exclude_input:
        exclude_patterns = [p.strip() for p in exclude_input.split(",") if p.strip()]

    # Password environment variable
    console.print()
    use_env_password = confirm_action("Use environment variable for password?", default=False)
    password_env_var = None
    if use_env_password:
        default_env = f"TERMBACKUP_{name.upper()}_PASSWORD"
        password_env_var = prompt_input("Environment variable name", default=default_env)

    # Create profile
    profile = Profile(
        name=name,
        source_directory=str(source_path),
        exclude_patterns=exclude_patterns,
        password_env_var=password_env_var,
    )

    try:
        create_profile(profile)
    except ConfigError as e:
        print_error(str(e))
        raise typer.Exit(1)

    console.print()
    print_success(f"Profile '{name}' created successfully!")
    console.print()
    print_info(f"Run backup with: [cyan]termbackup run {name}[/cyan]")
    console.print()


@profile_app.command("list")
def profile_list() -> None:
    """List all backup profiles."""
    try:
        profiles = list_profiles()
    except ConfigError as e:
        print_error(str(e))
        raise typer.Exit(1)

    print_header("Backup Profiles")

    if not profiles:
        print_no_profiles()
        return

    table = create_profile_table()
    for p in profiles:
        table.add_row(
            p.name,
            p.source_directory,
            str(len(p.exclude_patterns)) if p.exclude_patterns else "-",
        )

    console.print(table)
    console.print()
    print_info(f"Total: {len(profiles)} profile(s)")
    console.print()


@profile_app.command("show")
def profile_show(name: str = typer.Argument(..., help="Profile name")) -> None:
    """Show details of a backup profile."""
    try:
        profile = get_profile(name)
    except ConfigError as e:
        print_error(str(e))
        raise typer.Exit(1)

    print_header("Profile Details")
    print_profile_details(profile)
    console.print()


@profile_app.command("delete")
def profile_delete_cmd(name: str = typer.Argument(..., help="Profile name to delete")) -> None:
    """Delete a backup profile."""
    try:
        profile = get_profile(name)
    except ConfigError as e:
        print_error(str(e))
        raise typer.Exit(1)

    print_header("Delete Profile", name)

    if not confirm_action(
        f"Delete profile '{name}'?",
        warning="This cannot be undone. Existing backups will NOT be deleted.",
        default=False,
    ):
        print_warning("Deletion cancelled.")
        raise typer.Exit()

    try:
        delete_profile(name)
    except ConfigError as e:
        print_error(str(e))
        raise typer.Exit(1)

    console.print()
    print_success(f"Profile '{name}' deleted successfully!")
    console.print()


@app.command()
def run(
    profile_name: str = typer.Argument(..., help="Profile name to run"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Preview without creating backup"),
) -> None:
    """Run a backup using specified profile."""
    try:
        config = require_initialized()
        profile = get_profile(profile_name)
    except ConfigError as e:
        print_error(str(e))
        raise typer.Exit(1)

    if dry_run:
        print_header("Backup Preview", profile_name)
    else:
        print_header("Running Backup", profile_name)

    # Get password
    if profile.password_env_var:
        password = os.environ.get(profile.password_env_var, "")
        if not password:
            print_warning(f"Environment variable {profile.password_env_var} not set.")
            password = prompt_password("Encryption password")
    else:
        password = prompt_password("Encryption password")

    if not password:
        print_error("Password is required for encryption")
        raise typer.Exit(1)

    if not dry_run:
        confirm_password = prompt_password("Confirm password")
        if password != confirm_password:
            print_error("Passwords do not match")
            raise typer.Exit(1)

    console.print()

    try:
        if dry_run:
            from .backup import create_backup

            with progress_spinner("Scanning files..."):
                _, manifest = create_backup(profile, password, dry_run=True)

            file_preview = [{"path": f["path"], "size": f["size"]} for f in manifest.files]
            print_backup_preview(file_preview, manifest.total_size)
            console.print()
            print_info("Dry run complete. No backup was created.")
            console.print()
        else:
            progress = BackupProgressManager()

            with progress:
                manifest = run_backup(
                    config,
                    profile,
                    password,
                    progress_callback=progress.update,
                )

            print_backup_summary(manifest)
            console.print()

    except BackupError as e:
        print_error("Backup failed", str(e))
        raise typer.Exit(1)
    except GitHubError as e:
        print_error("Upload failed", str(e))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print()
        print_warning("Backup cancelled by user.")
        raise typer.Exit(130)


@app.command("list")
def list_backups() -> None:
    """List all backups in the repository."""
    try:
        config = require_initialized()
    except ConfigError as e:
        print_error(str(e))
        raise typer.Exit(1)

    print_header("Available Backups")

    with progress_spinner("Fetching backup list..."):
        try:
            client = GitHubClient(config)
            backups = client.list_backups()
        except GitHubError as e:
            print_error("Failed to list backups", str(e))
            raise typer.Exit(1)

    if not backups:
        print_no_backups()
        return

    table = create_backup_table()
    for backup in backups:
        timestamp = parse_backup_name(backup.name)
        date_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "Unknown"
        table.add_row(
            backup.name.replace(".tbk", ""),
            date_str,
            format_size(backup.size),
            f"[green]{Icons.SUCCESS}[/green]",
        )

    console.print(table)
    console.print()
    print_info(f"Total: {len(backups)} backup(s)")
    console.print()


@app.command()
def delete(
    backup_id: str = typer.Argument(..., help="Backup ID to delete"),
) -> None:
    """Delete a backup from the repository."""
    try:
        config = require_initialized()
    except ConfigError as e:
        print_error(str(e))
        raise typer.Exit(1)

    if not validate_backup_id(backup_id):
        print_error(f"Invalid backup ID format: {backup_id}")
        raise typer.Exit(1)

    print_header("Delete Backup", backup_id)

    # Verify backup exists
    backup_name = normalize_backup_id(backup_id)
    with progress_spinner("Checking backup..."):
        try:
            client = GitHubClient(config)
            backup_info = client.get_backup_info(backup_name)
        except GitHubError as e:
            print_error("Failed to check backup", str(e))
            raise typer.Exit(1)

    if not backup_info:
        print_error(f"Backup not found: {backup_id}")
        raise typer.Exit(1)

    console.print()
    print_info(f"Backup size: {format_size(backup_info.size)}")
    console.print()

    if not confirm_action(
        f"Delete backup '{backup_id}'?",
        warning="This action is IRREVERSIBLE. The backup will be permanently deleted.",
        default=False,
    ):
        print_warning("Deletion cancelled.")
        raise typer.Exit()

    with progress_spinner("Deleting backup..."):
        try:
            client.delete_backup(backup_name)
        except GitHubError as e:
            print_error("Failed to delete backup", str(e))
            raise typer.Exit(1)

    console.print()
    print_success(f"Backup '{backup_id}' deleted successfully!")
    console.print()


@app.command()
def restore(
    backup_id: str = typer.Argument(..., help="Backup ID to restore"),
    dest: Optional[str] = typer.Option(None, "--dest", "-d", help="Destination directory"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Preview without restoring"),
) -> None:
    """Restore a backup to specified destination."""
    try:
        config = require_initialized()
    except ConfigError as e:
        print_error(str(e))
        raise typer.Exit(1)

    if not validate_backup_id(backup_id):
        print_error(f"Invalid backup ID format: {backup_id}")
        raise typer.Exit(1)

    if dry_run:
        print_header("Restore Preview", backup_id)
    else:
        print_header("Restore Backup", backup_id)

    # Get password
    password = prompt_password("Decryption password")
    if not password:
        print_error("Password is required for decryption")
        raise typer.Exit(1)

    console.print()

    try:
        if dry_run:
            with progress_spinner("Fetching backup..."):
                preview = get_restore_preview(config, backup_id, password)

            dest_dir = dest or preview.source_directory
            print_restore_preview(preview.files, dest_dir)
            console.print()
            print_info("Dry run complete. No files were restored.")
            console.print()
        else:
            dest_path = Path(dest).expanduser().resolve() if dest else None

            # Confirm restore
            dest_display = str(dest_path) if dest_path else "(original location)"
            if not confirm_action(
                f"Restore to {dest_display}?",
                warning="Existing files may be overwritten.",
                default=False,
            ):
                print_warning("Restore cancelled.")
                raise typer.Exit()

            progress = RestoreProgressManager()

            with progress:
                preview, restored_files = restore_backup(
                    config,
                    backup_id,
                    password,
                    dest_path,
                    progress.update,
                )

            print_restore_summary(
                preview,
                len(restored_files),
                str(dest_path) if dest_path else preview.source_directory,
            )
            console.print()

    except RestoreError as e:
        print_error("Restore failed", str(e))
        raise typer.Exit(1)
    except GitHubError as e:
        print_error("Download failed", str(e))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print()
        print_warning("Restore cancelled by user.")
        raise typer.Exit(130)


@app.command()
def verify(
    backup_id: str = typer.Argument(..., help="Backup ID to verify"),
) -> None:
    """Verify backup integrity without restoring."""
    try:
        config = require_initialized()
    except ConfigError as e:
        print_error(str(e))
        raise typer.Exit(1)

    if not validate_backup_id(backup_id):
        print_error(f"Invalid backup ID format: {backup_id}")
        raise typer.Exit(1)

    print_header("Verify Backup", backup_id)

    # Get password
    password = prompt_password("Decryption password")
    if not password:
        print_error("Password is required for verification")
        raise typer.Exit(1)

    console.print()

    try:
        progress = RestoreProgressManager()
        progress.STAGES = {
            "download": (Icons.DOWNLOAD, "Downloading"),
            "decrypt": (Icons.ENCRYPT, "Decrypting"),
            "verify": (Icons.VERIFY, "Verifying"),
        }

        with progress:
            result = verify_backup(config, backup_id, password, progress.update)

        print_verify_result(result)
        console.print()

        if not result.is_valid:
            raise typer.Exit(1)

    except VerifyError as e:
        print_error("Verification failed", str(e))
        raise typer.Exit(1)
    except GitHubError as e:
        print_error("Download failed", str(e))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print()
        print_warning("Verification cancelled by user.")
        raise typer.Exit(130)


@app.command()
def status() -> None:
    """Show current TermBackup configuration status."""
    print_header("TermBackup Status")

    if not is_initialized():
        print_warning("TermBackup is not initialized.")
        console.print()
        print_info("Run [cyan]termbackup init[/cyan] to get started.")
        console.print()
        return

    try:
        config = load_config()
    except ConfigError as e:
        print_error(str(e))
        raise typer.Exit(1)

    from rich.panel import Panel
    from rich import box

    # Configuration info
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="dim")
    table.add_column("Value", style="bold")

    table.add_row("Status", f"[green]{Icons.SUCCESS} Initialized[/green]")
    table.add_row("Repository", f"[cyan]{config.github_username}/{config.github_repo}[/cyan]")
    table.add_row(
        "Token",
        f"[blue]${config.github_token_env_var}[/blue]"
        if config.github_token_env_var
        else "[dim](stored in config)[/dim]",
    )
    table.add_row("Profiles", f"[magenta]{len(config.profiles)}[/magenta]")

    console.print(
        Panel(
            table,
            title=f"[bold]{Icons.CONFIG} Configuration[/bold]",
            box=box.ROUNDED,
            border_style="cyan",
            padding=(1, 2),
        )
    )

    # Test connection
    console.print()
    with progress_spinner("Testing GitHub connection..."):
        try:
            client = GitHubClient(config)
            backups = client.list_backups()
            connection_ok = True
        except GitHubError:
            connection_ok = False
            backups = []

    if connection_ok:
        print_success(f"GitHub connection OK - {len(backups)} backup(s) found")
    else:
        print_warning("GitHub connection failed")

    console.print()


if __name__ == "__main__":
    app()
