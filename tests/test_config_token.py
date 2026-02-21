"""Tests for config token validation integration."""

import json
from unittest.mock import MagicMock, patch

import pytest

from termbackup import config
from termbackup.token_validator import TokenInfo, TokenType, ValidationStatus


class TestValidateAndDisplayToken:
    """Tests for _validate_and_display_token."""

    @patch("termbackup.token_validator.validate_token")
    def test_valid_token_returns_true(self, mock_validate, mock_config_dir):
        mock_validate.return_value = TokenInfo(
            status=ValidationStatus.VALID,
            token_type=TokenType.CLASSIC,
            username="testuser",
        )
        is_valid, username = config._validate_and_display_token("ghp_test123")
        assert is_valid is True
        assert username == "testuser"

    @patch("termbackup.token_validator.validate_token")
    def test_invalid_token_returns_false(self, mock_validate, mock_config_dir):
        mock_validate.return_value = TokenInfo(
            status=ValidationStatus.INVALID,
            message="Bad credentials",
        )
        is_valid, username = config._validate_and_display_token("bad_token")
        assert is_valid is False
        assert username is None

    @patch("termbackup.token_validator.validate_token")
    def test_network_error_returns_true(self, mock_validate, mock_config_dir):
        """Network errors shouldn't block init."""
        mock_validate.return_value = TokenInfo(
            status=ValidationStatus.NETWORK_ERROR,
            message="Connection failed",
        )
        is_valid, username = config._validate_and_display_token("ghp_test123")
        assert is_valid is True

    @patch("termbackup.token_validator.validate_token")
    def test_rate_limited_returns_true(self, mock_validate, mock_config_dir):
        mock_validate.return_value = TokenInfo(
            status=ValidationStatus.RATE_LIMITED,
            message="Rate limited",
        )
        is_valid, username = config._validate_and_display_token("ghp_test123")
        assert is_valid is True

    @patch("termbackup.token_validator.validate_token")
    def test_insufficient_scope_returns_true(self, mock_validate, mock_config_dir):
        """Insufficient scope warns but doesn't block."""
        mock_validate.return_value = TokenInfo(
            status=ValidationStatus.INSUFFICIENT_SCOPE,
            message="Missing repo scope",
            username="testuser",
        )
        is_valid, username = config._validate_and_display_token("ghp_test123")
        assert is_valid is True
        assert username == "testuser"

    @patch("termbackup.token_validator.validate_token")
    def test_expired_token_returns_false(self, mock_validate, mock_config_dir):
        mock_validate.return_value = TokenInfo(
            status=ValidationStatus.EXPIRED,
            message="Token expired",
        )
        is_valid, username = config._validate_and_display_token("ghp_expired")
        assert is_valid is False
        assert username is None


class TestUpdateToken:
    """Tests for the update_token function."""

    @patch("termbackup.credentials.save_token")
    @patch("termbackup.config._validate_and_display_token")
    def test_update_valid_token(self, mock_validate, mock_save_cred, mock_config_dir):
        mock_validate.return_value = (True, "testuser")
        # Create initial config
        config_data = {"github_token": "old_token"}
        (mock_config_dir / "config.json").write_text(json.dumps(config_data))

        result = config.update_token("ghp_new_token")
        assert result is True

        # Verify file was updated
        with open(mock_config_dir / "config.json") as f:
            data = json.load(f)
        assert data["github_token"] == "ghp_new_token"

    @patch("termbackup.config._validate_and_display_token")
    def test_update_empty_token(self, mock_validate, mock_config_dir):
        result = config.update_token("")
        assert result is False
        mock_validate.assert_not_called()

    @patch("termbackup.config._validate_and_display_token")
    @patch("termbackup.config.ui.confirm")
    def test_update_invalid_token_user_declines(self, mock_confirm, mock_validate, mock_config_dir):
        mock_validate.return_value = (False, None)
        mock_confirm.return_value = False
        config_data = {"github_token": "old_token"}
        (mock_config_dir / "config.json").write_text(json.dumps(config_data))

        result = config.update_token("bad_token")
        assert result is False

    @patch("termbackup.credentials.save_token")
    @patch("termbackup.config._validate_and_display_token")
    @patch("termbackup.config.ui.confirm")
    def test_update_invalid_token_user_confirms(self, mock_confirm, mock_validate, mock_save_cred, mock_config_dir):
        mock_validate.return_value = (False, None)
        mock_confirm.return_value = True
        config_data = {"github_token": "old_token"}
        (mock_config_dir / "config.json").write_text(json.dumps(config_data))

        result = config.update_token("questionable_token")
        assert result is True

    @patch("termbackup.credentials.save_token")
    @patch("termbackup.config._validate_and_display_token")
    def test_update_whitespace_stripped(self, mock_validate, mock_save_cred, mock_config_dir):
        mock_validate.return_value = (True, "testuser")
        config_data = {"github_token": "old"}
        (mock_config_dir / "config.json").write_text(json.dumps(config_data))

        config.update_token("  ghp_spaced_token  ")

        with open(mock_config_dir / "config.json") as f:
            data = json.load(f)
        assert data["github_token"] == "ghp_spaced_token"


