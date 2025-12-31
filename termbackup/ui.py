"""Advanced Rich UI components for TermBackup.

Professional, modern CLI interface with beautiful formatting.
"""

import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Generator, Optional

from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich.tree import Tree


# Detect if terminal supports Unicode
def _supports_unicode() -> bool:
    """Check if terminal supports Unicode characters."""
    if sys.platform == "win32":
        # Check if stdout encoding supports Unicode
        stdout_encoding = getattr(sys.stdout, "encoding", "").lower()
        if stdout_encoding and "utf" in stdout_encoding:
            return True
        # Check for explicit UTF-8 environment setting
        if "UTF-8" in str(os.environ.get("PYTHONIOENCODING", "")):
            return True
        # Default to ASCII on Windows for compatibility
        # Even Windows Terminal may not work if subprocess uses legacy encoding
        return False
    return True


UNICODE_SUPPORT = _supports_unicode()


class Theme:
    """Color theme for TermBackup UI."""

    # Primary colors
    PRIMARY = "cyan"
    SECONDARY = "blue"
    ACCENT = "magenta"

    # Status colors
    SUCCESS = "green"
    WARNING = "yellow"
    ERROR = "red"
    INFO = "cyan"

    # Text colors
    MUTED = "dim white"
    HIGHLIGHT = "bold white"
    SUBTLE = "dim"

    # Styles
    HEADER = Style(color="cyan", bold=True)
    SUBHEADER = Style(color="blue", bold=True)
    LABEL = Style(color="white", dim=True)
    VALUE = Style(color="white")
    PATH = Style(color="cyan")
    SIZE = Style(color="yellow")
    DATE = Style(color="green")
    HASH = Style(color="magenta", dim=True)


class Icons:
    """Icon set with Unicode and ASCII fallbacks (plain text, no markup)."""

    # Use Unicode if supported, otherwise ASCII
    if UNICODE_SUPPORT:
        # Status icons
        SUCCESS = "\u2714"  # ✔
        ERROR = "\u2718"  # ✘
        WARNING = "\u26a0"  # ⚠
        INFO = "\u2139"  # ℹ
        PENDING = "\u25cb"  # ○
        RUNNING = "\u25cf"  # ●

        # Action icons
        BACKUP = "\u2630"  # ☰
        RESTORE = "\u21bb"  # ↻
        ENCRYPT = "\u2616"  # ☖
        COMPRESS = "\u25a4"  # ▤
        UPLOAD = "\u2191"  # ↑
        DOWNLOAD = "\u2193"  # ↓
        VERIFY = "\u2713"  # ✓
        DELETE = "\u2715"  # ✕

        # Object icons
        FILE = "\u25a1"  # □
        FOLDER = "\u25a0"  # ■
        PROFILE = "\u2605"  # ★
        CONFIG = "\u2699"  # ⚙
        CLOUD = "\u2601"  # ☁
        LOCK = "\u2616"  # ☖
        KEY = "\u2511"  # ┑

        # Decorative
        ARROW = "\u2192"  # →
        BULLET = "\u2022"  # •
        CHECK = "\u2714"  # ✔
        CROSS = "\u2718"  # ✘
        DOT = "\u25cf"  # ●
        CIRCLE = "\u25cb"  # ○
        DIAMOND = "\u25c6"  # ◆
        STAR = "\u2605"  # ★
    else:
        # ASCII fallbacks
        SUCCESS = "[OK]"
        ERROR = "[X]"
        WARNING = "[!]"
        INFO = "[i]"
        PENDING = "[ ]"
        RUNNING = "[*]"

        BACKUP = "[B]"
        RESTORE = "[R]"
        ENCRYPT = "[E]"
        COMPRESS = "[C]"
        UPLOAD = "[^]"
        DOWNLOAD = "[v]"
        VERIFY = "[V]"
        DELETE = "[D]"

        FILE = "[-]"
        FOLDER = "[+]"
        PROFILE = "[P]"
        CONFIG = "[C]"
        CLOUD = "[~]"
        LOCK = "[#]"
        KEY = "[K]"

        ARROW = "->"
        BULLET = "*"
        CHECK = "+"
        CROSS = "x"
        DOT = "o"
        CIRCLE = "o"
        DIAMOND = "<>"
        STAR = "*"


# Global console instance
console = Console(highlight=False)


def get_app_header() -> Panel:
    """Create the application header panel."""
    title = Text()
    title.append("TERM", style="bold cyan")
    title.append("BACKUP", style="bold white")
    title.append(" v1.0", style="dim cyan")

    subtitle = Text("Secure Cloud-Backed Backup CLI", style="dim white")

    content = Align.center(Group(title, subtitle))

    return Panel(
        content,
        box=box.DOUBLE,
        border_style="cyan",
        padding=(0, 2),
    )


