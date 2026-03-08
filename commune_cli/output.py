"""Output formatting for the Commune CLI.

Rules:
  - All data goes to stdout.
  - All status / progress messages go to stderr.
  - In TTY mode: rich tables and panels.
  - In non-TTY / --json mode: raw JSON to stdout.
  - Errors always go to stderr (handled in errors.py).
"""

from __future__ import annotations

import json
import sys
from typing import Any, Optional, Sequence

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

# stdout console (data)
_out = Console(highlight=False)
# stderr console (status messages)
_err = Console(stderr=True, highlight=False)


# ── primitives ─────────────────────────────────────────────────────────────


def print_json(data: Any) -> None:
    """Print JSON to stdout."""
    sys.stdout.write(json.dumps(data, default=str, indent=2) + "\n")
    sys.stdout.flush()


def print_status(message: str) -> None:
    """Print a status message to stderr (never pollutes stdout)."""
    _err.print(message)


def print_success(message: str) -> None:
    """Print a success message to stderr."""
    _err.print(f"[green]✓[/green] {message}")


def print_warning(message: str) -> None:
    """Print a warning message to stderr."""
    _err.print(f"[yellow]⚠[/yellow] {message}")


# ── list output ────────────────────────────────────────────────────────────


def print_list(
    data: Any,
    json_output: bool,
    columns: Optional[Sequence[tuple[str, str]]] = None,
    title: Optional[str] = None,
) -> None:
    """Print a list response.

    Args:
        data: Raw API response (dict with 'data', list, or other).
        json_output: If True, emit JSON. If False, emit a rich table.
        columns: Sequence of (header, key_path) pairs for table columns.
                 key_path supports dot notation: "inbox.email"
        title: Optional table title.
    """
    if json_output:
        if isinstance(data, dict) and "data" in data:
            # Normalize to {data, has_more, next_cursor}
            out = {
                "data": data["data"],
                "has_more": data.get("hasMore", data.get("has_more", False)),
                "next_cursor": data.get("nextCursor", data.get("next_cursor")),
            }
        elif isinstance(data, list):
            out = {"data": data, "has_more": False, "next_cursor": None}
        else:
            out = {"data": data, "has_more": False, "next_cursor": None}
        print_json(out)
        return

    # Rich table
    items = data if isinstance(data, list) else data.get("data", data)
    if not items:
        _out.print("[dim]No results.[/dim]")
        return

    tbl = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan", title=title)

    if not columns:
        # Auto-columns from first item keys
        if items and isinstance(items[0], dict):
            columns = [(k.upper(), k) for k in list(items[0].keys())[:6]]
        else:
            columns = [("VALUE", "")]

    for header, _ in columns:
        tbl.add_column(header, overflow="fold")

    for item in items:
        if isinstance(item, dict):
            row = [_resolve(item, key) for _, key in columns]
        else:
            row = [str(item)]
        tbl.add_row(*row)

    _out.print(tbl)

    # Pagination hint
    if isinstance(data, dict):
        has_more = data.get("hasMore", data.get("has_more", False))
        cursor = data.get("nextCursor", data.get("next_cursor"))
        if has_more and cursor:
            _err.print(f"[dim]More results available. Use --cursor {cursor}[/dim]")


def print_record(
    data: dict,
    json_output: bool,
    title: Optional[str] = None,
    fields: Optional[Sequence[tuple[str, str]]] = None,
) -> None:
    """Print a single record.

    Args:
        data: Dict of key-value pairs.
        json_output: If True, emit JSON. If False, emit a rich panel.
        title: Panel title.
        fields: Sequence of (label, key_path) pairs. If None, all keys are shown.
    """
    if json_output:
        print_json(data)
        return

    tbl = Table.grid(padding=(0, 1))
    tbl.add_column("key", style="bold dim", no_wrap=True)
    tbl.add_column("value", overflow="fold")

    if fields:
        for label, key in fields:
            tbl.add_row(label, _resolve(data, key))
    else:
        for k, v in data.items():
            tbl.add_row(str(k), str(v) if v is not None else "[dim]null[/dim]")

    _out.print(Panel(tbl, title=f"[bold]{title}[/bold]" if title else None, border_style="cyan"))


def print_kv(pairs: dict[str, str], json_output: bool, title: Optional[str] = None) -> None:
    """Print simple key-value pairs (e.g. config show)."""
    if json_output:
        print_json(pairs)
        return
    tbl = Table.grid(padding=(0, 2))
    tbl.add_column("key", style="bold dim", no_wrap=True)
    tbl.add_column("value", overflow="fold")
    for k, v in pairs.items():
        tbl.add_row(k, v)
    _out.print(Panel(tbl, title=f"[bold]{title}[/bold]" if title else None, border_style="cyan"))


def print_value(value: str, json_output: bool, key: str = "result") -> None:
    """Print a single string value."""
    if json_output:
        print_json({key: value})
        return
    _out.print(value)


# ── helpers ────────────────────────────────────────────────────────────────


def _resolve(obj: dict, key_path: str) -> str:
    """Resolve a dot-notation key path from a dict. Returns '' on miss."""
    if not key_path:
        return str(obj)
    parts = key_path.split(".")
    cur: Any = obj
    for part in parts:
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return ""
    if cur is None:
        return "[dim]—[/dim]"
    if isinstance(cur, (list, dict)):
        return json.dumps(cur)
    return str(cur)
