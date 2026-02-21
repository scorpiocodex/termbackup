"""
TermBackup UI Module -- Next-Gen Futuristic Terminal Interface
===============================================================
All terminal output flows through this module for consistent styling.
Features gradient banner, themed panels, status badges, animated spinners,
token validation display, and Unicode/ASCII adaptive fallback.
"""

import sys
from datetime import UTC, datetime

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.rule import Rule
from rich.style import Style
from rich.table import Table
from rich.text import Text

from termbackup import __version__

# -- Terminal capability detection ---------------------------------------------
_UNICODE_OK = False
try:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    _UNICODE_OK = True
except Exception:
    pass

console = Console(force_terminal=True if _UNICODE_OK else None)


# -- Icon system with Unicode/ASCII fallback -----------------------------------
class Icons:
    if _UNICODE_OK:
        ARROW = "\u25b8"       # >
        CHECK = "\u2714"       # checkmark
        CROSS = "\u2718"       # x mark
        WARN = "\u26a0"        # warning
        STEP = "\u2502"        # vertical line
        DOT = "\u2022"         # bullet
        LOCK = "\U0001f512"    # lock
        GEAR = "\u2699"        # gear
        SHIELD = "\U0001f6e1"  # shield
        BOLT = "\u26a1"        # lightning
        KEY = "\U0001f511"     # key
        GLOBE = "\U0001f310"   # globe
        CLOCK = "\U0001f552"   # clock
        CHAIN = "\U0001f517"   # chain link
        STAR = "\u2605"        # star
        PIPE = "\u2503"        # thick pipe
        CORNER_TL = "\u250f"   # top-left corner
        CORNER_TR = "\u2513"   # top-right corner
        CORNER_BL = "\u2517"   # bottom-left corner
        CORNER_BR = "\u251b"   # bottom-right corner
        HORIZONTAL = "\u2501"  # horizontal line
        VERTICAL = "\u2503"    # vertical line
        TEE_R = "\u2523"       # right tee
        TEE_L = "\u252b"       # left tee
        ARROW_R = "\u25b6"     # right arrow
        DIAMOND = "\u25c8"     # diamond
        CIRCLE = "\u25cf"      # circle
        RING = "\u25cb"        # ring
        LOCK_CLOSED = "\U0001f510"  # closed lock with key
        TOKEN = "\U0001f3ab"   # ticket/token
        ROCKET = "\U0001f680"  # rocket
        FOLDER = "\U0001f4c1"  # folder
        FILE = "\U0001f4c4"    # file
        TRASH = "\U0001f5d1"   # trash
        DOWNLOAD = "\u2b07"    # download
        UPLOAD = "\u2b06"      # upload
        REFRESH = "\u21bb"     # refresh
        SEARCH = "\U0001f50d"  # search
        PULSE = "\u2764"       # heartbeat
    else:
        ARROW = ">"
        CHECK = "+"
        CROSS = "x"
        WARN = "!"
        STEP = "|"
        DOT = "*"
        LOCK = "#"
        GEAR = "*"
        SHIELD = "#"
        BOLT = "!"
        KEY = "#"
        GLOBE = "O"
        CLOCK = "@"
        CHAIN = "="
        STAR = "*"
        PIPE = "|"
        CORNER_TL = "+"
        CORNER_TR = "+"
        CORNER_BL = "+"
        CORNER_BR = "+"
        HORIZONTAL = "-"
        VERTICAL = "|"
        TEE_R = "+"
        TEE_L = "+"
        ARROW_R = ">"
        DIAMOND = "<>"
        CIRCLE = "o"
        RING = "o"
        LOCK_CLOSED = "#"
        TOKEN = "|"
        ROCKET = ">"
        FOLDER = "/"
        FILE = "F"
        TRASH = "D"
        DOWNLOAD = "v"
        UPLOAD = "^"
        REFRESH = "R"
        SEARCH = "?"
        PULSE = "+"


