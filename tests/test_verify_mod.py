"""Tests for the verify module with Pydantic models."""

import json
from unittest.mock import patch

import pytest

from termbackup import verify
from termbackup.models import ArchiveHeader, ProfileConfig
from tests.conftest import _create_mock_tar_payload


def _make_ledger(backup_id="abc123def456", sha256="dead" * 16):
    return json.dumps({
        "backups": [{
            "id": backup_id + "0" * (64 - len(backup_id)),
            "filename": "backup_abc123def456.tbk",
            "sha256": sha256,
            "size": 1024,
            "created_at": "2024-01-01T00:00:00+00:00",
            "file_count": 2,
            "verified": False,
            "commit_sha": "commit123",
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


@pytest.fixture
def mock_verify_deps(mock_config_dir):
    """Patches all dependencies for verify tests."""
    profile = ProfileConfig(
        name="test-profile",
        source_dir=str(mock_config_dir / "source"),
        repo="user/repo",
        excludes=[],
    )

    with patch("termbackup.verify.config.get_profile", return_value=profile), \
         patch("termbackup.verify.github.get_metadata_content") as mock_meta, \
         patch("termbackup.verify.github.download_blob") as mock_download, \
         patch("termbackup.verify.archive.read_archive_header") as mock_header, \
         patch("termbackup.verify.archive.read_archive_payload") as mock_payload, \
         patch("termbackup.verify.hash_file") as mock_hash, \
         patch("termbackup.verify.ledger.mark_verified") as mock_mark, \
         patch("termbackup.verify.audit.log_operation"):

        yield {
            "meta": mock_meta,
            "download": mock_download,
            "header": mock_header,
            "payload": mock_payload,
            "hash_file": mock_hash,
            "mark_verified": mock_mark,
            "config_dir": mock_config_dir,
        }


class TestVerifyBackup:
    def test_no_metadata(self, mock_verify_deps):
        mock_verify_deps["meta"].return_value = (None, None)

        with pytest.raises(SystemExit):
            verify.verify_backup("test-profile", "abc123", "pass")

    def test_backup_not_found(self, mock_verify_deps):
        mock_verify_deps["meta"].return_value = (
            json.dumps({"backups": []}), "sha"
        )

        with pytest.raises(SystemExit):
            verify.verify_backup("test-profile", "nonexistent", "pass")

    def test_sha256_mismatch(self, mock_verify_deps):
        mock_verify_deps["meta"].return_value = (_make_ledger(sha256="dead" * 16), "sha")
        mock_verify_deps["hash_file"].return_value = "beef" * 16

        def fake_download(repo, filename, dest):
            dest.write_bytes(b"fake")
        mock_verify_deps["download"].side_effect = fake_download

        with pytest.raises(SystemExit):
            verify.verify_backup("test-profile", "abc123", "pass")

    def test_decrypt_failure(self, mock_verify_deps):
        mock_verify_deps["meta"].return_value = (_make_ledger(), "sha")
        mock_verify_deps["hash_file"].return_value = "dead" * 16

        def fake_download(repo, filename, dest):
            dest.write_bytes(b"fake")
        mock_verify_deps["download"].side_effect = fake_download

        mock_verify_deps["header"].return_value = _make_header()
        mock_verify_deps["payload"].side_effect = Exception("HMAC verification failed")

        with pytest.raises(SystemExit):
            verify.verify_backup("test-profile", "abc123", "pass")

    def test_manifest_id_mismatch(self, mock_verify_deps):
        mock_verify_deps["meta"].return_value = (_make_ledger(), "sha")
        mock_verify_deps["hash_file"].return_value = "dead" * 16

        def fake_download(repo, filename, dest):
            dest.write_bytes(b"fake")
        mock_verify_deps["download"].side_effect = fake_download

        manifest_data = {
            "version": "1.0",
            "backup_id": "tampered_id_that_wont_match_recalculation_at_all_padding",
            "files": [{"relative_path": "file.txt", "size": 5, "sha256": "a" * 64}],
        }
        payload = _create_mock_tar_payload(manifest_data, {"file.txt": b"hello"})

        mock_verify_deps["header"].return_value = _make_header()
        mock_verify_deps["payload"].return_value = payload

        with pytest.raises(SystemExit):
            verify.verify_backup("test-profile", "abc123", "pass")

    def test_all_checks_pass(self, mock_verify_deps):
        """When all checks pass, mark_verified should be called."""
        from termbackup.manifest import generate_backup_id

        manifest_data = {
            "version": "1.0",
            "created_at": "2024-01-01T00:00:00+00:00",
            "files": [{"relative_path": "file.txt", "size": 5, "sha256": "a" * 64}],
            "backup_id": None,
        }
        real_id = generate_backup_id(manifest_data)
        manifest_data["backup_id"] = real_id

        payload = _create_mock_tar_payload(manifest_data, {"file.txt": b"hello"})

        mock_verify_deps["meta"].return_value = (_make_ledger(), "sha")
        mock_verify_deps["hash_file"].return_value = "dead" * 16
        mock_verify_deps["header"].return_value = _make_header()
        mock_verify_deps["payload"].return_value = payload

        def fake_download(repo, filename, dest):
            dest.write_bytes(b"fake")
        mock_verify_deps["download"].side_effect = fake_download

        verify.verify_backup("test-profile", "abc123", "pass")

        mock_verify_deps["mark_verified"].assert_called_once()

    def test_ledger_update_failure_non_critical(self, mock_verify_deps):
        """Ledger update failure should warn but not crash."""
        from termbackup.manifest import generate_backup_id

        manifest_data = {
            "version": "1.0",
            "created_at": "2024-01-01T00:00:00+00:00",
            "files": [{"relative_path": "file.txt", "size": 5, "sha256": "a" * 64}],
            "backup_id": None,
        }
        real_id = generate_backup_id(manifest_data)
        manifest_data["backup_id"] = real_id

        payload = _create_mock_tar_payload(manifest_data, {"file.txt": b"hello"})

        mock_verify_deps["meta"].return_value = (_make_ledger(), "sha")
        mock_verify_deps["hash_file"].return_value = "dead" * 16
        mock_verify_deps["header"].return_value = _make_header()
        mock_verify_deps["payload"].return_value = payload
        mock_verify_deps["mark_verified"].side_effect = RuntimeError("network error")

        def fake_download(repo, filename, dest):
            dest.write_bytes(b"fake")
        mock_verify_deps["download"].side_effect = fake_download

        verify.verify_backup("test-profile", "abc123", "pass")
