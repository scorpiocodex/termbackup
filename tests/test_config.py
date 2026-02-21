"""Tests for configuration and profile management with Pydantic."""

import json
from pathlib import Path

import pytest

from termbackup import config
from termbackup.models import AppConfig, ProfileConfig


def test_get_config_missing(mock_config_dir):
    with pytest.raises(SystemExit):
        config.get_config()


def test_get_config_exists(mock_config_dir):
    config_data = {"github_token": "ghp_test123"}
    (mock_config_dir / "config.json").write_text(json.dumps(config_data))

    result = config.get_config()
    assert isinstance(result, AppConfig)
    assert result.github_token == "ghp_test123"


def test_get_github_token(mock_config_dir, monkeypatch):
    config_data = {"github_token": "ghp_test123"}
    (mock_config_dir / "config.json").write_text(json.dumps(config_data))

    # Mock keyring to return None so it falls through to config file
    from termbackup import credentials
    monkeypatch.setattr(credentials, "get_token", lambda: None)

    token = config.get_github_token()
    assert token == "ghp_test123"


def test_get_github_token_missing(mock_config_dir, monkeypatch):
    config_data = {"github_token": ""}
    (mock_config_dir / "config.json").write_text(json.dumps(config_data))

    from termbackup import credentials
    monkeypatch.setattr(credentials, "get_token", lambda: None)

    with pytest.raises(SystemExit):
        config.get_github_token()


def test_create_profile(mock_config_dir, tmp_path: Path):
    source = tmp_path / "source_data"
    source.mkdir()

    config.create_profile("test-profile", str(source), "user/repo", ["*.log"])

    profile_file = mock_config_dir / "profiles" / "test-profile.json"
    assert profile_file.exists()

    data = json.loads(profile_file.read_text())
    assert data["name"] == "test-profile"
    assert data["repo"] == "user/repo"
    assert "*.log" in data["excludes"]


def test_create_profile_duplicate(mock_config_dir, tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    profiles_dir = mock_config_dir / "profiles"
    profiles_dir.mkdir(exist_ok=True)
    (profiles_dir / "dup.json").write_text("{}")

    with pytest.raises(SystemExit):
        config.create_profile("dup", str(source), "user/repo", [])


def test_create_profile_bad_source(mock_config_dir):
    with pytest.raises(SystemExit):
        config.create_profile("bad", "/nonexistent/path", "user/repo", [])


def test_get_profile(mock_config_dir):
    profiles_dir = mock_config_dir / "profiles"
    profiles_dir.mkdir(exist_ok=True)
    data = {"name": "myprofile", "source_dir": "/src", "repo": "u/r", "excludes": []}
    (profiles_dir / "myprofile.json").write_text(json.dumps(data))

    result = config.get_profile("myprofile")
    assert isinstance(result, ProfileConfig)
    assert result.name == "myprofile"


def test_get_profile_not_found(mock_config_dir):
    with pytest.raises(SystemExit):
        config.get_profile("nonexistent")


def test_delete_profile(mock_config_dir):
    profiles_dir = mock_config_dir / "profiles"
    profiles_dir.mkdir(exist_ok=True)
    (profiles_dir / "del.json").write_text("{}")

    config.delete_profile("del")
    assert not (profiles_dir / "del.json").exists()


def test_delete_profile_not_found(mock_config_dir):
    with pytest.raises(SystemExit):
        config.delete_profile("ghost")


def test_get_all_profiles(mock_config_dir):
    profiles_dir = mock_config_dir / "profiles"
    profiles_dir.mkdir(exist_ok=True)
    (profiles_dir / "a.json").write_text(json.dumps({"name": "a", "source_dir": "/src", "repo": "u/r", "excludes": []}))
    (profiles_dir / "b.json").write_text(json.dumps({"name": "b", "source_dir": "/src", "repo": "u/r", "excludes": []}))

    result = config.get_all_profiles()
    assert len(result) == 2
    assert all(isinstance(p, ProfileConfig) for p in result)
    names = [p.name for p in result]
    assert "a" in names
    assert "b" in names


def test_get_all_profiles_empty(mock_config_dir):
    result = config.get_all_profiles()
    assert result == []


def test_profile_name_validation():
    """Profile names with special chars should fail Pydantic validation."""
    with pytest.raises(Exception):
        ProfileConfig(
            name="bad name!",
            source_dir="/src",
            repo="user/repo",
            excludes=[],
        )


def test_profile_repo_validation():
    """Repo must be in user/repo format."""
    with pytest.raises(Exception):
        ProfileConfig(
            name="test",
            source_dir="/src",
            repo="invalid-repo-format",
            excludes=[],
        )