# -- Futuristic color theme ---------------------------------------------------
class Theme:
    PRIMARY = "#00d4ff"       # Neon cyan
    SECONDARY = "#7c3aed"    # Deep purple
    ACCENT = "#22d3ee"        # Light cyan
    SUCCESS = "#10b981"       # Emerald
    WARNING = "#f59e0b"       # Amber
    ERROR = "#ef4444"         # Red
    DIM = "#6b7280"           # Gray-500
    TEXT = "#e5e7eb"          # Gray-200
    HIGHLIGHT = "#f0abfc"     # Fuchsia-300
    SURFACE = "#1e293b"       # Slate-800
    GRADIENT_START = "#06b6d4"  # Cyan
    GRADIENT_MID = "#8b5cf6"    # Purple
    GRADIENT_END = "#ec4899"    # Pink
    GOLD = "#fbbf24"          # Gold
    STEEL = "#94a3b8"         # Steel
    NEON_GREEN = "#34d399"    # Neon green
    DEEP_BLUE = "#3b82f6"     # Deep blue


# Legacy color aliases (used by existing code)
CYAN = "bright_cyan"
BLUE = "blue"
GREEN = "bright_green"
RED = "bright_red"
YELLOW = "bright_yellow"
DIM = "dim"
WHITE = "white"
MAGENTA = "bright_magenta"
ACCENT = "cyan"


# -- Banner Art ----------------------------------------------------------------
BANNER_ART = r"""
 ▀█▀ █▀▀ █▀█ █▀▄▀█ █▄▄ ▄▀█ █▀▀ █▄▀ █ █ █▀█
  █  ██▄ █▀▄ █ ▀ █ █▄█ █▀█ █▄▄ █ █ █▄█ █▀▀
"""

TAGLINE = "ZERO-TRUST ENCRYPTED GITHUB BACKUP SYSTEM"

MINI_BANNER = (
    f"[{Theme.PRIMARY}]◈[/{Theme.PRIMARY}] "
    f"[bold white]TERM[/bold white][bold {Theme.HIGHLIGHT}]BACKUP[/bold {Theme.HIGHLIGHT}] "
    f"[{Theme.DIM}]v{__version__}[/{Theme.DIM}]"
)

# Gradient colors for banner lines
_GRADIENT = [
    "#00d4ff",  # Neon cyan
    "#8b5cf6",  # Deep purple
]


def print_banner():
    """Prints the full branded banner with gradient coloring and system info."""
    console.print()
    lines = BANNER_ART.strip("\n").split("\n")
    for i, line in enumerate(lines):
        color = _GRADIENT[min(i, len(_GRADIENT) - 1)]
        text = Text(line)
        text.stylize(Style(color=color, bold=True))
        console.print(text)
    console.print()

    # Tagline with gradient effect
    tagline_text = Text(f"  ◈  {TAGLINE}")
    tagline_text.stylize(Style(color=Theme.ACCENT, bold=True))
    console.print(tagline_text)

    # Version and encryption info
    console.print(
        f"  [{Theme.DIM}]v{__version__}[/{Theme.DIM}] "
        f"[{Theme.DIM}]│[/{Theme.DIM}] "
        f"[{Theme.PRIMARY}]AES-256-GCM[/{Theme.PRIMARY}] "
        f"[{Theme.DIM}]+[/{Theme.DIM}] "
        f"[{Theme.HIGHLIGHT}]Argon2id[/{Theme.HIGHLIGHT}] "
        f"[{Theme.DIM}]│[/{Theme.DIM}] "
        f"[{Theme.PRIMARY}]Ed25519[/{Theme.PRIMARY}]"
    )

    # System info line
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    console.print(
        f"  [{Theme.DIM}]{now}[/{Theme.DIM}] "
        f"[{Theme.DIM}]│[/{Theme.DIM}] "
        f"[{Theme.DIM}]Python {sys.version_info.major}.{sys.version_info.minor}[/{Theme.DIM}] "
        f"[{Theme.DIM}]│[/{Theme.DIM}] "
        f"[{Theme.DIM}]{sys.platform}[/{Theme.DIM}]"
    )
    console.print()


