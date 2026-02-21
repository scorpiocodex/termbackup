"""Integration tests for the CLI commands using Typer's CliRunner."""

from unittest.mock import patch

from typer.testing import CliRunner

from termbackup.cli import app
from termbackup.models import AppConfig, ProfileConfig

runner = CliRunner()


class TestMainApp:
    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0

    def test_no_command_shows_banner(self):
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "USAGE" in result.output

    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "init" in result.output
        assert "run" in result.output
        assert "list" in result.output
        assert "doctor" in result.output
        assert "diff" in result.output
        assert "rotate-key" in result.output
        assert "daemon" in result.output


class TestInitCommand:
    @patch("termbackup.cli.config.init_config")
    def test_init(self, mock_init):
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        mock_init.assert_called_once()

    @patch("termbackup.cli.config.init_config")
    def test_already_exists(self, mock_init):
        mock_init.side_effect = SystemExit(0)
        runner.invoke(app, ["init"])


class TestRunCommand:
    @patch("termbackup.cli.engine.run_backup")
    @patch("termbackup.cli.ui.prompt_secret")
    @patch("termbackup.cli.config.get_profile")
    @patch("termbackup.cli.config.get_config")
    def test_password_mismatch(self, mock_config, mock_profile, mock_secret, mock_run):
        mock_config.return_value = AppConfig()
        mock_profile.return_value = ProfileConfig(name="test", source_dir="/src", repo="u/r", excludes=[])
        mock_secret.side_effect = ["password1", "password2"]

        result = runner.invoke(app, ["run", "test-profile"])
        assert result.exit_code == 1

    @patch("termbackup.cli.config.get_profile")
    @patch("termbackup.cli.config.get_config")
    def test_missing_profile(self, mock_config, mock_profile):
        mock_config.return_value = AppConfig()
        mock_profile.side_effect = SystemExit(1)

        runner.invoke(app, ["run", "nonexistent"])


class TestListCommand:
    @patch("termbackup.cli.listing.list_backups")
    def test_success(self, mock_list):
        result = runner.invoke(app, ["list", "test-profile"])
        assert result.exit_code == 0
        mock_list.assert_called_once_with("test-profile")

    @patch("termbackup.cli.listing.list_backups")
    def test_runtime_error(self, mock_list):
        mock_list.side_effect = RuntimeError("API error")
        result = runner.invoke(app, ["list", "test-profile"])
        assert result.exit_code == 1


class TestRestoreCommand:
    @patch("termbackup.cli.restore_module.restore_backup")
    @patch("termbackup.cli.ui.prompt_secret", return_value="pass")
    @patch("termbackup.cli.config.get_profile")
    @patch("termbackup.cli.config.get_config")
    def test_success(self, mock_config, mock_profile, mock_secret, mock_restore):
        mock_config.return_value = AppConfig()
        mock_profile.return_value = ProfileConfig(name="p", source_dir="/src", repo="u/r", excludes=[])

        result = runner.invoke(app, ["restore", "abc123", "--profile", "p"])
        assert result.exit_code == 0
        mock_restore.assert_called_once()

    @patch("termbackup.cli.restore_module.restore_backup")
    @patch("termbackup.cli.ui.prompt_secret", return_value="pass")
    @patch("termbackup.cli.config.get_profile")
    @patch("termbackup.cli.config.get_config")
    def test_runtime_error(self, mock_config, mock_profile, mock_secret, mock_restore):
        mock_config.return_value = AppConfig()
        mock_profile.return_value = ProfileConfig(name="p", source_dir="/src", repo="u/r", excludes=[])
        mock_restore.side_effect = RuntimeError("download failed")

        result = runner.invoke(app, ["restore", "abc123", "--profile", "p"])
        assert result.exit_code == 1


class TestVerifyCommand:
    @patch("termbackup.cli.verify_module.verify_backup")
    @patch("termbackup.cli.ui.prompt_secret", return_value="pass")
    @patch("termbackup.cli.config.get_profile")
    @patch("termbackup.cli.config.get_config")
    def test_success(self, mock_config, mock_profile, mock_secret, mock_verify):
        mock_config.return_value = AppConfig()
        mock_profile.return_value = ProfileConfig(name="p", source_dir="/src", repo="u/r", excludes=[])

        result = runner.invoke(app, ["verify", "abc123", "--profile", "p"])
        assert result.exit_code == 0
        mock_verify.assert_called_once()

    @patch("termbackup.cli.verify_module.verify_backup")
    @patch("termbackup.cli.ui.prompt_secret", return_value="pass")
    @patch("termbackup.cli.config.get_profile")
    @patch("termbackup.cli.config.get_config")
    def test_runtime_error(self, mock_config, mock_profile, mock_secret, mock_verify):
        mock_config.return_value = AppConfig()
        mock_profile.return_value = ProfileConfig(name="p", source_dir="/src", repo="u/r", excludes=[])
        mock_verify.side_effect = RuntimeError("verify failed")

        result = runner.invoke(app, ["verify", "abc123", "--profile", "p"])
        assert result.exit_code == 1


