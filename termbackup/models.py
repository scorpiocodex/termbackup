"""Pydantic v2 models for all TermBackup data structures."""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class BackupMode(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"


class ProfileConfig(BaseModel):
    """Validated backup profile configuration."""

    name: str
    source_dir: str
    repo: str
    excludes: list[str] = Field(default_factory=list)
    compression_level: int = Field(default=6, ge=0, le=9)
    max_backups: int | None = None
    retention_days: int | None = None
    backup_mode: BackupMode = BackupMode.FULL
    webhook_url: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Profile name must contain only alphanumeric characters, hyphens, and underscores")
        return v

    @field_validator("repo")
    @classmethod
    def validate_repo(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$", v):
            raise ValueError("Repository must be in 'user/repo' format")
        return v


class FileMetadata(BaseModel):
    """Metadata for a single backed-up file."""

    relative_path: str
    size: int
    sha256: str = Field(min_length=64, max_length=64)
    permissions: int
    modified_at: float


class ManifestData(BaseModel):
    """Complete backup manifest."""

    version: str = "1.0"
    os_name: str
    python_version: str
    architecture: str
    created_at: str
    backup_mode: BackupMode = BackupMode.FULL
    files: list[FileMetadata] = Field(default_factory=list)
    parent_backup_id: str | None = None
    backup_id: str | None = None


class LedgerEntry(BaseModel):
    """A single backup entry in the metadata ledger."""

    id: str
    filename: str
    sha256: str
    commit_sha: str
    size: int
    created_at: str
    file_count: int
    verified: bool = False
    verified_at: str | None = None
    archive_version: int = 1
    signature: str | None = None


class LedgerData(BaseModel):
    """Complete metadata ledger."""

    tool_version: str = "6.0"
    repository: str
    created_at: str
    backups: list[LedgerEntry] = Field(default_factory=list)


class AppConfig(BaseModel):
    """Application configuration."""

    github_token: str | None = None
    default_repo: str | None = None
    audit_log_enabled: bool = True


class ArchiveHeader(BaseModel):
    """Parsed archive file header."""

    model_config = {"arbitrary_types_allowed": True}

    version: int
    kdf_algorithm: str = "pbkdf2"
    kdf_params: dict = Field(default_factory=dict)
    salt: bytes
    iv_or_nonce: bytes
    payload_len: int
    header_size: int
