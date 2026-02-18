"""System health checks for TermBackup."""

import platform
import sys
from pathlib import Path

from termbackup import __version__, ui
from termbackup.config import CONFIG_DIR, CONFIG_FILE, PROFILES_DIR


def run_doctor() -> None:
    """Runs comprehensive health checks and displays results."""
    ui.print_header("System Health Check", icon=ui.Icons.PULSE)

    checks: list[tuple[str, bool, str]] = []

    # 1. Config file exists and valid JSON
    checks.append(_check_config())

    # 2. GitHub token present
    checks.append(_check_github_token())

    # 3. GitHub token validation (type, scopes, permissions)
    checks.append(_check_token_validation())

    # 4. GitHub API connectivity
    checks.append(_check_github_connectivity())

    # 5. OS keyring accessible
    checks.append(_check_keyring())

    # 6. All profiles valid
    checks.append(_check_profiles())

    # 7. Profile source directories exist
    checks.append(_check_profile_sources())

    # 8. Signing key status
    checks.append(_check_signing_key())

    # 9. Audit log writable
    checks.append(_check_audit_log())

    # 10. Orphaned temp files
    checks.append(_check_temp_files())

    # 11. Dependencies
    checks.append(_check_dependencies())

    # 12. Disk space
    checks.append(_check_disk_space())

    ui.print_checklist(checks)

    passed = sum(1 for _, p, _ in checks if p)
    total = len(checks)
    ui.console.print()

    # System info panel
    ui.print_kv_list([
        ("Version", __version__),
        ("Python", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"),
        ("Platform", f"{platform.system()} {platform.release()}"),
        ("Config Dir", str(CONFIG_DIR)),
    ], title="Environment")

    if passed == total:
        ui.success(f"All {total} checks passed")
    else:
        ui.warning(f"{passed}/{total} checks passed")

    ui.print_footer()


def _check_config() -> tuple[str, bool, str]:
    """Check config file exists and parses as valid JSON."""
    import json

    if not CONFIG_FILE.exists():
        return ("Config File", False, "Not found -- run 'termbackup init'")
    try:
        with open(CONFIG_FILE) as f:
            json.load(f)
        return ("Config File", True, "Valid JSON")
    except Exception as e:
        return ("Config File", False, f"Parse error: {e}")


def _check_github_token() -> tuple[str, bool, str]:
    """Check GitHub token is available."""
    try:
        from termbackup import config

        token = config.get_github_token()
        from termbackup.token_validator import mask_token
        masked = mask_token(token)
        return ("GitHub Token", True, f"Found ({masked})")
    except (SystemExit, Exception):
        return ("GitHub Token", False, "Not configured")


def _check_token_validation() -> tuple[str, bool, str]:
    """Validate the GitHub token type, scopes, and permissions."""
    try:
        from termbackup import config
        from termbackup.token_validator import ValidationStatus, validate_token

        token = config.get_github_token()
        info = validate_token(token, timeout=10.0)

        if info.status == ValidationStatus.VALID:
            type_str = info.token_type.value.replace("-", " ").title()
            scope_info = ""
            if info.scopes:
                scope_info = f", scopes: {', '.join(info.scopes[:3])}"
            return (
                "Token Validation",
                True,
                f"{type_str} token, user: {info.username}{scope_info}",
            )

        if info.status == ValidationStatus.NETWORK_ERROR:
            return ("Token Validation", True, "Skipped (network unavailable)")

        if info.status == ValidationStatus.RATE_LIMITED:
            return ("Token Validation", True, "Skipped (rate limited)")

        if info.status == ValidationStatus.INSUFFICIENT_SCOPE:
            return ("Token Validation", False, info.message)

        return ("Token Validation", False, info.message)

    except (SystemExit, Exception) as e:
        return ("Token Validation", False, f"Error: {e}")


def _check_github_connectivity() -> tuple[str, bool, str]:
    """Check GitHub API is reachable with the current token."""
    try:
        import httpx

        from termbackup import config

        token = config.get_github_token()
        response = httpx.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {token}"},
            timeout=10.0,
        )
        if response.status_code == 200:
            username = response.json().get("login", "unknown")
            return ("GitHub API", True, f"Connected as {username}")
        else:
            return ("GitHub API", False, f"HTTP {response.status_code}")
    except (SystemExit, Exception) as e:
        return ("GitHub API", False, f"Unreachable: {e}")


