"""Restore functionality for TermBackup.

Handles downloading, decrypting, and restoring backup archives.
"""

import gzip
import io
import json
import shutil
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from .backup import BackupManifest
from .config import Config
from .crypto import CryptoError, decrypt_data, secure_delete
from .github import GitHubClient, GitHubError
from .utils import (
    calculate_data_hash,
    create_temp_directory,
    create_temp_file,
    normalize_backup_id,
)


class RestoreError(Exception):
    """Raised when restore operations fail."""


@dataclass
class RestorePreview:
    """Preview information for a restore operation."""

    backup_name: str
    profile_name: str
    source_directory: str
    file_count: int
    total_size: int
    files: list[str]


def download_backup(
    config: Config,
    backup_id: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> bytes:
    """Download encrypted backup from GitHub.

    Args:
        config: TermBackup configuration.
        backup_id: Backup identifier.
        progress_callback: Optional callback for progress updates.

    Returns:
        Encrypted backup data.

    Raises:
        RestoreError: If download fails.
    """
    backup_name = normalize_backup_id(backup_id)

    try:
        client = GitHubClient(config)
        return client.download_backup(backup_name, progress_callback)
    except GitHubError as e:
        raise RestoreError(f"Failed to download backup: {e}") from e


def decrypt_backup(encrypted_data: bytes, password: str) -> tuple[dict, bytes]:
    """Decrypt backup and extract manifest and archive.

    Args:
        encrypted_data: Encrypted backup data.
        password: Decryption password.

    Returns:
        Tuple of (manifest_dict, archive_bytes).

    Raises:
        RestoreError: If decryption fails.
    """
    try:
        decrypted = decrypt_data(encrypted_data, password)
    except CryptoError as e:
        raise RestoreError(f"Decryption failed: {e}") from e

    if len(decrypted) < 4:
        raise RestoreError("Invalid backup format: too short")

    header_size = int.from_bytes(decrypted[:4], "big")

    if len(decrypted) < 4 + header_size:
        raise RestoreError("Invalid backup format: manifest truncated")

    manifest_json = decrypted[4 : 4 + header_size]
    archive_data = decrypted[4 + header_size :]

    try:
        manifest = json.loads(manifest_json.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise RestoreError(f"Invalid manifest: {e}") from e

    return manifest, archive_data


def extract_archive(
    archive_data: bytes,
    dest_dir: Path,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> list[str]:
    """Extract compressed tar archive to destination.

    Args:
        archive_data: Gzip-compressed tar archive.
        dest_dir: Destination directory.
        progress_callback: Optional callback for progress updates.

    Returns:
        List of extracted file paths.

    Raises:
        RestoreError: If extraction fails.
    """
    extracted_files = []

    try:
        buffer = io.BytesIO(archive_data)
        with gzip.GzipFile(fileobj=buffer, mode="rb") as gz:
            with tarfile.open(fileobj=gz, mode="r") as tar:
                members = tar.getmembers()
                total = len(members)

                for i, member in enumerate(members):
                    if member.name.startswith("/") or ".." in member.name:
                        raise RestoreError(
                            f"Invalid archive: unsafe path {member.name}"
                        )

                    tar.extract(member, dest_dir)
                    extracted_files.append(member.name)

                    if progress_callback:
                        progress_callback(i + 1, total)

    except (gzip.BadGzipFile, tarfile.TarError) as e:
        raise RestoreError(f"Failed to extract archive: {e}") from e

    return extracted_files


def get_restore_preview(
    config: Config,
    backup_id: str,
    password: str,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> RestorePreview:
    """Get preview of restore operation without extracting files.

    Args:
        config: TermBackup configuration.
        backup_id: Backup identifier.
        password: Decryption password.
        progress_callback: Optional callback with (stage, current, total).

    Returns:
        RestorePreview object.

    Raises:
        RestoreError: If preview fails.
    """
    if progress_callback:
        progress_callback("download", 0, 0)

    encrypted_data = download_backup(config, backup_id)

    if progress_callback:
        progress_callback("decrypt", 0, 1)

    manifest, _ = decrypt_backup(encrypted_data, password)

    if progress_callback:
        progress_callback("decrypt", 1, 1)

    return RestorePreview(
        backup_name=manifest["backup_name"],
        profile_name=manifest["profile_name"],
        source_directory=manifest["source_directory"],
        file_count=manifest["file_count"],
        total_size=manifest["total_size"],
        files=[f["path"] for f in manifest["files"]],
    )


def restore_backup(
    config: Config,
    backup_id: str,
    password: str,
    dest_dir: Optional[Path] = None,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> tuple[RestorePreview, list[str]]:
    """Restore backup to destination directory.

    Args:
        config: TermBackup configuration.
        backup_id: Backup identifier.
        password: Decryption password.
        dest_dir: Destination directory (uses original source if None).
        progress_callback: Optional callback with (stage, current, total).

    Returns:
        Tuple of (preview, list of restored file paths).

    Raises:
        RestoreError: If restore fails.
    """
    temp_dir = None
    temp_file = None

    try:
        if progress_callback:
            progress_callback("download", 0, 0)

        encrypted_data = download_backup(config, backup_id)

        temp_file = create_temp_file(suffix=".tbk")
        temp_file.write_bytes(encrypted_data)

        if progress_callback:
            progress_callback("decrypt", 0, 1)

        manifest, archive_data = decrypt_backup(encrypted_data, password)

        if progress_callback:
            progress_callback("decrypt", 1, 1)

        preview = RestorePreview(
            backup_name=manifest["backup_name"],
            profile_name=manifest["profile_name"],
            source_directory=manifest["source_directory"],
            file_count=manifest["file_count"],
            total_size=manifest["total_size"],
            files=[f["path"] for f in manifest["files"]],
        )

        if dest_dir is None:
            dest_dir = Path(manifest["source_directory"])

        dest_dir = dest_dir.expanduser().resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            progress_callback("extract", 0, preview.file_count)

        def extract_progress(current: int, total: int) -> None:
            if progress_callback:
                progress_callback("extract", current, total)

        temp_dir = create_temp_directory()
        extracted_files = extract_archive(archive_data, temp_dir, extract_progress)

        if progress_callback:
            progress_callback("restore", 0, len(extracted_files))

        restored_files = []
        for i, rel_path in enumerate(extracted_files):
            src = temp_dir / rel_path
            dst = dest_dir / rel_path

            dst.parent.mkdir(parents=True, exist_ok=True)

            if src.is_file():
                shutil.copy2(src, dst)
                restored_files.append(str(dst))

            if progress_callback:
                progress_callback("restore", i + 1, len(extracted_files))

        return preview, restored_files

    finally:
        if temp_file and temp_file.exists():
            secure_delete(temp_file)
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def verify_restore_integrity(
    manifest: dict,
    dest_dir: Path,
) -> tuple[bool, list[str]]:
    """Verify restored files match manifest checksums.

    Args:
        manifest: Backup manifest dictionary.
        dest_dir: Destination directory where files were restored.

    Returns:
        Tuple of (all_valid, list of error messages).
    """
    from .utils import calculate_file_hash

    errors = []

    for file_info in manifest["files"]:
        file_path = dest_dir / file_info["path"]

        if not file_path.exists():
            errors.append(f"Missing file: {file_info['path']}")
            continue

        expected_hash = file_info.get("hash")
        if expected_hash:
            actual_hash = calculate_file_hash(file_path)
            if actual_hash != expected_hash:
                errors.append(
                    f"Hash mismatch: {file_info['path']} "
                    f"(expected {expected_hash[:8]}..., got {actual_hash[:8]}...)"
                )

    return len(errors) == 0, errors
