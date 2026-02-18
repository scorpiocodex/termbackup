"""Tests for new CLI commands: generate-key, audit-log, clean."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from termbackup.cli import app

runner = CliRunner()


class TestCleanCommand:
    def test_clean_no_tmp_dir(self, mock_config_dir):
        result = runner.invoke(app, ["clean"])
        assert result.exit_code == 0

    def test_clean_empty_tmp_dir(self, mock_config_dir):
        tmp_dir = mock_config_dir / "tmp"
        tmp_dir.mkdir()
        result = runner.invoke(app, ["clean"])
        assert result.exit_code == 0

    def test_clean_with_orphans_user_declines(self, mock_config_dir):
        tmp_dir = mock_config_dir / "tmp"
        tmp_dir.mkdir()
        (tmp_dir / "orphan.tbk").write_bytes(b"data")

        with patch("termbackup.ui.confirm", return_value=False):
            result = runner.invoke(app, ["clean"])
        assert result.exit_code == 0

    def test_clean_with_orphans_user_confirms(self, mock_config_dir):
        tmp_dir = mock_config_dir / "tmp"
        tmp_dir.mkdir()
        orphan = tmp_dir / "orphan.tbk"
        orphan.write_bytes(b"data")

        with patch("termbackup.ui.confirm", return_value=True):
            result = runner.invoke(app, ["clean"])
        assert result.exit_code == 0
        assert not orphan.exists()


class TestAuditLogCommand:
    def test_audit_log_no_file(self, mock_config_dir):
        from termbackup import audit
        with patch.object(audit, "AUDIT_LOG_PATH", mock_config_dir / "audit.log"):
            result = runner.invoke(app, ["audit-log"])
        assert result.exit_code == 0

    def test_audit_log_with_entries(self, mock_config_dir):
        log_path = mock_config_dir / "audit.log"
        entries = [
            {"timestamp": "2024-01-15T10:00:00+00:00", "operation": "backup", "profile": "test", "status": "success", "details": {"backup_id": "abc123"}},
            {"timestamp": "2024-01-16T10:00:00+00:00", "operation": "restore", "profile": "test", "status": "failure", "details": {"error": "bad password"}},
        ]
        with open(log_path, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        with patch("termbackup.audit.AUDIT_LOG_PATH", log_path):
            result = runner.invoke(app, ["audit-log"])
        assert result.exit_code == 0


class TestGenerateKeyCommand:
    @patch("termbackup.signing.has_signing_key", return_value=False)
    @patch("termbackup.signing.generate_signing_key")
    @patch("termbackup.ui.prompt_secret")
    def test_generate_new_key(self, mock_prompt, mock_gen, mock_has_key):
        mock_prompt.side_effect = ["password123", "password123"]
        result = runner.invoke(app, ["generate-key"])
        assert result.exit_code == 0
        mock_gen.assert_called_once_with("password123")

    @patch("termbackup.signing.has_signing_key", return_value=False)
    @patch("termbackup.ui.prompt_secret")
    def test_generate_key_password_mismatch(self, mock_prompt, mock_has_key):
        mock_prompt.side_effect = ["password1", "password2"]
        result = runner.invoke(app, ["generate-key"])
        assert result.exit_code == 1

    @patch("termbackup.signing.has_signing_key", return_value=True)
    @patch("termbackup.ui.confirm", return_value=False)
    def test_generate_key_exists_declined(self, mock_confirm, mock_has_key):
        result = runner.invoke(app, ["generate-key"])
        assert result.exit_code == 0
