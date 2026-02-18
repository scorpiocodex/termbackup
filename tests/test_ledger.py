"""Tests for the metadata ledger module."""

import json
from unittest.mock import patch

import pytest

from termbackup import ledger


@pytest.fixture
def mock_archive(tmp_path):
    """Creates a small archive file for ledger entry tests."""
    archive = tmp_path / "backup_abc123def456.tbk"
    archive.write_bytes(b"fake-archive-data")
    return archive


class TestGetInitialLedger:
    def test_structure(self):
        result = ledger._get_initial_ledger("user/repo")
        assert result.tool_version == "6.0"
        assert result.repository == "user/repo"
        assert result.created_at is not None
        assert result.backups == []


class TestAppendEntry:
    @patch("termbackup.ledger.github.update_metadata_content")
    @patch("termbackup.ledger.github.get_metadata_content")
    def test_new_ledger(self, mock_get, mock_update, mock_archive, sample_manifest):
        mock_get.return_value = (None, None)
        mock_update.return_value = "commit_sha"

        ledger.append_entry("user/repo", sample_manifest, mock_archive, "commit123")

        mock_update.assert_called_once()
        content = json.loads(mock_update.call_args[0][1])
        assert len(content["backups"]) == 1
        assert content["backups"][0]["id"] == sample_manifest["backup_id"]

    @patch("termbackup.ledger.github.update_metadata_content")
    @patch("termbackup.ledger.github.get_metadata_content")
    def test_existing_ledger(self, mock_get, mock_update, mock_archive, sample_manifest):
        existing = json.dumps({
            "tool_version": "4.0",
            "repository": "user/repo",
            "created_at": "2024-01-01T00:00:00+00:00",
            "backups": [{"id": "existing_backup", "filename": "old.tbk", "sha256": "abc", "commit_sha": "c1", "size": 100, "created_at": "2024-01-01T00:00:00+00:00", "file_count": 1, "verified": False}],
        })
        mock_get.return_value = (existing, "old_sha")
        mock_update.return_value = "commit_sha"

        ledger.append_entry("user/repo", sample_manifest, mock_archive, "commit123")

        content = json.loads(mock_update.call_args[0][1])
        assert len(content["backups"]) == 2

    @patch("termbackup.ledger.github.update_metadata_content")
    @patch("termbackup.ledger.github.get_metadata_content")
    def test_entry_fields(self, mock_get, mock_update, mock_archive, sample_manifest):
        mock_get.return_value = (None, None)
        mock_update.return_value = "commit_sha"

        ledger.append_entry("user/repo", sample_manifest, mock_archive, "commit_abc")

        content = json.loads(mock_update.call_args[0][1])
        entry = content["backups"][0]
        assert entry["id"] == sample_manifest["backup_id"]
        assert entry["filename"] == mock_archive.name
        assert "sha256" in entry
        assert entry["commit_sha"] == "commit_abc"
        assert entry["size"] == mock_archive.stat().st_size
        assert entry["file_count"] == len(sample_manifest["files"])
        assert entry["verified"] is False


class TestMarkVerified:
    @patch("termbackup.ledger.github.update_metadata_content")
    @patch("termbackup.ledger.github.get_metadata_content")
    def test_found(self, mock_get, mock_update, sample_ledger):
        mock_get.return_value = (json.dumps(sample_ledger), "sha123")
        mock_update.return_value = "commit"

        ledger.mark_verified("user/repo", "abc123")

        content = json.loads(mock_update.call_args[0][1])
        backup = content["backups"][0]
        assert backup["verified"] is True
        assert "verified_at" in backup

    @patch("termbackup.ledger.github.update_metadata_content")
    @patch("termbackup.ledger.github.get_metadata_content")
    def test_not_found(self, mock_get, mock_update, sample_ledger):
        mock_get.return_value = (json.dumps(sample_ledger), "sha123")

        ledger.mark_verified("user/repo", "nonexistent_id")

        mock_update.assert_not_called()

    @patch("termbackup.ledger.github.get_metadata_content")
    def test_no_metadata(self, mock_get):
        mock_get.return_value = (None, None)
        ledger.mark_verified("user/repo", "abc123")  # should not raise
