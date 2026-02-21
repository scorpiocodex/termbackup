"""Tests for the doctor health check module."""

import json
from unittest.mock import MagicMock, patch

from termbackup import doctor


class TestCheckConfig:
    def test_no_config_file(self, mock_config_dir):
        with patch.object(doctor, "CONFIG_FILE", mock_config_dir / "config.json"):
            name, passed, msg = doctor._check_config()
            assert not passed
            assert "Not found" in msg

    def test_valid_config(self, mock_config_dir):
        config_file = mock_config_dir / "config.json"
        config_file.write_text(json.dumps({"audit_log_enabled": True}))
        with patch.object(doctor, "CONFIG_FILE", config_file):
            name, passed, msg = doctor._check_config()
            assert passed
            assert "Valid JSON" in msg

    def test_invalid_json(self, mock_config_dir):
        config_file = mock_config_dir / "config.json"
        config_file.write_text("{invalid")
        with patch.object(doctor, "CONFIG_FILE", config_file):
            name, passed, msg = doctor._check_config()
            assert not passed
            assert "Parse error" in msg


class TestCheckGitHubToken:
    @patch("termbackup.config.get_github_token", return_value="ghp_abc123xyz789")
    def test_token_found(self, mock_token):
        name, passed, msg = doctor._check_github_token()
        assert passed
        assert "Found" in msg

    @patch("termbackup.config.get_github_token", side_effect=SystemExit(1))
    def test_no_token(self, mock_token):
        name, passed, msg = doctor._check_github_token()
        assert not passed
        assert "Not configured" in msg


class TestCheckGitHubConnectivity:
    @patch("termbackup.config.get_github_token", return_value="ghp_test")
    @patch("httpx.get")
    def test_connected(self, mock_get, mock_token):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"login": "testuser"}
        mock_get.return_value = mock_resp
        name, passed, msg = doctor._check_github_connectivity()
        assert passed
        assert "testuser" in msg

    @patch("termbackup.config.get_github_token", return_value="ghp_test")
    @patch("httpx.get")
    def test_http_error(self, mock_get, mock_token):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_get.return_value = mock_resp
        name, passed, msg = doctor._check_github_connectivity()
        assert not passed
        assert "401" in msg

    @patch("termbackup.config.get_github_token", side_effect=SystemExit(1))
    def test_no_token(self, mock_token):
        name, passed, msg = doctor._check_github_connectivity()
        assert not passed


class TestCheckKeyring:
    @patch("keyring.get_password", return_value=None)
    def test_accessible(self, mock_keyring):
        name, passed, msg = doctor._check_keyring()
        assert passed
        assert "Accessible" in msg

    @patch("keyring.get_password", side_effect=Exception("No backend"))
    def test_error(self, mock_keyring):
        name, passed, msg = doctor._check_keyring()
        assert not passed
        assert "Error" in msg


class TestCheckProfiles:
    def test_no_profiles_dir(self, mock_config_dir):
        with patch.object(doctor, "PROFILES_DIR", mock_config_dir / "profiles"):
            name, passed, msg = doctor._check_profiles()
            assert passed

    def test_valid_profiles(self, mock_config_dir):
        profiles_dir = mock_config_dir / "profiles"
        profiles_dir.mkdir()
        profile_data = {
            "name": "test",
            "source_dir": str(mock_config_dir / "src"),
            "repo": "user/repo",
            "excludes": [],
        }
        (profiles_dir / "test.json").write_text(json.dumps(profile_data))
        with patch.object(doctor, "PROFILES_DIR", profiles_dir):
            name, passed, msg = doctor._check_profiles()
            assert passed
            assert "1 valid" in msg

    def test_invalid_profile(self, mock_config_dir):
        profiles_dir = mock_config_dir / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "bad.json").write_text(json.dumps({"name": "!!invalid!!"}))
        with patch.object(doctor, "PROFILES_DIR", profiles_dir):
            name, passed, msg = doctor._check_profiles()
            assert not passed


class TestCheckSigningKey:
    @patch("termbackup.signing.has_signing_key", return_value=True)
    def test_key_found(self, mock_has):
        name, passed, msg = doctor._check_signing_key()
        assert passed
        assert "Ed25519" in msg

    @patch("termbackup.signing.has_signing_key", return_value=False)
    def test_no_key(self, mock_has):
        name, passed, msg = doctor._check_signing_key()
        assert passed
        assert "optional" in msg.lower()


class TestCheckAuditLog:
    def test_writable(self, mock_config_dir):
        with patch("termbackup.audit.AUDIT_LOG_PATH", mock_config_dir / "audit.log"):
            name, passed, msg = doctor._check_audit_log()
            assert passed


class TestCheckTempFiles:
    def test_no_tmp_dir(self, mock_config_dir):
        with patch.object(doctor, "CONFIG_DIR", mock_config_dir):
            name, passed, msg = doctor._check_temp_files()
            assert passed
            assert "Clean" in msg

    def test_orphaned_files(self, mock_config_dir):
        tmp_dir = mock_config_dir / "tmp"
        tmp_dir.mkdir()
        (tmp_dir / "orphan.tbk").write_bytes(b"data")
        with patch.object(doctor, "CONFIG_DIR", mock_config_dir):
            name, passed, msg = doctor._check_temp_files()
            assert not passed
            assert "1 orphaned" in msg


class TestRunDoctor:
    @patch("termbackup.doctor._check_temp_files", return_value=("Temp Files", True, "Clean"))
    @patch("termbackup.doctor._check_audit_log", return_value=("Audit Log", True, "OK"))
    @patch("termbackup.doctor._check_signing_key", return_value=("Signing Key", True, "Not configured"))
    @patch("termbackup.doctor._check_profiles", return_value=("Profiles", True, "1 valid"))
    @patch("termbackup.doctor._check_keyring", return_value=("Keyring", True, "Accessible"))
    @patch("termbackup.doctor._check_github_connectivity", return_value=("GitHub API", True, "Connected"))
    @patch("termbackup.doctor._check_github_token", return_value=("GitHub Token", True, "Found"))
    @patch("termbackup.doctor._check_config", return_value=("Config", True, "Valid"))
    def test_all_pass(self, *mocks):
        doctor.run_doctor()
