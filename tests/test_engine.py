"""Tests for the backup engine module with Pydantic models."""

from unittest.mock import patch

import pytest

from termbackup import engine
from termbackup.models import ProfileConfig


@pytest.fixture
def source_dir(tmp_path):
    """Creates a temporary source directory with files."""
    src = tmp_path / "source"
    src.mkdir()
    (src / "file1.txt").write_text("hello world")
    (src / "subdir").mkdir()
    (src / "subdir" / "file2.txt").write_text("nested content")
    return src


@pytest.fixture
def mock_profile(source_dir):
    return ProfileConfig(
        name="test-profile",
        source_dir=str(source_dir),
        repo="user/backup-repo",
        excludes=[],
    )


class TestRunBackup:
    @patch("termbackup.engine.audit.log_operation")
    @patch("termbackup.engine.ledger.append_entry")
    @patch("termbackup.engine.github.upload_blob", return_value="commit_sha_123")
    @patch("termbackup.engine.config.get_profile")
    def test_dry_run_no_upload(self, mock_get_profile, mock_upload, mock_ledger, mock_audit, mock_profile):
        mock_get_profile.return_value = mock_profile

        engine.run_backup("test-profile", "password123", dry_run=True)

        mock_upload.assert_not_called()
        mock_ledger.assert_not_called()

    @patch("termbackup.engine.config.get_profile")
    def test_source_dir_missing(self, mock_get_profile):
        mock_get_profile.return_value = ProfileConfig(
            name="bad",
            source_dir="/nonexistent/path",
            repo="user/repo",
            excludes=[],
        )

        with pytest.raises(SystemExit):
            engine.run_backup("bad", "password123")

    @patch("termbackup.engine.audit.log_operation")
    @patch("termbackup.engine.ledger.append_entry")
    @patch("termbackup.engine.github.upload_blob", return_value="commit_sha_456")
    @patch("termbackup.engine.config.get_profile")
    def test_full_flow(self, mock_get_profile, mock_upload, mock_ledger, mock_audit, mock_profile):
        mock_get_profile.return_value = mock_profile

        engine.run_backup("test-profile", "password123", dry_run=False)

        mock_upload.assert_called_once()
        mock_ledger.assert_called_once()

    @patch("termbackup.engine.audit.log_operation")
    @patch("termbackup.engine.ledger.append_entry")
    @patch("termbackup.engine.github.upload_blob", return_value="commit_sha_789")
    @patch("termbackup.engine.config.get_profile")
    def test_archive_cleaned_up_after_success(self, mock_get_profile, mock_upload, mock_ledger, mock_audit, mock_profile, mock_config_dir):
        mock_get_profile.return_value = mock_profile

        engine.run_backup("test-profile", "password123", dry_run=False)

        # Temp archive should be cleaned up
        tmp_dir = mock_config_dir / "tmp"
        if tmp_dir.exists():
            tbk_files = list(tmp_dir.glob("*.tbk"))
            assert len(tbk_files) == 0

    @patch("termbackup.engine.audit.log_operation")
    @patch("termbackup.engine.ledger.append_entry")
    @patch("termbackup.engine.github.upload_blob")
    @patch("termbackup.engine.config.get_profile")
    def test_cleanup_on_upload_failure(self, mock_get_profile, mock_upload, mock_ledger, mock_audit, mock_profile, mock_config_dir):
        mock_get_profile.return_value = mock_profile
        mock_upload.side_effect = RuntimeError("Upload failed")

        with pytest.raises(RuntimeError, match="Upload failed"):
            engine.run_backup("test-profile", "password123", dry_run=False)

        # Archive should still be cleaned up via finally block
        tmp_dir = mock_config_dir / "tmp"
        if tmp_dir.exists():
            tbk_files = list(tmp_dir.glob("*.tbk"))
            assert len(tbk_files) == 0

    @patch("termbackup.engine.audit.log_operation")
    @patch("termbackup.engine.ledger.append_entry")
    @patch("termbackup.engine.github.upload_blob", return_value="sha")
    @patch("termbackup.engine.config.get_profile")
    def test_cleanup_on_ledger_failure(self, mock_get_profile, mock_upload, mock_ledger, mock_audit, mock_profile, mock_config_dir):
        mock_get_profile.return_value = mock_profile
        mock_ledger.side_effect = RuntimeError("Ledger failed")

        with pytest.raises(RuntimeError, match="Ledger failed"):
            engine.run_backup("test-profile", "password123", dry_run=False)

        tmp_dir = mock_config_dir / "tmp"
        if tmp_dir.exists():
            tbk_files = list(tmp_dir.glob("*.tbk"))
            assert len(tbk_files) == 0

    @patch("termbackup.engine.audit.log_operation")
    @patch("termbackup.engine.ledger.append_entry")
    @patch("termbackup.engine.github.upload_blob", return_value="sha")
    @patch("termbackup.engine.config.get_profile")
    def test_dry_run_archive_cleaned_up(self, mock_get_profile, mock_upload, mock_ledger, mock_audit, mock_profile, mock_config_dir):
        mock_get_profile.return_value = mock_profile

        engine.run_backup("test-profile", "password123", dry_run=True)

        tmp_dir = mock_config_dir / "tmp"
        if tmp_dir.exists():
            tbk_files = list(tmp_dir.glob("*.tbk"))
            assert len(tbk_files) == 0
