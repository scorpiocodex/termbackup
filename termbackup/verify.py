"""Backup integrity verification with checklist UI and audit logging."""

import io
import json
import tarfile
from pathlib import Path

from termbackup import archive, audit, config, github, ledger, ui
from termbackup import manifest as manifest_module
from termbackup.utils import find_backup_in_ledger, hash_file


def verify_backup(profile_name: str, backup_id: str, password: str):
    """Verifies a backup's integrity."""
    ui.print_header("Integrity Verification", icon=ui.Icons.SHIELD)

    profile = config.get_profile(profile_name)
    repo_name = profile.repo

    ui.info(f"Profile: [bold]{profile_name}[/bold]")
    ui.detail("Backup ID", backup_id)

    # 1. Get metadata
    content, _ = github.get_metadata_content(repo_name)
    if not content:
        ui.error(f"No backups found for profile '{profile_name}'.")
        raise SystemExit(1)

    ledger_data = json.loads(content)

    # 2. Find backup in ledger
    backup_info = find_backup_in_ledger(ledger_data, backup_id)
    if not backup_info:
        ui.error(f"Backup '{backup_id}' not found in ledger.")
        raise SystemExit(1)

    archive_filename = backup_info["filename"] if isinstance(backup_info, dict) else backup_info.filename
    ui.detail("Archive", archive_filename)

    # 3. Download archive
    ui.step("Downloading archive...")
    temp_dir = Path(config.CONFIG_DIR / "tmp")
    temp_dir.mkdir(exist_ok=True)
    archive_path = temp_dir / archive_filename

    check_results = []

    try:
        with ui.create_spinner() as spinner:
            task = spinner.add_task("Downloading")
            github.download_blob(repo_name, archive_filename, archive_path)
            spinner.update(task, completed=True)

        ui.console.print()

        # 4. Verify SHA256
        ui.step("Verifying SHA-256 checksum...")
        local_sha256 = hash_file(archive_path)
        remote_sha256 = backup_info["sha256"] if isinstance(backup_info, dict) else backup_info.sha256
        if local_sha256 != remote_sha256:
            check_results.append(("SHA-256 Checksum", False, "Mismatch — archive may be tampered"))
            ui.print_checklist(check_results)
            audit.log_operation("verify", profile_name, "failure", {"check": "sha256_mismatch"})
            raise SystemExit(1)
        check_results.append(("SHA-256 Checksum", True, "Verified"))

        # 5. Verify HMAC/GCM and decrypt
        ui.step("Verifying encryption and decrypting...")
        try:
            header = archive.read_archive_header(archive_path)
            payload = archive.read_archive_payload(archive_path, password, header)
            check_results.append(("Encryption Integrity", True, "Verified"))
        except Exception as e:
            check_results.append(("Encryption Integrity", False, f"Failed: {e}"))
            ui.print_checklist(check_results)
            audit.log_operation("verify", profile_name, "failure", {"check": "decryption_failed"})
            raise SystemExit(1)

        # 6. Verify manifest integrity
        ui.step("Verifying manifest integrity...")
        tar_stream = io.BytesIO(payload)
        with tarfile.open(fileobj=tar_stream, mode="r") as tar:
            manifest_member = tar.getmember("manifest.json")
            manifest_file = tar.extractfile(manifest_member)
            if not manifest_file:
                check_results.append(("Manifest Integrity", False, "Manifest not found"))
                ui.print_checklist(check_results)
                raise SystemExit(1)

            manifest_data = json.load(manifest_file)

            # Re-calculate backup ID and compare
            # Reset backup_id to None (the value it had when the ID was originally computed)
            manifest_for_id = dict(manifest_data)
            manifest_for_id["backup_id"] = None
            backup_id_from_manifest = manifest_module.generate_backup_id(manifest_for_id)
            if backup_id_from_manifest != manifest_data["backup_id"]:
                check_results.append(("Manifest Integrity", False, "ID mismatch"))
                ui.print_checklist(check_results)
                audit.log_operation("verify", profile_name, "failure", {"check": "manifest_mismatch"})
                raise SystemExit(1)
            check_results.append(("Manifest Integrity", True, "Verified"))

        # 7. Mark as verified in the ledger
        ui.step("Updating ledger verification status...")
        try:
            ledger.mark_verified(repo_name, backup_id)
            check_results.append(("Ledger Update", True, "Marked as verified"))
        except Exception:
            check_results.append(("Ledger Update", False, "Non-critical: could not update"))

        audit.log_operation("verify", profile_name, "success", {
            "backup_id": backup_id,
            "checks_passed": sum(1 for _, p, _ in check_results if p),
        })
    finally:
        if archive_path.exists():
            archive_path.unlink()

    ui.console.print()
    ui.print_checklist(check_results)
    passed = sum(1 for _, p, _ in check_results if p)
    total = len(check_results)

    ui.print_summary_panel("Verification Complete", [
        ("Backup ID", backup_id[:12] if len(backup_id) > 12 else backup_id),
        ("Checks", f"{passed}/{total} passed"),
        ("Archive Version", f"v{header.version}"),
        ("Encryption", "AES-256-GCM + Argon2id" if header.version == 2 else "AES-256-CBC + PBKDF2"),
    ], style="success" if passed == total else "warning")
    ui.print_footer()
