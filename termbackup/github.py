"""GitHub API integration using httpx with retry transport and HTTP/2."""

import base64
import json
from pathlib import Path

import httpx

from termbackup import config
from termbackup.errors import GitHubError

API_URL = "https://api.github.com"

_transport = httpx.HTTPTransport(retries=3)
_client: httpx.Client | None = None


def _get_client() -> httpx.Client:
    """Returns a singleton httpx client with retry transport."""
    global _client
    if _client is None:
        _client = httpx.Client(
            transport=_transport,
            timeout=httpx.Timeout(60.0, connect=10.0),
            headers={
                "Authorization": f"token {config.get_github_token()}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
    return _client


def reset_client() -> None:
    """Resets the singleton client (useful for testing or token refresh)."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


def _handle_response_error(response: httpx.Response, context: str):
    """Raises a clear error for failed API responses."""
    if response.status_code == 401:
        raise GitHubError(
            f"{context}: Authentication failed — check your GitHub token.",
            status_code=401,
            hint="Run 'termbackup update-token' to set a valid token.",
        )
    elif response.status_code == 403:
        raise GitHubError(
            f"{context}: Access denied — check token permissions (repo scope).",
            status_code=403,
            hint="Ensure your token has the 'repo' scope for classic PATs.",
        )
    elif response.status_code == 404:
        raise GitHubError(
            f"{context}: Resource not found — verify the repository exists.",
            status_code=404,
        )
    elif response.status_code == 422:
        raise GitHubError(
            f"{context}: Validation failed — {response.text[:200]}",
            status_code=422,
        )
    elif response.status_code >= 400:
        raise GitHubError(
            f"{context}: HTTP {response.status_code} — {response.text[:200]}",
            status_code=response.status_code,
        )


def create_repo(
    token: str,
    repo_name: str,
    private: bool = True,
    description: str = "TermBackup encrypted storage repository",
) -> str:
    """Creates a new GitHub repository for backup storage.

    Uses a fresh httpx request with the token directly (not the singleton client,
    since during init the client isn't set up yet).

    Args:
        token: GitHub Personal Access Token.
        repo_name: Repository name (without owner prefix).
        private: Whether the repo should be private.
        description: Repository description.

    Returns:
        Full repo name in 'owner/repo' format.

    Raises:
        RuntimeError: If creation fails (except 422 which means repo exists).
    """
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {
        "name": repo_name,
        "private": private,
        "description": description,
        "auto_init": True,
    }

    transport = httpx.HTTPTransport(retries=3)
    with httpx.Client(transport=transport, timeout=httpx.Timeout(30.0, connect=10.0)) as client:
        response = client.post(f"{API_URL}/user/repos", json=data, headers=headers)

    if response.status_code == 201:
        return response.json()["full_name"]

    if response.status_code == 422:
        # Repo already exists — fetch the authenticated user's login to build full name
        with httpx.Client(transport=transport, timeout=httpx.Timeout(15.0)) as client:
            user_resp = client.get(f"{API_URL}/user", headers=headers)
        if user_resp.status_code == 200:
            username = user_resp.json()["login"]
            return f"{username}/{repo_name}"
        raise RuntimeError(
            f"Repository '{repo_name}' may already exist, but could not verify owner."
        )

    if response.status_code == 401:
        raise RuntimeError("Authentication failed — check your GitHub token.")
    if response.status_code == 403:
        raise RuntimeError("Access denied — token may lack permission to create repositories.")

    raise RuntimeError(f"Failed to create repository: HTTP {response.status_code} — {response.text[:200]}")


def init_repo_structure(token: str, full_repo_name: str) -> None:
    """Creates initial directory structure in a newly created repo.

    Creates backups/.gitkeep, manifests/.gitkeep, and metadata.json.

    Args:
        token: GitHub Personal Access Token.
        full_repo_name: Full repo name in 'owner/repo' format.
    """
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    transport = httpx.HTTPTransport(retries=3)
    with httpx.Client(transport=transport, timeout=httpx.Timeout(30.0, connect=10.0)) as client:
        # Get default branch
        repo_resp = client.get(f"{API_URL}/repos/{full_repo_name}", headers=headers)
        if repo_resp.status_code != 200:
            raise RuntimeError(f"Failed to get repo info: HTTP {repo_resp.status_code}")
        branch = repo_resp.json()["default_branch"]

        # Create directory structure files
        files_to_create = {
            "backups/.gitkeep": "",
            "manifests/.gitkeep": "",
            "metadata.json": json.dumps({
                "tool_version": "6.0",
                "repository": full_repo_name,
                "created_at": "",
                "backups": [],
            }, indent=2),
        }

        for path, content in files_to_create.items():
            # Check if file exists first
            check_resp = client.get(
                f"{API_URL}/repos/{full_repo_name}/contents/{path}",
                headers=headers,
            )
            if check_resp.status_code == 200:
                continue  # File already exists, skip

            data = {
                "message": f"Initialize {path}",
                "content": base64.b64encode(content.encode()).decode(),
                "branch": branch,
            }
            resp = client.put(
                f"{API_URL}/repos/{full_repo_name}/contents/{path}",
                json=data,
                headers=headers,
            )
            if resp.status_code not in (200, 201):
                raise RuntimeError(
                    f"Failed to create {path}: HTTP {resp.status_code} — {resp.text[:200]}"
                )


def get_repo_default_branch(repo_name: str) -> str:
    """Gets the default branch of a repository."""
    url = f"{API_URL}/repos/{repo_name}"
    response = _get_client().get(url)
    _handle_response_error(response, "Failed to get repository info")
    return response.json()["default_branch"]


def upload_blob(repo_name: str, file_path: Path) -> str:
    """Uploads a file to the GitHub repository and returns the commit SHA."""
    branch = get_repo_default_branch(repo_name)
    url = f"{API_URL}/repos/{repo_name}/contents/backups/{file_path.name}"

    with open(file_path, "rb") as f:
        content = base64.b64encode(f.read()).decode()

    data = {
        "message": f"Add backup {file_path.name}",
        "content": content,
        "branch": branch,
    }

    response = _get_client().put(url, json=data)
    _handle_response_error(response, "Failed to upload backup")
    return response.json()["commit"]["sha"]


def get_metadata_content(repo_name: str) -> tuple[str | None, str | None]:
    """Gets the content and SHA of the metadata.json file."""
    url = f"{API_URL}/repos/{repo_name}/contents/metadata.json"
    response = _get_client().get(url)

    if response.status_code == 404:
        return None, None

    _handle_response_error(response, "Failed to read metadata")
    data = response.json()
    return base64.b64decode(data["content"]).decode(), data["sha"]


def update_metadata_content(repo_name: str, content: str, sha: str | None) -> str:
    """Updates the metadata.json file."""
    url = f"{API_URL}/repos/{repo_name}/contents/metadata.json"

    data = {
        "message": "Update metadata.json",
        "content": base64.b64encode(content.encode()).decode(),
        "branch": get_repo_default_branch(repo_name),
    }
    if sha:
        data["sha"] = sha

    response = _get_client().put(url, json=data)
    _handle_response_error(response, "Failed to update metadata")
    return response.json()["commit"]["sha"]


def delete_blob(repo_name: str, file_name: str):
    """Deletes a backup file from the GitHub repository."""
    url = f"{API_URL}/repos/{repo_name}/contents/backups/{file_name}"

    # First get the file SHA
    response = _get_client().get(url)
    _handle_response_error(response, "Failed to get file info for deletion")
    file_sha = response.json()["sha"]

    # Then delete
    data = {
        "message": f"Remove backup {file_name}",
        "sha": file_sha,
        "branch": get_repo_default_branch(repo_name),
    }
    response = _get_client().request("DELETE", url, json=data)
    _handle_response_error(response, "Failed to delete backup")


def upload_manifest(repo_name: str, manifest_id: str, content: str):
    """Uploads a manifest JSON to the manifests directory."""
    file_name = f"manifest_{manifest_id[:12]}.json"
    url = f"{API_URL}/repos/{repo_name}/contents/manifests/{file_name}"

    # Check if file already exists
    response = _get_client().get(url)
    sha = response.json().get("sha") if response.status_code == 200 else None

    data = {
        "message": f"Add manifest {file_name}",
        "content": base64.b64encode(content.encode()).decode(),
        "branch": get_repo_default_branch(repo_name),
    }
    if sha:
        data["sha"] = sha

    response = _get_client().put(url, json=data)
    _handle_response_error(response, "Failed to upload manifest")


def download_manifest(repo_name: str, manifest_id: str) -> dict | None:
    """Downloads a manifest JSON from the manifests directory."""
    file_name = f"manifest_{manifest_id[:12]}.json"
    url = f"{API_URL}/repos/{repo_name}/contents/manifests/{file_name}"
    response = _get_client().get(url)

    if response.status_code == 404:
        return None

    _handle_response_error(response, "Failed to download manifest")
    content = base64.b64decode(response.json()["content"]).decode()
    return json.loads(content)


def download_blob(repo_name: str, file_name: str, destination_path: Path):
    """Downloads a file from the GitHub repository using streaming."""
    url = f"{API_URL}/repos/{repo_name}/contents/backups/{file_name}"

    client = _get_client()
    with client.stream(
        "GET", url, headers={"Accept": "application/vnd.github.raw"}
    ) as r:
        if r.status_code >= 400:
            r.read()
            _handle_response_error(r, "Failed to download backup")
        with open(destination_path, "wb") as f:
            for chunk in r.iter_bytes(8192):
                f.write(chunk)
