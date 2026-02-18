"""Configuration and profile management with Pydantic validation."""

import json
import os
import platform
import stat
from pathlib import Path

from termbackup import ui
from termbackup.models import AppConfig, ProfileConfig

# Lazy-loaded module references (set at first use to avoid circular imports)
github = None  # type: ignore[assignment]


def _get_github():
    """Lazy-load the github module to avoid circular imports."""
    global github
    if github is None:
        from termbackup import github as _gh
        github = _gh
    return github

CONFIG_DIR = Path.home() / ".termbackup"
CONFIG_FILE = CONFIG_DIR / "config.json"
PROFILES_DIR = CONFIG_DIR / "profiles"


def _secure_file(file_path: Path) -> None:
    """Sets restrictive permissions (chmod 600) on Unix systems."""
    if platform.system() != "Windows":
        os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)


def _validate_and_display_token(token: str) -> tuple[bool, str | None]:
    """Validates a GitHub token and displays the result.

    Returns:
        Tuple of (is_valid, username). is_valid is True if the token is valid
        (or network is unavailable), False only if definitively invalid/expired.
        username is the GitHub username if authentication succeeded, None otherwise.
    """
    from termbackup.token_validator import ValidationStatus, validate_token

    ui.step("Validating GitHub token...")
    info = validate_token(token)
    ui.print_token_validation(info)

    username = info.username or None

    if info.status == ValidationStatus.VALID:
        return True, username

    if info.status == ValidationStatus.NETWORK_ERROR:
        ui.warning("Token saved but could not be validated (network unavailable).")
        return True, username  # Don't block init due to network issues

    if info.status == ValidationStatus.RATE_LIMITED:
        ui.warning("Token saved but could not be validated (rate limited).")
        return True, username

    if info.status == ValidationStatus.INSUFFICIENT_SCOPE:
        ui.warning("Token authenticated but may lack required permissions.")
        ui.info("TermBackup requires 'repo' scope (classic) or Contents read/write (fine-grained).")
        return True, username  # Still allow save — user may fix permissions later

    # Token is invalid or expired
    return False, None


def _validate_repo_name(name: str) -> bool:
    """Validates a GitHub repository name."""
    import re

    return bool(re.match(r"^[a-zA-Z0-9._-]+$", name)) and len(name) <= 100


def init_config():
    """Initializes the configuration directory and file."""
    ui.print_header("System Initialization", icon=ui.Icons.GEAR)

    if CONFIG_FILE.exists():
        ui.warning("Configuration already exists.")
        ui.detail("Location", str(CONFIG_FILE))
        raise SystemExit(0)

    CONFIG_DIR.mkdir(exist_ok=True)
    PROFILES_DIR.mkdir(exist_ok=True)

    ui.info("Enter your GitHub Personal Access Token.")
    ui.info("Supported token types:")
    ui.detail("Classic PAT", "Starts with ghp_ (requires 'repo' scope)")
    ui.detail("Fine-grained", "Starts with github_pat_ (requires Contents read/write)")
    ui.console.print()

    # Token input with validation loop
    max_attempts = 3
    github_token = ""
    username = None

    for attempt in range(1, max_attempts + 1):
        github_token = ui.prompt_secret("GitHub Personal Access Token")

        if not github_token.strip():
            ui.error("Token cannot be empty.")
            if attempt < max_attempts:
                ui.info(f"Attempt {attempt}/{max_attempts}. Please try again.")
                continue
            else:
                ui.error("Maximum attempts reached. Run 'termbackup init' again.")
                raise SystemExit(1)

        is_valid, username = _validate_and_display_token(github_token.strip())

        if is_valid:
            break
        elif attempt < max_attempts:
            ui.console.print()
            ui.info(f"Attempt {attempt}/{max_attempts}. Please enter a valid token.")
        else:
            ui.console.print()
            ui.error("Maximum attempts reached with invalid token.")
            if ui.confirm("Save this token anyway?"):
                break
            ui.error("Configuration cancelled. Run 'termbackup init' again.")
            raise SystemExit(1)

    github_token = github_token.strip()

    # Optional: Create a storage repository on GitHub
    default_repo = None
    if username:
        ui.console.print()
        if ui.confirm_default_yes("Create a GitHub storage repository now?"):
            default_repo = _create_storage_repo(github_token, username)

    app_config = AppConfig(
        github_token=github_token,
        default_repo=default_repo,
    )

    with open(CONFIG_FILE, "w") as f:
        json.dump(app_config.model_dump(mode="json"), f, indent=4)
    _secure_file(CONFIG_FILE)

    summary_items = [
        ("Location", str(CONFIG_FILE)),
        ("Token", "Stored in config"),
        ("Token Status", "Validated"),
        ("Audit Log", "Enabled"),
    ]
    if default_repo:
        summary_items.insert(2, ("Storage Repo", default_repo))

    ui.print_summary_panel("Configuration Initialized", summary_items, style="success")
    ui.print_footer()


