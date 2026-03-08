"""commune webhooks — webhook delivery log management."""

from __future__ import annotations

from typing import Optional

import typer

from ..client import CommuneClient
from ..errors import api_error, auth_required_error, network_error
from ..output import print_json, print_list, print_record, print_success
from ..state import AppState

app = typer.Typer(help="Webhook delivery log and health.", no_args_is_help=True)


@app.command("list")
def webhooks_list(
    ctx: typer.Context,
    inbox_id: Optional[str] = typer.Option(None, "--inbox-id", help="Filter by inbox ID."),
    status: Optional[str] = typer.Option(None, "--status", help="Filter by delivery status: pending, success, failed."),
    endpoint: Optional[str] = typer.Option(None, "--endpoint", help="Filter by endpoint URL."),
    limit: Optional[int] = typer.Option(None, "--limit", help="Maximum results."),
    cursor: Optional[str] = typer.Option(None, "--cursor", help="Pagination cursor."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """List webhook delivery attempts. GET /v1/webhooks/deliveries."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/webhooks/deliveries", params={
            "inbox_id": inbox_id,
            "status": status,
            "endpoint": endpoint,
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
        title="Webhook Deliveries",
        columns=[
            ("ID", "id"),
            ("Status", "status"),
            ("Endpoint", "endpoint"),
            ("HTTP Status", "httpStatus"),
            ("Attempts", "attemptCount"),
            ("Created", "createdAt"),
        ],
    )


@app.command("get")
def webhooks_get(
    ctx: typer.Context,
    delivery_id: str = typer.Argument(..., help="Webhook delivery ID."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Get a specific webhook delivery attempt. GET /v1/webhooks/deliveries/{deliveryId}."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get(f"/v1/webhooks/deliveries/{delivery_id}")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_record(r.json(), json_output=json_output or state.should_json(), title=f"Webhook Delivery {delivery_id}")


@app.command("retry")
def webhooks_retry(
    ctx: typer.Context,
    delivery_id: str = typer.Argument(..., help="Webhook delivery ID to retry."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Retry a failed webhook delivery. POST /v1/webhooks/deliveries/{deliveryId}/retry."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.post(f"/v1/webhooks/deliveries/{delivery_id}/retry")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    if json_output or state.should_json():
        print_json(r.json())
        return
    print_success(f"Webhook delivery [bold]{delivery_id}[/bold] queued for retry.")


@app.command("health")
def webhooks_health(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Get overall webhook delivery health stats. GET /v1/webhooks/health."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/webhooks/health")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_record(r.json(), json_output=json_output or state.should_json(), title="Webhook Health")
