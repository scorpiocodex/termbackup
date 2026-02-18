"""Core backup execution engine with Pydantic models, audit logging, and signing."""

import json
from pathlib import Path

from termbackup import archive, audit, config, diff, github, ledger, manifest, rotation, ui
from termbackup.utils import format_size


def run_backup(profile_name: str, password: str, dry_run: bool = False):
    """Runs a backup for the given profile."""
    ui.print_header("Backup Operation", icon=ui.Icons.SHIELD)

    # 1. Get profile
    profile = config.get_profile(profile_name)
    source_dir = Path(profile.source_dir)
    repo_name = profile.repo
    excludes = profile.excludes

    ui.print_step_progress(1, 5, "Loading profile")
    ui.detail("Profile", profile_name)
    ui.detail("Source", str(source_dir))
    ui.detail("Repository", repo_name)
    ui.console.print()

    if not source_dir.is_dir():
        ui.error(f"Source directory not found: {source_dir}")
        raise SystemExit(1)

    # 2. Create manifest (with incremental support)
    backup_mode = profile.backup_mode.value
    parent_backup_id = None
    previous_manifest = None

    if backup_mode == "incremental":
        latest = ledger.get_latest_backup(repo_name)
        if latest:
            parent_backup_id = latest.id
            previous_manifest = github.download_manifest(repo_name, parent_backup_id)

    ui.print_step_progress(2, 5, "Creating file manifest")
    manifest_data = manifest.create_manifest(
        source_dir, excludes, backup_mode, parent_backup_id
    )

    # For incremental: filter to changed files only
    if backup_mode == "incremental" and previous_manifest:
        changes = diff.compute_changes(manifest_data, previous_manifest)
        changed_files_dicts = changes["added"] + changes["modified"]
        if changed_files_dicts:
            # Reconstruct FileMetadata from dicts
            from termbackup.models import FileMetadata

            manifest_data.files = [FileMetadata.model_validate(f) for f in changed_files_dicts]
            ui.info(
                f"Incremental: {len(changes['added'])} added, "
                f"{len(changes['modified'])} modified, "
                f"{len(changes['deleted'])} deleted"
            )
        else:
            ui.success("No changes detected — skipping backup")
            ui.print_footer()
            return

    backup_id = manifest_data.backup_id or ""
    file_count = len(manifest_data.files)
    total_size = sum(f.size for f in manifest_data.files)
    archive_filename = f"backup_{backup_id[:12]}.tbk"

    ui.detail("Files", str(file_count))
    ui.detail("Total size", format_size(total_size))
    ui.detail("Backup ID", backup_id[:12])

    # Create a temporary directory for the archive
    temp_dir = Path(config.CONFIG_DIR / "tmp")
    temp_dir.mkdir(exist_ok=True)
    archive_path = temp_dir / archive_filename

    # 3. Create archive
    compression_level = profile.compression_level
    ui.print_step_progress(3, 5, "Encrypting and packaging archive")
    with ui.create_spinner() as spinner:
        task = spinner.add_task("Encrypting payload (AES-256-GCM + Argon2id)")
        archive.create_archive(archive_path, source_dir, manifest_data, password, compression_level)
        spinner.update(task, completed=True)

    archive_size = archive_path.stat().st_size

    if dry_run:
        ui.console.print()
        ui.warning("Dry run complete — no upload performed")
        ui.detail("Archive path", str(archive_path))
        archive_path.unlink()
        ui.print_footer()
        return

    # 4. GitHub integration
    commit_sha = ""
    try:
        ui.print_step_progress(4, 5, "Uploading to GitHub")
        with ui.create_spinner() as spinner:
            task = spinner.add_task("Uploading archive")
            commit_sha = github.upload_blob(repo_name, archive_path)
            spinner.update(task, completed=True)

        ui.print_step_progress(5, 5, "Updating metadata ledger")

        # Check for signing key
        signature = None
        try:
            from termbackup import signing

            if signing.has_signing_key():
                sig_bytes = signing.sign_archive(archive_path, password)
                signature = sig_bytes.hex()
        except Exception as e:
            ui.warning(f"Signing skipped: {e}")

        with ui.create_spinner() as spinner:
            task = spinner.add_task("Updating ledger")
            ledger.append_entry(repo_name, manifest_data, archive_path, commit_sha, signature=signature)
            spinner.update(task, completed=True)

        # Upload manifest for incremental chain
        if backup_mode == "incremental":
            ui.step("Uploading manifest for incremental chain...")
            github.upload_manifest(
                repo_name, backup_id,
                json.dumps(manifest_data.model_dump(mode="json"), indent=2),
            )

        # Send webhook notification if configured
        if profile.webhook_url:
            try:
                from termbackup import webhooks

                webhooks.send_notification(
                    profile.webhook_url,
                    "backup_complete",
                    profile_name,
                    {
                        "backup_id": backup_id[:12],
                        "files": file_count,
                        "size": format_size(archive_size),
                    },
                )
            except Exception as e:
                ui.warning(f"Webhook notification failed: {e}")

        # Audit log
        audit.log_operation("backup", profile_name, "success", {
            "backup_id": backup_id[:12],
            "file_count": file_count,
            "archive_size": archive_size,
        })
    except Exception as e:
        audit.log_operation("backup", profile_name, "failure", {"error": str(e)})
        raise
    finally:
        # 5. Clean up temp archive regardless of success or failure
        if archive_path.exists():
            archive_path.unlink()

    ui.print_summary_panel("Backup Complete", [
        ("Backup ID", backup_id[:12]),
        ("Files", f"{file_count} ({format_size(total_size)})"),
        ("Archive", f"{format_size(archive_size)} compressed"),
        ("Encryption", "AES-256-GCM + Argon2id"),
        ("Commit", commit_sha[:10]),
        ("Status", "[UPLOADED]"),
    ], style="success")

    # 6. Run rotation if retention policy is configured
    max_backups = profile.max_backups
    retention_days = profile.retention_days
    if max_backups or retention_days:
        _run_rotation(repo_name, max_backups, retention_days, profile_name)

    ui.print_footer()


def _run_rotation(
    repo_name: str,
    max_backups: int | None,
    retention_days: int | None,
    profile_name: str = "",
):
    """Prunes old backups based on retention policy."""
    content, _ = github.get_metadata_content(repo_name)
    if not content:
        return

    ledger_data = json.loads(content)
    backups = ledger_data.get("backups", [])
    to_prune = rotation.compute_backups_to_prune(backups, max_backups, retention_days)

    if not to_prune:
        return

    pruned_ids = []
    ui.step(f"Pruning {len(to_prune)} old backup(s)...")
    for entry in to_prune:
        entry_id = entry.id if hasattr(entry, "id") else entry["id"]
        entry_filename = entry.filename if hasattr(entry, "filename") else entry["filename"]
        try:
            github.delete_blob(repo_name, entry_filename)
            ledger.remove_entry(repo_name, entry_id)
            ui.detail("Removed", entry_filename)
            pruned_ids.append(entry_id[:12])
        except Exception as e:
            ui.warning(f"Failed to prune {entry_filename}: {e}")

    if pruned_ids and profile_name:
        audit.log_operation("prune", profile_name, "success", {"pruned": pruned_ids})
