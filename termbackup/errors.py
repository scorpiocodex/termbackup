"""Structured error hierarchy for TermBackup.

All TermBackup errors inherit from TermBackupError, enabling clean
catch-all handling while preserving specific error types for targeted
error handling in calling code.
"""


class TermBackupError(Exception):
    """Base exception for all TermBackup errors."""

    def __init__(self, message: str, *, hint: str | None = None):
        super().__init__(message)
        self.hint = hint


class ConfigError(TermBackupError):
    """Configuration-related errors (missing config, invalid values)."""


class ProfileError(TermBackupError):
    """Profile-related errors (missing, invalid, duplicate)."""


class CryptoError(TermBackupError):
    """Encryption/decryption errors (wrong password, corrupted data)."""


class ArchiveError(TermBackupError):
    """Archive format errors (invalid magic bytes, corrupted headers)."""


class GitHubError(TermBackupError):
    """GitHub API errors (auth, network, rate limiting)."""

    def __init__(self, message: str, *, status_code: int | None = None, hint: str | None = None):
        super().__init__(message, hint=hint)
        self.status_code = status_code


class TokenError(TermBackupError):
    """Token validation errors (invalid, expired, insufficient scope)."""


class RestoreError(TermBackupError):
    """Restore operation errors (missing backup, path traversal)."""


class BackupError(TermBackupError):
    """Backup operation errors (source not found, upload failed)."""


class IntegrityError(TermBackupError):
    """Data integrity verification errors (checksum mismatch, tampered data)."""
