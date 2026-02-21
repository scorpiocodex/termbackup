"""Tests for the structured error hierarchy."""

import pytest

from termbackup.errors import (
    ArchiveError,
    BackupError,
    ConfigError,
    CryptoError,
    GitHubError,
    IntegrityError,
    ProfileError,
    RestoreError,
    TermBackupError,
    TokenError,
)


class TestErrorHierarchy:
    """All error types inherit from TermBackupError."""

    def test_base_error(self):
        err = TermBackupError("test error")
        assert str(err) == "test error"
        assert err.hint is None

    def test_base_error_with_hint(self):
        err = TermBackupError("test error", hint="try this")
        assert err.hint == "try this"

    def test_config_error_inherits(self):
        err = ConfigError("config issue")
        assert isinstance(err, TermBackupError)

    def test_profile_error_inherits(self):
        err = ProfileError("profile issue")
        assert isinstance(err, TermBackupError)

    def test_crypto_error_inherits(self):
        err = CryptoError("crypto issue")
        assert isinstance(err, TermBackupError)

    def test_archive_error_inherits(self):
        err = ArchiveError("archive issue")
        assert isinstance(err, TermBackupError)

    def test_github_error_inherits(self):
        err = GitHubError("github issue", status_code=404)
        assert isinstance(err, TermBackupError)
        assert err.status_code == 404

    def test_github_error_with_hint(self):
        err = GitHubError("auth failed", status_code=401, hint="check token")
        assert err.hint == "check token"
        assert err.status_code == 401

    def test_token_error_inherits(self):
        assert issubclass(TokenError, TermBackupError)

    def test_restore_error_inherits(self):
        assert issubclass(RestoreError, TermBackupError)

    def test_backup_error_inherits(self):
        assert issubclass(BackupError, TermBackupError)

    def test_integrity_error_inherits(self):
        assert issubclass(IntegrityError, TermBackupError)

    def test_catch_all(self):
        """Can catch all specific errors with TermBackupError."""
        errors = [
            ConfigError("a"),
            ProfileError("b"),
            CryptoError("c"),
            GitHubError("d"),
        ]
        for err in errors:
            with pytest.raises(TermBackupError):
                raise err
