"""Tests for the backup listing module."""

import json
from unittest.mock import patch

import pytest

from termbackup import listing
from termbackup.models import ProfileConfig


class TestListBackups:
    @patch("termbackup.listing.github.get_metadata_content")
    @patch("termbackup.listing.config.get_profile")
    def test_no_metadata(self, mock_profile, mock_meta):
        mock_profile.return_value = ProfileConfig(
            name="test-profile", source_dir="/src", repo="user/repo", excludes=[]
        )
        mock_meta.return_value = (None, None)

        listing.list_backups("test-profile")
        # Should not raise, just print empty message

    @patch("termbackup.listing.github.get_metadata_content")
    @patch("termbackup.listing.config.get_profile")
    def test_empty_backups_list(self, mock_profile, mock_meta):
        mock_profile.return_value = ProfileConfig(
            name="test-profile", source_dir="/src", repo="user/repo", excludes=[]
        )
        content = json.dumps({"backups": []})
        mock_meta.return_value = (content, "sha")

        listing.list_backups("test-profile")

    @patch("termbackup.listing.github.get_metadata_content")
    @patch("termbackup.listing.config.get_profile")
    def test_multiple_backups(self, mock_profile, mock_meta, sample_ledger):
        mock_profile.return_value = ProfileConfig(
            name="test-profile", source_dir="/src", repo="user/repo", excludes=[]
        )
        mock_meta.return_value = (json.dumps(sample_ledger), "sha")

        listing.list_backups("test-profile")

    @patch("termbackup.listing.github.get_metadata_content")
    @patch("termbackup.listing.config.get_profile")
    def test_verified_display(self, mock_profile, mock_meta):
        mock_profile.return_value = ProfileConfig(
            name="test-profile", source_dir="/src", repo="user/repo", excludes=[]
        )
        ledger_data = {
            "backups": [
                {
                    "id": "a" * 64,
                    "filename": "backup.tbk",
                    "created_at": "2024-01-01T00:00:00+00:00",
                    "size": 1024,
                    "file_count": 3,
                    "verified": True,
                },
                {
                    "id": "b" * 64,
                    "filename": "backup2.tbk",
                    "created_at": "2024-02-01T00:00:00+00:00",
                    "size": 2048,
                    "file_count": 5,
                    "verified": False,
                },
            ]
        }
        mock_meta.return_value = (json.dumps(ledger_data), "sha")

        listing.list_backups("test-profile")

    def test_profile_not_found(self):
        with pytest.raises(SystemExit):
            listing.list_backups("nonexistent-profile")
