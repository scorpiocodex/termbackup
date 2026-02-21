"""Backup rotation / retention policy module."""

from datetime import UTC, datetime, timedelta
from typing import Any

from termbackup.models import LedgerEntry


def compute_backups_to_prune(
    backups: list[LedgerEntry] | list[dict[str, Any]],
    max_backups: int | None = None,
    retention_days: int | None = None,
) -> list[LedgerEntry] | list[dict[str, Any]]:
    """Determines which backups should be pruned based on retention policy.

    Args:
        backups: List of backup entries (Pydantic models or dicts).
        max_backups: Maximum number of backups to keep (oldest pruned first).
        retention_days: Maximum age in days; backups older than this are pruned.

    Returns:
        List of backup entries that should be removed.
    """
    if not backups:
        return []

    def _get_id(entry):
        return entry.id if isinstance(entry, LedgerEntry) else entry.get("id", "")

    def _get_created_at(entry):
        return entry.created_at if isinstance(entry, LedgerEntry) else entry.get("created_at", "")

    # Sort by created_at descending (newest first)
    sorted_backups = sorted(backups, key=lambda b: _get_created_at(b), reverse=True)

    to_prune = set()

    # Apply max_backups limit
    if max_backups is not None and max_backups > 0:
        if len(sorted_backups) > max_backups:
            for entry in sorted_backups[max_backups:]:
                to_prune.add(_get_id(entry))

    # Apply retention_days limit
    if retention_days is not None and retention_days > 0:
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        for entry in sorted_backups:
            try:
                created = datetime.fromisoformat(_get_created_at(entry))
                if created < cutoff:
                    to_prune.add(_get_id(entry))
            except (ValueError, KeyError):
                continue

    return [b for b in sorted_backups if _get_id(b) in to_prune]
