"""commune domains — domain management."""

from __future__ import annotations

from typing import Optional

import typer

from ..client import CommuneClient
from ..errors import api_error, auth_required_error, network_error
from ..output import print_list, print_record, print_success
from ..state import AppState

app = typer.Typer(help="Domain management.", no_args_is_help=True)


@app.command("list")
def domains_list(
    ctx: typer.Context,
    limit: Optional[int] = typer.Option(None, "--limit", help="Maximum number of domains to return."),
    cursor: Optional[str] = typer.Option(None, "--cursor", help="Pagination cursor from a previous response."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """List all domains in your organization. GET /v1/domains."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/domains", params={"limit": limit, "cursor": cursor})
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_list(
        r.json(),
        json_output=json_output or state.should_json(),
        title="Domains",
        columns=[
            ("ID", "id"),
            ("Domain", "domain"),
            ("Status", "status"),
            ("Created", "createdAt"),
        ],
    )


@app.command("get")
def domains_get(
    ctx: typer.Context,
    domain_id: str = typer.Argument(..., help="Domain ID."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Get a specific domain. GET /v1/domains/{domainId}."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get(f"/v1/domains/{domain_id}")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_record(r.json(), json_output=json_output or state.should_json(), title="Domain")


@app.command("create")
def domains_create(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Domain name (e.g. mail.example.com)."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Add a domain to your organization. POST /v1/domains."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.post("/v1/domains", json={"domain": name})
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    data = r.json()
    if not (json_output or state.should_json()):
        print_success(f"Domain [bold]{name}[/bold] created.")
    print_record(data, json_output=json_output or state.should_json(), title="Domain Created")


@app.command("verify")
def domains_verify(
    ctx: typer.Context,
    domain_id: str = typer.Argument(..., help="Domain ID to trigger DNS verification for."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Trigger DNS verification for a domain. POST /v1/domains/{domainId}/verify."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.post(f"/v1/domains/{domain_id}/verify")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    data = r.json()
    if not (json_output or state.should_json()):
        status = data.get("status", "unknown")
        print_success(f"Verification triggered. Status: [bold]{status}[/bold]")
    print_record(data, json_output=json_output or state.should_json(), title="Domain Verification")


@app.command("records")
def domains_records(
    ctx: typer.Context,
    domain_id: str = typer.Argument(..., help="Domain ID."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Get the required DNS records for a domain. GET /v1/domains/{domainId}/records."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get(f"/v1/domains/{domain_id}/records")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    data = r.json()
    print_list(
        data,
        json_output=json_output or state.should_json(),
        title="DNS Records",
        columns=[
            ("Type", "type"),
            ("Name", "name"),
            ("Value", "value"),
            ("Status", "status"),
        ],
    )
