"""Utility functions for TermBackup."""

import fnmatch
import hashlib
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional


BACKUP_EXTENSION = ".tbk"
BACKUP_NAME_PATTERN = re.compile(r"^backup_(\d{8}_\d{6})\.tbk$")

DEFAULT_EXCLUDES = [
    ".git/",
    ".git\\",
    "__pycache__/",
    "__pycache__\\",
    "node_modules/",
    "node_modules\\",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
    "Thumbs.db",
]


def generate_backup_name() -> str:
    """Generate a deterministic backup filename based on current UTC timestamp.

    Returns:
        Filename in format: backup_YYYYMMDD_HHMMSS.tbk
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"backup_{timestamp}{BACKUP_EXTENSION}"


def parse_backup_name(filename: str) -> Optional[datetime]:
    """Parse backup filename and return the timestamp.

    Args:
        filename: Backup filename to parse.

    Returns:
        Datetime object if valid, None otherwise.
    """
    match = BACKUP_NAME_PATTERN.match(filename)
    if not match:
        return None

    timestamp_str = match.group(1)
    try:
        return datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


def calculate_file_hash(path: Path, algorithm: str = "sha256") -> str:
    """Calculate hash of a file.

    Args:
        path: Path to file.
        algorithm: Hash algorithm (default: sha256).

    Returns:
        Hex digest of file hash.
    """
    hasher = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def calculate_data_hash(data: bytes, algorithm: str = "sha256") -> str:
    """Calculate hash of bytes data.

    Args:
        data: Bytes to hash.
        algorithm: Hash algorithm (default: sha256).

    Returns:
        Hex digest of hash.
    """
    hasher = hashlib.new(algorithm)
    hasher.update(data)
    return hasher.hexdigest()


def format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Human-readable size string.
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def matches_pattern(path: Path, pattern: str) -> bool:
    """Check if path matches a glob pattern.

    Args:
        path: Path to check.
        pattern: Glob pattern.

    Returns:
        True if path matches pattern.
    """
    path_str = str(path)
    path_parts = path.parts

    if pattern.endswith("/") or pattern.endswith("\\"):
        dir_name = pattern.rstrip("/\\")
        return dir_name in path_parts

    return fnmatch.fnmatch(path.name, pattern) or fnmatch.fnmatch(path_str, pattern)


def should_exclude(path: Path, exclude_patterns: list[str]) -> bool:
    """Check if path should be excluded based on patterns.

    Args:
        path: Path to check.
        exclude_patterns: List of glob patterns.

    Returns:
        True if path should be excluded.
    """
    all_patterns = DEFAULT_EXCLUDES + exclude_patterns

    for pattern in all_patterns:
        if matches_pattern(path, pattern):
            return True
    return False


def scan_directory(
    directory: Path, exclude_patterns: Optional[list[str]] = None
) -> Iterator[Path]:
    """Scan directory recursively, yielding files not matching exclusions.

    Args:
        directory: Directory to scan.
        exclude_patterns: Additional patterns to exclude.

    Yields:
        Path objects for files to include.
    """
    exclude_patterns = exclude_patterns or []

    for item in directory.rglob("*"):
        if item.is_file():
            relative = item.relative_to(directory)
            if not should_exclude(relative, exclude_patterns):
                yield item


def get_file_info(path: Path) -> dict:
    """Get file metadata.

    Args:
        path: Path to file.

    Returns:
        Dictionary with size, modified timestamp, and hash.
    """
    stat = path.stat()
    return {
        "size": stat.st_size,
        "modified": stat.st_mtime,
        "hash": calculate_file_hash(path),
    }


def create_temp_file(suffix: str = "", prefix: str = "termbackup_") -> Path:
    """Create a temporary file and return its path.

    Args:
        suffix: File suffix.
        prefix: File prefix.

    Returns:
        Path to temporary file.
    """
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
    import os

    os.close(fd)
    return Path(path)


def create_temp_directory(prefix: str = "termbackup_") -> Path:
    """Create a temporary directory and return its path.

    Args:
        prefix: Directory prefix.

    Returns:
        Path to temporary directory.
    """
    return Path(tempfile.mkdtemp(prefix=prefix))


def validate_backup_id(backup_id: str) -> bool:
    """Validate backup ID format.

    Args:
        backup_id: Backup identifier to validate.

    Returns:
        True if valid format.
    """
    if backup_id.endswith(BACKUP_EXTENSION):
        return BACKUP_NAME_PATTERN.match(backup_id) is not None
    return BACKUP_NAME_PATTERN.match(f"{backup_id}{BACKUP_EXTENSION}") is not None


def normalize_backup_id(backup_id: str) -> str:
    """Normalize backup ID to include extension.

    Args:
        backup_id: Backup identifier.

    Returns:
        Backup ID with .tbk extension.
    """
    if not backup_id.endswith(BACKUP_EXTENSION):
        return f"{backup_id}{BACKUP_EXTENSION}"
    return backup_id