# -- Header / Footer ----------------------------------------------------------

def print_header(subtitle: str = "", icon: str | None = None):
    """Prints the branded CLI header with optional subtitle and icon."""
    console.print()
    console.print(MINI_BANNER)
    console.print(Rule(style=Theme.ACCENT))
    if subtitle:
        icon_str = f"{icon} " if icon else f"{Icons.ARROW_R} "
        console.print(
            f"  [bold {Theme.PRIMARY}]{icon_str}[/bold {Theme.PRIMARY}]"
            f" [{Theme.TEXT}]{subtitle}[/{Theme.TEXT}]"
        )
        console.print()


def print_footer():
    """Prints a footer separator."""
    console.print(Rule(style=Theme.DIM))
    console.print()


# -- Status Messages -----------------------------------------------------------

def info(message: str):
    """Prints an info message."""
    console.print(f"  [{Theme.PRIMARY}]{Icons.ARROW}[/{Theme.PRIMARY}]  {message}")


def success(message: str):
    """Prints a success message."""
    console.print(f"  [{Theme.SUCCESS}]{Icons.CHECK}[/{Theme.SUCCESS}]  [bold]{message}[/bold]")


def warning(message: str):
    """Prints a warning message."""
    console.print(f"  [{Theme.WARNING}]{Icons.WARN}[/{Theme.WARNING}]  {message}")


def error(message: str):
    """Prints an error message."""
    console.print(
        f"  [{Theme.ERROR}]{Icons.CROSS}[/{Theme.ERROR}]  "
        f"[bold {Theme.ERROR}]{message}[/bold {Theme.ERROR}]"
    )


def step(message: str):
    """Prints a step indicator for multi-step operations."""
    console.print(f"  [{Theme.DIM}]{Icons.STEP}[/{Theme.DIM}]  {message}")


def detail(label: str, value: str):
    """Prints a labeled detail line."""
    console.print(f"    [{Theme.DIM}]{label}:[/{Theme.DIM}]  {value}")


# -- Step Progress -------------------------------------------------------------

def print_step_progress(current: int, total: int, description: str):
    """Prints [2/5] style step progress with visual indicator."""
    if total > 0:
        progress_str = f"[{current}/{total}]"
        # Visual progress bar
        filled = int((current / total) * 10)
        bar = f"[{Theme.PRIMARY}]{'=' * filled}[/{Theme.PRIMARY}][{Theme.DIM}]{'-' * (10 - filled)}[/{Theme.DIM}]"
        console.print(
            f"  [{Theme.PRIMARY}]{progress_str}[/{Theme.PRIMARY}] {bar}  {description}"
        )
    else:
        progress_str = f"[{current}]"
        console.print(
            f"  [{Theme.PRIMARY}]{progress_str}[/{Theme.PRIMARY}]  {description}"
        )


# -- Status Badge --------------------------------------------------------------

def status_badge(text: str, variant: str = "success") -> Text:
    """Returns a styled status badge Text object."""
    colors = {
        "success": Theme.SUCCESS,
        "error": Theme.ERROR,
        "warning": Theme.WARNING,
        "info": Theme.PRIMARY,
        "encrypted": Theme.ACCENT,
        "gold": Theme.GOLD,
    }
    color = colors.get(variant, Theme.DIM)
    badge = Text(f"[{text.upper()}]")
    badge.stylize(Style(color=color, bold=True))
    return badge


# -- Tables --------------------------------------------------------------------

def create_table(*columns: str, title: str = "", show_row_numbers: bool = False) -> Table:
    """Creates a styled table with the project's visual identity."""
    table = Table(
        box=box.ROUNDED,
        border_style=Theme.ACCENT,
        header_style=f"bold {Theme.PRIMARY}",
        title=f"[bold {Theme.PRIMARY}]{title}[/bold {Theme.PRIMARY}]" if title else None,
        title_style=f"bold {Theme.PRIMARY}",
        show_edge=True,
        pad_edge=True,
        padding=(0, 1),
        row_styles=[Style(), Style(dim=True)],
        show_lines=False,
    )
    if show_row_numbers:
        table.add_column("#", style=Theme.DIM, width=4)
    for col in columns:
        table.add_column(col)
    return table


