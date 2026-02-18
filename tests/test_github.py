"""Tests for the GitHub API integration module (httpx)."""

import base64
import json
from unittest.mock import MagicMock, patch

import pytest

from termbackup import github
from termbackup.errors import GitHubError


@pytest.fixture(autouse=True)
def mock_github_token(monkeypatch):
    """Prevents real config reads in all github tests."""
    monkeypatch.setattr(
        "termbackup.github.config.get_github_token", lambda: "ghp_test_token"
    )


@pytest.fixture(autouse=True)
def reset_github_client():
    """Reset the singleton httpx client before each test."""
    github._client = None
    yield
    github._client = None


class TestHandleResponseError:
    def test_401_raises(self):
        resp = MagicMock(status_code=401)
        with pytest.raises(GitHubError, match="Authentication failed"):
            github._handle_response_error(resp, "test")

    def test_403_raises(self):
        resp = MagicMock(status_code=403)
        with pytest.raises(GitHubError, match="Access denied"):
            github._handle_response_error(resp, "test")

    def test_404_raises(self):
        resp = MagicMock(status_code=404)
        with pytest.raises(GitHubError, match="not found"):
            github._handle_response_error(resp, "test")

    def test_500_raises(self):
        resp = MagicMock(status_code=500)
        resp.text = "Internal Server Error"
        with pytest.raises(GitHubError, match="HTTP 500"):
            github._handle_response_error(resp, "test")

    def test_200_no_error(self):
        resp = MagicMock(status_code=200)
        github._handle_response_error(resp, "test")  # should not raise


class TestGetRepoDefaultBranch:
    @patch("termbackup.github._get_client")
    def test_success(self, mock_client):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"default_branch": "main"}
        mock_client.return_value.get.return_value = mock_resp

        result = github.get_repo_default_branch("user/repo")
        assert result == "main"

    @patch("termbackup.github._get_client")
    def test_error(self, mock_client):
        mock_resp = MagicMock(status_code=404)
        mock_client.return_value.get.return_value = mock_resp

        with pytest.raises(GitHubError):
            github.get_repo_default_branch("user/nonexistent")


class TestUploadBlob:
    @patch("termbackup.github._get_client")
    @patch("termbackup.github.get_repo_default_branch", return_value="main")
    def test_success(self, mock_branch, mock_client, tmp_path):
        archive = tmp_path / "backup_abc123.tbk"
        archive.write_bytes(b"archive-data")

        mock_resp = MagicMock(status_code=201)
        mock_resp.json.return_value = {"commit": {"sha": "abc123commit"}}
        mock_client.return_value.put.return_value = mock_resp

        result = github.upload_blob("user/repo", archive)
        assert result == "abc123commit"

    @patch("termbackup.github._get_client")
    @patch("termbackup.github.get_repo_default_branch", return_value="main")
    def test_base64_encoding(self, mock_branch, mock_client, tmp_path):
        archive = tmp_path / "test.tbk"
        archive.write_bytes(b"\x00\x01\x02\x03")

        mock_resp = MagicMock(status_code=201)
        mock_resp.json.return_value = {"commit": {"sha": "sha123"}}
        mock_client.return_value.put.return_value = mock_resp

        github.upload_blob("user/repo", archive)

        call_kwargs = mock_client.return_value.put.call_args
        sent_content = call_kwargs.kwargs["json"]["content"]
        assert base64.b64decode(sent_content) == b"\x00\x01\x02\x03"


class TestGetMetadataContent:
    @patch("termbackup.github._get_client")
    def test_exists(self, mock_client):
        content = json.dumps({"backups": []})
        encoded = base64.b64encode(content.encode()).decode()

        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"content": encoded, "sha": "file_sha"}
        mock_client.return_value.get.return_value = mock_resp

        text, sha = github.get_metadata_content("user/repo")
        assert text == content
        assert sha == "file_sha"

    @patch("termbackup.github._get_client")
    def test_404_returns_none(self, mock_client):
        mock_resp = MagicMock(status_code=404)
        mock_client.return_value.get.return_value = mock_resp

        text, sha = github.get_metadata_content("user/repo")
        assert text is None
        assert sha is None


class TestUpdateMetadataContent:
    @patch("termbackup.github._get_client")
    @patch("termbackup.github.get_repo_default_branch", return_value="main")
    def test_new_file(self, mock_branch, mock_client):
        mock_resp = MagicMock(status_code=201)
        mock_resp.json.return_value = {"commit": {"sha": "newsha"}}
        mock_client.return_value.put.return_value = mock_resp

        result = github.update_metadata_content("user/repo", '{"test": true}', None)
        assert result == "newsha"

        sent_data = mock_client.return_value.put.call_args.kwargs["json"]
        assert "sha" not in sent_data

    @patch("termbackup.github._get_client")
    @patch("termbackup.github.get_repo_default_branch", return_value="main")
    def test_existing_file(self, mock_branch, mock_client):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"commit": {"sha": "updsha"}}
        mock_client.return_value.put.return_value = mock_resp

        result = github.update_metadata_content("user/repo", '{}', "old_sha")
        assert result == "updsha"

        sent_data = mock_client.return_value.put.call_args.kwargs["json"]
        assert sent_data["sha"] == "old_sha"


class TestDownloadBlob:
    @patch("termbackup.github._get_client")
    def test_streams_chunks(self, mock_client, tmp_path):
        mock_resp = MagicMock(status_code=200)
        mock_resp.iter_bytes.return_value = [b"chunk1", b"chunk2"]
        mock_client.return_value.stream.return_value.__enter__ = MagicMock(return_value=mock_resp)
        mock_client.return_value.stream.return_value.__exit__ = MagicMock(return_value=False)

        dest = tmp_path / "downloaded.tbk"
        github.download_blob("user/repo", "backup.tbk", dest)

        assert dest.read_bytes() == b"chunk1chunk2"
