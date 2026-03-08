"""commune inboxes — inbox management."""

from __future__ import annotations

from typing import Optional

import typer

from ..client import CommuneClient
from ..errors import api_error, auth_required_error, network_error
from ..output import print_list, print_record, print_success, print_json
from ..state import AppState

app = typer.Typer(help="Inbox management.", no_args_is_help=True)
schema_app = typer.Typer(help="Manage inbox extraction schema.", no_args_is_help=True)
app.add_typer(schema_app, name="extraction-schema")


@app.command("list")
def inboxes_list(
    ctx: typer.Context,
    domain_id: Optional[str] = typer.Option(None, "--domain-id", help="Filter by domain ID."),
    limit: Optional[int] = typer.Option(None, "--limit", help="Maximum results to return."),
    cursor: Optional[str] = typer.Option(None, "--cursor", help="Pagination cursor."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """List inboxes in your organization. GET /v1/inboxes."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/inboxes", params={"domain_id": domain_id, "limit": limit, "cursor": cursor})
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_list(
        r.json(),
        json_output=json_output or state.should_json(),
        title="Inboxes",
        columns=[
            ("ID", "id"),
            ("Email", "email"),
            ("Name", "name"),
            ("Domain", "domainId"),
            ("Created", "createdAt"),
        ],
    )


@app.command("get")
def inboxes_get(
    ctx: typer.Context,
    inbox_id: str = typer.Argument(..., help="Inbox ID."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Get a specific inbox. GET /v1/inboxes/{inboxId}."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get(f"/v1/inboxes/{inbox_id}")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_record(r.json(), json_output=json_output or state.should_json(), title="Inbox")


@app.command("create")
def inboxes_create(
    ctx: typer.Context,
    local_part: Optional[str] = typer.Option(None, "--local-part", help="Local part of the email address (before @)."),
    domain_id: Optional[str] = typer.Option(None, "--domain-id", help="Domain ID for the inbox."),
    name: Optional[str] = typer.Option(None, "--name", help="Display name for the inbox."),
    webhook_url: Optional[str] = typer.Option(None, "--webhook-url", help="Webhook URL for inbound emails."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Create a new inbox. POST /v1/inboxes."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    body: dict = {}
    if local_part:
        body["local_part"] = local_part
    if domain_id:
        body["domain_id"] = domain_id
    if name:
        body["name"] = name
    if webhook_url:
        body["webhook"] = {"endpoint": webhook_url, "events": ["inbound"]}

    client = CommuneClient.from_state(state)
    try:
        r = client.post("/v1/inboxes", json=body)
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    data = r.json()
    if not (json_output or state.should_json()):
        email = data.get("email", "")
        print_success(f"Inbox created: [bold]{email}[/bold]")
    print_record(data, json_output=json_output or state.should_json(), title="Inbox Created")


@app.command("update")
def inboxes_update(
    ctx: typer.Context,
    inbox_id: str = typer.Argument(..., help="Inbox ID to update."),
    name: Optional[str] = typer.Option(None, "--name", help="New display name."),
    webhook_url: Optional[str] = typer.Option(None, "--webhook-url", help="New webhook URL."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Update inbox settings. PATCH /v1/inboxes/{inboxId}."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    body: dict = {}
    if name:
        body["name"] = name
    if webhook_url:
        body["webhook"] = {"endpoint": webhook_url, "events": ["inbound"]}

    if not body:
        from ..errors import validation_error
        validation_error("No fields to update — pass --name or --webhook-url.", json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.patch(f"/v1/inboxes/{inbox_id}", json=body)
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_record(r.json(), json_output=json_output or state.should_json(), title="Inbox Updated")


@app.command("delete")
def inboxes_delete(
    ctx: typer.Context,
    inbox_id: str = typer.Argument(..., help="Inbox ID to delete."),
    domain_id: str = typer.Option(..., "--domain-id", help="Domain ID the inbox belongs to."),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Delete an inbox. DELETE /v1/domains/{domainId}/inboxes/{inboxId}."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    if not confirm and state.is_tty():
        typer.confirm(f"Delete inbox {inbox_id}?", abort=True)

    client = CommuneClient.from_state(state)
    try:
        r = client.delete(f"/v1/domains/{domain_id}/inboxes/{inbox_id}")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    if json_output or state.should_json():
        print_json({"deleted": True, "inbox_id": inbox_id})
        return
    print_success(f"Inbox [bold]{inbox_id}[/bold] deleted.")


@app.command("set-webhook")
def inboxes_set_webhook(
    ctx: typer.Context,
    inbox_id: str = typer.Argument(..., help="Inbox ID."),
    domain_id: str = typer.Option(..., "--domain-id", help="Domain ID the inbox belongs to."),
    url: str = typer.Option(..., "--url", help="Webhook URL to set."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Set the webhook URL for an inbox. POST /v1/domains/{domainId}/inboxes/{inboxId}/webhook."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.post(f"/v1/domains/{domain_id}/inboxes/{inbox_id}/webhook", json={"endpoint": url, "events": ["inbound"]})
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    if json_output or state.should_json():
        print_json(r.json())
        return
    print_success(f"Webhook set to [bold]{url}[/bold] for inbox [bold]{inbox_id}[/bold].")


# ── extraction-schema subcommands ──────────────────────────────────────────


@schema_app.command("set")
def schema_set(
    ctx: typer.Context,
    inbox_id: str = typer.Argument(..., help="Inbox ID."),
    domain_id: str = typer.Option(..., "--domain-id", help="Domain ID the inbox belongs to."),
    schema_json: str = typer.Option(..., "--schema", help="JSON schema string for structured extraction."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Set the extraction schema for an inbox.

    POST /v1/domains/{domainId}/inboxes/{inboxId}/schema

    The schema is a JSON object defining the fields to extract from inbound emails.
    """
    import json as _json
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    try:
        schema = _json.loads(schema_json)
    except _json.JSONDecodeError as exc:
        from ..errors import validation_error
        validation_error(f"Invalid JSON schema: {exc}", json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.post(f"/v1/domains/{domain_id}/inboxes/{inbox_id}/schema", json={"schema": schema})
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    if json_output or state.should_json():
        print_json(r.json())
        return
    print_success(f"Extraction schema set for inbox [bold]{inbox_id}[/bold].")


@schema_app.command("remove")
def schema_remove(
    ctx: typer.Context,
    inbox_id: str = typer.Argument(..., help="Inbox ID."),
    domain_id: str = typer.Option(..., "--domain-id", help="Domain ID the inbox belongs to."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Remove the extraction schema from an inbox.

    DELETE /v1/domains/{domainId}/inboxes/{inboxId}/schema
    """
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.delete(f"/v1/domains/{domain_id}/inboxes/{inbox_id}/schema")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    if json_output or state.should_json():
        print_json({"removed": True, "inbox_id": inbox_id})
        return
    print_success(f"Extraction schema removed from inbox [bold]{inbox_id}[/bold].")
