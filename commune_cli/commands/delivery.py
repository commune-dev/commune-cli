"""commune delivery — delivery metrics, events, suppressions, and pre-send checks."""

from __future__ import annotations

from typing import Optional

import typer

from ..client import CommuneClient
from ..errors import EXIT_ERROR, api_error, auth_required_error, network_error
from ..output import print_json, print_list, print_record, print_success, print_warning
from ..state import AppState

app = typer.Typer(help="Delivery metrics, events, suppressions, and pre-send checks.", no_args_is_help=True)

PERIOD_HELP = "Time period: 1d, 7d, 30d (default: 7d)."


@app.command("metrics")
def delivery_metrics(
    ctx: typer.Context,
    domain_id: Optional[str] = typer.Option(None, "--domain-id", help="Filter by domain ID."),
    inbox_id: Optional[str] = typer.Option(None, "--inbox-id", help="Filter by inbox ID."),
    period: Optional[str] = typer.Option(None, "--period", help=PERIOD_HELP),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Get delivery metrics: sent, delivered, bounced, spam rate. GET /v1/delivery/metrics."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/delivery/metrics", params={
            "domainId": domain_id,
            "inboxId": inbox_id,
            "period": period,
        })
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_record(r.json(), json_output=json_output or state.should_json(), title="Delivery Metrics")


@app.command("events")
def delivery_events(
    ctx: typer.Context,
    domain_id: Optional[str] = typer.Option(None, "--domain-id", help="Filter by domain ID."),
    inbox_id: Optional[str] = typer.Option(None, "--inbox-id", help="Filter by inbox ID."),
    limit: Optional[int] = typer.Option(None, "--limit", help="Maximum results to return."),
    cursor: Optional[str] = typer.Option(None, "--cursor", help="Pagination cursor."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """List delivery events: sent, bounce, complaint, open, click. GET /v1/delivery/events."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/delivery/events", params={
            "domainId": domain_id,
            "inboxId": inbox_id,
            "limit": limit,
            "cursor": cursor,
        })
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_list(
        r.json(),
        json_output=json_output or state.should_json(),
        title="Delivery Events",
        columns=[
            ("Type", "type"),
            ("Email", "email"),
            ("Message ID", "messageId"),
            ("Timestamp", "timestamp"),
        ],
    )


@app.command("suppressions")
def delivery_suppressions(
    ctx: typer.Context,
    domain_id: Optional[str] = typer.Option(None, "--domain-id", help="Filter by domain ID."),
    inbox_id: Optional[str] = typer.Option(None, "--inbox-id", help="Filter by inbox ID."),
    limit: Optional[int] = typer.Option(None, "--limit", help="Maximum results."),
    cursor: Optional[str] = typer.Option(None, "--cursor", help="Pagination cursor."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """List suppressed addresses (bounces and spam complaints). GET /v1/delivery/suppressions."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/delivery/suppressions", params={
            "domainId": domain_id,
            "inboxId": inbox_id,
            "limit": limit,
            "cursor": cursor,
        })
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_list(
        r.json(),
        json_output=json_output or state.should_json(),
        title="Suppressed Addresses",
        columns=[
            ("Email", "email"),
            ("Reason", "reason"),
            ("Suppressed At", "suppressedAt"),
        ],
    )


@app.command("check")
def delivery_check(
    ctx: typer.Context,
    email: str = typer.Argument(..., help="Email address to check before sending."),
    inbox_id: Optional[str] = typer.Option(
        None, "--inbox-id",
        help="Check suppression at inbox scope (more specific).",
    ),
    domain_id: Optional[str] = typer.Option(
        None, "--domain-id",
        help="Check suppression at domain scope.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Check if an email address is suppressed before sending. GET /v1/delivery/suppressions.

    Exit code 0 = clear to send.
    Exit code 1 = suppressed — do not send.

    Pipe-friendly — use in scripts before outbound sends:

      commune delivery check user@example.com && commune messages send --to user@example.com ...
    """
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/delivery/suppressions", params={
            "email": email,
            "domainId": domain_id,
            "inboxId": inbox_id,
            "limit": 1,
        })
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    data = r.json()
    items = data if isinstance(data, list) else data.get("data", [])

    # Match by email (case-insensitive)
    match = next(
        (s for s in items if (s.get("email") or "").lower() == email.lower()),
        None,
    )
    suppressed = match is not None

    if json_output or state.should_json():
        print_json({
            "email": email,
            "suppressed": suppressed,
            "reason": match.get("reason") if match else None,
            "suppressedAt": match.get("suppressedAt") if match else None,
        })
        raise typer.Exit(1 if suppressed else 0)

    if suppressed:
        reason = match.get("reason", "unknown")
        suppressed_at = match.get("suppressedAt", "")
        print_warning(
            f"[bold]{email}[/bold] is suppressed  "
            f"reason: {reason}"
            + (f"  since: {suppressed_at}" if suppressed_at else "")
        )
        raise typer.Exit(1)

    print_success(f"[bold]{email}[/bold] is not suppressed — clear to send.")
    raise typer.Exit(0)
