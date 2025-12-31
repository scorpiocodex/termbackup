"""Backup retention policies for TermBackup v2.0."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from .config import Config, load_config, save_config
from .github import GitHubClient, GitHubError, BackupInfo
from .utils import parse_backup_name


class RetentionError(Exception):
    """Raised when retention operations fail."""


@dataclass
class RetentionPolicy:
    """Backup retention policy configuration."""

    days: Optional[int] = None  # Keep backups for N days
    count: Optional[int] = None  # Keep last N backups
    keep_tagged: bool = True  # Always keep tagged backups

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "days": self.days,
            "count": self.count,
            "keep_tagged": self.keep_tagged,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RetentionPolicy":
        """Create from dictionary."""
        return cls(
            days=data.get("days"),
            count=data.get("count"),
            keep_tagged=data.get("keep_tagged", True),
        )


@dataclass
class RetentionResult:
    """Result of retention policy application."""

    total_backups: int
    kept: int
    deleted: int
    deleted_names: list[str]
    kept_names: list[str]
    errors: list[str]


def get_retention_policy(config: Config) -> Optional[RetentionPolicy]:
    """Get current retention policy from config."""
    policy_data = getattr(config, "retention_policy", None)
    if policy_data:
        return RetentionPolicy.from_dict(policy_data)
    return None


def set_retention_policy(
    days: Optional[int] = None,
    count: Optional[int] = None,
    keep_tagged: bool = True,
) -> RetentionPolicy:
    """Set retention policy in config."""
    config = load_config()

    policy = RetentionPolicy(days=days, count=count, keep_tagged=keep_tagged)

    # Store policy in config (we'll need to extend Config class)
    if not hasattr(config, "retention_policy"):
        config_dict = config.to_dict()
        config_dict["retention_policy"] = policy.to_dict()
        # Save extended config
        import json
        from .config import CONFIG_FILE, ensure_config_dir
        ensure_config_dir()
        CONFIG_FILE.write_text(json.dumps(config_dict, indent=2), encoding="utf-8")
    else:
        config.retention_policy = policy.to_dict()
        save_config(config)

    return policy


def get_backups_to_delete(
    backups: list[BackupInfo],
    policy: RetentionPolicy,
    tagged_backups: Optional[set[str]] = None,
) -> list[BackupInfo]:
    """Determine which backups should be deleted based on policy."""
    if not policy.days and not policy.count:
        return []  # No policy set

    tagged = tagged_backups or set()
    candidates = []

    # Sort by date (newest first)
    sorted_backups = sorted(backups, key=lambda b: b.name, reverse=True)

    now = datetime.now()

    for i, backup in enumerate(sorted_backups):
        # Skip tagged backups if configured
        if policy.keep_tagged and backup.name in tagged:
            continue

        should_delete = False

        # Check count policy
        if policy.count and i >= policy.count:
            should_delete = True

        # Check age policy
        if policy.days:
            timestamp = parse_backup_name(backup.name)
            if timestamp:
                age = now - timestamp
                if age > timedelta(days=policy.days):
                    should_delete = True

        if should_delete:
            candidates.append(backup)

    return candidates


def apply_retention_policy(
    config: Config,
    policy: Optional[RetentionPolicy] = None,
    dry_run: bool = False,
) -> RetentionResult:
    """Apply retention policy and delete old backups."""
    if policy is None:
        policy = get_retention_policy(config)

    if policy is None:
        return RetentionResult(
            total_backups=0,
            kept=0,
            deleted=0,
            deleted_names=[],
            kept_names=[],
            errors=["No retention policy configured"],
        )

    try:
        client = GitHubClient(config)
        backups = client.list_backups()
    except GitHubError as e:
        return RetentionResult(
            total_backups=0,
            kept=0,
            deleted=0,
            deleted_names=[],
            kept_names=[],
            errors=[f"Failed to list backups: {e}"],
        )

    # Get tagged backups
    tagged = set()
    if policy.keep_tagged:
        try:
            from .tags import load_tags
            store = load_tags(config)
            tagged = set(store.tags.keys())
        except Exception:
            pass  # Ignore tag errors

    to_delete = get_backups_to_delete(backups, policy, tagged)
    to_keep = [b for b in backups if b not in to_delete]

    deleted_names = []
    errors = []

    if not dry_run:
        for backup in to_delete:
            try:
                client.delete_backup(backup.name)
                deleted_names.append(backup.name)
            except GitHubError as e:
                errors.append(f"Failed to delete {backup.name}: {e}")

    return RetentionResult(
        total_backups=len(backups),
        kept=len(to_keep),
        deleted=len(to_delete) if dry_run else len(deleted_names),
        deleted_names=[b.name for b in to_delete] if dry_run else deleted_names,
        kept_names=[b.name for b in to_keep],
        errors=errors,
    )


def preview_retention(config: Config, policy: RetentionPolicy) -> RetentionResult:
    """Preview what retention policy would delete (dry run)."""
    return apply_retention_policy(config, policy, dry_run=True)
