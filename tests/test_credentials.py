"""Tests for the credential storage module."""

from unittest.mock import MagicMock, patch

import pytest

from termbackup import credentials


@pytest.fixture(autouse=True)
def mock_keyring():
    """Mock the keyring module for all credential tests."""
    mock_kr = MagicMock()
    mock_kr.errors.PasswordDeleteError = type("PasswordDeleteError", (Exception,), {})
    with patch.dict("sys.modules", {"keyring": mock_kr, "keyring.errors": mock_kr.errors}):
        yield mock_kr


class TestTokenStorage:
    def test_save_token(self, mock_keyring):
        credentials.save_token("ghp_test123")
        mock_keyring.set_password.assert_called_once_with(
            "termbackup", "github_token", "ghp_test123"
        )

    def test_get_token(self, mock_keyring):
        mock_keyring.get_password.return_value = "ghp_test123"
        result = credentials.get_token()
        assert result == "ghp_test123"
        mock_keyring.get_password.assert_called_once_with("termbackup", "github_token")

    def test_get_token_not_found(self, mock_keyring):
        mock_keyring.get_password.return_value = None
        result = credentials.get_token()
        assert result is None

    def test_delete_token(self, mock_keyring):
        credentials.delete_token()
        mock_keyring.delete_password.assert_called_once_with("termbackup", "github_token")

    def test_delete_token_not_exists(self, mock_keyring):
        mock_keyring.delete_password.side_effect = mock_keyring.errors.PasswordDeleteError()
        credentials.delete_token()  # Should not raise


class TestProfilePasswordStorage:
    def test_save_profile_password(self, mock_keyring):
        credentials.save_profile_password("my-profile", "secret123")
        mock_keyring.set_password.assert_called_once_with(
            "termbackup", "profile_password_my-profile", "secret123"
        )

    def test_get_profile_password(self, mock_keyring):
        mock_keyring.get_password.return_value = "secret123"
        result = credentials.get_profile_password("my-profile")
        assert result == "secret123"
