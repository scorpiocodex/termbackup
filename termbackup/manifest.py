"""File manifest generation with parallel hashing."""

import hashlib
import os
import platform
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pathspec

from termbackup import ui
from termbackup.models import BackupMode, FileMetadata, ManifestData
from termbackup.utils import canonicalize_dict, hash_file


def _get_file_metadata(file_path: Path, base_dir: Path) -> FileMetadata:
    """Gathers metadata for a single file."""
    stat_info = file_path.stat()
    return FileMetadata(
        relative_path=str(file_path.relative_to(base_dir)),
        size=stat_info.st_size,
        sha256=hash_file(file_path),
        permissions=stat_info.st_mode,
        modified_at=stat_info.st_mtime,
    )


def generate_backup_id(manifest_data: ManifestData | dict[str, Any]) -> str:
    """Generates a deterministic backup ID based on the manifest content."""
    data = manifest_data.model_dump(mode="json") if isinstance(manifest_data, ManifestData) else manifest_data
    canonical_manifest = canonicalize_dict(data)
    return hashlib.sha256(canonical_manifest.encode()).hexdigest()


def create_manifest(
    source_dir: Path,
    excludes: list[str],
    backup_mode: str = "full",
    parent_backup_id: str | None = None,
) -> ManifestData:
    """Creates a manifest of all files with parallel hashing."""
    # Build excludes list without mutating the caller's list
    effective_excludes = list(excludes) if excludes else []
    effective_excludes.extend([".git/", ".idea/", "__pycache__/", ".DS_Store"])

    spec = pathspec.PathSpec.from_lines("gitwildmatch", effective_excludes)

    all_files = sorted(p for p in source_dir.rglob("*") if p.is_file())

    # Filter files first
    filtered_files = []
    for file_path in all_files:
        relative_path = file_path.relative_to(source_dir)
        if not spec.match_file(str(relative_path)):
            filtered_files.append(file_path)

    files_manifest: list[FileMetadata] = []

    # Parallel file hashing with ThreadPoolExecutor
    max_workers = min(8, (os.cpu_count() or 4))
    with ui.create_progress() as progress:
        task = progress.add_task("Scanning files", total=len(filtered_files))

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(_get_file_metadata, fp, source_dir): fp
                for fp in filtered_files
            }
            for future in as_completed(futures):
                files_manifest.append(future.result())
                progress.update(task, advance=1)

    # Sort files lexicographically by relative path for determinism
    files_manifest.sort(key=lambda x: x.relative_path)

    manifest = ManifestData(
        version="1.0",
        os_name=platform.system(),
        python_version=sys.version,
        architecture=platform.machine(),
        created_at=datetime.now(UTC).isoformat(),
        backup_mode=BackupMode(backup_mode),
        files=files_manifest,
        parent_backup_id=parent_backup_id,
    )

    backup_id = generate_backup_id(manifest)
    manifest.backup_id = backup_id

    return manifest
