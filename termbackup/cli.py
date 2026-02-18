"""TermBackup CLI -- all commands registered here."""

import time

import typer

from termbackup import __version__, config, engine, listing, ui
from termbackup import restore as restore_module
from termbackup import verify as verify_module
from termbackup.errors import TermBackupError
from termbackup.profile import app as profile_app

app = typer.Typer(
    name="termbackup",
    help="Zero-Trust Encrypted GitHub Backup CLI",
    add_completion=False,
    invoke_without_command=True,
    add_help_option=False,
    rich_markup_mode="rich",
    context_settings={"max_content_width": 120},
)
app.add_typer(profile_app)


def _handle_error(e: Exception) -> None:
    """Handles errors uniformly across CLI commands."""
    if isinstance(e, TermBackupError):
        ui.error(str(e))
        if e.hint:
            ui.info(f"Hint: {e.hint}")
    else:
        ui.error(str(e))
    raise typer.Exit(code=1)


def _version_callback(value: bool):
    if value:
        ui.print_banner()
        raise typer.Exit()


def _help_callback(value: bool) -> None:
    if value:
        ui.print_help_screen()
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-v",
        callback=_version_callback, is_eager=True,
        help="Show version and exit.",
    ),
    help: bool = typer.Option(  # noqa: A002
        False, "--help", "-h",
        callback=_help_callback, is_eager=True,
        help="Show this help screen and exit.",
    ),
):
    """TermBackup -- Zero-Trust Encrypted GitHub Backup CLI."""
    if ctx.invoked_subcommand is None:
        ui.print_help_screen()
        raise typer.Exit()


@app.command()
def init():
    """Initialize TermBackup configuration."""
    config.init_config()


