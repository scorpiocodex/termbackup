"""Tests for the GitHub token validation module."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from termbackup.token_validator import (
    TokenInfo,
    TokenType,
    ValidationStatus,
    _parse_rate_limit,
    _parse_scopes,
    detect_token_type,
    mask_token,
    validate_token,
    validate_token_for_repo,
)


class TestDetectTokenType:
    """Tests for token type detection from prefix."""

    def test_classic_ghp_prefix(self):
        assert detect_token_type("ghp_abc123def456xyz") == TokenType.CLASSIC

    def test_fine_grained_prefix(self):
        assert detect_token_type("github_pat_abc123def456xyz") == TokenType.FINE_GRAINED

    def test_old_hex_token(self):
        token = "a" * 40
        assert detect_token_type(token) == TokenType.CLASSIC

    def test_oauth_token(self):
        assert detect_token_type("gho_abc123def") == TokenType.CLASSIC

    def test_app_installation_token(self):
        assert detect_token_type("ghs_abc123def") == TokenType.CLASSIC

    def test_user_to_server_token(self):
        assert detect_token_type("ghu_abc123def") == TokenType.CLASSIC

    def test_unknown_format(self):
        assert detect_token_type("random_unknown_token") == TokenType.UNKNOWN

    def test_empty_token(self):
        assert detect_token_type("") == TokenType.UNKNOWN

    def test_whitespace_stripped(self):
        assert detect_token_type("  ghp_abc123def  ") == TokenType.CLASSIC


class TestMaskToken:
    """Tests for token masking."""

    def test_classic_token(self):
        result = mask_token("ghp_abcdefghijk12345")
        assert result.startswith("ghp_")
        assert result.endswith("2345")
        assert "****" in result

    def test_fine_grained_token(self):
        result = mask_token("github_pat_abcdefghijk12345")
        assert result.startswith("github_pat_")
        assert result.endswith("2345")
        assert "****" in result

    def test_short_token(self):
        result = mask_token("short")
        assert result == "****"

    def test_empty_token(self):
        result = mask_token("")
        assert result == "****"

    def test_hex_token(self):
        token = "abcdef" + "0" * 30 + "1234"
        result = mask_token(token)
        assert result.startswith("abcd")
        assert result.endswith("1234")


class TestParseRateLimit:
    """Tests for rate limit header parsing."""

    def test_valid_headers(self):
        headers = httpx.Headers({
            "x-ratelimit-remaining": "4990",
            "x-ratelimit-limit": "5000",
            "x-ratelimit-reset": "1700000000",
        })
        remaining, total, reset = _parse_rate_limit(headers)
        assert remaining == 4990
        assert total == 5000
        assert "UTC" in reset

    def test_missing_headers(self):
        headers = httpx.Headers({})
        remaining, total, reset = _parse_rate_limit(headers)
        assert remaining == 0
        assert total == 0
        assert reset == ""

    def test_partial_headers(self):
        headers = httpx.Headers({"x-ratelimit-remaining": "100"})
        remaining, total, reset = _parse_rate_limit(headers)
        assert remaining == 100
        assert total == 0


class TestParseScopes:
    """Tests for OAuth scope parsing."""

    def test_multiple_scopes(self):
        headers = httpx.Headers({"x-oauth-scopes": "repo, user, gist"})
        scopes = _parse_scopes(headers)
        assert scopes == ["repo", "user", "gist"]

    def test_single_scope(self):
        headers = httpx.Headers({"x-oauth-scopes": "repo"})
        scopes = _parse_scopes(headers)
        assert scopes == ["repo"]

    def test_no_scopes_header(self):
        headers = httpx.Headers({})
        scopes = _parse_scopes(headers)
        assert scopes == []

    def test_empty_scopes(self):
        headers = httpx.Headers({"x-oauth-scopes": ""})
        scopes = _parse_scopes(headers)
        assert scopes == []


class TestValidateToken:
    """Tests for the main token validation function."""

    def test_empty_token(self):
        result = validate_token("")
        assert result.status == ValidationStatus.INVALID
        assert "empty" in result.message.lower()

    def test_whitespace_only_token(self):
        result = validate_token("   ")
        assert result.status == ValidationStatus.INVALID

    @patch("termbackup.token_validator.httpx.get")
    def test_valid_classic_token(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"login": "testuser", "id": 12345}
        mock_response.headers = httpx.Headers({
            "x-oauth-scopes": "repo, user",
            "x-ratelimit-remaining": "4999",
            "x-ratelimit-limit": "5000",
            "x-ratelimit-reset": "1700000000",
        })
        mock_get.return_value = mock_response

        result = validate_token("ghp_test1234567890abcdef")
        assert result.status == ValidationStatus.VALID
        assert result.token_type == TokenType.CLASSIC
        assert result.username == "testuser"
        assert "repo" in result.scopes
        assert result.rate_limit_remaining == 4999

    @patch("termbackup.token_validator.httpx.get")
    def test_valid_fine_grained_token(self, mock_get):
        # Fine-grained tokens don't return X-OAuth-Scopes
        # First call: /user (main validation)
        user_response = MagicMock()
        user_response.status_code = 200
        user_response.json.return_value = {"login": "testuser", "id": 12345}
        user_response.headers = httpx.Headers({
            "x-ratelimit-remaining": "4999",
            "x-ratelimit-limit": "5000",
            "x-ratelimit-reset": "1700000000",
        })

        # Second call: /user/repos (permission check)
        repos_response = MagicMock()
        repos_response.status_code = 200
        repos_response.json.return_value = []
        repos_response.headers = httpx.Headers({})

        mock_get.side_effect = [user_response, repos_response]

        result = validate_token("github_pat_test1234567890abcdef")
        assert result.status == ValidationStatus.VALID
        assert result.token_type == TokenType.FINE_GRAINED
        assert result.username == "testuser"

    @patch("termbackup.token_validator.httpx.get")
    def test_invalid_token_401(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Bad credentials"}
        mock_response.headers = httpx.Headers({})
        mock_get.return_value = mock_response

        result = validate_token("ghp_invalid_token_here")
        assert result.status == ValidationStatus.INVALID
        assert result.token_type == TokenType.CLASSIC

    @patch("termbackup.token_validator.httpx.get")
    def test_expired_token(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Token expired"}
        mock_response.headers = httpx.Headers({})
        mock_get.return_value = mock_response

        result = validate_token("ghp_expired_token")
        assert result.status == ValidationStatus.EXPIRED

    @patch("termbackup.token_validator.httpx.get")
    def test_forbidden_403(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = httpx.Headers({
            "x-ratelimit-remaining": "0",
            "x-ratelimit-limit": "5000",
            "x-ratelimit-reset": "1700000000",
        })
        mock_get.return_value = mock_response

        result = validate_token("ghp_forbidden_token")
        assert result.status == ValidationStatus.INSUFFICIENT_SCOPE

    @patch("termbackup.token_validator.httpx.get")
    def test_rate_limited_429(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = httpx.Headers({
            "x-ratelimit-remaining": "0",
            "x-ratelimit-limit": "5000",
            "x-ratelimit-reset": "1700000000",
        })
        mock_get.return_value = mock_response

        result = validate_token("ghp_rate_limited")
        assert result.status == ValidationStatus.RATE_LIMITED

    @patch("termbackup.token_validator.httpx.get")
    def test_timeout_error(self, mock_get):
        mock_get.side_effect = httpx.TimeoutException("timed out")

        result = validate_token("ghp_timeout_token")
        assert result.status == ValidationStatus.NETWORK_ERROR
        assert "timed out" in result.message.lower()

    @patch("termbackup.token_validator.httpx.get")
    def test_connect_error(self, mock_get):
        mock_get.side_effect = httpx.ConnectError("connection refused")

        result = validate_token("ghp_connect_error")
        assert result.status == ValidationStatus.NETWORK_ERROR

    @patch("termbackup.token_validator.httpx.get")
    def test_missing_repo_scope(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"login": "testuser", "id": 12345}
        mock_response.headers = httpx.Headers({
            "x-oauth-scopes": "user, gist",  # Missing 'repo'
            "x-ratelimit-remaining": "4999",
            "x-ratelimit-limit": "5000",
            "x-ratelimit-reset": "1700000000",
        })
        mock_get.return_value = mock_response

        result = validate_token("ghp_missing_scope")
        assert result.status == ValidationStatus.INSUFFICIENT_SCOPE
        assert "repo" in result.missing_scopes

    @patch("termbackup.token_validator.httpx.get")
    def test_unexpected_status_code(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = httpx.Headers({})
        mock_get.return_value = mock_response

        result = validate_token("ghp_server_error")
        assert result.status == ValidationStatus.INVALID
        assert "500" in result.message


class TestValidateTokenForRepo:
    """Tests for repo-specific token validation."""

    @patch("termbackup.token_validator.httpx.get")
    def test_valid_token_with_repo_access(self, mock_get):
        # /user response
        user_response = MagicMock()
        user_response.status_code = 200
        user_response.json.return_value = {"login": "testuser", "id": 12345}
        user_response.headers = httpx.Headers({
            "x-oauth-scopes": "repo",
            "x-ratelimit-remaining": "4999",
            "x-ratelimit-limit": "5000",
            "x-ratelimit-reset": "1700000000",
        })

        # /repos/owner/repo response
        repo_response = MagicMock()
        repo_response.status_code = 200
        repo_response.json.return_value = {
            "full_name": "owner/repo",
            "permissions": {"push": True, "pull": True, "admin": False},
        }
        repo_response.headers = httpx.Headers({})

        mock_get.side_effect = [user_response, repo_response]

        result = validate_token_for_repo("ghp_valid_token", "owner/repo")
        assert result.status == ValidationStatus.VALID
        assert "write access" in result.message

    @patch("termbackup.token_validator.httpx.get")
    def test_repo_not_found(self, mock_get):
        user_response = MagicMock()
        user_response.status_code = 200
        user_response.json.return_value = {"login": "testuser", "id": 12345}
        user_response.headers = httpx.Headers({
            "x-oauth-scopes": "repo",
            "x-ratelimit-remaining": "4999",
            "x-ratelimit-limit": "5000",
            "x-ratelimit-reset": "1700000000",
        })

        repo_response = MagicMock()
        repo_response.status_code = 404
        repo_response.headers = httpx.Headers({})

        mock_get.side_effect = [user_response, repo_response]

        result = validate_token_for_repo("ghp_valid_token", "owner/nonexistent")
        assert result.status == ValidationStatus.INSUFFICIENT_SCOPE
        assert "not found" in result.message.lower()

    @patch("termbackup.token_validator.httpx.get")
    def test_read_only_access(self, mock_get):
        user_response = MagicMock()
        user_response.status_code = 200
        user_response.json.return_value = {"login": "testuser", "id": 12345}
        user_response.headers = httpx.Headers({
            "x-oauth-scopes": "repo",
            "x-ratelimit-remaining": "4999",
            "x-ratelimit-limit": "5000",
            "x-ratelimit-reset": "1700000000",
        })

        repo_response = MagicMock()
        repo_response.status_code = 200
        repo_response.json.return_value = {
            "full_name": "owner/repo",
            "permissions": {"push": False, "pull": True, "admin": False},
        }
        repo_response.headers = httpx.Headers({})

        mock_get.side_effect = [user_response, repo_response]

        result = validate_token_for_repo("ghp_readonly", "owner/repo")
        assert result.status == ValidationStatus.INSUFFICIENT_SCOPE
        assert "read-only" in result.message.lower()


class TestTokenInfoDataclass:
    """Tests for the TokenInfo dataclass."""

    def test_default_values(self):
        info = TokenInfo(status=ValidationStatus.VALID)
        assert info.token_type == TokenType.UNKNOWN
        assert info.username == ""
        assert info.scopes == []
        assert info.permissions == {}
        assert info.missing_scopes == []
        assert info.message == ""

    def test_full_creation(self):
        info = TokenInfo(
            status=ValidationStatus.VALID,
            token_type=TokenType.CLASSIC,
            username="testuser",
            scopes=["repo", "user"],
            rate_limit_remaining=4999,
            rate_limit_total=5000,
            masked_token="ghp_****5678",
            message="All good",
        )
        assert info.status == ValidationStatus.VALID
        assert info.username == "testuser"
        assert len(info.scopes) == 2
        assert info.rate_limit_remaining == 4999
