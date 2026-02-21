"""OS-native backup scheduling (Windows Task Scheduler / Unix crontab).

Profile names are validated by Pydantic (^[a-zA-Z0-9_-]+$) but we also
validate here as defense in depth, and use shlex.quote() on Unix.
"""

import platform
import re
import shlex
import subprocess
import sys

from termbackup import audit

TASK_PREFIX = "TermBackup_"


def _validate_profile_name(profile_name: str) -> None:
    """Defense-in-depth validation of profile name for shell safety."""
    if not re.match(r"^[a-zA-Z0-9_-]+$", profile_name):
        raise ValueError(f"Invalid profile name for scheduling: {profile_name}")


def enable_schedule(profile_name: str, cron_expr: str):
    """Creates an OS-level scheduled task for a backup profile."""
    _validate_profile_name(profile_name)
    if platform.system() == "Windows":
        _enable_schedule_windows(profile_name, cron_expr)
    else:
        _enable_schedule_unix(profile_name, cron_expr)
    audit.log_operation("schedule", profile_name, "success", {"action": "enable"})


def _enable_schedule_windows(profile_name: str, schedule_spec: str):
    """Creates a Windows Task Scheduler entry."""
    task_name = f"{TASK_PREFIX}{profile_name}"
    python_exe = sys.executable
    command = f'"{python_exe}" -m termbackup run {profile_name} --scheduled'

    # Parse schedule_spec into /SC and /ST parts
    parts = schedule_spec.strip().split()
    sc_type = parts[0] if parts else "DAILY"
    st_time = parts[2] if len(parts) > 2 and parts[1] == "/ST" else "03:00"

    result = subprocess.run(
        [
            "schtasks", "/Create",
            "/TN", task_name,
            "/TR", command,
            "/SC", sc_type,
            "/ST", st_time,
            "/F",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to create scheduled task: {result.stderr.strip()}")


def _enable_schedule_unix(profile_name: str, cron_expr: str):
    """Adds a crontab entry with marker comments. Uses shlex.quote() for safety."""
    python_exe = shlex.quote(sys.executable)
    safe_profile = shlex.quote(profile_name)
    command = f"{python_exe} -m termbackup run {safe_profile} --scheduled"
    marker_start = f"# TERMBACKUP_START:{profile_name}"
    marker_end = f"# TERMBACKUP_END:{profile_name}"
    cron_line = f"{cron_expr} {command}"

    # Read existing crontab
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing = result.stdout if result.returncode == 0 else ""

    # Remove any existing entry for this profile
    lines = existing.splitlines()
    new_lines = []
    skip = False
    for line in lines:
        if line.strip() == marker_start:
            skip = True
            continue
        if line.strip() == marker_end:
            skip = False
            continue
        if not skip:
            new_lines.append(line)

    # Add new entry
    new_lines.append(marker_start)
    new_lines.append(cron_line)
    new_lines.append(marker_end)

    new_crontab = "\n".join(new_lines) + "\n"
    result = subprocess.run(
        ["crontab", "-"],
        input=new_crontab,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to update crontab: {result.stderr.strip()}")


def disable_schedule(profile_name: str):
    """Removes the scheduled task for a profile."""
    _validate_profile_name(profile_name)
    if platform.system() == "Windows":
        _disable_schedule_windows(profile_name)
    else:
        _disable_schedule_unix(profile_name)
    audit.log_operation("schedule", profile_name, "success", {"action": "disable"})


def _disable_schedule_windows(profile_name: str):
    task_name = f"{TASK_PREFIX}{profile_name}"
    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", task_name, "/F"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to delete scheduled task: {result.stderr.strip()}")


def _disable_schedule_unix(profile_name: str):
    marker_start = f"# TERMBACKUP_START:{profile_name}"
    marker_end = f"# TERMBACKUP_END:{profile_name}"

    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if result.returncode != 0:
        return

    lines = result.stdout.splitlines()
    new_lines = []
    skip = False
    for line in lines:
        if line.strip() == marker_start:
            skip = True
            continue
        if line.strip() == marker_end:
            skip = False
            continue
        if not skip:
            new_lines.append(line)

    new_crontab = "\n".join(new_lines) + "\n"
    subprocess.run(["crontab", "-"], input=new_crontab, capture_output=True, text=True)


def get_schedule_status(profile_name: str) -> str | None:
    """Returns the schedule info for a profile, or None if not scheduled."""
    _validate_profile_name(profile_name)
    if platform.system() == "Windows":
        return _get_status_windows(profile_name)
    else:
        return _get_status_unix(profile_name)


def _get_status_windows(profile_name: str) -> str | None:
    task_name = f"{TASK_PREFIX}{profile_name}"
    result = subprocess.run(
        ["schtasks", "/Query", "/TN", task_name, "/FO", "LIST"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _get_status_unix(profile_name: str) -> str | None:
    marker_start = f"# TERMBACKUP_START:{profile_name}"
    marker_end = f"# TERMBACKUP_END:{profile_name}"

    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if result.returncode != 0:
        return None

    lines = result.stdout.splitlines()
    in_block = False
    schedule_lines = []
    for line in lines:
        if line.strip() == marker_start:
            in_block = True
            continue
        if line.strip() == marker_end:
            break
        if in_block:
            schedule_lines.append(line)

    return "\n".join(schedule_lines) if schedule_lines else None
