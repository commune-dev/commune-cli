"""Structured error handling and exit codes for the Commune CLI.

Exit codes:
  0  — success
  1  — validation or general API error (400, 422, 409, 5xx)
  2  — authentication/authorization error (401, 403)
  3  — not found (404)
  4  — rate limit or plan gate (429, 403 with plan_upgrade_required)
  5  — network / connection error

Error output format (always to stderr, never pollutes stdout):
  {"error": {"code": "slug_exists", "message": "...", "status_code": 409}}
"""

from __future__ import annotations

import json
import sys
from typing import Optional

import typer


# Exit code constants
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_AUTH = 2
EXIT_NOT_FOUND = 3
EXIT_RATE_LIMIT = 4
EXIT_NETWORK = 5


def _status_to_exit(status_code: int, api_code: Optional[str] = None) -> int:
    if status_code in (401, 403):
        if api_code == "plan_upgrade_required":
            return EXIT_RATE_LIMIT
        return EXIT_AUTH
    if status_code == 404:
        return EXIT_NOT_FOUND
    if status_code == 429:
        return EXIT_RATE_LIMIT
    return EXIT_ERROR


def emit_error(
    message: str,
    code: str = "error",
    status_code: int = 0,
    json_output: bool = False,
) -> None:
    """Write a structured error to stderr."""
    payload = {"error": {"code": code, "message": message}}
    if status_code:
        payload["error"]["status_code"] = status_code  # type: ignore[index]

    if json_output:
        sys.stderr.write(json.dumps(payload) + "\n")
    else:
        from rich.console import Console
        from rich.panel import Panel
        console = Console(stderr=True, highlight=False)
        label = f"[bold red]{code}[/bold red]" if code != "error" else ""
        body = f"{label} {message}".strip() if label else message
        console.print(Panel(body, title="[red]Error[/red]", border_style="red"))


def api_error(
    response,  # httpx.Response
    json_output: bool = False,
) -> typer.Exit:
    """Parse an error HTTP response, emit to stderr, return typer.Exit."""
    status_code = response.status_code
    try:
        data = response.json()
        # Support {"error": "..."}, {"error": {"message": "..."}}, {"message": "..."}
        err = data.get("error", {})
        if isinstance(err, str):
            message = err
            code = "api_error"
        elif isinstance(err, dict):
            message = err.get("message") or err.get("error") or str(data)
            code = err.get("code", "api_error")
        else:
            message = data.get("message", response.text)
            code = "api_error"
    except Exception:
        message = response.text or f"HTTP {status_code}"
        code = "api_error"

    emit_error(message, code=code, status_code=status_code, json_output=json_output)
    exit_code = _status_to_exit(status_code, code)
    raise typer.Exit(exit_code)


def network_error(exc: Exception, json_output: bool = False) -> typer.Exit:
    """Emit a network/connection error and exit with code 5."""
    emit_error(str(exc), code="network_error", json_output=json_output)
    raise typer.Exit(EXIT_NETWORK)


def validation_error(message: str, json_output: bool = False) -> typer.Exit:
    """Emit a client-side validation error and exit with code 1."""
    emit_error(message, code="validation_error", json_output=json_output)
    raise typer.Exit(EXIT_ERROR)


def auth_required_error(json_output: bool = False) -> typer.Exit:
    """Emit an auth-missing error and exit with code 2."""
    emit_error(
        "No API key configured. Set COMMUNE_API_KEY or run: commune config set api_key comm_...",
        code="auth_required",
        json_output=json_output,
    )
    raise typer.Exit(EXIT_AUTH)
