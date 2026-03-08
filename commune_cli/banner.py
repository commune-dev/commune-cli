"""Animated startup banner for the Commune CLI."""

from __future__ import annotations

import time

from rich.console import Console, Group
from rich.live import Live
from rich.padding import Padding
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from . import __version__

# ── ASCII art (ANSI Shadow font) ───────────────────────────────────────────

_ASCII_LINES = [
    " ██████╗ ██████╗ ███╗   ███╗███╗   ███╗██╗   ██╗███╗   ██╗███████╗",
    "██╔════╝██╔═══██╗████╗ ████║████╗ ████║██║   ██║████╗  ██║██╔════╝",
    "██║     ██║   ██║██╔████╔██║██╔████╔██║██║   ██║██╔██╗ ██║█████╗  ",
    "██║     ██║   ██║██║╚██╔╝██║██║╚██╔╝██║██║   ██║██║╚██╗██║██╔══╝  ",
    "╚██████╗╚██████╔╝██║ ╚═╝ ██║██║ ╚═╝ ██║╚██████╔╝██║ ╚████║███████╗",
    " ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝",
]

# Cyan → electric blue gradient top-to-bottom
_COLORS = [
    "rgb(0,240,255)",
    "rgb(0,210,255)",
    "rgb(0,178,255)",
    "rgb(0,145,255)",
    "rgb(30,110,255)",
    "rgb(80,80,255)",
]

# ── Command registry ───────────────────────────────────────────────────────

_COMMANDS = [
    ("inboxes",     "create · list · update · delete · webhooks · schema"),
    ("messages",    "send · list  (pass --thread-id to reply)"),
    ("threads",     "list · messages · contacts · companies · set-status · tags · assign"),
    ("domains",     "list · create · verify · records"),
    ("search",      "full-text search across threads"),
    ("delivery",    "metrics · events · suppressions · check"),
    ("webhooks",    "deliveries · retry · health"),
    ("attachments", "upload · get · url"),
    ("dmarc",       "list · summary"),
    ("data",        "deletion-request · confirm"),
    ("config",      "set · show · register · status · keys list · keys revoke"),
]

_TAGLINE = "email infrastructure for agents"

# ── Renderable builders ────────────────────────────────────────────────────


def _ascii_art(n: int) -> Text:
    """Render n lines of ASCII art (rest are blank to hold height)."""
    t = Text(no_wrap=True)
    for i in range(min(n, len(_ASCII_LINES))):
        t.append(_ASCII_LINES[i] + "\n", style=f"bold {_COLORS[i]}")
    # Pad remaining lines so the live area height stays constant
    for _ in range(n, len(_ASCII_LINES)):
        t.append("\n")
    return t


def _commands_table() -> Table:
    tbl = Table(box=None, show_header=False, padding=(0, 1), expand=False)
    tbl.add_column("cmd", style="bold bright_cyan", no_wrap=True, min_width=12)
    tbl.add_column("sep", style="dim", no_wrap=True, width=1)
    tbl.add_column("desc", style="dim white")
    for cmd, desc in _COMMANDS:
        tbl.add_row(cmd, "·", desc)
    return tbl


def _frame(
    n: int,
    tagline: str = "",
    show_commands: bool = False,
    show_footer: bool = False,
) -> Group:
    """Build a single animation frame."""
    parts: list = []

    # ASCII block (always takes full 6-line height to prevent jitter)
    parts.append(Padding(_ascii_art(n), (1, 2, 0, 2)))

    # Tagline + version
    sub = Text(no_wrap=True)
    if tagline:
        sub.append(tagline, style="italic white")
        sub.append(f"   v{__version__}", style="bold yellow")
    parts.append(Padding(sub, (0, 2, 0, 2)))

    # Commands section
    if show_commands:
        parts.append(Padding(Rule(characters="─", style="dim"), (1, 2, 0, 2)))
        parts.append(Padding(_commands_table(), (0, 2, 0, 2)))

    # Footer
    if show_footer:
        foot = Text(no_wrap=True)
        foot.append("\n")
        foot.append("commune <command> --help", style="bold cyan")
        foot.append("  ·  ", style="dim")
        foot.append("commune.email", style="dim cyan underline")
        foot.append("  ·  ", style="dim")
        foot.append("docs.commune.email", style="dim cyan underline")
        parts.append(Padding(foot, (0, 2, 1, 2)))

    return Group(*parts)


# ── Entry point ────────────────────────────────────────────────────────────


def show_banner(no_color: bool = False) -> None:
    """Display the animated Commune startup banner.

    Animates in TTY mode; prints static output when piped.
    """
    console = Console(no_color=no_color, highlight=False)

    if not console.is_terminal:
        # Pipe / agent mode — static, no ANSI escape sequences
        console.print(_frame(len(_ASCII_LINES), _TAGLINE, True, True))
        return

    tagline = _TAGLINE

    with Live(
        _frame(0),
        console=console,
        refresh_per_second=50,
        transient=False,
    ) as live:
        # Stage 1: ASCII art — line-by-line reveal  (~270 ms)
        for i in range(1, len(_ASCII_LINES) + 1):
            time.sleep(0.045)
            live.update(_frame(i))

        # Stage 2: Tagline — character-by-character typing  (~400 ms)
        for i in range(1, len(tagline) + 1):
            time.sleep(0.013)
            live.update(_frame(len(_ASCII_LINES), tagline[:i]))

        time.sleep(0.15)

        # Stage 3: Commands drop in
        live.update(_frame(len(_ASCII_LINES), tagline, show_commands=True))
        time.sleep(0.08)

        # Stage 4: Footer appears
        live.update(_frame(len(_ASCII_LINES), tagline, True, True))
