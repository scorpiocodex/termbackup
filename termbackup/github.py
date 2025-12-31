"""GitHub API interactions for TermBackup."""

import base64
from dataclasses import dataclass
from typing import Callable, Optional

import requests

from .config import Config


API_BASE = "https://api.github.com"


class GitHubError(Exception):
    """Raised when GitHub API operations fail."""


@dataclass
class BackupInfo:
    """Information about a backup stored in GitHub."""

    name: str
    path: str
    sha: str
    size: int
    download_url: str


class GitHubClient:
    """Client for GitHub API operations."""

    def __init__(self, config: Config) -> None:
        """Initialize GitHub client.

        Args:
            config: TermBackup configuration.
        """
        self.config = config
        self.token = config.get_token()
        self.repo = config.get_repo_full_name()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> requests.Response:
        """Make authenticated request to GitHub API.

        Args:
            method: HTTP method.
            endpoint: API endpoint.
            **kwargs: Additional arguments to pass to requests.

        Returns:
            Response object.

        Raises:
            GitHubError: If request fails.
        """
        url = f"{API_BASE}{endpoint}"
        response = self.session.request(method, url, **kwargs)

        if response.status_code == 401:
            raise GitHubError("Authentication failed. Check your GitHub token.")
        if response.status_code == 403:
            raise GitHubError("Access forbidden. Check token permissions (needs 'repo' scope).")
        if response.status_code == 404:
            raise GitHubError(f"Resource not found: {endpoint}")

        return response

    def validate_token(self) -> bool:
        """Validate the GitHub token has correct permissions.

        Returns:
            True if token is valid and has required scopes.

        Raises:
            GitHubError: If validation fails.
        """
        response = self._request("GET", "/user")
        if response.status_code != 200:
            raise GitHubError("Failed to validate token")

        scopes = response.headers.get("X-OAuth-Scopes", "")
        if "repo" not in scopes:
            raise GitHubError("Token missing 'repo' scope")

        return True

    def get_user(self) -> str:
        """Get authenticated user's username.

        Returns:
            Username string.
        """
        response = self._request("GET", "/user")
        response.raise_for_status()
        return response.json()["login"]

    def repo_exists(self) -> bool:
        """Check if the configured repository exists.

        Returns:
            True if repository exists.
        """
        url = f"{API_BASE}/repos/{self.repo}"
        response = self.session.get(url)
        return response.status_code == 200

    def create_repo(self, private: bool = True) -> None:
        """Create the backup repository.

        Args:
            private: Whether to create as private repository.

        Raises:
            GitHubError: If creation fails.
        """
        response = self._request(
            "POST",
            "/user/repos",
            json={
                "name": self.config.github_repo,
                "private": private,
                "description": "TermBackup encrypted backup storage",
                "auto_init": False,
            },
        )

        if response.status_code not in (200, 201):
            error = response.json().get("message", "Unknown error")
            raise GitHubError(f"Failed to create repository: {error}")

    def initialize_repo(self) -> None:
        """Initialize repository with README and backups directory.

        Creates initial commit with README and empty backups directory.
        """
        readme_content = """# TermBackup Storage

This repository contains encrypted backups created by [TermBackup](https://github.com/termbackup/termbackup).

## Structure

```
backups/
├── backup_YYYYMMDD_HHMMSS.tbk
├── backup_YYYYMMDD_HHMMSS.tbk
└── ...
```

## Security

- All `.tbk` files are AES-256 encrypted
- Only encrypted data is stored in this repository
- Decryption requires the original password

**Warning:** If you lose your encryption password, your backups cannot be recovered.
"""
        self._create_or_update_file(
            "README.md",
            readme_content.encode("utf-8"),
            "Initialize TermBackup repository",
        )

        self._create_or_update_file(
            "backups/.gitkeep",
            b"",
            "Create backups directory",
        )

    def _get_file_sha(self, path: str) -> Optional[str]:
        """Get SHA of existing file.

        Args:
            path: File path in repository.

        Returns:
            SHA string or None if file doesn't exist.
        """
        url = f"{API_BASE}/repos/{self.repo}/contents/{path}"
        response = self.session.get(url)
        if response.status_code == 200:
            return response.json().get("sha")
        return None

    def _create_or_update_file(
        self,
        path: str,
        content: bytes,
        message: str,
    ) -> None:
        """Create or update a file in the repository.

        Args:
            path: File path in repository.
            content: File content as bytes.
            message: Commit message.

        Raises:
            GitHubError: If operation fails.
        """
        sha = self._get_file_sha(path)
        encoded_content = base64.b64encode(content).decode("ascii")

        data = {
            "message": message,
            "content": encoded_content,
        }

        if sha:
            data["sha"] = sha

        response = self._request(
            "PUT",
            f"/repos/{self.repo}/contents/{path}",
            json=data,
        )

        if response.status_code not in (200, 201):
            error = response.json().get("message", "Unknown error")
            raise GitHubError(f"Failed to create/update file: {error}")

    def upload_backup(
        self,
        backup_name: str,
        content: bytes,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """Upload encrypted backup to repository.

        Args:
            backup_name: Name of the backup file.
            content: Encrypted backup content.
            progress_callback: Optional callback for progress updates.

        Raises:
            GitHubError: If upload fails.
        """
        path = f"backups/{backup_name}"
        message = f"Add {backup_name}"

        if progress_callback:
            progress_callback(0, len(content))

        self._create_or_update_file(path, content, message)

        if progress_callback:
            progress_callback(len(content), len(content))

    def list_backups(self) -> list[BackupInfo]:
        """List all backups in the repository.

        Returns:
            List of BackupInfo objects.
        """
        response = self._request("GET", f"/repos/{self.repo}/contents/backups")

        if response.status_code == 404:
            return []

        if response.status_code != 200:
            raise GitHubError("Failed to list backups")

        backups = []
        for item in response.json():
            if item["name"].endswith(".tbk"):
                backups.append(
                    BackupInfo(
                        name=item["name"],
                        path=item["path"],
                        sha=item["sha"],
                        size=item["size"],
                        download_url=item["download_url"],
                    )
                )

        backups.sort(key=lambda b: b.name, reverse=True)
        return backups

    def get_backup_info(self, backup_name: str) -> Optional[BackupInfo]:
        """Get information about a specific backup.

        Args:
            backup_name: Name of the backup file.

        Returns:
            BackupInfo or None if not found.
        """
        backups = self.list_backups()
        for backup in backups:
            if backup.name == backup_name:
                return backup
        return None

    def download_backup(
        self,
        backup_name: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bytes:
        """Download a backup from the repository.

        Args:
            backup_name: Name of the backup file.
            progress_callback: Optional callback for progress updates.

        Returns:
            Backup content as bytes.

        Raises:
            GitHubError: If download fails.
        """
        path = f"backups/{backup_name}"
        url = f"{API_BASE}/repos/{self.repo}/contents/{path}"
        response = self.session.get(url)

        if response.status_code == 404:
            raise GitHubError(f"Backup not found: {backup_name}")

        if response.status_code != 200:
            raise GitHubError("Failed to download backup")

        data = response.json()
        download_url = data.get("download_url")

        if not download_url:
            raise GitHubError("No download URL available")

        dl_response = self.session.get(download_url)
        if dl_response.status_code != 200:
            raise GitHubError("Failed to download backup content")

        content_bytes = dl_response.content

        if progress_callback:
            progress_callback(len(content_bytes), len(content_bytes))

        return content_bytes

    def delete_backup(self, backup_name: str) -> None:
        """Delete a backup from the repository.

        Args:
            backup_name: Name of the backup file.

        Raises:
            GitHubError: If deletion fails.
        """
        path = f"backups/{backup_name}"
        sha = self._get_file_sha(path)

        if not sha:
            raise GitHubError(f"Backup not found: {backup_name}")

        response = self._request(
            "DELETE",
            f"/repos/{self.repo}/contents/{path}",
            json={
                "message": f"Delete {backup_name}",
                "sha": sha,
            },
        )

        if response.status_code not in (200, 204):
            error = response.json().get("message", "Unknown error")
            raise GitHubError(f"Failed to delete backup: {error}")