def print_table(table: Table):
    """Prints a styled table."""
    console.print()
    console.print(table)
    console.print()


# -- Panels --------------------------------------------------------------------

def print_panel(content: str, title: str = "", style: str = ""):
    """Prints content inside a styled panel."""
    console.print()
    console.print(Panel(
        content,
        title=f"[bold]{title}[/bold]" if title else None,
        border_style=style or Theme.ACCENT,
        padding=(1, 2),
    ))
    console.print()


def print_summary_panel(title: str, items: list[tuple[str, str]], style: str = "success"):
    """Prints a summary panel with key-value pairs."""
    style_colors = {
        "success": Theme.SUCCESS,
        "error": Theme.ERROR,
        "warning": Theme.WARNING,
        "info": Theme.PRIMARY,
    }
    border_color = style_colors.get(style, Theme.ACCENT)

    lines = []
    for label, value in items:
        lines.append(f"  [{Theme.DIM}]{label:<18}[/{Theme.DIM}]  {value}")

    content = "\n".join(lines)
    console.print()
    console.print(Panel(
        content,
        title=f"[bold]{title}[/bold]",
        border_style=border_color,
        padding=(1, 2),
    ))
    console.print()


# -- Dashboard -----------------------------------------------------------------

def print_dashboard(sections: list[Panel]):
    """Prints multiple panels in a dashboard layout."""
    console.print()
    console.print(Columns(sections, equal=True, expand=True))
    console.print()


# -- Diff Table ----------------------------------------------------------------

def print_diff_table(changes: dict):
    """Prints a color-coded diff of file changes."""
    table = create_table("Status", "File", "Size", title="Changes")

    for f in changes.get("added", []):
        path = f.get("relative_path", "")
        size = f.get("size", 0)
        table.add_row(
            f"[{Theme.SUCCESS}]+ added[/{Theme.SUCCESS}]",
            path,
            _format_size_inline(size),
        )
    for f in changes.get("modified", []):
        path = f.get("relative_path", "")
        size = f.get("size", 0)
        table.add_row(
            f"[{Theme.WARNING}]~ modified[/{Theme.WARNING}]",
            path,
            _format_size_inline(size),
        )
    for f in changes.get("deleted", []):
        path = f.get("relative_path", "")
        size = f.get("size", 0)
        table.add_row(
            f"[{Theme.ERROR}]- deleted[/{Theme.ERROR}]",
            path,
            _format_size_inline(size),
        )

    total = len(changes.get("added", [])) + len(changes.get("modified", [])) + len(changes.get("deleted", []))
    unchanged = len(changes.get("unchanged", []))

    print_table(table)
    info(f"{total} change(s), {unchanged} unchanged")


