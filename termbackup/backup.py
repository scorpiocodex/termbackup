"""Backup creation for TermBackup.

Handles scanning, compression, and encryption of backup archives.
"""

import gzip
import io
import json
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from .config import Config, Profile
from .crypto import encrypt_data, secure_delete
from .github import GitHubClient, GitHubError
from .utils import (
    calculate_data_hash,
    calculate_file_hash,
    create_temp_file,
    format_size,
    generate_backup_name,
    get_file_info,
    scan_directory,
)


class BackupError(Exception):
    """Raised when backup operations fail."""


@dataclass
class FileEntry:
    """Information about a file to be backed up."""

    path: Path
    relative_path: str
    size: int
    modified: float
    hash: str


@dataclass
class BackupManifest:
    """Manifest describing backup contents."""

    backup_name: str
    profile_name: str
    source_directory: str
    file_count: int
    total_size: int
    compressed_size: int
    encrypted_size: int
    files: list[dict]
    checksum: str

    def to_dict(self) -> dict:
        """Convert manifest to dictionary."""
        return {
            "backup_name": self.backup_name,
            "profile_name": self.profile_name,
            "source_directory": self.source_directory,
            "file_count": self.file_count,
            "total_size": self.total_size,
            "compressed_size": self.compressed_size,
            "encrypted_size": self.encrypted_size,
            "files": self.files,
            "checksum": self.checksum,
        }

    def to_json(self) -> str:
        """Convert manifest to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "BackupManifest":
        """Create manifest from dictionary."""
        return cls(
            backup_name=data["backup_name"],
            profile_name=data["profile_name"],
            source_directory=data["source_directory"],
            file_count=data["file_count"],
            total_size=data["total_size"],
            compressed_size=data["compressed_size"],
            encrypted_size=data["encrypted_size"],
            files=data["files"],
            checksum=data["checksum"],
        )


def scan_files(profile: Profile) -> list[FileEntry]:
    """Scan source directory for files to backup.

    Args:
        profile: Backup profile.

    Returns:
        List of FileEntry objects.

    Raises:
        BackupError: If scanning fails.
    """
    source_path = profile.get_source_path()

    if not source_path.exists():
        raise BackupError(f"Source directory does not exist: {source_path}")

    if not source_path.is_dir():
        raise BackupError(f"Source path is not a directory: {source_path}")

    entries = []
    for file_path in scan_directory(source_path, profile.exclude_patterns):
        try:
            info = get_file_info(file_path)
            relative = file_path.relative_to(source_path)
            entries.append(
                FileEntry(
                    path=file_path,
                    relative_path=str(relative),
                    size=info["size"],
                    modified=info["modified"],
                    hash=info["hash"],
                )
            )
        except (OSError, IOError) as e:
            raise BackupError(f"Failed to read file {file_path}: {e}") from e

    return entries


def create_archive(
    files: list[FileEntry],
    source_dir: Path,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> bytes:
    """Create a compressed tar archive of files.

    Args:
        files: List of FileEntry objects.
        source_dir: Source directory path.
        progress_callback: Optional callback for progress updates.

    Returns:
        Compressed archive as bytes.
    """
    buffer = io.BytesIO()
    total_files = len(files)

    with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=6) as gz:
        with tarfile.open(fileobj=gz, mode="w") as tar:
            for i, entry in enumerate(files):
                tar.add(entry.path, arcname=entry.relative_path)
                if progress_callback:
                    progress_callback(i + 1, total_files)

    return buffer.getvalue()


def create_backup(
    profile: Profile,
    password: str,
    dry_run: bool = False,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> tuple[Optional[bytes], BackupManifest]:
    """Create an encrypted backup.

    Args:
        profile: Backup profile.
        password: Encryption password.
        dry_run: If True, don't create actual backup, just return manifest.
        progress_callback: Optional callback with (stage, current, total).

    Returns:
        Tuple of (encrypted_data or None, manifest).

    Raises:
        BackupError: If backup creation fails.
    """
    backup_name = generate_backup_name()
    source_dir = profile.get_source_path()

    if progress_callback:
        progress_callback("scan", 0, 0)

    files = scan_files(profile)

    if not files:
        raise BackupError("No files to backup")

    total_size = sum(f.size for f in files)
    file_count = len(files)

    file_list = [
        {
            "path": f.relative_path,
            "size": f.size,
            "hash": f.hash,
        }
        for f in files
    ]

    if dry_run:
        manifest = BackupManifest(
            backup_name=backup_name,
            profile_name=profile.name,
            source_directory=str(source_dir),
            file_count=file_count,
            total_size=total_size,
            compressed_size=0,
            encrypted_size=0,
            files=file_list,
            checksum="",
        )
        return None, manifest

    if progress_callback:
        progress_callback("compress", 0, file_count)

    def compress_progress(current: int, total: int) -> None:
        if progress_callback:
            progress_callback("compress", current, total)

    archive_data = create_archive(files, source_dir, compress_progress)
    compressed_size = len(archive_data)

    if progress_callback:
        progress_callback("encrypt", 0, 1)

    manifest_data = {
        "backup_name": backup_name,
        "profile_name": profile.name,
        "source_directory": str(source_dir),
        "file_count": file_count,
        "total_size": total_size,
        "compressed_size": compressed_size,
        "files": file_list,
    }
    manifest_json = json.dumps(manifest_data).encode("utf-8")

    header_size = len(manifest_json).to_bytes(4, "big")
    payload = header_size + manifest_json + archive_data

    checksum = calculate_data_hash(payload)
    encrypted_data = encrypt_data(payload, password)
    encrypted_size = len(encrypted_data)

    if progress_callback:
        progress_callback("encrypt", 1, 1)

    manifest = BackupManifest(
        backup_name=backup_name,
        profile_name=profile.name,
        source_directory=str(source_dir),
        file_count=file_count,
        total_size=total_size,
        compressed_size=compressed_size,
        encrypted_size=encrypted_size,
        files=file_list,
        checksum=checksum,
    )

    return encrypted_data, manifest


def run_backup(
    config: Config,
    profile: Profile,
    password: str,
    dry_run: bool = False,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> BackupManifest:
    """Run full backup workflow: create, encrypt, and upload.

    Args:
        config: TermBackup configuration.
        profile: Backup profile.
        password: Encryption password.
        dry_run: If True, don't upload, just preview.
        progress_callback: Optional callback with (stage, current, total).

    Returns:
        Backup manifest.

    Raises:
        BackupError: If backup fails.
        GitHubError: If upload fails.
    """
    encrypted_data, manifest = create_backup(
        profile, password, dry_run, progress_callback
    )

    if dry_run:
        return manifest

    if not encrypted_data:
        raise BackupError("Failed to create encrypted backup")

    temp_file = None
    try:
        temp_file = create_temp_file(suffix=".tbk")
        temp_file.write_bytes(encrypted_data)

        if progress_callback:
            progress_callback("upload", 0, manifest.encrypted_size)

        client = GitHubClient(config)

        def upload_progress(current: int, total: int) -> None:
            if progress_callback:
                progress_callback("upload", current, total)

        client.upload_backup(manifest.backup_name, encrypted_data, upload_progress)

        if progress_callback:
            progress_callback("upload", manifest.encrypted_size, manifest.encrypted_size)

    finally:
        if temp_file and temp_file.exists():
            secure_delete(temp_file)

    return manifest
