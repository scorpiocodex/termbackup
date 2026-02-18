"""Tests for backup manifest creation with Pydantic models."""

import os
from pathlib import Path

from termbackup import manifest
from termbackup.models import FileMetadata, ManifestData


def test_create_manifest(tmp_path: Path, mocker):
    mocker.patch("termbackup.manifest.datetime")
    manifest.datetime.now.return_value.isoformat.return_value = (
        "2024-01-01T00:00:00+00:00"
    )

    (tmp_path / "file1.txt").write_text("hello")
    (tmp_path / "dir1").mkdir()
    (tmp_path / "dir1" / "file2.txt").write_text("world")
    (tmp_path / "dir2").mkdir()
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("git config")

    manifest_data = manifest.create_manifest(tmp_path, [])

    assert isinstance(manifest_data, ManifestData)
    assert manifest_data.version == "1.0"
    assert len(manifest_data.files) == 2

    file_paths = [f.relative_path for f in manifest_data.files]
    assert "file1.txt" in file_paths
    assert os.path.join("dir1", "file2.txt") in file_paths
    assert os.path.join(".git", "config") not in file_paths

    # Determinism
    manifest_data2 = manifest.create_manifest(tmp_path, [])
    assert manifest_data.backup_id == manifest_data2.backup_id


def test_manifest_excludes_custom_patterns(tmp_path: Path, mocker):
    mocker.patch("termbackup.manifest.datetime")
    manifest.datetime.now.return_value.isoformat.return_value = (
        "2024-01-01T00:00:00+00:00"
    )

    (tmp_path / "keep.txt").write_text("keep")
    (tmp_path / "exclude.log").write_text("log data")
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "output.bin").write_text("binary")

    manifest_data = manifest.create_manifest(tmp_path, ["*.log", "build/"])

    file_paths = [f.relative_path for f in manifest_data.files]
    assert "keep.txt" in file_paths
    assert "exclude.log" not in file_paths
    assert os.path.join("build", "output.bin") not in file_paths


def test_manifest_does_not_mutate_excludes_list(tmp_path: Path, mocker):
    mocker.patch("termbackup.manifest.datetime")
    manifest.datetime.now.return_value.isoformat.return_value = (
        "2024-01-01T00:00:00+00:00"
    )

    (tmp_path / "file.txt").write_text("data")

    excludes = ["*.log"]
    original_len = len(excludes)
    manifest.create_manifest(tmp_path, excludes)

    assert len(excludes) == original_len


def test_manifest_file_metadata(tmp_path: Path, mocker):
    mocker.patch("termbackup.manifest.datetime")
    manifest.datetime.now.return_value.isoformat.return_value = (
        "2024-01-01T00:00:00+00:00"
    )

    content = "test content"
    (tmp_path / "test.txt").write_text(content)

    manifest_data = manifest.create_manifest(tmp_path, [])
    file_meta = manifest_data.files[0]

    assert isinstance(file_meta, FileMetadata)
    assert file_meta.relative_path == "test.txt"
    assert file_meta.size == len(content)
    assert len(file_meta.sha256) == 64
    assert file_meta.permissions > 0
    assert file_meta.modified_at > 0


def test_generate_backup_id_deterministic():
    data = {"key": "value", "files": [{"path": "a.txt"}]}
    id1 = manifest.generate_backup_id(data)
    id2 = manifest.generate_backup_id(data)
    assert id1 == id2
    assert len(id1) == 64
