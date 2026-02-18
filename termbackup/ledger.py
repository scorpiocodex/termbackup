"""Metadata ledger management using Pydantic models."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from termbackup import github
from termbackup.models import LedgerData, LedgerEntry, ManifestData
from termbackup.utils import hash_file


def _get_initial_ledger(repo_name: str) -> LedgerData:
    """Returns the initial structure for the metadata ledger."""
    return LedgerData(
        tool_version="6.0",
        repository=repo_name,
        created_at=datetime.now(UTC).isoformat(),
        backups=[],
    )


def append_entry(
    repo_name: str,
    manifest_data: ManifestData | dict[str, Any],
    archive_path: Path,
    commit_sha: str,
    archive_version: int = 2,
    signature: str | None = None,
):
    """Appends a new backup entry to the metadata ledger."""
    content, sha = github.get_metadata_content(repo_name)

    if content:
        raw = json.loads(content)
        # Handle both old-style and new-style ledger data
        try:
            ledger_data = LedgerData.model_validate(raw)
        except Exception:
            ledger_data = LedgerData(
                tool_version=raw.get("tool_version", "4.0"),
                repository=raw.get("repository", repo_name),
                created_at=raw.get("created_at", datetime.now(UTC).isoformat()),
                backups=[LedgerEntry.model_validate(b) for b in raw.get("backups", [])],
            )
    else:
        ledger_data = _get_initial_ledger(repo_name)

    # Extract fields from either model or dict
    if isinstance(manifest_data, ManifestData):
        backup_id = manifest_data.backup_id or ""
        created_at = manifest_data.created_at
        file_count = len(manifest_data.files)
    else:
        backup_id = manifest_data.get("backup_id", "")
        created_at = manifest_data.get("created_at", "")
        file_count = len(manifest_data.get("files", []))

    new_entry = LedgerEntry(
        id=backup_id,
        filename=archive_path.name,
        sha256=hash_file(archive_path),
        commit_sha=commit_sha,
        size=archive_path.stat().st_size,
        created_at=created_at,
        file_count=file_count,
        verified=False,
        archive_version=archive_version,
        signature=signature,
    )

    ledger_data.backups.append(new_entry)

    new_content = json.dumps(ledger_data.model_dump(mode="json"), indent=4)
    github.update_metadata_content(repo_name, new_content, sha)


def get_latest_backup(repo_name: str) -> LedgerEntry | None:
    """Returns the most recent backup entry from the ledger."""
    content, sha = github.get_metadata_content(repo_name)
    if not content:
        return None

    raw = json.loads(content)
    backups = raw.get("backups", [])
    if not backups:
        return None

    sorted_backups = sorted(backups, key=lambda b: b.get("created_at", ""), reverse=True)
    return LedgerEntry.model_validate(sorted_backups[0])


def remove_entry(repo_name: str, backup_id: str):
    """Removes a backup entry from the ledger."""
    content, sha = github.get_metadata_content(repo_name)
    if not content:
        return

    ledger_data = json.loads(content)
    original_count = len(ledger_data.get("backups", []))
    ledger_data["backups"] = [
        b for b in ledger_data.get("backups", []) if b["id"] != backup_id
    ]

    if len(ledger_data["backups"]) < original_count:
        new_content = json.dumps(ledger_data, indent=4)
        github.update_metadata_content(repo_name, new_content, sha)


def mark_verified(repo_name: str, backup_id: str):
    """Marks a backup as verified in the ledger."""
    content, sha = github.get_metadata_content(repo_name)
    if not content:
        return

    ledger_data = json.loads(content)
    updated = False

    for backup in ledger_data.get("backups", []):
        if backup["id"].startswith(backup_id):
            backup["verified"] = True
            backup["verified_at"] = datetime.now(UTC).isoformat()
            updated = True
            break

    if updated:
        new_content = json.dumps(ledger_data, indent=4)
        github.update_metadata_content(repo_name, new_content, sha)
