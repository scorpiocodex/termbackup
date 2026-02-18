"""Append-only JSONL audit log for TermBackup operations."""

import json
from datetime import UTC, datetime

from termbackup.config import CONFIG_DIR

AUDIT_LOG_PATH = CONFIG_DIR / "audit.log"


def log_operation(
    operation: str,
    profile: str,
    status: str,
    details: dict | None = None,
) -> None:
    """Appends one JSON line to the audit log.

    Args:
        operation: One of backup, restore, verify, prune, rotate-key, schedule.
        profile: Profile name involved.
        status: 'success' or 'failure'.
        details: Optional extra data (backup_id, file_count, etc.).
    """
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "operation": operation,
        "profile": profile,
        "status": status,
    }
    if details:
        entry["details"] = details

    try:
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")
    except OSError as e:
        import sys
        print(f"Warning: Could not write audit log: {e}", file=sys.stderr)
