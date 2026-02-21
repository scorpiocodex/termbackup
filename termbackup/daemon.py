"""Background backup daemon loop with graceful shutdown and health monitoring."""

import signal
import time
from datetime import UTC, datetime

from termbackup import audit, ui

_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    _shutdown = True


def run_daemon(profile_name: str, interval_minutes: int) -> None:
    """Runs backups in a loop with the given interval.

    Reads password from keyring. Catches and logs errors per iteration
    without crashing. Handles SIGINT/SIGTERM for graceful shutdown.
    Tracks consecutive failures and reports health status.
    """
    from termbackup import credentials, engine

    ui.print_header("Daemon Mode", icon=ui.Icons.GEAR)
    ui.info(f"Profile: [bold]{profile_name}[/bold]")
    ui.detail("Interval", f"{interval_minutes} minutes")

    password = credentials.get_profile_password(profile_name)
    if not password:
        ui.error("No stored password found. Use 'termbackup schedule-enable' to store one.")
        raise SystemExit(1)

    # Set up signal handlers
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    ui.info("Daemon started. Press Ctrl+C to stop.")
    start_time = datetime.now(UTC)
    iteration = 0
    successes = 0
    failures = 0
    consecutive_failures = 0

    while not _shutdown:
        iteration += 1
        ui.console.print()
        ui.print_step_progress(iteration, 0, f"Running backup iteration {iteration}")

        try:
            t0 = time.time()
            engine.run_backup(profile_name, password)
            elapsed = time.time() - t0
            successes += 1
            consecutive_failures = 0
            audit.log_operation("backup", profile_name, "success", {
                "source": "daemon",
                "iteration": iteration,
                "elapsed_seconds": round(elapsed, 1),
            })
        except SystemExit as e:
            if e.code != 0:
                ui.warning(f"Daemon received exit signal with code {e.code}.")
            break
        except Exception as e:
            failures += 1
            consecutive_failures += 1
            ui.error(f"Backup failed: {e}")
            audit.log_operation("backup", profile_name, "failure", {
                "source": "daemon",
                "iteration": iteration,
                "error": str(e),
                "consecutive_failures": consecutive_failures,
            })

            # Warn on repeated failures
            if consecutive_failures >= 3:
                ui.warning(
                    f"{consecutive_failures} consecutive failures. "
                    "Check your configuration and network."
                )

        if _shutdown:
            break

        ui.info(f"Next backup in {interval_minutes} minutes...")
        # Sleep in small increments to respond to signals quickly
        for _ in range(interval_minutes * 60):
            if _shutdown:
                break
            time.sleep(1)

    # Shutdown summary
    ui.console.print()
    uptime = datetime.now(UTC) - start_time
    hours = int(uptime.total_seconds() // 3600)
    minutes = int((uptime.total_seconds() % 3600) // 60)

    ui.print_summary_panel("Daemon Stopped", [
        ("Uptime", f"{hours}h {minutes}m"),
        ("Iterations", str(iteration)),
        ("Successes", str(successes)),
        ("Failures", str(failures)),
    ], style="info")
