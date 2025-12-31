"""Incremental backup support for TermBackup v2.0."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from .backup import FileEntry, scan_files
from .config import Config, Profile
from .github import GitHubClient, GitHubError


CHECKSUMS_FILE = "metadata/checksums.json"


class IncrementalError(Exception):
    """Raised when incremental backup operations fail."""


@dataclass
class FileChecksum:
    """Stored checksum for a file."""

    path: str
    hash: str
    size: int
    modified: float


@dataclass
class ChecksumStore:
    """Storage for file checksums from last backup."""

    profile_name: str
    backup_name: str
    timestamp: str
    files: dict[str, FileChecksum] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "profile_name": self.profile_name,
            "backup_name": self.backup_name,
            "timestamp": self.timestamp,
            "files": {
                path: {
                    "path": f.path,
                    "hash": f.hash,
                    "size": f.size,
                    "modified": f.modified,
                }
                for path, f in self.files.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChecksumStore":
        """Create from dictionary."""
        store = cls(
            profile_name=data["profile_name"],
            backup_name=data["backup_name"],
            timestamp=data["timestamp"],
        )
        for path, f_data in data.get("files", {}).items():
            store.files[path] = FileChecksum(
                path=f_data["path"],
                hash=f_data["hash"],
                size=f_data["size"],
                modified=f_data["modified"],
            )
        return store


@dataclass
class IncrementalAnalysis:
    """Analysis of changes since last backup."""

    profile_name: str
    last_backup: Optional[str]
    new_files: list[FileEntry]
    modified_files: list[FileEntry]
    deleted_files: list[str]
    unchanged_files: list[str]

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return bool(self.new_files or self.modified_files or self.deleted_files)

    @property
    def changed_files(self) -> list[FileEntry]:
        """Get all files that need to be backed up."""
        return self.new_files + self.modified_files

    @property
    def total_changes(self) -> int:
        """Get total number of changes."""
        return len(self.new_files) + len(self.modified_files) + len(self.deleted_files)


def load_checksums(config: Config, profile_name: str) -> Optional[ChecksumStore]:
    """Load checksums for a profile from GitHub."""
    try:
        client = GitHubClient(config)
        response = client.session.get(
            f"https://api.github.com/repos/{client.repo}/contents/{CHECKSUMS_FILE}"
        )

        if response.status_code == 404:
            return None

        if response.status_code != 200:
            return None

        import base64

        content = base64.b64decode(response.json()["content"]).decode("utf-8")
        all_data = json.loads(content)

        if profile_name not in all_data:
            return None

        return ChecksumStore.from_dict(all_data[profile_name])

    except (GitHubError, json.JSONDecodeError, KeyError):
        return None


def save_checksums(
    config: Config, profile_name: str, store: ChecksumStore
) -> None:
    """Save checksums for a profile to GitHub."""
    try:
        client = GitHubClient(config)

        # Load existing checksums
        all_data = {}
        response = client.session.get(
            f"https://api.github.com/repos/{client.repo}/contents/{CHECKSUMS_FILE}"
        )

        sha = None
        if response.status_code == 200:
            import base64

            content = base64.b64decode(response.json()["content"]).decode("utf-8")
            all_data = json.loads(content)
            sha = response.json().get("sha")

        # Update with new data
        all_data[profile_name] = store.to_dict()

        # Save
        import base64

        encoded = base64.b64encode(
            json.dumps(all_data, indent=2).encode("utf-8")
        ).decode("ascii")

        data = {
            "message": f"Update checksums for {profile_name}",
            "content": encoded,
        }
        if sha:
            data["sha"] = sha

        response = client.session.put(
            f"https://api.github.com/repos/{client.repo}/contents/{CHECKSUMS_FILE}",
            json=data,
        )

    except GitHubError:
        pass  # Non-critical, continue without saving


def analyze_changes(
    config: Config, profile: Profile
) -> IncrementalAnalysis:
    """Analyze what has changed since the last backup."""
    # Get current files
    current_files = scan_files(profile)

    # Load previous checksums
    previous = load_checksums(config, profile.name)

    if previous is None:
        # No previous backup, everything is new
        return IncrementalAnalysis(
            profile_name=profile.name,
            last_backup=None,
            new_files=current_files,
            modified_files=[],
            deleted_files=[],
            unchanged_files=[],
        )

    # Build lookup of current files
    current_lookup = {f.relative_path: f for f in current_files}
    previous_paths = set(previous.files.keys())
    current_paths = set(current_lookup.keys())

    # Find new files
    new_paths = current_paths - previous_paths
    new_files = [current_lookup[p] for p in new_paths]

    # Find deleted files
    deleted_paths = previous_paths - current_paths
    deleted_files = list(deleted_paths)

    # Find modified and unchanged files
    modified_files = []
    unchanged_files = []

    for path in current_paths & previous_paths:
        current = current_lookup[path]
        prev = previous.files[path]

        # Check if file has changed (by hash or size)
        if current.hash != prev.hash or current.size != prev.size:
            modified_files.append(current)
        else:
            unchanged_files.append(path)

    return IncrementalAnalysis(
        profile_name=profile.name,
        last_backup=previous.backup_name,
        new_files=new_files,
        modified_files=modified_files,
        deleted_files=deleted_files,
        unchanged_files=unchanged_files,
    )


def create_checksum_store(
    profile: Profile, backup_name: str, files: list[FileEntry]
) -> ChecksumStore:
    """Create a checksum store from backup files."""
    store = ChecksumStore(
        profile_name=profile.name,
        backup_name=backup_name,
        timestamp=datetime.now().isoformat(),
    )

    for f in files:
        store.files[f.relative_path] = FileChecksum(
            path=f.relative_path,
            hash=f.hash,
            size=f.size,
            modified=f.modified,
        )

    return store
