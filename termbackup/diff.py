"""Backup comparison (diff) for TermBackup v2.0."""

from dataclasses import dataclass
from typing import Optional

from .config import Config
from .restore import decrypt_backup, download_backup, RestoreError
from .utils import format_size


class DiffError(Exception):
    """Raised when diff operations fail."""


@dataclass
class FileDiff:
    """Difference information for a single file."""

    path: str
    status: str  # "added", "removed", "modified", "unchanged"
    size_before: Optional[int] = None
    size_after: Optional[int] = None
    hash_before: Optional[str] = None
    hash_after: Optional[str] = None

    @property
    def size_diff(self) -> int:
        """Get size difference."""
        before = self.size_before or 0
        after = self.size_after or 0
        return after - before


@dataclass
class BackupDiff:
    """Comparison result between two backups."""

    backup1_name: str
    backup2_name: str
    backup1_files: int
    backup2_files: int
    backup1_size: int
    backup2_size: int
    added: list[FileDiff]
    removed: list[FileDiff]
    modified: list[FileDiff]
    unchanged: list[FileDiff]

    @property
    def total_changes(self) -> int:
        """Get total number of changes."""
        return len(self.added) + len(self.removed) + len(self.modified)

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return self.total_changes > 0

    @property
    def size_diff(self) -> int:
        """Get total size difference."""
        return self.backup2_size - self.backup1_size

    def summary(self) -> str:
        """Get a summary of changes."""
        parts = []
        if self.added:
            parts.append(f"+{len(self.added)} added")
        if self.removed:
            parts.append(f"-{len(self.removed)} removed")
        if self.modified:
            parts.append(f"~{len(self.modified)} modified")
        if not parts:
            return "No changes"
        return ", ".join(parts)


def get_backup_manifest(config: Config, backup_id: str, password: str) -> dict:
    """Download and decrypt a backup to get its manifest."""
    try:
        encrypted_data = download_backup(config, backup_id)
        manifest, _ = decrypt_backup(encrypted_data, password)
        return manifest
    except RestoreError as e:
        raise DiffError(f"Failed to read backup {backup_id}: {e}") from e


def compare_backups(
    config: Config,
    backup1_id: str,
    backup2_id: str,
    password: str,
) -> BackupDiff:
    """Compare two backups and return the differences."""
    # Get manifests
    manifest1 = get_backup_manifest(config, backup1_id, password)
    manifest2 = get_backup_manifest(config, backup2_id, password)

    # Build file lookups
    files1 = {f["path"]: f for f in manifest1["files"]}
    files2 = {f["path"]: f for f in manifest2["files"]}

    paths1 = set(files1.keys())
    paths2 = set(files2.keys())

    added = []
    removed = []
    modified = []
    unchanged = []

    # Find added files
    for path in paths2 - paths1:
        f = files2[path]
        added.append(
            FileDiff(
                path=path,
                status="added",
                size_after=f["size"],
                hash_after=f.get("hash"),
            )
        )

    # Find removed files
    for path in paths1 - paths2:
        f = files1[path]
        removed.append(
            FileDiff(
                path=path,
                status="removed",
                size_before=f["size"],
                hash_before=f.get("hash"),
            )
        )

    # Find modified and unchanged files
    for path in paths1 & paths2:
        f1 = files1[path]
        f2 = files2[path]

        hash1 = f1.get("hash", "")
        hash2 = f2.get("hash", "")

        if hash1 != hash2 or f1["size"] != f2["size"]:
            modified.append(
                FileDiff(
                    path=path,
                    status="modified",
                    size_before=f1["size"],
                    size_after=f2["size"],
                    hash_before=hash1,
                    hash_after=hash2,
                )
            )
        else:
            unchanged.append(
                FileDiff(
                    path=path,
                    status="unchanged",
                    size_before=f1["size"],
                    size_after=f2["size"],
                    hash_before=hash1,
                    hash_after=hash2,
                )
            )

    return BackupDiff(
        backup1_name=manifest1["backup_name"],
        backup2_name=manifest2["backup_name"],
        backup1_files=manifest1["file_count"],
        backup2_files=manifest2["file_count"],
        backup1_size=manifest1["total_size"],
        backup2_size=manifest2["total_size"],
        added=sorted(added, key=lambda x: x.path),
        removed=sorted(removed, key=lambda x: x.path),
        modified=sorted(modified, key=lambda x: x.path),
        unchanged=sorted(unchanged, key=lambda x: x.path),
    )


def format_diff_summary(diff: BackupDiff) -> str:
    """Format diff as a readable summary."""
    lines = [
        f"Comparing: {diff.backup1_name} → {diff.backup2_name}",
        "",
        f"Backup 1: {diff.backup1_files} files ({format_size(diff.backup1_size)})",
        f"Backup 2: {diff.backup2_files} files ({format_size(diff.backup2_size)})",
        "",
        f"Changes: {diff.summary()}",
    ]

    if diff.size_diff > 0:
        lines.append(f"Size change: +{format_size(diff.size_diff)}")
    elif diff.size_diff < 0:
        lines.append(f"Size change: -{format_size(abs(diff.size_diff))}")

    return "\n".join(lines)
