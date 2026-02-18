"""Shared test fixtures for TermBackup test suite."""

from pathlib import Path

import pytest

from termbackup import config
from termbackup.models import FileMetadata, ManifestData, ProfileConfig


@pytest.fixture
def mock_config_dir(tmp_path: Path, monkeypatch):
    """Redirects config paths to a temporary directory."""
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(config, "PROFILES_DIR", tmp_path / "profiles")
    return tmp_path


@pytest.fixture
def sample_profile():
    """Returns a typical profile dict (legacy format for backward compat tests)."""
    return {
        "name": "test-profile",
        "source_dir": "/tmp/test-source",
        "repo": "user/backup-repo",
        "excludes": ["*.log", "node_modules/"],
    }


@pytest.fixture
def sample_profile_model(tmp_path):
    """Returns a ProfileConfig Pydantic model."""
    source = tmp_path / "source"
    source.mkdir(exist_ok=True)
    return ProfileConfig(
        name="test-profile",
        source_dir=str(source),
        repo="user/backup-repo",
        excludes=["*.log", "node_modules/"],
    )


@pytest.fixture
def sample_manifest():
    """Returns a manifest dict (legacy format)."""
    return {
        "version": "1.0",
        "os_name": "Windows",
        "python_version": "3.11.0",
        "architecture": "AMD64",
        "created_at": "2024-01-15T10:00:00+00:00",
        "backup_mode": "full",
        "backup_id": "abc123def456789012345678901234567890123456789012345678901234",
        "files": [
            {
                "relative_path": "file1.txt",
                "size": 100,
                "sha256": "aaa" + "0" * 61,
                "permissions": 33206,
                "modified_at": 1700000000.0,
            },
            {
                "relative_path": "subdir/file2.txt",
                "size": 200,
                "sha256": "bbb" + "0" * 61,
                "permissions": 33206,
                "modified_at": 1700000001.0,
            },
        ],
    }


@pytest.fixture
def sample_manifest_model():
    """Returns a ManifestData Pydantic model."""
    return ManifestData(
        version="1.0",
        os_name="Windows",
        python_version="3.11.0",
        architecture="AMD64",
        created_at="2024-01-15T10:00:00+00:00",
        backup_mode="full",
        backup_id="abc123def456789012345678901234567890123456789012345678901234",
        files=[
            FileMetadata(
                relative_path="file1.txt",
                size=100,
                sha256="aaa" + "0" * 61,
                permissions=33206,
                modified_at=1700000000.0,
            ),
            FileMetadata(
                relative_path="subdir/file2.txt",
                size=200,
                sha256="bbb" + "0" * 61,
                permissions=33206,
                modified_at=1700000001.0,
            ),
        ],
    )


@pytest.fixture
def sample_ledger():
    """Returns a ledger with 2 backup entries."""
    return {
        "tool_version": "4.0",
        "repository": "user/backup-repo",
        "created_at": "2024-01-01T00:00:00+00:00",
        "backups": [
            {
                "id": "abc123def456789012345678901234567890123456789012345678901234",
                "filename": "backup_abc123def456.tbk",
                "sha256": "deadbeef" * 8,
                "commit_sha": "commit123456",
                "size": 1024,
                "created_at": "2024-01-15T10:00:00+00:00",
                "file_count": 5,
                "verified": False,
            },
            {
                "id": "xyz789abc012345678901234567890123456789012345678901234567890",
                "filename": "backup_xyz789abc012.tbk",
                "sha256": "cafebabe" * 8,
                "commit_sha": "commit789012",
                "size": 2048,
                "created_at": "2024-02-01T12:00:00+00:00",
                "file_count": 10,
                "verified": True,
            },
        ],
    }


def _create_mock_tar_payload(manifest_data, files):
    """Build in-memory tar bytes containing a manifest and file entries."""
    import io
    import tarfile

    from termbackup.utils import canonicalize_dict

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        manifest_bytes = canonicalize_dict(manifest_data).encode()
        info = tarfile.TarInfo(name="manifest.json")
        info.size = len(manifest_bytes)
        tar.addfile(info, io.BytesIO(manifest_bytes))

        for rel_path, content in files.items():
            info = tarfile.TarInfo(name=rel_path)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))

    return buf.getvalue()
