"""Backup tagging system for TermBackup v2.0."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .config import Config
from .github import GitHubClient, GitHubError


TAGS_FILE = "metadata/tags.json"


class TagError(Exception):
    """Raised when tag operations fail."""


@dataclass
class BackupTag:
    """A tag associated with a backup."""

    backup_id: str
    label: str
    created_at: str
    description: Optional[str] = None


@dataclass
class TagStore:
    """Storage for backup tags."""

    tags: dict[str, list[BackupTag]] = field(default_factory=dict)

    def add_tag(
        self, backup_id: str, label: str, description: Optional[str] = None
    ) -> BackupTag:
        """Add a tag to a backup."""
        tag = BackupTag(
            backup_id=backup_id,
            label=label,
            created_at=datetime.now().isoformat(),
            description=description,
        )

        if backup_id not in self.tags:
            self.tags[backup_id] = []

        # Check for duplicate labels
        for existing in self.tags[backup_id]:
            if existing.label == label:
                raise TagError(f"Tag '{label}' already exists for backup {backup_id}")

        self.tags[backup_id].append(tag)
        return tag

    def remove_tag(self, backup_id: str, label: str) -> None:
        """Remove a tag from a backup."""
        if backup_id not in self.tags:
            raise TagError(f"No tags found for backup {backup_id}")

        original_len = len(self.tags[backup_id])
        self.tags[backup_id] = [t for t in self.tags[backup_id] if t.label != label]

        if len(self.tags[backup_id]) == original_len:
            raise TagError(f"Tag '{label}' not found for backup {backup_id}")

        if not self.tags[backup_id]:
            del self.tags[backup_id]

    def get_tags(self, backup_id: str) -> list[BackupTag]:
        """Get all tags for a backup."""
        return self.tags.get(backup_id, [])

    def find_by_tag(self, label: str) -> list[str]:
        """Find all backups with a specific tag."""
        results = []
        for backup_id, tags in self.tags.items():
            if any(t.label == label for t in tags):
                results.append(backup_id)
        return results

    def list_all_tags(self) -> list[str]:
        """List all unique tag labels."""
        all_labels = set()
        for tags in self.tags.values():
            for tag in tags:
                all_labels.add(tag.label)
        return sorted(all_labels)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            backup_id: [
                {
                    "backup_id": t.backup_id,
                    "label": t.label,
                    "created_at": t.created_at,
                    "description": t.description,
                }
                for t in tags
            ]
            for backup_id, tags in self.tags.items()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TagStore":
        """Create from dictionary."""
        store = cls()
        for backup_id, tag_list in data.items():
            store.tags[backup_id] = [
                BackupTag(
                    backup_id=t["backup_id"],
                    label=t["label"],
                    created_at=t["created_at"],
                    description=t.get("description"),
                )
                for t in tag_list
            ]
        return store


def load_tags(config: Config) -> TagStore:
    """Load tags from GitHub repository."""
    try:
        client = GitHubClient(config)
        response = client.session.get(
            f"https://api.github.com/repos/{client.repo}/contents/{TAGS_FILE}"
        )

        if response.status_code == 404:
            return TagStore()

        if response.status_code != 200:
            raise TagError("Failed to load tags")

        import base64

        content = base64.b64decode(response.json()["content"]).decode("utf-8")
        data = json.loads(content)
        return TagStore.from_dict(data)

    except GitHubError as e:
        raise TagError(f"Failed to load tags: {e}") from e


def save_tags(config: Config, store: TagStore) -> None:
    """Save tags to GitHub repository."""
    try:
        client = GitHubClient(config)
        content = json.dumps(store.to_dict(), indent=2)

        # Check if file exists to get SHA
        sha = client._get_file_sha(TAGS_FILE)

        import base64

        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")

        data = {
            "message": "Update backup tags",
            "content": encoded,
        }
        if sha:
            data["sha"] = sha

        response = client.session.put(
            f"https://api.github.com/repos/{client.repo}/contents/{TAGS_FILE}",
            json=data,
        )

        if response.status_code not in (200, 201):
            raise TagError("Failed to save tags")

    except GitHubError as e:
        raise TagError(f"Failed to save tags: {e}") from e


def add_backup_tag(
    config: Config, backup_id: str, label: str, description: Optional[str] = None
) -> BackupTag:
    """Add a tag to a backup."""
    store = load_tags(config)
    tag = store.add_tag(backup_id, label, description)
    save_tags(config, store)
    return tag


def remove_backup_tag(config: Config, backup_id: str, label: str) -> None:
    """Remove a tag from a backup."""
    store = load_tags(config)
    store.remove_tag(backup_id, label)
    save_tags(config, store)


def get_backup_tags(config: Config, backup_id: str) -> list[BackupTag]:
    """Get all tags for a backup."""
    store = load_tags(config)
    return store.get_tags(backup_id)


def find_backups_by_tag(config: Config, label: str) -> list[str]:
    """Find all backups with a specific tag."""
    store = load_tags(config)
    return store.find_by_tag(label)
