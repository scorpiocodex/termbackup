"""Backup restoration with Pydantic models and audit logging."""

import io
import json
import tarfile
from pathlib import Path

from termbackup import archive, audit, config, github, ui
from termbackup.utils import find_backup_in_ledger, format_size, is_path_safe


def _collect_parent_chain(repo_name, ledger_data, parent_id, password):
    """Traverses the incremental parent chain and returns payloads (oldest first)."""
    payloads = []
    current_id = parent_id

    while current_id:
        backup_info = find_backup_in_ledger(ledger_data, current_id)
        if not backup_info:
            ui.warning(f"Parent backup {current_id[:12]} not found — restoring partial chain")
            break

        filename = backup_info["filename"] if isinstance(backup_info, dict) else backup_info.filename
        ui.step(f"Downloading parent archive {filename}...")
        temp_dir = Path(config.CONFIG_DIR / "tmp")
        temp_dir.mkdir(exist_ok=True)
        parent_path = temp_dir / filename

        try:
            github.download_blob(repo_name, filename, parent_path)
            header = archive.read_archive_header(parent_path)
            payload = archive.read_archive_payload(parent_path, password, header)
            payloads.append(payload)

            # Check if this parent is also incremental
            tar_stream = io.BytesIO(payload)
            with tarfile.open(fileobj=tar_stream, mode="r") as tar:
                mf = tar.extractfile(tar.getmember("manifest.json"))
                if mf:
                    m_data = json.load(mf)
                    current_id = m_data.get("parent_backup_id")
                else:
                    current_id = None
        finally:
            if parent_path.exists():
                parent_path.unlink()

    # Reverse so full backup is first
    payloads.reverse()
    return payloads


def restore_backup(profile_name: str, backup_id: str, password: str, dry_run: bool):
    """Restores a backup."""
    ui.print_header("Restore Operation", icon=ui.Icons.LOCK)

    profile = config.get_profile(profile_name)
    repo_name = profile.repo

    ui.print_step_progress(1, 4, "Locating backup")
    ui.detail("Backup ID", backup_id)

    # 1. Get metadata
    content, _ = github.get_metadata_content(repo_name)
    if not content:
        ui.error(f"No backups found for profile '{profile_name}'.")
        raise SystemExit(1)

    ledger_data = json.loads(content)

    # 2. Find backup
    backup_info = find_backup_in_ledger(ledger_data, backup_id)
    if not backup_info:
        ui.error(f"Backup '{backup_id}' not found in ledger.")
        raise SystemExit(1)

    archive_filename = backup_info["filename"] if isinstance(backup_info, dict) else backup_info.filename
    ui.detail("Archive", archive_filename)

    # 3. Download archive
    ui.print_step_progress(2, 4, "Downloading archive")
    temp_dir = Path(config.CONFIG_DIR / "tmp")
    temp_dir.mkdir(exist_ok=True)
    archive_path = temp_dir / archive_filename

    try:
        with ui.create_spinner() as spinner:
            task = spinner.add_task("Downloading")
            github.download_blob(repo_name, archive_filename, archive_path)
            spinner.update(task, completed=True)

        # 4. Decrypt and extract
        ui.print_step_progress(3, 4, "Decrypting archive")
        with ui.create_spinner() as spinner:
            task = spinner.add_task("Decrypting")
            header = archive.read_archive_header(archive_path)
            payload = archive.read_archive_payload(archive_path, password, header)
            spinner.update(task, completed=True)

        # Collect all payloads (for incremental: full chain; for full: just this one)
        payloads = [payload]
        tar_stream = io.BytesIO(payload)
        with tarfile.open(fileobj=tar_stream, mode="r") as tar:
            manifest_member = tar.getmember("manifest.json")
            manifest_file = tar.extractfile(manifest_member)
            if not manifest_file:
                ui.error("Manifest not found in archive.")
                raise SystemExit(1)
            manifest_data = json.load(manifest_file)

        # If incremental, traverse the parent chain
        if manifest_data.get("backup_mode") == "incremental" and manifest_data.get("parent_backup_id"):
            parent_payloads = _collect_parent_chain(
                repo_name, ledger_data, manifest_data["parent_backup_id"], password
            )
            payloads = parent_payloads + payloads

        # Gather all members from all payloads
        all_members_and_tars = []
        for p in payloads:
            ts = io.BytesIO(p)
            tf = tarfile.open(fileobj=ts, mode="r")
            members = [m for m in tf.getmembers() if m.name != "manifest.json"]
            all_members_and_tars.append((tf, members))

        if dry_run:
            ui.console.print()
            ui.warning("Dry run — files that would be restored:")
            table = ui.create_table("File", "Size")
            for _tf, members in all_members_and_tars:
                for member in members:
                    table.add_row(member.name, format_size(member.size))
            ui.print_table(table)
            total = sum(len(m) for _, m in all_members_and_tars)
            ui.info(f"Total: {total} file(s)")
            for tf, _ in all_members_and_tars:
                tf.close()
            ui.print_footer()
            return

        # Restore files from all archives (full first, then incrementals overlay)
        ui.print_step_progress(4, 4, "Restoring files")
        source_dir = Path(profile.source_dir)
        restored = 0
        skipped = 0

        for tf, members in all_members_and_tars:
            for member in members:
                if not is_path_safe(member.name, source_dir):
                    ui.warning(f"Skipped unsafe path: {member.name}")
                    skipped += 1
                    continue

                target_path = source_dir / member.name

                if target_path.exists():
                    if not ui.confirm(f"Overwrite '{member.name}'?"):
                        skipped += 1
                        continue

                target_path.parent.mkdir(parents=True, exist_ok=True)
                tf.extract(member, path=source_dir, set_attrs=True)
                restored += 1
            tf.close()

        audit.log_operation("restore", profile_name, "success", {
            "backup_id": backup_id,
            "files_restored": restored,
        })
    except SystemExit:
        raise
    except Exception as e:
        audit.log_operation("restore", profile_name, "failure", {"error": str(e)})
        raise
    finally:
        if archive_path.exists():
            archive_path.unlink()

    ui.print_summary_panel("Restore Complete", [
        ("Backup ID", backup_id[:12] if len(backup_id) > 12 else backup_id),
        ("Restored", f"{restored} file(s)"),
        ("Skipped", f"{skipped} file(s)"),
        ("Destination", str(source_dir)),
    ], style="success")
    ui.print_footer()
