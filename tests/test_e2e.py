"""End-to-end integration test: backup -> restore cycle with mocked GitHub."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from termbackup import engine, restore
from termbackup.models import AppConfig, ProfileConfig


class MockGitHubStorage:
    """In-memory mock of GitHub blob storage."""

    def __init__(self):
        self.blobs: dict[str, bytes] = {}
        self.metadata: tuple[str | None, str | None] = (None, None)

    def upload_blob(self, repo, file_path):
        path = Path(file_path)
        self.blobs[path.name] = path.read_bytes()
        return "commit_sha_upload"

    def download_blob(self, repo, filename, dest):
        if filename not in self.blobs:
            raise RuntimeError(f"Blob not found: {filename}")
        Path(dest).write_bytes(self.blobs[filename])

    def get_metadata_content(self, repo):
        return self.metadata

    def update_metadata_content(self, repo, content, sha=None):
        self.metadata = (content, "sha_" + str(len(content)))
        return "commit_sha_meta"

    def delete_blob(self, repo, filename):
        self.blobs.pop(filename, None)


@pytest.fixture
def mock_storage():
    return MockGitHubStorage()


@pytest.fixture
def source_dir(tmp_path):
    """Creates a source directory with test files."""
    src = tmp_path / "source"
    src.mkdir()
    (src / "hello.txt").write_text("Hello World!")
    (src / "data").mkdir()
    (src / "data" / "numbers.txt").write_text("1 2 3 4 5")
    return src


@pytest.fixture
def restore_dir(tmp_path):
    dest = tmp_path / "restored"
    dest.mkdir()
    return dest


class TestBackupRestoreCycle:
    def test_full_cycle(self, source_dir, restore_dir, tmp_path, mock_storage):
        """Full backup -> restore -> verify file integrity."""
        profile = ProfileConfig(
            name="e2e-test",
            source_dir=str(source_dir),
            repo="user/e2e-repo",
            excludes=[],
        )
        password = "test-e2e-password"

        with patch("termbackup.engine.config.get_profile", return_value=profile), \
             patch("termbackup.engine.config.get_config", return_value=AppConfig()), \
             patch("termbackup.engine.github.upload_blob", side_effect=mock_storage.upload_blob), \
             patch("termbackup.engine.github.get_metadata_content", side_effect=lambda r: mock_storage.get_metadata_content(r)), \
             patch("termbackup.engine.github.update_metadata_content", side_effect=mock_storage.update_metadata_content), \
             patch("termbackup.signing.has_signing_key", return_value=False), \
             patch("termbackup.engine.audit.log_operation"):

            engine.run_backup("e2e-test", password)

        # Verify upload happened
        assert len(mock_storage.blobs) == 1
        archive_name = list(mock_storage.blobs.keys())[0]
        assert archive_name.endswith(".tbk")

        # Verify metadata was updated
        meta_content, _ = mock_storage.metadata
        assert meta_content is not None
        ledger = json.loads(meta_content)
        assert len(ledger["backups"]) == 1
        backup_id = ledger["backups"][0]["id"]

        # Restore — restore_backup restores to profile.source_dir
        # Use a fresh profile pointing at restore_dir
        restore_profile = ProfileConfig(
            name="e2e-test",
            source_dir=str(restore_dir),
            repo="user/e2e-repo",
            excludes=[],
        )

        with patch("termbackup.restore.config.get_profile", return_value=restore_profile), \
             patch("termbackup.restore.github.get_metadata_content", side_effect=lambda r: mock_storage.get_metadata_content(r)), \
             patch("termbackup.restore.github.download_blob", side_effect=mock_storage.download_blob), \
             patch("termbackup.restore.audit.log_operation"):

            restore.restore_backup("e2e-test", backup_id, password, False)

        # Verify restored files match originals
        assert (restore_dir / "hello.txt").read_text() == "Hello World!"
        assert (restore_dir / "data" / "numbers.txt").read_text() == "1 2 3 4 5"
