"""Tests for the config module."""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch

from termbackup.config import (
    Config,
    ConfigError,
    Profile,
    ensure_config_dir,
    load_config,
    save_config,
)


class TestProfile:
    def test_profile_to_dict(self) -> None:
        profile = Profile(
            name="test",
            source_directory="/home/user/data",
            exclude_patterns=["*.log"],
            password_env_var="TEST_PASSWORD",
        )

        data = profile.to_dict()

        assert data["name"] == "test"
        assert data["source_directory"] == "/home/user/data"
        assert data["exclude_patterns"] == ["*.log"]
        assert data["password_env_var"] == "TEST_PASSWORD"

    def test_profile_from_dict(self) -> None:
        data = {
            "name": "test",
            "source_directory": "/home/user/data",
            "exclude_patterns": ["*.log"],
            "password_env_var": "TEST_PASSWORD",
        }

        profile = Profile.from_dict(data)

        assert profile.name == "test"
        assert profile.source_directory == "/home/user/data"
        assert profile.exclude_patterns == ["*.log"]
        assert profile.password_env_var == "TEST_PASSWORD"

    def test_profile_validate_existing_directory(self, tmp_path: Path) -> None:
        profile = Profile(
            name="test",
            source_directory=str(tmp_path),
        )

        errors = profile.validate()
        assert len(errors) == 0

    def test_profile_validate_nonexistent_directory(self) -> None:
        profile = Profile(
            name="test",
            source_directory="/nonexistent/path",
        )

        errors = profile.validate()
        assert len(errors) == 1
        assert "does not exist" in errors[0]

    def test_profile_validate_file_not_directory(self, tmp_path: Path) -> None:
        test_file = tmp_path / "file.txt"
        test_file.write_text("content")

        profile = Profile(
            name="test",
            source_directory=str(test_file),
        )

        errors = profile.validate()
        assert len(errors) == 1
        assert "not a directory" in errors[0]


class TestConfig:
    def test_config_to_dict(self) -> None:
        profile = Profile(name="test", source_directory="/data")
        config = Config(
            github_username="user",
            github_repo="repo",
            github_token="token123",
            profiles={"test": profile},
            initialized=True,
        )

        data = config.to_dict()

        assert data["github_username"] == "user"
        assert data["github_repo"] == "repo"
        assert data["github_token"] == "token123"
        assert "test" in data["profiles"]
        assert data["initialized"] is True

    def test_config_from_dict(self) -> None:
        data = {
            "github_username": "user",
            "github_repo": "repo",
            "github_token": "token123",
            "profiles": {
                "test": {
                    "name": "test",
                    "source_directory": "/data",
                }
            },
            "initialized": True,
        }

        config = Config.from_dict(data)

        assert config.github_username == "user"
        assert config.github_repo == "repo"
        assert config.github_token == "token123"
        assert "test" in config.profiles
        assert config.initialized is True

    def test_config_get_repo_full_name(self) -> None:
        config = Config(
            github_username="user",
            github_repo="repo",
        )

        assert config.get_repo_full_name() == "user/repo"

    def test_config_get_token_from_config(self) -> None:
        config = Config(
            github_token="direct_token",
        )

        assert config.get_token() == "direct_token"

    def test_config_get_token_from_env_var(self) -> None:
        config = Config(
            github_token_env_var="TEST_TOKEN_VAR",
        )

        with patch.dict(os.environ, {"TEST_TOKEN_VAR": "env_token"}):
            assert config.get_token() == "env_token"

    def test_config_get_token_env_var_priority(self) -> None:
        config = Config(
            github_token="direct_token",
            github_token_env_var="TEST_TOKEN_VAR",
        )

        with patch.dict(os.environ, {"TEST_TOKEN_VAR": "env_token"}):
            assert config.get_token() == "env_token"

    def test_config_get_token_missing(self) -> None:
        config = Config()

        with pytest.raises(ConfigError):
            config.get_token()


class TestConfigPersistence:
    def test_save_and_load_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.json"

        with patch("termbackup.config.CONFIG_DIR", tmp_path):
            with patch("termbackup.config.CONFIG_FILE", config_file):
                profile = Profile(name="test", source_directory="/data")
                original_config = Config(
                    github_username="user",
                    github_repo="repo",
                    github_token="token",
                    profiles={"test": profile},
                    initialized=True,
                )

                save_config(original_config)
                assert config_file.exists()

                loaded_config = load_config()
                assert loaded_config.github_username == "user"
                assert loaded_config.github_repo == "repo"
                assert loaded_config.github_token == "token"
                assert "test" in loaded_config.profiles
                assert loaded_config.initialized is True

    def test_load_nonexistent_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / "nonexistent.json"

        with patch("termbackup.config.CONFIG_FILE", config_file):
            config = load_config()
            assert config.github_username == ""
            assert config.initialized is False

    def test_load_invalid_json(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.json"
        config_file.write_text("invalid json{")

        with patch("termbackup.config.CONFIG_FILE", config_file):
            with pytest.raises(ConfigError):
                load_config()