class TestInitConfigWithValidation:
    """Tests for init_config with token validation."""

    @patch("termbackup.config.ui.confirm_default_yes")
    @patch("termbackup.config._validate_and_display_token")
    @patch("termbackup.config.ui.prompt_secret")
    def test_init_with_valid_token(self, mock_prompt, mock_validate, mock_confirm_repo, mock_config_dir):
        mock_prompt.return_value = "ghp_valid_token_123"
        mock_validate.return_value = (True, "testuser")
        mock_confirm_repo.return_value = False  # Skip repo creation

        config.init_config()

        assert (mock_config_dir / "config.json").exists()
        with open(mock_config_dir / "config.json") as f:
            data = json.load(f)
        assert data["github_token"] == "ghp_valid_token_123"

    @patch("termbackup.config.ui.confirm_default_yes")
    @patch("termbackup.config._validate_and_display_token")
    @patch("termbackup.config.ui.prompt_secret")
    def test_init_retries_on_invalid(self, mock_prompt, mock_validate, mock_confirm_repo, mock_config_dir):
        # First two attempts invalid, third valid
        mock_prompt.side_effect = ["bad_token", "bad_token2", "ghp_valid"]
        mock_validate.side_effect = [(False, None), (False, None), (True, "testuser")]
        mock_confirm_repo.return_value = False  # Skip repo creation

        config.init_config()

        assert mock_prompt.call_count == 3
        with open(mock_config_dir / "config.json") as f:
            data = json.load(f)
        assert data["github_token"] == "ghp_valid"

    @patch("termbackup.config.ui.confirm")
    @patch("termbackup.config._validate_and_display_token")
    @patch("termbackup.config.ui.prompt_secret")
    def test_init_all_attempts_fail_user_saves_anyway(self, mock_prompt, mock_validate, mock_confirm, mock_config_dir):
        mock_prompt.side_effect = ["bad1", "bad2", "bad3"]
        mock_validate.side_effect = [(False, None), (False, None), (False, None)]
        mock_confirm.return_value = True

        config.init_config()

        assert (mock_config_dir / "config.json").exists()

    @patch("termbackup.config.ui.confirm")
    @patch("termbackup.config._validate_and_display_token")
    @patch("termbackup.config.ui.prompt_secret")
    def test_init_all_attempts_fail_user_cancels(self, mock_prompt, mock_validate, mock_confirm, mock_config_dir):
        mock_prompt.side_effect = ["bad1", "bad2", "bad3"]
        mock_validate.side_effect = [(False, None), (False, None), (False, None)]
        mock_confirm.return_value = False

        with pytest.raises(SystemExit):
            config.init_config()

    @patch("termbackup.config.ui.confirm_default_yes")
    @patch("termbackup.config._validate_and_display_token")
    @patch("termbackup.config.ui.prompt_secret")
    def test_init_empty_token_retries(self, mock_prompt, mock_validate, mock_confirm_repo, mock_config_dir):
        mock_prompt.side_effect = ["", "", "ghp_valid"]
        mock_validate.return_value = (True, "testuser")
        mock_confirm_repo.return_value = False  # Skip repo creation

        config.init_config()

        # validate only called once (for the non-empty token)
        mock_validate.assert_called_once_with("ghp_valid")

    def test_init_config_already_exists(self, mock_config_dir):
        (mock_config_dir / "config.json").write_text("{}")

        with pytest.raises(SystemExit):
            config.init_config()

    @patch("termbackup.config.ui.prompt_input_default")
    @patch("termbackup.config.ui.confirm_default_yes")
    @patch("termbackup.config._validate_and_display_token")
    @patch("termbackup.config.ui.prompt_secret")
    def test_init_with_repo_creation(
        self, mock_prompt, mock_validate, mock_confirm_repo,
        mock_repo_name, mock_config_dir,
    ):
        mock_prompt.return_value = "ghp_valid_token_123"
        mock_validate.return_value = (True, "testuser")
        mock_confirm_repo.return_value = True
        mock_repo_name.return_value = "termbackup-storage"

        # Mock the github module via the lazy loader
        mock_gh = MagicMock()
        mock_gh.create_repo.return_value = "testuser/termbackup-storage"
        import termbackup.config as cfg
        original_get_github = cfg._get_github
        cfg._get_github = lambda: mock_gh
        cfg.github = mock_gh

        try:
            config.init_config()

            mock_gh.create_repo.assert_called_once_with("ghp_valid_token_123", "termbackup-storage")
            mock_gh.init_repo_structure.assert_called_once_with("ghp_valid_token_123", "testuser/termbackup-storage")

            with open(mock_config_dir / "config.json") as f:
                data = json.load(f)
            assert data["default_repo"] == "testuser/termbackup-storage"
        finally:
            cfg._get_github = original_get_github
            cfg.github = None

    @patch("termbackup.config.ui.confirm_default_yes")
    @patch("termbackup.config._validate_and_display_token")
    @patch("termbackup.config.ui.prompt_secret")
    def test_init_skip_repo_creation(self, mock_prompt, mock_validate, mock_confirm_repo, mock_config_dir):
        mock_prompt.return_value = "ghp_valid_token_123"
        mock_validate.return_value = (True, "testuser")
        mock_confirm_repo.return_value = False

        config.init_config()

        with open(mock_config_dir / "config.json") as f:
            data = json.load(f)
        assert data.get("default_repo") is None