class TestStatusCommand:
    @patch("termbackup.signing.has_signing_key", return_value=False)
    @patch("termbackup.cli.config.get_all_profiles", return_value=[])
    @patch("termbackup.cli.config.CONFIG_FILE")
    def test_without_config(self, mock_file, mock_profiles, mock_signing):
        mock_file.exists.return_value = False
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0

    @patch("termbackup.signing.has_signing_key", return_value=False)
    @patch("termbackup.cli.config.get_all_profiles")
    @patch("termbackup.cli.config.CONFIG_FILE")
    def test_with_profiles(self, mock_file, mock_profiles, mock_signing):
        mock_file.exists.return_value = True
        mock_profiles.return_value = [
            ProfileConfig(name="p1", source_dir="/src", repo="u/r", excludes=[]),
        ]
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0


class TestProfileCommands:
    @patch("termbackup.cli.config.create_profile")
    def test_profile_create(self, mock_create):
        result = runner.invoke(app, [
            "profile", "create", "my-profile",
            "--source", "/tmp/src",
            "--repo", "user/repo",
        ])
        assert result.exit_code == 0

    @patch("termbackup.cli.config.get_all_profiles", return_value=[])
    def test_profile_list(self, mock_profiles):
        result = runner.invoke(app, ["profile", "list"])
        assert result.exit_code == 0

    @patch("termbackup.cli.config.get_profile")
    def test_profile_show(self, mock_profile):
        mock_profile.return_value = ProfileConfig(
            name="test", source_dir="/src", repo="u/r", excludes=[]
        )
        result = runner.invoke(app, ["profile", "show", "test"])
        assert result.exit_code == 0

    @patch("termbackup.cli.config.delete_profile")
    @patch("termbackup.cli.config.get_profile")
    def test_profile_delete(self, mock_get, mock_delete):
        mock_get.return_value = ProfileConfig(name="test", source_dir="/src", repo="u/r", excludes=[])
        result = runner.invoke(app, ["profile", "delete", "test"], input="y\n")
        assert result.exit_code == 0


class TestDoctorCommand:
    @patch("termbackup.doctor.run_doctor")
    def test_doctor(self, mock_doctor):
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        mock_doctor.assert_called_once()


class TestDiffCommand:
    @patch("termbackup.diff.diff_backups", return_value={"added": [], "modified": [], "deleted": [], "unchanged": []})
    @patch("termbackup.cli.ui.prompt_secret", return_value="pass")
    @patch("termbackup.cli.config.get_profile")
    @patch("termbackup.cli.config.get_config")
    def test_diff(self, mock_config, mock_profile, mock_secret, mock_diff):
        mock_config.return_value = AppConfig()
        mock_profile.return_value = ProfileConfig(name="p", source_dir="/src", repo="u/r", excludes=[])

        result = runner.invoke(app, ["diff", "id1", "id2", "--profile", "p"])
        assert result.exit_code == 0


class TestRotateKeyCommand:
    @patch("termbackup.rotate_key.rotate_key")
    @patch("termbackup.cli.ui.prompt_secret")
    @patch("termbackup.cli.config.get_profile")
    @patch("termbackup.cli.config.get_config")
    def test_rotate_key(self, mock_config, mock_profile, mock_secret, mock_rotate):
        mock_config.return_value = AppConfig()
        mock_profile.return_value = ProfileConfig(name="p", source_dir="/src", repo="u/r", excludes=[])
        mock_secret.side_effect = ["oldpass", "newpass", "newpass"]

        result = runner.invoke(app, ["rotate-key", "p"])
        assert result.exit_code == 0
        mock_rotate.assert_called_once()

    @patch("termbackup.cli.ui.prompt_secret")
    @patch("termbackup.cli.config.get_profile")
    @patch("termbackup.cli.config.get_config")
    def test_rotate_key_password_mismatch(self, mock_config, mock_profile, mock_secret):
        mock_config.return_value = AppConfig()
        mock_profile.return_value = ProfileConfig(name="p", source_dir="/src", repo="u/r", excludes=[])
        mock_secret.side_effect = ["oldpass", "newpass1", "newpass2"]

        result = runner.invoke(app, ["rotate-key", "p"])
        assert result.exit_code == 1
