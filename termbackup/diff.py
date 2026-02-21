"""Diff engine for computing changes between manifests."""

import json
from typing import Any

from termbackup.models import ManifestData


def compute_changes(
    current_manifest: ManifestData | dict[str, Any],
    previous_manifest: ManifestData | dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Computes the diff between two manifests.

    Args:
        current_manifest: The current manifest data (model or dict).
        previous_manifest: The previous manifest data (model or dict).

    Returns:
        Dict with keys: added, modified, deleted, unchanged.
        Each value is a list of file metadata dicts.
    """
    # Extract files as dicts for uniform handling
    if isinstance(current_manifest, ManifestData):
        current_files_list = [f.model_dump(mode="json") for f in current_manifest.files]
    else:
        current_files_list = current_manifest.get("files", [])

    if isinstance(previous_manifest, ManifestData):
        previous_files_list = [f.model_dump(mode="json") for f in previous_manifest.files]
    else:
        previous_files_list = previous_manifest.get("files", [])

    current_files = {f["relative_path"]: f for f in current_files_list}
    previous_files = {f["relative_path"]: f for f in previous_files_list}

    current_paths = set(current_files.keys())
    previous_paths = set(previous_files.keys())

    added = [current_files[p] for p in sorted(current_paths - previous_paths)]
    deleted = [previous_files[p] for p in sorted(previous_paths - current_paths)]

    modified = []
    unchanged = []

    for path in sorted(current_paths & previous_paths):
        if current_files[path]["sha256"] != previous_files[path]["sha256"]:
            modified.append(current_files[path])
        else:
            unchanged.append(current_files[path])

    return {
        "added": added,
        "modified": modified,
        "deleted": deleted,
        "unchanged": unchanged,
    }


def diff_backups(
    repo_name: str,
    id1: str,
    id2: str,
    password: str,
) -> dict[str, list[dict[str, Any]]]:
    """Downloads two backup manifests and computes their diff.

    Args:
        repo_name: GitHub repository (user/repo).
        id1: First (older) backup ID.
        id2: Second (newer) backup ID.
        password: Decryption password.

    Returns:
        Changes dict with added, modified, deleted, unchanged.
    """
    from pathlib import Path

    from termbackup import archive, github
    from termbackup.config import CONFIG_DIR
    from termbackup.utils import find_backup_in_ledger

    content, _ = github.get_metadata_content(repo_name)
    if not content:
        raise RuntimeError("No backups found in ledger.")

    ledger_data = json.loads(content)

    manifests = []
    for bid in (id1, id2):
        # Try downloading manifest directly first
        manifest_data = github.download_manifest(repo_name, bid)
        if manifest_data:
            manifests.append(manifest_data)
            continue

        # Fall back to downloading and decrypting the archive
        backup_info = find_backup_in_ledger(ledger_data, bid)
        if not backup_info:
            raise RuntimeError(f"Backup '{bid}' not found in ledger.")

        filename = backup_info["filename"] if isinstance(backup_info, dict) else backup_info.filename
        temp_dir = Path(CONFIG_DIR / "tmp")
        temp_dir.mkdir(exist_ok=True)
        archive_path = temp_dir / filename

        try:
            github.download_blob(repo_name, filename, archive_path)
            header = archive.read_archive_header(archive_path)
            payload = archive.read_archive_payload(archive_path, password, header)

            import io
            import tarfile

            tar_stream = io.BytesIO(payload)
            with tarfile.open(fileobj=tar_stream, mode="r") as tar:
                mf = tar.extractfile(tar.getmember("manifest.json"))
                if mf:
                    manifests.append(json.load(mf))
                else:
                    raise RuntimeError(f"Manifest not found in archive for backup '{bid}'")
        finally:
            if archive_path.exists():
                archive_path.unlink()

    return compute_changes(manifests[1], manifests[0])
