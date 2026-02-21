"""Tests for the restore module with Pydantic models."""

import io
import json
import tarfile
from unittest.mock import patch

import pytest

from termbackup import restore
from termbackup.models import ArchiveHeader, ProfileConfig
from tests.conftest import _create_mock_tar_payload


@pytest.fixture
def mock_restore_deps(mock_config_dir):
    """Patches config, github, and archive for restore tests."""
    source = mock_config_dir / "restore-target"
    source.mkdir(exist_ok=True)
    profile = ProfileConfig(
        name="test-profile",
        source_dir=str(source),
        repo="user/repo",
        excludes=[],
    )

    with patch("termbackup.restore.config.get_profile", return_value=profile) as mock_prof, \
         patch("termbackup.restore.github.get_metadata_content") as mock_meta, \
         patch("termbackup.restore.github.download_blob") as mock_download, \
         patch("termbackup.restore.archive.read_archive_header") as mock_header, \
         patch("termbackup.restore.archive.read_archive_payload") as mock_payload, \
         patch("termbackup.restore.audit.log_operation"):

        yield {
            "profile": mock_prof,
            "meta": mock_meta,
            "download": mock_download,
            "header": mock_header,
            "payload": mock_payload,
            "config_dir": mock_config_dir,
            "source_dir": source,
        }


def _make_ledger(backup_id="abc123def456", filename="backup_abc123def456.tbk"):
    return json.dumps({
        "backups": [{
            "id": backup_id + "0" * (64 - len(backup_id)),
            "filename": filename,
            "sha256": "dead" * 16,
            "commit_sha": "commit123",
            "size": 1024,
            "created_at": "2024-01-01T00:00:00+00:00",
            "file_count": 2,
            "verified": False,
        }]
    })


def _make_header():
    return ArchiveHeader(
        version=2,
        kdf_algorithm="argon2id",
        salt=b"\x00" * 32,
        iv_or_nonce=b"\x00" * 12,
        payload_len=0,
        header_size=0,
    )


