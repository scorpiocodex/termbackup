"""Backup verification for TermBackup.

Handles integrity verification of encrypted backups.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from .config import Config
from .crypto import CryptoError, secure_delete
from .github import GitHubClient, GitHubError
from .restore import decrypt_backup, download_backup
from .utils import calculate_data_hash, create_temp_file, normalize_backup_id


class VerifyError(Exception):
    """Raised when verification operations fail."""


@dataclass
class VerifyResult:
    """Result of backup verification."""

    backup_name: str
    is_valid: bool
    can_decrypt: bool
    manifest_valid: bool
    archive_valid: bool
    file_count: int
    total_size: int
    errors: list[str]


def verify_backup(
    config: Config,
    backup_id: str,
    password: str,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> VerifyResult:
    """Verify backup integrity.

    Downloads and attempts to decrypt backup to verify it's valid.
    Does not extract files to filesystem.

    Args:
        config: TermBackup configuration.
        backup_id: Backup identifier.
        password: Decryption password.
        progress_callback: Optional callback with (stage, current, total).

    Returns:
        VerifyResult object.
    """
    backup_name = normalize_backup_id(backup_id)
    errors = []
    can_decrypt = False
    manifest_valid = False
    archive_valid = False
    file_count = 0
    total_size = 0

    temp_file = None

    try:
        if progress_callback:
            progress_callback("download", 0, 0)

        try:
            encrypted_data = download_backup(config, backup_id)
        except Exception as e:
            errors.append(f"Download failed: {e}")
            return VerifyResult(
                backup_name=backup_name,
                is_valid=False,
                can_decrypt=False,
                manifest_valid=False,
                archive_valid=False,
                file_count=0,
                total_size=0,
                errors=errors,
            )

        temp_file = create_temp_file(suffix=".tbk")
        temp_file.write_bytes(encrypted_data)

        if progress_callback:
            progress_callback("decrypt", 0, 1)

        try:
            manifest, archive_data = decrypt_backup(encrypted_data, password)
            can_decrypt = True
        except CryptoError as e:
            errors.append(f"Decryption failed: {e}")
            return VerifyResult(
                backup_name=backup_name,
                is_valid=False,
                can_decrypt=False,
                manifest_valid=False,
                archive_valid=False,
                file_count=0,
                total_size=0,
                errors=errors,
            )
        except Exception as e:
            errors.append(f"Decryption error: {e}")
            return VerifyResult(
                backup_name=backup_name,
                is_valid=False,
                can_decrypt=False,
                manifest_valid=False,
                archive_valid=False,
                file_count=0,
                total_size=0,
                errors=errors,
            )

        if progress_callback:
            progress_callback("decrypt", 1, 1)

        if progress_callback:
            progress_callback("verify", 0, 2)

        required_fields = [
            "backup_name",
            "profile_name",
            "source_directory",
            "file_count",
            "total_size",
            "files",
        ]

        missing_fields = [f for f in required_fields if f not in manifest]
        if missing_fields:
            errors.append(f"Manifest missing fields: {', '.join(missing_fields)}")
        else:
            manifest_valid = True
            file_count = manifest["file_count"]
            total_size = manifest["total_size"]

            if len(manifest["files"]) != file_count:
                errors.append(
                    f"File count mismatch: manifest says {file_count}, "
                    f"but contains {len(manifest['files'])} entries"
                )
                manifest_valid = False

        if progress_callback:
            progress_callback("verify", 1, 2)

        import gzip
        import io
        import tarfile

        try:
            buffer = io.BytesIO(archive_data)
            with gzip.GzipFile(fileobj=buffer, mode="rb") as gz:
                with tarfile.open(fileobj=gz, mode="r") as tar:
                    members = tar.getmembers()

                    for member in members:
                        if member.name.startswith("/") or ".." in member.name:
                            errors.append(f"Unsafe path in archive: {member.name}")
                            break
                    else:
                        archive_valid = True

                        if manifest_valid:
                            manifest_paths = {
                                f["path"].replace("\\", "/") for f in manifest["files"]
                            }
                            archive_paths = {
                                m.name.replace("\\", "/") for m in members if m.isfile()
                            }

                            missing = manifest_paths - archive_paths
                            extra = archive_paths - manifest_paths

                            if missing:
                                errors.append(
                                    f"Files in manifest but not archive: "
                                    f"{len(missing)} files"
                                )
                            if extra:
                                errors.append(
                                    f"Files in archive but not manifest: "
                                    f"{len(extra)} files"
                                )

        except (gzip.BadGzipFile, tarfile.TarError) as e:
            errors.append(f"Archive corrupted: {e}")
            archive_valid = False

        if progress_callback:
            progress_callback("verify", 2, 2)

        is_valid = can_decrypt and manifest_valid and archive_valid and len(errors) == 0

        return VerifyResult(
            backup_name=backup_name,
            is_valid=is_valid,
            can_decrypt=can_decrypt,
            manifest_valid=manifest_valid,
            archive_valid=archive_valid,
            file_count=file_count,
            total_size=total_size,
            errors=errors,
        )

    finally:
        if temp_file and temp_file.exists():
            secure_delete(temp_file)


def quick_verify(config: Config, backup_id: str) -> bool:
    """Quick verification that backup exists and is accessible.

    Does not check decryption or content validity.

    Args:
        config: TermBackup configuration.
        backup_id: Backup identifier.

    Returns:
        True if backup exists and is accessible.
    """
    backup_name = normalize_backup_id(backup_id)

    try:
        client = GitHubClient(config)
        info = client.get_backup_info(backup_name)
        return info is not None
    except GitHubError:
        return False