def _format_size_inline(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


# -- Checklist -----------------------------------------------------------------

def print_checklist(items: list[tuple[str, bool, str]]):
    """Prints a checklist of items with pass/fail status.

    Args:
        items: List of (name, passed, message) tuples.
    """
    for name, passed, message in items:
        if passed:
            console.print(
                f"  [{Theme.SUCCESS}]{Icons.CHECK}[/{Theme.SUCCESS}]  "
                f"{name} [{Theme.DIM}]{message}[/{Theme.DIM}]"
            )
        else:
            console.print(
                f"  [{Theme.ERROR}]{Icons.CROSS}[/{Theme.ERROR}]  "
                f"{name} [{Theme.ERROR}]{message}[/{Theme.ERROR}]"
            )


# -- Progress ------------------------------------------------------------------

def create_progress(description: str = "", total: int | None = None) -> Progress:
    """Creates a styled progress bar."""
    return Progress(
        SpinnerColumn(style=Theme.PRIMARY),
        TextColumn("[bold]{task.description}[/bold]"),
        BarColumn(
            bar_width=30,
            style=Theme.DIM,
            complete_style=Theme.PRIMARY,
            finished_style=Theme.SUCCESS,
        ),
        TextColumn("[{task.percentage:>3.0f}%]"),
        TimeElapsedColumn(),
        console=console,
    )


def create_spinner() -> Progress:
    """Creates a simple spinner for indeterminate operations."""
    return Progress(
        SpinnerColumn(style=Theme.PRIMARY),
        TextColumn("[bold]{task.description}[/bold]"),
        TimeElapsedColumn(),
        console=console,
    )


# -- Confirmation / Input -----------------------------------------------------

def confirm(message: str) -> bool:
    """Asks for user confirmation."""
    return console.input(
        f"  [{Theme.WARNING}]?[/{Theme.WARNING}]  {message} [{Theme.DIM}](y/N)[/{Theme.DIM}] "
    ).lower().strip() in ("y", "yes")


def prompt_secret(message: str) -> str:
    """Prompts for hidden input (passwords)."""
    return console.input(
        f"  [{Theme.PRIMARY}]{Icons.LOCK}[/{Theme.PRIMARY}]  {message}: ",
        password=True,
    )


def prompt_input(message: str) -> str:
    """Prompts for visible text input."""
    return console.input(
        f"  [{Theme.PRIMARY}]{Icons.ARROW}[/{Theme.PRIMARY}]  {message}: "
    )


def prompt_input_default(message: str, default: str) -> str:
    """Prompts for visible text input with a default value shown in brackets."""
    raw = console.input(
        f"  [{Theme.PRIMARY}]{Icons.ARROW}[/{Theme.PRIMARY}]  {message} "
        f"[{Theme.DIM}][{default}][/{Theme.DIM}]: "
    ).strip()
    return raw if raw else default


def confirm_default_yes(message: str) -> bool:
    """Asks for user confirmation with Y as the default."""
    return console.input(
        f"  [{Theme.WARNING}]?[/{Theme.WARNING}]  {message} [{Theme.DIM}](Y/n)[/{Theme.DIM}] "
    ).lower().strip() not in ("n", "no")


def prompt_select(message: str, choices: list[str]) -> int:
    """Numbered selection prompt for interactive choices.

    Returns:
        Zero-based index of the selected choice.
    """
    console.print(f"\n  [{Theme.PRIMARY}]{Icons.ARROW}[/{Theme.PRIMARY}]  {message}")
    for i, choice in enumerate(choices, 1):
        console.print(f"    [{Theme.DIM}]{i}.[/{Theme.DIM}]  {choice}")

    while True:
        raw = console.input(
            f"  [{Theme.PRIMARY}]{Icons.ARROW}[/{Theme.PRIMARY}]  Choice (1-{len(choices)}): "
        ).strip()
        try:
            idx = int(raw)
            if 1 <= idx <= len(choices):
                return idx - 1
        except ValueError:
            pass
        warning(f"Please enter a number between 1 and {len(choices)}")


# -- Key-Value Display ---------------------------------------------------------

def print_kv_list(items: list[tuple[str, str]], title: str = "", border: bool = False):
    """Prints a key-value list. Optionally wraps in a Panel."""
    lines = []
    for label, value in items:
        lines.append(f"    [{Theme.DIM}]{label:<20}[/{Theme.DIM}]  {value}")

    content = "\n".join(lines)

    if border:
        console.print()
        console.print(Panel(
            content,
            title=f"[bold]{title}[/bold]" if title else None,
            border_style=Theme.ACCENT,
        ))
        console.print()
    else:
        if title:
            console.print(f"\n  [bold {Theme.PRIMARY}]{title}[/bold {Theme.PRIMARY}]")
        console.print(content)
        console.print()


# -- Empty State ---------------------------------------------------------------

def print_empty(message: str, suggestion: str | None = None):
    """Prints an empty state message with optional suggestion."""
    console.print(f"\n  [{Theme.DIM}]{message}[/{Theme.DIM}]")
    if suggestion:
        console.print(f"  [{Theme.DIM}]{Icons.ARROW}  {suggestion}[/{Theme.DIM}]")
    console.print()


# -- Section Header ------------------------------------------------------------

def print_section(title: str):
    """Prints a section header with thin rule."""
    console.print()
    console.print(f"  [bold {Theme.PRIMARY}]{title}[/bold {Theme.PRIMARY}]")
    console.print(Rule(style=Theme.DIM))


# -- Token Validation Display --------------------------------------------------

def print_token_validation(info) -> None:
    """Displays token validation results with visual indicators.

    Args:
        info: TokenInfo dataclass from token_validator module.
    """
    from termbackup.token_validator import ValidationStatus

    # Status indicator
    status_map = {
        ValidationStatus.VALID: (Icons.CHECK, Theme.SUCCESS, "TOKEN VALID"),
        ValidationStatus.INVALID: (Icons.CROSS, Theme.ERROR, "TOKEN INVALID"),
        ValidationStatus.EXPIRED: (Icons.CROSS, Theme.ERROR, "TOKEN EXPIRED"),
        ValidationStatus.INSUFFICIENT_SCOPE: (Icons.WARN, Theme.WARNING, "INSUFFICIENT PERMISSIONS"),
        ValidationStatus.NETWORK_ERROR: (Icons.WARN, Theme.WARNING, "NETWORK ERROR"),
        ValidationStatus.RATE_LIMITED: (Icons.CLOCK, Theme.WARNING, "RATE LIMITED"),
    }

    icon, color, label = status_map.get(
        info.status,
        (Icons.WARN, Theme.WARNING, "UNKNOWN"),
    )

    console.print()
    console.print(
        f"  [{color}]{icon}[/{color}]  "
        f"[bold {color}]{label}[/bold {color}]"
    )

    # Token details
    items: list[tuple[str, str]] = []

    if info.masked_token:
        items.append(("Token", info.masked_token))

    if info.token_type.value != "unknown":
        type_display = info.token_type.value.replace("-", " ").title()
        items.append(("Type", type_display))

    if info.username:
        items.append(("User", f"[bold]{info.username}[/bold]"))

    if info.scopes:
        scopes_str = ", ".join(info.scopes)
        items.append(("Scopes", scopes_str))

    if info.rate_limit_total > 0:
        rl_pct = (info.rate_limit_remaining / info.rate_limit_total * 100) if info.rate_limit_total else 0
        rl_color = Theme.SUCCESS if rl_pct > 50 else Theme.WARNING if rl_pct > 10 else Theme.ERROR
        items.append(
            ("Rate Limit", f"[{rl_color}]{info.rate_limit_remaining}/{info.rate_limit_total}[/{rl_color}]")
        )

    if info.missing_scopes:
        missing = ", ".join(info.missing_scopes)
        items.append(("Missing Scopes", f"[{Theme.ERROR}]{missing}[/{Theme.ERROR}]"))

    if info.missing_permissions:
        missing = ", ".join(f"{k}={v}" for k, v in info.missing_permissions.items())
        items.append(("Missing Perms", f"[{Theme.ERROR}]{missing}[/{Theme.ERROR}]"))

    if items:
        for label, value in items:
            detail(label, value)

    # Message
    if info.message:
        console.print()
        msg_color = color
        console.print(f"  [{Theme.DIM}]{Icons.ARROW}[/{Theme.DIM}]  [{msg_color}]{info.message}[/{msg_color}]")


def print_token_validation_compact(info) -> None:
    """Displays a compact single-line token validation result.

    Args:
        info: TokenInfo dataclass from token_validator module.
    """
    from termbackup.token_validator import ValidationStatus

    if info.status == ValidationStatus.VALID:
        type_str = info.token_type.value.replace("-", " ")
        console.print(
            f"  [{Theme.SUCCESS}]{Icons.CHECK}[/{Theme.SUCCESS}]  "
            f"Token valid ({type_str}) "
            f"[{Theme.DIM}]{Icons.DOT} {info.username}[/{Theme.DIM}]"
        )
    elif info.status == ValidationStatus.INSUFFICIENT_SCOPE:
        console.print(
            f"  [{Theme.WARNING}]{Icons.WARN}[/{Theme.WARNING}]  "
            f"Token authenticated but missing required permissions"
        )
    elif info.status == ValidationStatus.NETWORK_ERROR:
        console.print(
            f"  [{Theme.WARNING}]{Icons.WARN}[/{Theme.WARNING}]  "
            f"Could not validate token (network issue)"
        )
    else:
        console.print(
            f"  [{Theme.ERROR}]{Icons.CROSS}[/{Theme.ERROR}]  "
            f"[bold {Theme.ERROR}]Token validation failed: {info.message}[/bold {Theme.ERROR}]"
        )


# -- Help Screen ---------------------------------------------------------------

def print_help_screen() -> None:
    """Renders the full sci-fi themed help screen, grouped by command category."""
    from termbackup import __version__

    console.print()

    # ── Header ─────────────────────────────────────────────────────────────
    print_banner()
    console.print()

    # ── Usage ──────────────────────────────────────────────────────────────
    usage_text = Text()
    usage_text.append("  ◢ USAGE ◣  ", style=f"bold {Theme.PRIMARY}")
    usage_text.append("termbackup ", style="bold white")
    usage_text.append("<command> ", style=f"bold {Theme.HIGHLIGHT}")
    usage_text.append("[options] [arguments]", style=Theme.DIM)
    console.print(usage_text)
    console.print(Rule(style=Theme.DIM))
    console.print()

    # ── Helper to render a command group ───────────────────────────────────
    def _section(icon: str, title: str, rows: list[tuple[str, str, str]]) -> None:
        """Render one command group. rows = (command, args_hint, description)."""
        console.print(f"  [{Theme.GOLD}]{icon}[/{Theme.GOLD}]  [bold {Theme.GOLD}]{title}[/bold {Theme.GOLD}]")
        tbl = Table(
            box=None,
            show_header=False,
            show_edge=False,
            pad_edge=False,
            padding=(0, 3, 0, 4),
            expand=False,
        )
        # Column 1: bold-cyan command name
        tbl.add_column("cmd",  no_wrap=True, min_width=18, max_width=22)
        # Column 2: dim args hint
        tbl.add_column("args", no_wrap=True, min_width=28, max_width=36)
        # Column 3: description (allow wrap on narrow terminals)
        tbl.add_column("desc", min_width=30)
        for cmd, args, desc in rows:
            tbl.add_row(
                f"[bold {Theme.PRIMARY}]{cmd}[/bold {Theme.PRIMARY}]",
                f"[{Theme.ACCENT}]{args}[/{Theme.ACCENT}]",
                f"[{Theme.TEXT}]{desc}[/{Theme.TEXT}]",
            )
        console.print(tbl)
        console.print()

    # ── Core Operations ─────────────────────────────────────────────────────
    _section(Icons.ROCKET, "CORE OPERATIONS", [
        ("init",    "",                         "Initialize TermBackup config & GitHub token"),
        ("run",     "<profile>",                "Execute an encrypted backup"),
        ("list",    "<profile>",                "List all backups for a profile"),
        ("restore", "<id> -p <profile>",        "Decrypt and restore a backup to disk"),
        ("verify",  "<id> -p <profile>",        "Verify backup integrity & signatures"),
        ("prune",   "<profile>",                "Prune old backups by retention policy"),
    ])

    # ── Cryptography ────────────────────────────────────────────────────────
    _section(Icons.SHIELD, "CRYPTOGRAPHY & KEYS", [
        ("generate-key", "",          "Generate an Ed25519 signing keypair"),
        ("rotate-key",   "<profile>", "Re-encrypt all backups with a new password"),
        ("migrate",      "",          "Migrate GitHub token to OS keyring"),
    ])

    # ── Token Management ────────────────────────────────────────────────────
    _section(Icons.KEY, "TOKEN MANAGEMENT", [
        ("update-token", "",  "Update and validate GitHub PAT"),
        ("token-info",   "",  "Display current token details & scopes"),
    ])

    # ── Diagnostics ─────────────────────────────────────────────────────────
    _section(Icons.SEARCH, "DIAGNOSTICS", [
        ("status",    "",                       "Display full system status overview"),
        ("doctor",    "",                       "Run 12-point health check suite"),
        ("diff",      "<id1> <id2> -p <name>",  "Compare two backups side-by-side"),
        ("audit-log", "[-n <n>] [-o <op>]",     "View the structured audit trail"),
        ("clean",     "",                       "Remove orphaned temporary files"),
    ])

    # ── Scheduling & Daemon ─────────────────────────────────────────────────
    _section(Icons.CLOCK, "SCHEDULING & DAEMON", [
        ("schedule-enable",  "<profile> --schedule <cron>", "Enable automated scheduled backups"),
        ("schedule-disable", "<profile>",                   "Disable scheduled backups"),
        ("schedule-status",  "<profile>",                   "Check schedule status for a profile"),
        ("daemon",           "<profile> [-i <min>]",        "Run in continuous daemon loop"),
    ])

    # ── Profile Management ──────────────────────────────────────────────────
    _section(Icons.FOLDER, "PROFILE MANAGEMENT", [
        ("profile create", "<name>", "Create a new backup profile"),
        ("profile list",   "",       "List all configured profiles"),
        ("profile show",   "<name>", "Show profile configuration"),
        ("profile edit",   "<name>", "Edit an existing profile"),
        ("profile delete", "<name>", "Delete a profile permanently"),
    ])

    # ── Global Options ──────────────────────────────────────────────────────
    console.print(f"  [bold {Theme.DIM}]OPTIONS[/bold {Theme.DIM}]")
    opts = Table(
        box=None,
        show_header=False,
        show_edge=False,
        pad_edge=False,
        padding=(0, 3, 0, 4),
        expand=False,
    )
    opts.add_column("flag", no_wrap=True, min_width=18, max_width=22)
    opts.add_column("args", no_wrap=True, min_width=28, max_width=36)
    opts.add_column("desc", min_width=30)
    opts.add_row(
        f"[bold {Theme.PRIMARY}]--version,  -v[/bold {Theme.PRIMARY}]",
        "",
        f"[{Theme.TEXT}]Print version info and exit[/{Theme.TEXT}]",
    )
    opts.add_row(
        f"[bold {Theme.PRIMARY}]--help,     -h[/bold {Theme.PRIMARY}]",
        "",
        f"[{Theme.TEXT}]Show this help screen and exit[/{Theme.TEXT}]",
    )
    console.print(opts)
    console.print()

    # ── Footer ──────────────────────────────────────────────────────────────
    console.print(Rule(style=Theme.DIM))
    footer = Text()
    footer.append(
        f"  AES-256-GCM  {Icons.DOT}  Argon2id  {Icons.DOT}  Ed25519  "
        f"{Icons.DOT}  HTTP/2  {Icons.DOT}  MIT License",
        style=Theme.DIM,
    )
    console.print(footer)
    console.print(
        f"  [{Theme.DIM}]Run[/{Theme.DIM}] "
        f"[bold {Theme.PRIMARY}]termbackup <command> --help[/bold {Theme.PRIMARY}] "
        f"[{Theme.DIM}]for detailed usage of any command.[/{Theme.DIM}]"
    )
    console.print()


# -- Elapsed Time Display ------------------------------------------------------

def print_elapsed(start_time: float, label: str = "Completed"):
    """Prints elapsed time since start_time."""
    import time
    elapsed = time.time() - start_time
    if elapsed < 1:
        time_str = f"{elapsed * 1000:.0f}ms"
    elif elapsed < 60:
        time_str = f"{elapsed:.1f}s"
    else:
        minutes = int(elapsed // 60)
        secs = elapsed % 60
        time_str = f"{minutes}m {secs:.0f}s"
    console.print(f"  [{Theme.DIM}]{Icons.CLOCK} {label} in {time_str}[/{Theme.DIM}]")