class TestRestoreBackup:
    def test_no_metadata(self, mock_restore_deps):
        mock_restore_deps["meta"].return_value = (None, None)

        with pytest.raises(SystemExit):
            restore.restore_backup("test-profile", "abc123", "pass", dry_run=False)

    def test_backup_not_found(self, mock_restore_deps):
        mock_restore_deps["meta"].return_value = (
            json.dumps({"backups": []}), "sha"
        )

        with pytest.raises(SystemExit):
            restore.restore_backup("test-profile", "nonexistent", "pass", dry_run=False)

    def test_manifest_missing_in_archive(self, mock_restore_deps):
        mock_restore_deps["meta"].return_value = (_make_ledger(), "sha")

        # Create tar without manifest
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            data = b"some data"
            info = tarfile.TarInfo(name="somefile.txt")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        payload = buf.getvalue()

        mock_restore_deps["header"].return_value = _make_header()
        mock_restore_deps["payload"].return_value = payload

        def fake_download(repo, filename, dest):
            dest.write_bytes(b"fake")
        mock_restore_deps["download"].side_effect = fake_download

        with pytest.raises(KeyError):
            restore.restore_backup("test-profile", "abc123", "pass", dry_run=False)

    def test_dry_run(self, mock_restore_deps):
        manifest_data = {
            "version": "1.0",
            "backup_id": "abc123def456" + "0" * 52,
            "files": [
                {"relative_path": "file1.txt", "size": 100, "sha256": "a" * 64},
            ],
        }
        files = {"file1.txt": b"hello world"}
        payload = _create_mock_tar_payload(manifest_data, files)

        mock_restore_deps["meta"].return_value = (_make_ledger(), "sha")
        mock_restore_deps["header"].return_value = _make_header()
        mock_restore_deps["payload"].return_value = payload

        def fake_download(repo, filename, dest):
            dest.write_bytes(b"fake")
        mock_restore_deps["download"].side_effect = fake_download

        restore.restore_backup("test-profile", "abc123", "pass", dry_run=True)

        source_dir = mock_restore_deps["source_dir"]
        assert not (source_dir / "file1.txt").exists()

    def test_path_traversal_skipped(self, mock_restore_deps):
        manifest_data = {
            "version": "1.0",
            "backup_id": "abc123def456" + "0" * 52,
            "files": [
                {"relative_path": "../../etc/passwd", "size": 100, "sha256": "a" * 64},
                {"relative_path": "safe.txt", "size": 5, "sha256": "b" * 64},
            ],
        }
        files = {"../../etc/passwd": b"root:x:0:0", "safe.txt": b"hello"}
        payload = _create_mock_tar_payload(manifest_data, files)

        mock_restore_deps["meta"].return_value = (_make_ledger(), "sha")
        mock_restore_deps["header"].return_value = _make_header()
        mock_restore_deps["payload"].return_value = payload

        def fake_download(repo, filename, dest):
            dest.write_bytes(b"fake")
        mock_restore_deps["download"].side_effect = fake_download

        restore.restore_backup("test-profile", "abc123", "pass", dry_run=False)

        source_dir = mock_restore_deps["source_dir"]
        assert (source_dir / "safe.txt").exists()

    @patch("termbackup.restore.ui.confirm", return_value=True)
    def test_overwrite_confirm_yes(self, mock_confirm, mock_restore_deps):
        source_dir = mock_restore_deps["source_dir"]
        (source_dir / "file1.txt").write_text("old content")

        manifest_data = {
            "version": "1.0",
            "backup_id": "abc123def456" + "0" * 52,
            "files": [
                {"relative_path": "file1.txt", "size": 11, "sha256": "a" * 64},
            ],
        }
        files = {"file1.txt": b"new content"}
        payload = _create_mock_tar_payload(manifest_data, files)

        mock_restore_deps["meta"].return_value = (_make_ledger(), "sha")
        mock_restore_deps["header"].return_value = _make_header()
        mock_restore_deps["payload"].return_value = payload

        def fake_download(repo, filename, dest):
            dest.write_bytes(b"fake")
        mock_restore_deps["download"].side_effect = fake_download

        restore.restore_backup("test-profile", "abc123", "pass", dry_run=False)
        mock_confirm.assert_called_once()

    @patch("termbackup.restore.ui.confirm", return_value=False)
    def test_overwrite_confirm_no(self, mock_confirm, mock_restore_deps):
        source_dir = mock_restore_deps["source_dir"]
        (source_dir / "file1.txt").write_text("old content")

        manifest_data = {
            "version": "1.0",
            "backup_id": "abc123def456" + "0" * 52,
            "files": [
                {"relative_path": "file1.txt", "size": 11, "sha256": "a" * 64},
            ],
        }
        files = {"file1.txt": b"new content"}
        payload = _create_mock_tar_payload(manifest_data, files)

        mock_restore_deps["meta"].return_value = (_make_ledger(), "sha")
        mock_restore_deps["header"].return_value = _make_header()
        mock_restore_deps["payload"].return_value = payload

        def fake_download(repo, filename, dest):
            dest.write_bytes(b"fake")
        mock_restore_deps["download"].side_effect = fake_download

        restore.restore_backup("test-profile", "abc123", "pass", dry_run=False)

        assert (source_dir / "file1.txt").read_text() == "old content"

    def test_cleanup_on_failure(self, mock_restore_deps):
        mock_restore_deps["meta"].return_value = (_make_ledger(), "sha")
        mock_restore_deps["header"].side_effect = RuntimeError("corrupt")

        def fake_download(repo, filename, dest):
            dest.write_bytes(b"fake")
        mock_restore_deps["download"].side_effect = fake_download

        with pytest.raises(RuntimeError, match="corrupt"):
            restore.restore_backup("test-profile", "abc123", "pass", dry_run=False)

        config_dir = mock_restore_deps["config_dir"]
        tmp_dir = config_dir / "tmp"
        if tmp_dir.exists():
            tbk_files = list(tmp_dir.glob("*.tbk"))
            assert len(tbk_files) == 0
