"""commune feedback — submit errors, feature requests, and signals to Commune."""

from __future__ import annotations

import json
from enum import Enum
from typing import Optional

import typer

from ..client import CommuneClient
from ..errors import api_error, auth_required_error, network_error
from ..output import print_json, print_success
from ..state import AppState

app = typer.Typer(
    help=(
        "Submit feedback to Commune.\n\n"
        "Three types:\n\n"
        "  error    — something broke or behaved unexpectedly\n\n"
        "  feature  — request for new functionality\n\n"
        "  signal   — observations, impressions, things working well or needing polish"
    ),
    no_args_is_help=True,
)


class FeedbackType(str, Enum):
    error = "error"
    feature = "feature"
    signal = "signal"


@app.command("submit")
def feedback_submit(
    ctx: typer.Context,
    type: FeedbackType = typer.Option(
        ...,
        "--type",
        "-t",
        help="Feedback type: error, feature, or signal.",
        show_choices=True,
    ),
    message: Optional[str] = typer.Option(
        None,
        "--message",
        "-m",
        help="Feedback message (prompted if omitted).",
    ),
    context: Optional[str] = typer.Option(
        None,
        "--context",
        help='Optional JSON context object, e.g. \'{"command":"list_threads","status_code":500}\'.',
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Submit feedback. POST /v1/feedback.

    Examples:

      commune feedback submit --type error --message "Thread list 500s when inbox is empty"

      commune feedback submit --type feature --message "Add cursor pagination to search"

      commune feedback submit --type signal --message "Semantic search quality has improved a lot"
    """
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    # Prompt for message if not provided
    if not message:
        message = typer.prompt(f"[{type.value}] Feedback message")

    payload: dict = {"type": type.value, "message": message}

    if context:
        try:
            payload["context"] = json.loads(context)
        except json.JSONDecodeError:
            typer.echo("Error: --context must be valid JSON.", err=True)
            raise typer.Exit(1)

    client = CommuneClient.from_state(state)
    try:
        r = client.post("/v1/feedback", json=payload)
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    data = r.json()
    if json_output or state.should_json():
        print_json(data)
        return

    record = data.get("data", data)
    feedback_id = record.get("id", "")
    type_label = {"error": "Error", "feature": "Feature request", "signal": "Signal"}.get(type.value, type.value)
    print_success(f"[bold]{type_label}[/bold] received. ID: [dim]{feedback_id}[/dim]")
