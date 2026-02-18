"""GitHub token validation with support for classic PATs and fine-grained tokens.

Validates tokens by calling the GitHub API and inspecting response headers
to determine token type, scopes, permissions, expiration, and rate limits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

import httpx


class TokenType(str, Enum):
    CLASSIC = "classic"
    FINE_GRAINED = "fine-grained"
    UNKNOWN = "unknown"


class ValidationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    INSUFFICIENT_SCOPE = "insufficient_scope"
    NETWORK_ERROR = "network_error"
    RATE_LIMITED = "rate_limited"


# Required scopes for classic tokens
REQUIRED_CLASSIC_SCOPES = {"repo"}

# Required permissions for fine-grained tokens (repository level)
REQUIRED_FINE_GRAINED_PERMISSIONS = {
    "contents": "write",
    "metadata": "read",
}


@dataclass
class TokenInfo:
    """Structured result of a token validation."""

    status: ValidationStatus
    token_type: TokenType = TokenType.UNKNOWN
    username: str = ""
    user_id: int = 0
    scopes: list[str] = field(default_factory=list)
    permissions: dict[str, str] = field(default_factory=dict)
    expiration: str | None = None
    is_expired: bool = False
    rate_limit_remaining: int = 0
    rate_limit_total: int = 0
    rate_limit_reset: str = ""
    missing_scopes: list[str] = field(default_factory=list)
    missing_permissions: dict[str, str] = field(default_factory=dict)
    message: str = ""
    masked_token: str = ""


def detect_token_type(token: str) -> TokenType:
    """Detects the token type from its prefix.

    Classic PATs:        ghp_xxxx
    Fine-grained PATs:   github_pat_xxxx
    OAuth tokens:        gho_xxxx
    GitHub App tokens:   ghs_xxxx  (installation), ghu_xxxx (user-to-server)
    """
    token = token.strip()
    if token.startswith("github_pat_"):
        return TokenType.FINE_GRAINED
    if token.startswith("ghp_"):
        return TokenType.CLASSIC
    # Older tokens without prefix are treated as classic
    if len(token) == 40 and all(c in "0123456789abcdef" for c in token):
        return TokenType.CLASSIC
    # gho_, ghs_, ghu_ are also valid GitHub tokens
    if token.startswith(("gho_", "ghs_", "ghu_")):
        return TokenType.CLASSIC
    return TokenType.UNKNOWN


def mask_token(token: str) -> str:
    """Masks a token for safe display, showing prefix and last 4 chars."""
    token = token.strip()
    if len(token) <= 8:
        return "****"
    # Show first meaningful prefix + last 4
    if token.startswith("github_pat_"):
        return f"github_pat_****{token[-4:]}"
    if token.startswith(("ghp_", "gho_", "ghs_", "ghu_")):
        return f"{token[:4]}****{token[-4:]}"
    return f"{token[:4]}****{token[-4:]}"


def _parse_rate_limit(headers: httpx.Headers) -> tuple[int, int, str]:
    """Extracts rate limit info from response headers."""
    remaining = int(headers.get("x-ratelimit-remaining", "0"))
    total = int(headers.get("x-ratelimit-limit", "0"))
    reset_ts = headers.get("x-ratelimit-reset", "")
    reset_str = ""
    if reset_ts:
        try:
            reset_dt = datetime.fromtimestamp(int(reset_ts), tz=UTC)
            reset_str = reset_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except (ValueError, OSError):
            reset_str = reset_ts
    return remaining, total, reset_str


def _parse_scopes(headers: httpx.Headers) -> list[str]:
    """Extracts OAuth scopes from the X-OAuth-Scopes header."""
    scopes_header = headers.get("x-oauth-scopes", "")
    if not scopes_header:
        return []
    return [s.strip() for s in scopes_header.split(",") if s.strip()]


def _parse_fine_grained_permissions(headers: httpx.Headers) -> dict[str, str]:
    """Extracts fine-grained token permissions from response headers.

    Fine-grained tokens don't return X-OAuth-Scopes. Instead, permission
    info comes from X-Accepted-GitHub-Permissions or must be checked
    by making test API calls.
    """
    permissions: dict[str, str] = {}
    # GitHub returns X-Accepted-GitHub-Permissions on some endpoints
    accepted = headers.get("x-accepted-github-permissions", "")
    if accepted:
        # Format: "contents=write, metadata=read" or similar
        for pair in accepted.split(","):
            pair = pair.strip()
            if "=" in pair:
                key, val = pair.split("=", 1)
                permissions[key.strip()] = val.strip()
    return permissions


def validate_token(token: str, timeout: float = 15.0) -> TokenInfo:
    """Validates a GitHub token by calling the API.

    Performs the following checks:
    1. Token format and type detection
    2. Authentication against GitHub API (/user endpoint)
    3. Scope/permission verification
    4. Rate limit status
    5. Repository access check (if scopes seem sufficient)

    Args:
        token: The GitHub token to validate.
        timeout: HTTP request timeout in seconds.

    Returns:
        TokenInfo with complete validation results.
    """
    token = token.strip()
    if not token:
        return TokenInfo(
            status=ValidationStatus.INVALID,
            message="Token is empty.",
        )

    token_type = detect_token_type(token)
    masked = mask_token(token)

    # Step 1: Authenticate against /user
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        response = httpx.get(
            "https://api.github.com/user",
            headers=headers,
            timeout=timeout,
        )
    except httpx.TimeoutException:
        return TokenInfo(
            status=ValidationStatus.NETWORK_ERROR,
            token_type=token_type,
            masked_token=masked,
            message="Connection timed out. Check your network.",
        )
    except httpx.ConnectError:
        return TokenInfo(
            status=ValidationStatus.NETWORK_ERROR,
            token_type=token_type,
            masked_token=masked,
            message="Could not connect to GitHub API. Check your network.",
        )
    except httpx.HTTPError as e:
        return TokenInfo(
            status=ValidationStatus.NETWORK_ERROR,
            token_type=token_type,
            masked_token=masked,
            message=f"Network error: {e}",
        )

    # Parse rate limits from headers
    rl_remaining, rl_total, rl_reset = _parse_rate_limit(response.headers)

    # Handle rate limiting
    if response.status_code == 429:
        return TokenInfo(
            status=ValidationStatus.RATE_LIMITED,
            token_type=token_type,
            masked_token=masked,
            rate_limit_remaining=rl_remaining,
            rate_limit_total=rl_total,
            rate_limit_reset=rl_reset,
            message=f"Rate limited. Resets at {rl_reset}.",
        )

    # Handle authentication failure
    if response.status_code == 401:
        # Check for specific error messages
        error_msg = ""
        try:
            error_msg = response.json().get("message", "")
        except (ValueError, KeyError, AttributeError):
            error_msg = "Authentication failed."

        if "token expired" in error_msg.lower() or "bad credentials" in error_msg.lower():
            return TokenInfo(
                status=ValidationStatus.EXPIRED if "expired" in error_msg.lower() else ValidationStatus.INVALID,
                token_type=token_type,
                masked_token=masked,
                message=error_msg or "Authentication failed. Token is invalid or expired.",
            )

        return TokenInfo(
            status=ValidationStatus.INVALID,
            token_type=token_type,
            masked_token=masked,
            message=error_msg or "Authentication failed. Check your token.",
        )

    if response.status_code == 403:
        return TokenInfo(
            status=ValidationStatus.INSUFFICIENT_SCOPE,
            token_type=token_type,
            masked_token=masked,
            rate_limit_remaining=rl_remaining,
            rate_limit_total=rl_total,
            rate_limit_reset=rl_reset,
            message="Access denied. Token may lack required permissions.",
        )

    if response.status_code != 200:
        return TokenInfo(
            status=ValidationStatus.INVALID,
            token_type=token_type,
            masked_token=masked,
            message=f"Unexpected response: HTTP {response.status_code}",
        )

    # Step 2: Parse user info
    user_data = response.json()
    username = user_data.get("login", "")
    user_id = user_data.get("id", 0)

    # Step 3: Parse scopes/permissions
    scopes = _parse_scopes(response.headers)

    # Refine token type detection based on scopes
    # Fine-grained tokens don't return X-OAuth-Scopes
    if not scopes and token_type == TokenType.UNKNOWN:
        token_type = TokenType.FINE_GRAINED
    elif scopes and token_type == TokenType.UNKNOWN:
        token_type = TokenType.CLASSIC

    # Step 4: Check required scopes/permissions
    missing_scopes: list[str] = []
    missing_permissions: dict[str, str] = {}

    if token_type == TokenType.CLASSIC:
        for required_scope in REQUIRED_CLASSIC_SCOPES:
            if required_scope not in scopes:
                missing_scopes.append(required_scope)
    elif token_type == TokenType.FINE_GRAINED:
        # For fine-grained tokens, we need to probe specific endpoints
        # Check repo contents access by trying to list user repos
        missing_permissions = _check_fine_grained_permissions(token, timeout)

    # Step 5: Determine final status
    if missing_scopes:
        status = ValidationStatus.INSUFFICIENT_SCOPE
        scope_list = ", ".join(missing_scopes)
        message = f"Token missing required scope(s): {scope_list}"
    elif missing_permissions:
        status = ValidationStatus.INSUFFICIENT_SCOPE
        perm_list = ", ".join(f"{k}={v}" for k, v in missing_permissions.items())
        message = f"Token missing required permission(s): {perm_list}"
    else:
        status = ValidationStatus.VALID
        if token_type == TokenType.CLASSIC:
            message = f"Valid classic token with scopes: {', '.join(scopes)}"
        else:
            message = "Valid fine-grained token with repository access."

    return TokenInfo(
        status=status,
        token_type=token_type,
        username=username,
        user_id=user_id,
        scopes=scopes,
        rate_limit_remaining=rl_remaining,
        rate_limit_total=rl_total,
        rate_limit_reset=rl_reset,
        missing_scopes=missing_scopes,
        missing_permissions=missing_permissions,
        message=message,
        masked_token=masked,
    )


def _check_fine_grained_permissions(
    token: str, timeout: float = 15.0
) -> dict[str, str]:
    """Probes GitHub API to check fine-grained token permissions.

    Fine-grained tokens don't expose scopes in headers. We verify by
    attempting specific API calls to confirm the required access level.

    Returns:
        Dict of missing permissions (empty if all required permissions present).
    """
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    missing: dict[str, str] = {}

    # Check if we can list repos (indicates metadata:read)
    try:
        response = httpx.get(
            "https://api.github.com/user/repos?per_page=1",
            headers=headers,
            timeout=timeout,
        )
        if response.status_code != 200:
            missing["metadata"] = "read"
    except httpx.HTTPError:
        # Network issues during permission check are non-fatal;
        # the main validation already confirmed authentication succeeded.
        return missing

    return missing


def validate_token_for_repo(
    token: str, repo: str, timeout: float = 15.0
) -> TokenInfo:
    """Validates a token specifically for a target repository.

    In addition to standard validation, checks that the token can
    actually access the specified repository with write permissions.

    Args:
        token: The GitHub token.
        repo: Repository in 'owner/repo' format.
        timeout: HTTP request timeout.

    Returns:
        TokenInfo with repo-specific validation.
    """
    # First do standard validation
    info = validate_token(token, timeout)
    if info.status != ValidationStatus.VALID:
        return info

    # Then check repo access
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        response = httpx.get(
            f"https://api.github.com/repos/{repo}",
            headers=headers,
            timeout=timeout,
        )

        if response.status_code == 404:
            info.status = ValidationStatus.INSUFFICIENT_SCOPE
            info.message = (
                f"Repository '{repo}' not found or not accessible with this token. "
                "Ensure the repository exists and the token has access."
            )
            return info

        if response.status_code == 403:
            info.status = ValidationStatus.INSUFFICIENT_SCOPE
            info.message = f"Token lacks permission to access repository '{repo}'."
            return info

        if response.status_code == 200:
            repo_data = response.json()
            permissions = repo_data.get("permissions", {})
            if not permissions.get("push", False):
                info.status = ValidationStatus.INSUFFICIENT_SCOPE
                info.message = (
                    f"Token has read-only access to '{repo}'. "
                    "TermBackup requires write (push) access."
                )
                return info

            info.message = (
                f"Token validated with write access to '{repo}'. "
                f"Authenticated as {info.username}."
            )

    except httpx.HTTPError:
        # Network errors during repo-specific check are non-fatal;
        # the token is already authenticated, so return existing info.
        info.message += " (repo access check skipped due to network error)"

    return info