def print_header(title: str, subtitle: Optional[str] = None) -> None:
    """Print a styled section header."""
    console.print()

    header_text = Text(title, style=Theme.HEADER)
    if subtitle:
        header_text.append(f"  {subtitle}", style=Theme.MUTED)

    console.print(Panel(header_text, box=box.ROUNDED, border_style="cyan", padding=(0, 2)))
    console.print()


def print_subheader(title: str) -> None:
    """Print a styled subheader."""
    console.print()
    console.print(Rule(title, style="blue"))
    console.print()


def print_success(message: str, details: Optional[str] = None) -> None:
    """Print a success message with icon."""
    text = Text()
    text.append(f" {Icons.SUCCESS} ", style="green")
    text.append(message, style="bold green")
    if details:
        text.append(f"  {details}", style="dim")
    console.print(text)


def print_error(message: str, details: Optional[str] = None) -> None:
    """Print an error message with icon."""
    text = Text()
    text.append(f" {Icons.ERROR} ", style="red")
    text.append(message, style="bold red")
    if details:
        text.append(f"\n    {details}", style="dim red")
    console.print(Panel(text, box=box.ROUNDED, border_style="red", padding=(0, 1)))


def print_warning(message: str) -> None:
    """Print a warning message with icon."""
    text = Text()
    text.append(f" {Icons.WARNING} ", style="yellow")
    text.append(message, style="yellow")
    console.print(text)


def print_info(message: str) -> None:
    """Print an info message with icon."""
    text = Text()
    text.append(f" {Icons.INFO} ", style="cyan")
    text.append(message, style="cyan")
    console.print(text)


def print_step(icon: str, message: str, status: str = "running") -> None:
    """Print a step with status indicator."""
    status_icons = {
        "running": Icons.RUNNING,
        "success": Icons.SUCCESS,
        "error": Icons.ERROR,
        "pending": Icons.PENDING,
    }
    status_icon = status_icons.get(status, Icons.RUNNING)

    text = Text()
    text.append(f"  {status_icon} ", style="bold")
    text.append(f"{icon} ", style="bold")
    text.append(message)
    console.print(text)


def print_key_value(
    key: str,
    value: str,
    key_style: str = "dim white",
    value_style: str = "white",
    indent: int = 2,
) -> None:
    """Print a formatted key-value pair."""
    padding = " " * indent
    console.print(f"{padding}[{key_style}]{key}:[/{key_style}] [{value_style}]{value}[/{value_style}]")