def _check_keyring() -> tuple[str, bool, str]:
    """Check if OS keyring is accessible."""
    try:
        import keyring

        # Try a read operation (won't modify anything)
        keyring.get_password("termbackup_doctor_test", "test")
        return ("OS Keyring", True, "Accessible")
    except Exception as e:
        return ("OS Keyring", False, f"Error: {e}")


def _check_profiles() -> tuple[str, bool, str]:
    """Check all profiles are valid."""
    if not PROFILES_DIR.exists():
        return ("Profiles", True, "No profiles directory (none configured)")

    import json

    from termbackup.models import ProfileConfig

    profile_files = list(PROFILES_DIR.glob("*.json"))
    if not profile_files:
        return ("Profiles", True, "No profiles configured")

    errors = []
    for pf in profile_files:
        try:
            with open(pf) as f:
                data = json.load(f)
            ProfileConfig.model_validate(data)
        except Exception as e:
            errors.append(f"{pf.stem}: {e}")

    if errors:
        return ("Profiles", False, f"{len(errors)} invalid: {errors[0]}")
    return ("Profiles", True, f"{len(profile_files)} valid")


def _check_profile_sources() -> tuple[str, bool, str]:
    """Check that profile source directories exist."""
    if not PROFILES_DIR.exists():
        return ("Source Dirs", True, "No profiles to check")

    import json

    profile_files = list(PROFILES_DIR.glob("*.json"))
    if not profile_files:
        return ("Source Dirs", True, "No profiles to check")

    missing = []
    for pf in profile_files:
        try:
            with open(pf) as f:
                data = json.load(f)
            source_dir = Path(data.get("source_dir", ""))
            if not source_dir.is_dir():
                missing.append(f"{pf.stem}: {source_dir}")
        except Exception:
            continue

    if missing:
        return ("Source Dirs", False, f"{len(missing)} missing: {missing[0]}")
    return ("Source Dirs", True, "All source directories exist")


def _check_signing_key() -> tuple[str, bool, str]:
    """Check signing key status."""
    try:
        from termbackup import signing

        if signing.has_signing_key():
            return ("Signing Key", True, "Ed25519 keypair found")
        return ("Signing Key", True, "Not configured (optional)")
    except Exception as e:
        return ("Signing Key", False, f"Error: {e}")


def _check_audit_log() -> tuple[str, bool, str]:
    """Check audit log is writable."""
    from termbackup.audit import AUDIT_LOG_PATH

    try:
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        AUDIT_LOG_PATH.touch(exist_ok=True)
        # Report log size
        size = AUDIT_LOG_PATH.stat().st_size
        if size > 0:
            from termbackup.utils import format_size
            return ("Audit Log", True, f"Writable ({format_size(size)})")
        return ("Audit Log", True, str(AUDIT_LOG_PATH))
    except Exception as e:
        return ("Audit Log", False, f"Not writable: {e}")


def _check_temp_files() -> tuple[str, bool, str]:
    """Check for orphaned temp files."""
    tmp_dir = CONFIG_DIR / "tmp"
    if not tmp_dir.exists():
        return ("Temp Files", True, "Clean")

    orphans = list(tmp_dir.iterdir())
    if orphans:
        total_size = sum(f.stat().st_size for f in orphans if f.is_file())
        from termbackup.utils import format_size
        return (
            "Temp Files",
            False,
            f"{len(orphans)} orphaned file(s) ({format_size(total_size)}) in {tmp_dir}",
        )
    return ("Temp Files", True, "Clean")


def _check_dependencies() -> tuple[str, bool, str]:
    """Check that critical dependencies are importable."""
    missing = []
    for module_name in ["cryptography", "httpx", "argon2", "keyring", "pydantic", "pathspec"]:
        try:
            __import__(module_name)
        except ImportError:
            missing.append(module_name)

    if missing:
        return ("Dependencies", False, f"Missing: {', '.join(missing)}")
    return ("Dependencies", True, "All critical modules available")


def _check_disk_space() -> tuple[str, bool, str]:
    """Check available disk space in the config directory."""
    import shutil

    try:
        usage = shutil.disk_usage(str(CONFIG_DIR.parent))
        free_gb = usage.free / (1024 ** 3)
        if free_gb < 0.5:
            return ("Disk Space", False, f"Low: {free_gb:.1f} GB free")
        return ("Disk Space", True, f"{free_gb:.1f} GB free")
    except Exception as e:
        return ("Disk Space", True, f"Could not check: {e}")