def _create_storage_repo(token: str, username: str) -> str | None:
    """Guides the user through creating a GitHub storage repository.

    Returns the full repo name (user/repo) on success, or None if skipped/failed.
    """
    gh = _get_github()

    repo_name = ui.prompt_input_default("Repository name", "termbackup-storage")

    if not _validate_repo_name(repo_name):
        ui.error("Invalid repository name. Use only letters, numbers, hyphens, dots, and underscores.")
        return None

    ui.console.print()
    ui.info(f"Will create: [{ui.Theme.ACCENT}]{username}/{repo_name}[/{ui.Theme.ACCENT}] (private)")

    spinner = ui.create_spinner()
    try:
        with spinner:
            task_id = spinner.add_task("Creating repository...", total=None)
            full_name = gh.create_repo(token, repo_name)
            spinner.update(task_id, description="Initializing repo structure...")
            gh.init_repo_structure(token, full_name)

        ui.success(f"Repository created: {full_name}")
        return full_name
    except RuntimeError as e:
        ui.error(f"Failed to create repository: {e}")
        return None


def get_config() -> AppConfig:
    """Reads and returns the configuration as a Pydantic model."""
    if not CONFIG_FILE.exists():
        ui.error("Configuration not found. Run 'termbackup init' first.")
        raise SystemExit(1)

    with open(CONFIG_FILE) as f:
        data = json.load(f)

    return AppConfig.model_validate(data)


def get_github_token() -> str:
    """Returns the GitHub token. Checks keyring first, then config file."""
    try:
        from termbackup import credentials

        token = credentials.get_token()
        if token:
            return token
    except ImportError:
        ui.warning("Keyring module not available; falling back to config file.")

    app_config = get_config()
    token = app_config.github_token
    if not token:
        ui.error("GitHub token not found. Run 'termbackup init' first.")
        raise SystemExit(1)
    return token


def update_token(new_token: str) -> bool:
    """Updates the GitHub token in the config file after validation.

    Returns True if the token was updated, False if validation failed
    and the user chose not to save.
    """
    new_token = new_token.strip()
    if not new_token:
        ui.error("Token cannot be empty.")
        return False

    is_valid, _username = _validate_and_display_token(new_token)

    if not is_valid:
        if not ui.confirm("Save this token anyway?"):
            return False

    # Update config file
    raw = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            raw = json.load(f)
    raw["github_token"] = new_token
    with open(CONFIG_FILE, "w") as f:
        json.dump(raw, f, indent=4)
    _secure_file(CONFIG_FILE)

    ui.success("Token updated in config.")

    # Also update keyring if available
    try:
        from termbackup import credentials
        credentials.save_token(new_token)
        ui.success("Token updated in OS keyring.")
    except Exception as e:
        ui.warning(f"Could not update OS keyring: {e}")

    return True


def create_profile(
    name: str,
    source_dir: str,
    repo: str,
    excludes: list[str],
    compression_level: int = 6,
    max_backups: int | None = None,
    retention_days: int | None = None,
    backup_mode: str = "full",
    webhook_url: str | None = None,
):
    """Creates a new backup profile with Pydantic validation."""
    PROFILES_DIR.mkdir(exist_ok=True)
    profile_file = PROFILES_DIR / f"{name}.json"

    if profile_file.exists():
        ui.error(f"Profile '{name}' already exists.")
        raise SystemExit(1)

    source_path = Path(source_dir).resolve()
    if not source_path.is_dir():
        ui.error(f"Source directory does not exist: {source_dir}")
        raise SystemExit(1)

    profile = ProfileConfig(
        name=name,
        source_dir=str(source_path),
        repo=repo,
        excludes=excludes if excludes else [],
        compression_level=compression_level,
        max_backups=max_backups,
        retention_days=retention_days,
        backup_mode=backup_mode,
        webhook_url=webhook_url,
    )

    with open(profile_file, "w") as f:
        json.dump(profile.model_dump(mode="json"), f, indent=4)
    _secure_file(profile_file)

    ui.success(f"Profile '{name}' created")
    ui.detail("Source", str(source_path))
    ui.detail("Repository", repo)


def get_profile(name: str) -> ProfileConfig:
    """Reads and returns a specific profile as a Pydantic model."""
    profile_file = PROFILES_DIR / f"{name}.json"

    if not profile_file.exists():
        ui.error(f"Profile '{name}' not found.")
        raise SystemExit(1)

    with open(profile_file) as f:
        data = json.load(f)

    return ProfileConfig.model_validate(data)


def delete_profile(name: str):
    """Deletes a backup profile."""
    profile_file = PROFILES_DIR / f"{name}.json"

    if not profile_file.exists():
        ui.error(f"Profile '{name}' not found.")
        raise SystemExit(1)

    profile_file.unlink()
    ui.success(f"Profile '{name}' deleted")


def get_all_profiles() -> list[ProfileConfig]:
    """Returns a list of all profiles as Pydantic models."""
    if not PROFILES_DIR.exists():
        return []

    profiles = []
    for profile_file in sorted(PROFILES_DIR.glob("*.json")):
        with open(profile_file) as f:
            data = json.load(f)
        try:
            profiles.append(ProfileConfig.model_validate(data))
        except Exception:
            continue
    return profiles