def print_stats_panel(stats: dict[str, str], title: str = "Statistics") -> None:
    """Print a panel with statistics."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="dim")
    table.add_column("Value", style="bold")

    for key, value in stats.items():
        table.add_row(key, value)

    console.print(Panel(table, title=f"[bold]{title}[/bold]", box=box.ROUNDED, border_style="blue"))


def create_backup_table() -> Table:
    """Create a styled table for backup listing."""
    table = Table(
        show_header=True,
        header_style="bold cyan",
        box=box.ROUNDED,
        border_style="dim",
        row_styles=["", "dim"],
        padding=(0, 1),
    )
    table.add_column(f"{Icons.BACKUP} Backup ID", style="cyan", no_wrap=True)
    table.add_column(f"{Icons.FOLDER} Date", style="green")
    table.add_column("Size", style="yellow", justify="right")
    table.add_column("Status", justify="center")
    return table


def create_profile_table() -> Table:
    """Create a styled table for profile listing."""
    table = Table(
        show_header=True,
        header_style="bold magenta",
        box=box.ROUNDED,
        border_style="dim",
        row_styles=["", "dim"],
        padding=(0, 1),
    )
    table.add_column(f"{Icons.PROFILE} Profile", style="magenta", no_wrap=True)
    table.add_column(f"{Icons.FOLDER} Source Directory", style="cyan")
    table.add_column("Exclusions", style="yellow", justify="right")
    return table


def create_file_tree(files: list[dict], root_name: str = "Files") -> Tree:
    """Create a tree view of files."""
    tree = Tree(f"[bold cyan]{Icons.FOLDER} {root_name}[/bold cyan]")

    # Group files by directory
    dirs: dict[str, list] = {}
    for f in files:
        path = f.get("path", f) if isinstance(f, dict) else f
        parts = path.replace("\\", "/").split("/")
        if len(parts) > 1:
            dir_name = "/".join(parts[:-1])
            if dir_name not in dirs:
                dirs[dir_name] = []
            dirs[dir_name].append((parts[-1], f))
        else:
            if "" not in dirs:
                dirs[""] = []
            dirs[""].append((path, f))

    # Build tree
    for dir_name, dir_files in sorted(dirs.items()):
        if dir_name:
            dir_branch = tree.add(f"[yellow]{Icons.FOLDER} {dir_name}/[/yellow]")
        else:
            dir_branch = tree

        for filename, f in sorted(dir_files):
            if isinstance(f, dict):
                size = f.get("size", 0)
                from .utils import format_size

                size_str = format_size(size)
                dir_branch.add(f"[white]{Icons.FILE} {filename}[/white] [dim]({size_str})[/dim]")
            else:
                dir_branch.add(f"[white]{Icons.FILE} {filename}[/white]")

    return tree


def confirm_action(
    message: str,
    default: bool = False,
    warning: Optional[str] = None,
) -> bool:
    """Prompt user for confirmation with styled dialog."""
    if warning:
        console.print()
        print_warning(warning)

    console.print()
    return Confirm.ask(f"  {message}", default=default, console=console)


def prompt_input(
    message: str,
    default: Optional[str] = None,
    password: bool = False,
) -> str:
    """Prompt user for input with styling."""
    if password:
        return Prompt.ask(f"  {Icons.KEY} {message}", password=True, console=console) or ""
    if default:
        return Prompt.ask(f"  {message}", default=default, console=console)
    return Prompt.ask(f"  {message}", console=console) or ""


def prompt_password(message: str = "Password") -> str:
    """Prompt for password with hidden input."""
    return prompt_input(message, password=True)


class StageColumn(ProgressColumn):
    """Custom column showing the current stage with icon."""

    def __init__(self, stage_icons: dict[str, str]) -> None:
        super().__init__()
        self.stage_icons = stage_icons

    def render(self, task: "Task") -> Text:  # type: ignore
        stage = task.fields.get("stage", "")
        icon = self.stage_icons.get(stage, Icons.RUNNING)
        return Text(f"{icon} {stage.capitalize()}", style="bold")


def create_backup_progress() -> Progress:
    """Create a progress bar for backup operations."""
    return Progress(
        SpinnerColumn(spinner_name="dots", style="cyan"),
        TextColumn("[bold blue]{task.description}[/bold blue]"),
        BarColumn(bar_width=30, style="cyan", complete_style="green"),
        TaskProgressColumn(),
        TextColumn("[dim]|[/dim]"),
        TimeElapsedColumn(),
        TextColumn("[dim]|[/dim]"),
        TimeRemainingColumn(),
        console=console,
        expand=False,
    )


def create_transfer_progress() -> Progress:
    """Create a progress bar for upload/download operations."""
    return Progress(
        SpinnerColumn(spinner_name="dots", style="cyan"),
        TextColumn("[bold blue]{task.description}[/bold blue]"),
        BarColumn(bar_width=30, style="blue", complete_style="green"),
        DownloadColumn(),
        TextColumn("[dim]|[/dim]"),
        TransferSpeedColumn(),
        TextColumn("[dim]|[/dim]"),
        TimeRemainingColumn(),
        console=console,
        expand=False,
    )


def create_simple_progress(description: str = "Processing") -> Progress:
    """Create a simple spinner progress."""
    return Progress(
        SpinnerColumn(spinner_name="dots", style="cyan"),
        TextColumn(f"[bold blue]{description}[/bold blue]"),
        console=console,
        transient=True,
    )


@contextmanager
def progress_spinner(description: str) -> Generator[None, None, None]:
    """Context manager for a simple spinner."""
    with create_simple_progress(description):
        yield


class BackupProgressManager:
    """Manages multi-stage backup progress display."""

    STAGES = {
        "scan": (Icons.BACKUP, "Scanning files"),
        "compress": (Icons.COMPRESS, "Compressing"),
        "encrypt": (Icons.ENCRYPT, "Encrypting"),
        "upload": (Icons.UPLOAD, "Uploading"),
    }

    def __init__(self) -> None:
        self.progress = create_backup_progress()
        self.task_id: Optional[TaskID] = None
        self.current_stage = ""

    def __enter__(self) -> "BackupProgressManager":
        self.progress.__enter__()
        return self

    def __exit__(self, *args: Any) -> None:
        self.progress.__exit__(*args)

    def update(self, stage: str, current: int, total: int) -> None:
        """Update progress for a stage."""
        if stage != self.current_stage:
            if self.task_id is not None:
                self.progress.update(self.task_id, completed=self.progress.tasks[self.task_id].total)

            icon, desc = self.STAGES.get(stage, (Icons.RUNNING, stage.capitalize()))
            self.task_id = self.progress.add_task(
                f"{icon} {desc}",
                total=total if total > 0 else None,
            )
            self.current_stage = stage

        if self.task_id is not None and total > 0:
            self.progress.update(self.task_id, completed=current)


class RestoreProgressManager:
    """Manages multi-stage restore progress display."""

    STAGES = {
        "download": (Icons.DOWNLOAD, "Downloading"),
        "decrypt": (Icons.ENCRYPT, "Decrypting"),
        "extract": (Icons.COMPRESS, "Extracting"),
        "restore": (Icons.RESTORE, "Restoring"),
    }

    def __init__(self) -> None:
        self.progress = create_transfer_progress()
        self.task_id: Optional[TaskID] = None
        self.current_stage = ""

    def __enter__(self) -> "RestoreProgressManager":
        self.progress.__enter__()
        return self

    def __exit__(self, *args: Any) -> None:
        self.progress.__exit__(*args)

    def update(self, stage: str, current: int, total: int) -> None:
        """Update progress for a stage."""
        if stage != self.current_stage:
            if self.task_id is not None:
                self.progress.update(
                    self.task_id,
                    completed=self.progress.tasks[self.task_id].total or current,
                )

            icon, desc = self.STAGES.get(stage, (Icons.RUNNING, stage.capitalize()))
            self.task_id = self.progress.add_task(
                f"{icon} {desc}",
                total=total if total > 0 else None,
            )
            self.current_stage = stage

        if self.task_id is not None and total > 0:
            self.progress.update(self.task_id, completed=current)


def print_backup_summary(manifest: Any) -> None:
    """Print a beautiful backup summary panel."""
    from .utils import format_size

    console.print()

    # Create summary table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Label", style="dim")
    table.add_column("Value", style="bold")

    table.add_row("Backup ID", f"[cyan]{manifest.backup_name}[/cyan]")
    table.add_row("Files", f"[white]{manifest.file_count}[/white]")
    table.add_row("Original", f"[yellow]{format_size(manifest.total_size)}[/yellow]")
    table.add_row("Compressed", f"[blue]{format_size(manifest.compressed_size)}[/blue]")
    table.add_row("Encrypted", f"[green]{format_size(manifest.encrypted_size)}[/green]")

    # Calculate compression ratio
    if manifest.total_size > 0:
        ratio = (1 - manifest.compressed_size / manifest.total_size) * 100
        table.add_row("Compression", f"[magenta]{ratio:.1f}% saved[/magenta]")

    panel = Panel(
        table,
        title=f"[bold green]{Icons.SUCCESS} Backup Complete[/bold green]",
        box=box.ROUNDED,
        border_style="green",
        padding=(1, 2),
    )
    console.print(panel)


def print_restore_summary(preview: Any, file_count: int, dest: str) -> None:
    """Print a beautiful restore summary panel."""
    console.print()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Label", style="dim")
    table.add_column("Value", style="bold")

    table.add_row("Backup", f"[cyan]{preview.backup_name}[/cyan]")
    table.add_row("Profile", f"[magenta]{preview.profile_name}[/magenta]")
    table.add_row("Destination", f"[blue]{dest}[/blue]")
    table.add_row("Files Restored", f"[green]{file_count}[/green]")

    panel = Panel(
        table,
        title=f"[bold green]{Icons.SUCCESS} Restore Complete[/bold green]",
        box=box.ROUNDED,
        border_style="green",
        padding=(1, 2),
    )
    console.print(panel)


def print_verify_result(result: Any) -> None:
    """Print verification results in a styled panel."""
    from .utils import format_size

    console.print()

    # Status indicators
    def status_text(ok: bool) -> str:
        return f"[green]{Icons.SUCCESS} OK[/green]" if ok else f"[red]{Icons.ERROR} FAILED[/red]"

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Check", style="dim")
    table.add_column("Status")

    table.add_row("Decryption", status_text(result.can_decrypt))
    table.add_row("Manifest", status_text(result.manifest_valid))
    table.add_row("Archive", status_text(result.archive_valid))
    table.add_row("", "")
    table.add_row("Files", f"[white]{result.file_count}[/white]")
    table.add_row("Total Size", f"[yellow]{format_size(result.total_size)}[/yellow]")

    if result.is_valid:
        title = f"[bold green]{Icons.SUCCESS} Verification Passed[/bold green]"
        border = "green"
    else:
        title = f"[bold red]{Icons.ERROR} Verification Failed[/bold red]"
        border = "red"

    panel = Panel(
        table,
        title=title,
        subtitle=f"[dim]{result.backup_name}[/dim]",
        box=box.ROUNDED,
        border_style=border,
        padding=(1, 2),
    )
    console.print(panel)

    if result.errors:
        console.print()
        for error in result.errors:
            print_warning(error)


def print_backup_preview(files: list[dict], total_size: int) -> None:
    """Print a preview of files to be backed up."""
    from .utils import format_size

    console.print()

    # Create file tree
    tree = create_file_tree(files)
    console.print(Panel(tree, title="[bold]Files to Backup[/bold]", box=box.ROUNDED, border_style="cyan"))

    console.print()
    stats = {
        "Total Files": str(len(files)),
        "Total Size": format_size(total_size),
    }
    print_stats_panel(stats, "Backup Preview")


def print_restore_preview(files: list[str], dest: str) -> None:
    """Print a preview of files to be restored."""
    console.print()

    # Create file tree
    file_dicts = [{"path": f} for f in files]
    tree = create_file_tree(file_dicts)
    console.print(
        Panel(
            tree,
            title="[bold]Files to Restore[/bold]",
            subtitle=f"[dim]Destination: {dest}[/dim]",
            box=box.ROUNDED,
            border_style="blue",
        )
    )

    console.print()
    console.print(f"  [dim]Total:[/dim] [bold]{len(files)}[/bold] files")


def print_profile_details(profile: Any) -> None:
    """Print detailed profile information."""
    console.print()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="dim")
    table.add_column("Value", style="bold")

    table.add_row("Name", f"[magenta]{profile.name}[/magenta]")
    table.add_row("Source", f"[cyan]{profile.source_directory}[/cyan]")
    table.add_row(
        "Password",
        f"[yellow]{profile.password_env_var}[/yellow]"
        if profile.password_env_var
        else "[dim](prompt at runtime)[/dim]",
    )

    panel = Panel(
        table,
        title=f"[bold magenta]{Icons.PROFILE} Profile Details[/bold magenta]",
        box=box.ROUNDED,
        border_style="magenta",
        padding=(1, 2),
    )
    console.print(panel)

    if profile.exclude_patterns:
        console.print()
        console.print("  [dim]Exclusion Patterns:[/dim]")
        for pattern in profile.exclude_patterns:
            console.print(f"    [yellow]{Icons.BULLET}[/yellow] {pattern}")


def print_welcome() -> None:
    """Print welcome message for init."""
    console.print()
    console.print(get_app_header())
    console.print()
    console.print(
        Align.center(
            Text("Encrypt locally. Upload safely. Restore reliably.", style="dim italic")
        )
    )
    console.print()


def print_init_success(username: str, repo: str) -> None:
    """Print initialization success message."""
    console.print()

    content = Table(show_header=False, box=None, padding=(0, 1))
    content.add_column("", style="dim")
    content.add_column("")

    content.add_row("Repository", f"[cyan]{username}/{repo}[/cyan]")
    content.add_row("Config", f"[blue]~/.termbackup/config.json[/blue]")

    panel = Panel(
        Group(
            Align.center(Text(f"{Icons.SUCCESS} Initialization Complete!", style="bold green")),
            Text(""),
            content,
            Text(""),
            Align.center(Text("Next steps:", style="bold")),
            Text("  1. Create a profile:  termbackup profile create", style="cyan"),
            Text("  2. Run a backup:      termbackup run <profile>", style="cyan"),
        ),
        box=box.DOUBLE,
        border_style="green",
        padding=(1, 3),
    )
    console.print(panel)


def print_no_backups() -> None:
    """Print message when no backups exist."""
    console.print()
    panel = Panel(
        Group(
            Align.center(Text("No backups found", style="dim")),
            Text(""),
            Align.center(Text("Create your first backup:", style="bold")),
            Align.center(Text("termbackup run <profile>", style="cyan")),
        ),
        box=box.ROUNDED,
        border_style="dim",
        padding=(1, 2),
    )
    console.print(panel)


def print_no_profiles() -> None:
    """Print message when no profiles exist."""
    console.print()
    panel = Panel(
        Group(
            Align.center(Text("No profiles configured", style="dim")),
            Text(""),
            Align.center(Text("Create a profile:", style="bold")),
            Align.center(Text("termbackup profile create", style="cyan")),
        ),
        box=box.ROUNDED,
        border_style="dim",
        padding=(1, 2),
    )
    console.print(panel)