@app.command()
def run(
    profile_name: str = typer.Argument(..., help="The profile to run."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without uploading."),
    scheduled: bool = typer.Option(
        False, "--scheduled", hidden=True, help="Read password from keyring (for scheduled runs)."
    ),
):
    """Run a backup for the given profile."""
    config.get_config()
    config.get_profile(profile_name)

    if scheduled:
        from termbackup import credentials

        password = credentials.get_profile_password(profile_name)
        if not password:
            ui.error("No stored password found for scheduled run.")
            raise typer.Exit(code=1)
    else:
        password = ui.prompt_secret("Backup password")
        password_confirm = ui.prompt_secret("Confirm password")

        if password != password_confirm:
            ui.error("Passwords do not match.")
            raise typer.Exit(code=1)

    try:
        t0 = time.time()
        engine.run_backup(profile_name, password, dry_run)
        if not dry_run:
            ui.print_elapsed(t0, "Backup completed")
    except (RuntimeError, TermBackupError) as e:
        _handle_error(e)


@app.command("list")
def list_backups(
    profile_name: str = typer.Argument(..., help="The profile to list backups for."),
):
    """List all backups for a profile."""
    try:
        listing.list_backups(profile_name)
    except (RuntimeError, TermBackupError) as e:
        _handle_error(e)


@app.command()
def restore(
    backup_id: str = typer.Argument(..., help="The backup ID to restore."),
    profile_name: str = typer.Option(
        ..., "--profile", "-p", help="The profile to restore from."
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show files without restoring."),
):
    """Restore a backup to its original location."""
    config.get_config()
    config.get_profile(profile_name)

    password = ui.prompt_secret("Backup password")
    try:
        t0 = time.time()
        restore_module.restore_backup(profile_name, backup_id, password, dry_run)
        if not dry_run:
            ui.print_elapsed(t0, "Restore completed")
    except (RuntimeError, TermBackupError) as e:
        _handle_error(e)


@app.command()
def verify(
    backup_id: str = typer.Argument(..., help="The backup ID to verify."),
    profile_name: str = typer.Option(
        ..., "--profile", "-p", help="The profile to verify from."
    ),
):
    """Verify the integrity of a backup."""
    config.get_config()
    config.get_profile(profile_name)

    password = ui.prompt_secret("Backup password")
    try:
        t0 = time.time()
        verify_module.verify_backup(profile_name, backup_id, password)
        ui.print_elapsed(t0, "Verification completed")
    except (RuntimeError, TermBackupError) as e:
        _handle_error(e)


@app.command()
def prune(
    profile_name: str = typer.Argument(..., help="The profile to prune backups for."),
    max_backups: int = typer.Option(None, "--max-backups", help="Maximum backups to keep."),
    retention_days: int = typer.Option(None, "--retention-days", help="Maximum age in days."),
):
    """Manually prune old backups based on retention policy."""
    config.get_config()
    profile = config.get_profile(profile_name)

    effective_max = max_backups or profile.max_backups
    effective_days = retention_days or profile.retention_days

    if not effective_max and not effective_days:
        ui.error("No retention policy specified. Use --max-backups or --retention-days.")
        raise typer.Exit(code=1)

    try:
        engine._run_rotation(profile.repo, effective_max, effective_days, profile_name)
    except (RuntimeError, TermBackupError) as e:
        _handle_error(e)


@app.command()
def migrate():
    """Migrate GitHub token from config.json to OS keyring."""
    from termbackup import credentials

    cfg = config.get_config()
    token = cfg.github_token

    if not token:
        ui.error("No GitHub token found in config.json.")
        raise typer.Exit(code=1)

    # Validate token before migration
    ui.print_header("Token Migration", icon=ui.Icons.KEY)
    config._validate_and_display_token(token)

    try:
        credentials.save_token(token)
        ui.success("Token migrated to OS keyring.")

        # Remove token from config.json
        import json

        raw = {}
        if config.CONFIG_FILE.exists():
            with open(config.CONFIG_FILE) as f:
                raw = json.load(f)
        raw.pop("github_token", None)
        with open(config.CONFIG_FILE, "w") as f:
            json.dump(raw, f, indent=4)
        ui.success("Token removed from config.json.")
    except Exception as e:
        ui.error(f"Migration failed: {e}")
        raise typer.Exit(code=1)


@app.command("update-token")
def update_token():
    """Update the GitHub token with validation."""
    ui.print_header("Token Update", icon=ui.Icons.KEY)

    ui.info("Enter your new GitHub Personal Access Token.")
    ui.info("Supported token types:")
    ui.detail("Classic PAT", "Starts with ghp_ (requires 'repo' scope)")
    ui.detail("Fine-grained", "Starts with github_pat_ (requires Contents read/write)")
    ui.console.print()

    new_token = ui.prompt_secret("New GitHub Token")

    if not new_token.strip():
        ui.error("Token cannot be empty.")
        raise typer.Exit(code=1)

    updated = config.update_token(new_token)
    if updated:
        ui.print_summary_panel("Token Updated", [
            ("Status", "Saved and validated"),
            ("Location", str(config.CONFIG_FILE)),
        ], style="success")
    else:
        ui.error("Token update cancelled.")
        raise typer.Exit(code=1)

    ui.print_footer()


@app.command("token-info")
def token_info():
    """Display detailed information about the current GitHub token."""
    ui.print_header("Token Information", icon=ui.Icons.KEY)

    try:
        token = config.get_github_token()
    except SystemExit:
        raise typer.Exit(code=1)

    from termbackup.token_validator import validate_token

    info = validate_token(token)
    ui.print_token_validation(info)
    ui.print_footer()


@app.command("schedule-enable")
def schedule_enable(
    profile_name: str = typer.Argument(..., help="The profile to schedule."),
    schedule: str = typer.Option(..., "--schedule", help="Schedule expression (cron or Windows format)."),
):
    """Enable scheduled backups for a profile."""
    from termbackup import credentials, scheduler

    config.get_config()
    config.get_profile(profile_name)

    password = ui.prompt_secret("Backup password (stored in keyring)")
    credentials.save_profile_password(profile_name, password)
    ui.success("Password stored in OS keyring.")

    try:
        scheduler.enable_schedule(profile_name, schedule)
        ui.success(f"Schedule enabled for '{profile_name}'.")
    except (RuntimeError, TermBackupError) as e:
        _handle_error(e)


@app.command("schedule-disable")
def schedule_disable(
    profile_name: str = typer.Argument(..., help="The profile to unschedule."),
):
    """Disable scheduled backups for a profile."""
    from termbackup import scheduler

    try:
        scheduler.disable_schedule(profile_name)
        ui.success(f"Schedule disabled for '{profile_name}'.")
    except (RuntimeError, TermBackupError) as e:
        _handle_error(e)


@app.command("schedule-status")
def schedule_status(
    profile_name: str = typer.Argument(..., help="The profile to check."),
):
    """Check schedule status for a profile."""
    from termbackup import scheduler

    status_info = scheduler.get_schedule_status(profile_name)
    if status_info:
        ui.success(f"Schedule active for '{profile_name}':")
        ui.detail("Schedule", status_info)
    else:
        ui.info(f"No schedule found for '{profile_name}'.")


@app.command()
def status():
    """Show TermBackup system status."""
    ui.print_header("System Status", icon=ui.Icons.GEAR)

    config_exists = config.CONFIG_FILE.exists()
    profiles = config.get_all_profiles() if config_exists else []

    from termbackup.signing import has_signing_key

    # Token status
    token_status = f"[{ui.Theme.ERROR}]Not configured[/]"
    if config_exists:
        try:
            token = config.get_github_token()
            from termbackup.token_validator import ValidationStatus, mask_token, validate_token
            masked = mask_token(token)
            info = validate_token(token, timeout=5.0)
            if info.status == ValidationStatus.VALID:
                type_str = info.token_type.value.replace("-", " ").title()
                token_status = (
                    f"[{ui.Theme.SUCCESS}]{masked}[/] "
                    f"[{ui.Theme.DIM}]({type_str}, {info.username})[/{ui.Theme.DIM}]"
                )
            elif info.status == ValidationStatus.NETWORK_ERROR:
                token_status = f"[{ui.Theme.WARNING}]{masked}[/] [{ui.Theme.DIM}](not verified)[/{ui.Theme.DIM}]"
            else:
                token_status = f"[{ui.Theme.WARNING}]{masked}[/] [{ui.Theme.ERROR}]({info.status.value})[/{ui.Theme.ERROR}]"
        except (SystemExit, Exception):
            token_status = f"[{ui.Theme.ERROR}]Error reading token[/]"

    items = [
        ("Config", f"[{ui.Theme.SUCCESS}]Found[/]" if config_exists else f"[{ui.Theme.ERROR}]Not found[/]"),
        ("Config Path", str(config.CONFIG_FILE)),
        ("Token", token_status),
        ("Profiles", str(len(profiles))),
        ("Version", __version__),
        ("Encryption", "AES-256-GCM + Argon2id"),
        ("Signing Key", "Configured" if has_signing_key() else "Not configured"),
    ]

    ui.print_kv_list(items, title="System Overview", border=True)

    if profiles:
        table = ui.create_table("Profile", "Source", "Repository", "Mode")
        for p in profiles:
            table.add_row(p.name, p.source_dir, p.repo, p.backup_mode.value)
        ui.print_table(table)

    ui.print_footer()


@app.command()
def doctor():
    """Run system health checks."""
    from termbackup import doctor as doctor_module

    doctor_module.run_doctor()


@app.command("diff")
def diff_cmd(
    id1: str = typer.Argument(..., help="First (older) backup ID."),
    id2: str = typer.Argument(..., help="Second (newer) backup ID."),
    profile_name: str = typer.Option(
        ..., "--profile", "-p", help="The profile to compare backups from."
    ),
):
    """Compare two backups and show file differences."""
    from termbackup import diff

    config.get_config()
    profile = config.get_profile(profile_name)

    password = ui.prompt_secret("Backup password")

    try:
        changes = diff.diff_backups(profile.repo, id1, id2, password)
        ui.print_diff_table(changes)
    except (RuntimeError, TermBackupError) as e:
        _handle_error(e)


@app.command("rotate-key")
def rotate_key_cmd(
    profile_name: str = typer.Argument(..., help="The profile to rotate keys for."),
):
    """Re-encrypt all backups with a new password."""
    from termbackup import rotate_key

    config.get_config()
    config.get_profile(profile_name)

    old_password = ui.prompt_secret("Current backup password")
    new_password = ui.prompt_secret("New backup password")
    new_password_confirm = ui.prompt_secret("Confirm new password")

    if new_password != new_password_confirm:
        ui.error("New passwords do not match.")
        raise typer.Exit(code=1)

    try:
        t0 = time.time()
        rotate_key.rotate_key(profile_name, old_password, new_password)
        ui.print_elapsed(t0, "Key rotation completed")
    except (RuntimeError, TermBackupError) as e:
        _handle_error(e)


@app.command()
def daemon(
    profile_name: str = typer.Argument(..., help="The profile to run in daemon mode."),
    interval: int = typer.Option(60, "--interval", "-i", help="Interval in minutes between backups."),
):
    """Run backups in a continuous loop (daemon mode)."""
    from termbackup import daemon as daemon_module

    config.get_config()
    config.get_profile(profile_name)

    daemon_module.run_daemon(profile_name, interval)


@app.command("generate-key")
def generate_signing_key():
    """Generate an Ed25519 signing keypair for backup authentication."""
    from termbackup import signing

    ui.print_header("Signing Key Generation", icon=ui.Icons.KEY)

    if signing.has_signing_key():
        ui.warning("Signing key already exists.")
        ui.detail("Private Key", str(signing.SIGNING_KEY_PATH))
        ui.detail("Public Key", str(signing.SIGNING_PUB_PATH))
        if not ui.confirm("Overwrite existing signing key?"):
            ui.info("Cancelled.")
            return

    password = ui.prompt_secret("Password to encrypt the signing key")
    password_confirm = ui.prompt_secret("Confirm password")

    if password != password_confirm:
        ui.error("Passwords do not match.")
        raise typer.Exit(code=1)

    try:
        signing.generate_signing_key(password)
        ui.print_summary_panel("Signing Key Created", [
            ("Algorithm", "Ed25519"),
            ("Private Key", str(signing.SIGNING_KEY_PATH)),
            ("Public Key", str(signing.SIGNING_PUB_PATH)),
            ("Encryption", "Password-protected (PKCS8)"),
        ], style="success")
    except Exception as e:
        ui.error(f"Key generation failed: {e}")
        raise typer.Exit(code=1)

    ui.print_footer()


@app.command("audit-log")
def audit_log(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of entries to show."),
    operation: str = typer.Option(None, "--operation", "-o", help="Filter by operation type."),
    profile_filter: str = typer.Option(None, "--profile", "-p", help="Filter by profile name."),
):
    """View the audit log in a formatted table."""
    import json

    from termbackup.audit import AUDIT_LOG_PATH

    ui.print_header("Audit Log", icon=ui.Icons.SEARCH)

    if not AUDIT_LOG_PATH.exists() or AUDIT_LOG_PATH.stat().st_size == 0:
        ui.print_empty("No audit log entries found.")
        return

    entries = []
    with open(AUDIT_LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                # Apply filters
                if operation and entry.get("operation") != operation:
                    continue
                if profile_filter and entry.get("profile") != profile_filter:
                    continue
                entries.append(entry)
            except json.JSONDecodeError:
                continue

    if not entries:
        ui.print_empty("No matching audit log entries.")
        return

    # Show most recent entries
    recent = entries[-limit:]

    table = ui.create_table("Timestamp", "Operation", "Profile", "Status", "Details")
    for entry in reversed(recent):
        from termbackup.utils import format_timestamp
        ts = format_timestamp(entry.get("timestamp", ""))
        op = entry.get("operation", "")
        profile_name = entry.get("profile", "")
        entry_status = entry.get("status", "")
        details = entry.get("details", {})

        # Format status with color
        if entry_status == "success":
            status_display = f"[{ui.Theme.SUCCESS}]{entry_status}[/{ui.Theme.SUCCESS}]"
        else:
            status_display = f"[{ui.Theme.ERROR}]{entry_status}[/{ui.Theme.ERROR}]"

        # Format details concisely
        detail_parts = []
        for k, v in details.items():
            if k in ("backup_id", "file_count", "re_encrypted", "pruned"):
                detail_parts.append(f"{k}={v}")
        detail_str = ", ".join(detail_parts) if detail_parts else "-"

        table.add_row(ts, op, profile_name, status_display, detail_str)

    ui.print_table(table)
    ui.info(f"Showing {len(recent)} of {len(entries)} entries")
    ui.print_footer()


@app.command("clean")
def clean():
    """Remove orphaned temporary files."""
    ui.print_header("Cleanup", icon=ui.Icons.TRASH)

    tmp_dir = config.CONFIG_DIR / "tmp"
    if not tmp_dir.exists():
        ui.success("No temporary files found.")
        ui.print_footer()
        return

    orphans = list(tmp_dir.iterdir())
    if not orphans:
        ui.success("No temporary files found.")
        ui.print_footer()
        return

    from termbackup.utils import format_size
    total_size = sum(f.stat().st_size for f in orphans if f.is_file())

    ui.warning(f"Found {len(orphans)} orphaned file(s) ({format_size(total_size)})")
    for f in orphans:
        ui.detail("File", f.name)

    if not ui.confirm("Delete all temporary files?"):
        ui.info("Cancelled.")
        return

    deleted = 0
    for f in orphans:
        try:
            if f.is_file():
                f.unlink()
                deleted += 1
            elif f.is_dir():
                import shutil
                shutil.rmtree(f)
                deleted += 1
        except Exception as e:
            ui.warning(f"Could not delete {f.name}: {e}")

    ui.success(f"Cleaned {deleted} file(s), freed {format_size(total_size)}")
    ui.print_footer()


if __name__ == "__main__":
    app()

