"""Local configuration and profile management for TermBackup."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


CONFIG_DIR = Path.home() / ".termbackup"
CONFIG_FILE = CONFIG_DIR / "config.json"


class ConfigError(Exception):
    """Raised when configuration operations fail."""


@dataclass
class Profile:
    """Backup profile definition."""

    name: str
    source_directory: str
    exclude_patterns: list[str] = field(default_factory=list)
    password_env_var: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert profile to dictionary."""
        return {
            "name": self.name,
            "source_directory": self.source_directory,
            "exclude_patterns": self.exclude_patterns,
            "password_env_var": self.password_env_var,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        """Create profile from dictionary."""
        return cls(
            name=data["name"],
            source_directory=data["source_directory"],
            exclude_patterns=data.get("exclude_patterns", []),
            password_env_var=data.get("password_env_var"),
        )

    def get_source_path(self) -> Path:
        """Get source directory as Path object."""
        return Path(self.source_directory).expanduser().resolve()

    def validate(self) -> list[str]:
        """Validate profile configuration.

        Returns:
            List of validation error messages.
        """
        errors = []
        source = self.get_source_path()

        if not source.exists():
            errors.append(f"Source directory does not exist: {source}")
        elif not source.is_dir():
            errors.append(f"Source path is not a directory: {source}")

        return errors


@dataclass
class Config:
    """Global TermBackup configuration."""

    github_username: str = ""
    github_repo: str = ""
    github_token: str = ""
    github_token_env_var: Optional[str] = None
    profiles: dict[str, Profile] = field(default_factory=dict)
    initialized: bool = False

    def to_dict(self) -> dict:
        """Convert config to dictionary for serialization."""
        return {
            "github_username": self.github_username,
            "github_repo": self.github_repo,
            "github_token": self.github_token,
            "github_token_env_var": self.github_token_env_var,
            "profiles": {name: p.to_dict() for name, p in self.profiles.items()},
            "initialized": self.initialized,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Create config from dictionary."""
        profiles = {}
        for name, profile_data in data.get("profiles", {}).items():
            profiles[name] = Profile.from_dict(profile_data)

        return cls(
            github_username=data.get("github_username", ""),
            github_repo=data.get("github_repo", ""),
            github_token=data.get("github_token", ""),
            github_token_env_var=data.get("github_token_env_var"),
            profiles=profiles,
            initialized=data.get("initialized", False),
        )

    def get_token(self) -> str:
        """Get GitHub token from config or environment variable.

        Returns:
            GitHub token string.

        Raises:
            ConfigError: If no token is available.
        """
        if self.github_token_env_var:
            token = os.environ.get(self.github_token_env_var, "")
            if token:
                return token

        if self.github_token:
            return self.github_token

        raise ConfigError(
            "No GitHub token configured. Run 'termbackup init' to configure."
        )

    def get_repo_full_name(self) -> str:
        """Get full repository name in owner/repo format."""
        return f"{self.github_username}/{self.github_repo}"


def ensure_config_dir() -> None:
    """Ensure the config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> Config:
    """Load configuration from file.

    Returns:
        Config object, or default config if file doesn't exist.
    """
    if not CONFIG_FILE.exists():
        return Config()

    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return Config.from_dict(data)
    except (json.JSONDecodeError, KeyError) as e:
        raise ConfigError(f"Invalid config file: {e}") from e


def save_config(config: Config) -> None:
    """Save configuration to file.

    Args:
        config: Config object to save.
    """
    ensure_config_dir()
    CONFIG_FILE.write_text(
        json.dumps(config.to_dict(), indent=2),
        encoding="utf-8",
    )


def is_initialized() -> bool:
    """Check if TermBackup has been initialized."""
    if not CONFIG_FILE.exists():
        return False
    config = load_config()
    return config.initialized


def require_initialized() -> Config:
    """Load config and require it to be initialized.

    Returns:
        Config object.

    Raises:
        ConfigError: If not initialized.
    """
    config = load_config()
    if not config.initialized:
        raise ConfigError(
            "TermBackup is not initialized. Run 'termbackup init' first."
        )
    return config


def get_profile(name: str) -> Profile:
    """Get a profile by name.

    Args:
        name: Profile name.

    Returns:
        Profile object.

    Raises:
        ConfigError: If profile doesn't exist.
    """
    config = require_initialized()
    if name not in config.profiles:
        raise ConfigError(f"Profile '{name}' not found.")
    return config.profiles[name]


def create_profile(profile: Profile) -> None:
    """Create a new profile.

    Args:
        profile: Profile to create.

    Raises:
        ConfigError: If profile already exists or validation fails.
    """
    config = require_initialized()

    if profile.name in config.profiles:
        raise ConfigError(f"Profile '{profile.name}' already exists.")

    errors = profile.validate()
    if errors:
        raise ConfigError(f"Profile validation failed: {'; '.join(errors)}")

    config.profiles[profile.name] = profile
    save_config(config)


def list_profiles() -> list[Profile]:
    """List all profiles.

    Returns:
        List of Profile objects.
    """
    config = require_initialized()
    return list(config.profiles.values())


def delete_profile(name: str) -> None:
    """Delete a profile.

    Args:
        name: Profile name to delete.

    Raises:
        ConfigError: If profile doesn't exist.
    """
    config = require_initialized()

    if name not in config.profiles:
        raise ConfigError(f"Profile '{name}' not found.")

    del config.profiles[name]
    save_config(config)
