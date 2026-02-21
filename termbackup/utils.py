"""Utility functions for TermBackup."""

import hashlib
import json
from pathlib import Path
from typing import Any

from termbackup.models import LedgerData, LedgerEntry


def canonicalize_dict(d: dict[str, Any] | Any) -> str:
    """Converts a dictionary (or Pydantic model dump) to a canonical JSON string."""
    if hasattr(d, "model_dump"):
        d = d.model_dump(mode="json")
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


def hash_file(file_path: Path) -> str:
    """Computes the SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def find_backup_in_ledger(
    ledger_data: LedgerData | dict, backup_id: str
) -> LedgerEntry | dict | None:
    """Finds a backup in the ledger by its ID (supports prefix matching)."""
    if isinstance(ledger_data, LedgerData):
        for backup in ledger_data.backups:
            if backup.id.startswith(backup_id):
                return backup
    else:
        for backup in ledger_data.get("backups", []):
            if backup["id"].startswith(backup_id):
                return backup
    return None


def format_size(size_bytes: int) -> str:
    """Formats a byte count into a human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_timestamp(iso_timestamp: str) -> str:
    """Formats an ISO timestamp into a readable format."""
    from datetime import datetime

    try:
        dt = datetime.fromisoformat(iso_timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, TypeError):
        return iso_timestamp


def is_path_safe(member_name: str, target_dir: Path) -> bool:
    """Checks if a tar member path is safe (no path traversal)."""
    target = (target_dir / member_name).resolve()
    return str(target).startswith(str(target_dir.resolve()))
