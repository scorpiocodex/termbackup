"""Key rotation — re-encrypts all backups with a new password."""

import json
from pathlib import Path

from termbackup import archive, audit, config, github, ui


def rotate_key(profile_name: str, old_password: str, new_password: str) -> None:
    """Re-encrypts all backups for a profile with a new password.

    1. Fetches the ledger and iterates all backups.
    2. For each: download -> decrypt (auto v1/v2) -> re-encrypt (always v2) -> upload -> update ledger.
    3. Deletes old archives after successful re-upload.
    """
    ui.print_header("Key Rotation", icon=ui.Icons.LOCK)

    profile = config.get_profile(profile_name)
    repo_name = profile.repo

    ui.info(f"Profile: [bold]{profile_name}[/bold]")
    ui.detail("Repository", repo_name)

    content, _ = github.get_metadata_content(repo_name)
    if not content:
        ui.error("No backups found.")
        raise SystemExit(1)

    ledger_data = json.loads(content)
    backups = ledger_data.get("backups", [])

    if not backups:
        ui.error("No backups to rotate.")
        raise SystemExit(1)

    ui.info(f"Re-encrypting {len(backups)} backup(s)...")

    temp_dir = Path(config.CONFIG_DIR / "tmp")
    temp_dir.mkdir(exist_ok=True)
    re_encrypted = 0

    try:
        for i, backup_entry in enumerate(backups, 1):
            filename = backup_entry["filename"]
            ui.print_step_progress(i, len(backups), f"Processing {filename}")

            old_path = temp_dir / filename
            new_path = temp_dir / f"new_{filename}"

            try:
                # Download
                github.download_blob(repo_name, filename, old_path)

                # Decrypt (auto v1/v2)
                header = archive.read_archive_header(old_path)
                payload = archive.read_archive_payload(old_path, old_password, header)

                # Re-encrypt as v2 (write payload directly)
                import gzip
                import io

                from termbackup import crypto

                # payload is already the decompressed tar — re-gzip it
                gzipped = io.BytesIO()
                with gzip.GzipFile(fileobj=gzipped, mode="wb") as gz:
                    gz.write(payload)
                gzipped_data = gzipped.getvalue()

                salt, nonce, ciphertext = crypto.encrypt_v2(gzipped_data, new_password)

                import struct

                with open(new_path, "wb") as f:
                    f.write(b"TBK2")
                    f.write(struct.pack("!B", 2))
                    f.write(struct.pack("!B", 0x02))
                    f.write(struct.pack("!I", crypto.ARGON2_MEMORY_COST))
                    f.write(struct.pack("!H", crypto.ARGON2_TIME_COST))
                    f.write(struct.pack("!B", crypto.ARGON2_PARALLELISM))
                    f.write(struct.pack("!B", len(salt)))
                    f.write(salt)
                    f.write(struct.pack("!B", len(nonce)))
                    f.write(nonce)
                    f.write(struct.pack("!B", 0x02))
                    f.write(struct.pack("!Q", len(ciphertext)))
                    f.write(ciphertext)

                # Upload new archive
                github.upload_blob(repo_name, new_path)

                # Delete old archive from GitHub
                try:
                    github.delete_blob(repo_name, filename)
                except Exception as e:
                    ui.warning(f"Could not delete old archive {filename}: {e}")

                re_encrypted += 1
            finally:
                if old_path.exists():
                    old_path.unlink()
                if new_path.exists():
                    new_path.unlink()

        audit.log_operation("rotate-key", profile_name, "success", {
            "re_encrypted": re_encrypted,
        })
    except Exception as e:
        audit.log_operation("rotate-key", profile_name, "failure", {"error": str(e)})
        raise

    ui.print_summary_panel("Key Rotation Complete", [
        ("Profile", profile_name),
        ("Re-encrypted", f"{re_encrypted} backup(s)"),
        ("New Encryption", "AES-256-GCM + Argon2id"),
    ], style="success")
    ui.print_footer()
