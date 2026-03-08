"""commune data — data deletion requests (GDPR / destructive).

These commands are destructive and irreversible. They require explicit confirmation.
"""

from __future__ import annotations

from typing import Optional

import typer

from ..client import CommuneClient
from ..errors import api_error, auth_required_error, network_error
from ..output import print_json, print_record, print_success, print_warning, print_status
from ..state import AppState

app = typer.Typer(
    help="Data deletion requests. Destructive — use with care.",
    no_args_is_help=True,
)


@app.command("delete-request")
def data_delete_request(
    ctx: typer.Context,
    email: Optional[str] = typer.Option(None, "--email", help="Email address to delete data for."),
    inbox_id: Optional[str] = typer.Option(None, "--inbox-id", help="Inbox ID scope for deletion."),
    domain_id: Optional[str] = typer.Option(None, "--domain-id", help="Domain ID scope for deletion."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Initiate a data deletion request. POST /v1/data/deletion-request.

    Returns a preview of what will be deleted and a confirmation token.
    Use `commune data delete-confirm <id>` to execute.
    """
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    body: dict = {}
    if email:
        body["email"] = email
    if inbox_id:
        body["inboxId"] = inbox_id
    if domain_id:
        body["domainId"] = domain_id

    client = CommuneClient.from_state(state)
    try:
        r = client.post("/v1/data/deletion-request", json=body)
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    data = r.json()
    if json_output or state.should_json():
        print_json(data)
        return

    req_id = data.get("id", "")
    print_warning(f"Deletion request created. ID: [bold]{req_id}[/bold]")
    print_status("Review the preview above, then confirm with:")
    print_status(f"  commune data delete-confirm {req_id}")


@app.command("delete-confirm")
def data_delete_confirm(
    ctx: typer.Context,
    request_id: str = typer.Argument(..., help="Deletion request ID from `commune data delete-request`."),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt. REQUIRED for non-interactive use."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Confirm and execute a data deletion request. POST /v1/data/deletion-request/{id}/confirm.

    This action is IRREVERSIBLE. Data is permanently deleted.
    """
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    if not confirm:
        if state.is_tty():
            print_warning("[bold red]WARNING:[/bold red] This action permanently deletes data and cannot be undone.")
            typer.confirm(f"Confirm deletion of request {request_id}?", abort=True)
        else:
            # Non-TTY without --yes flag: require explicit confirmation
            from ..errors import validation_error
            validation_error(
                "Deletion requires --yes flag in non-interactive mode.",
                json_output=json_output or state.should_json(),
            )

    client = CommuneClient.from_state(state)
    try:
        r = client.post(f"/v1/data/deletion-request/{request_id}/confirm")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    if json_output or state.should_json():
        print_json(r.json())
        return
    print_success(f"Deletion confirmed. Request [bold]{request_id}[/bold] is processing.")


@app.command("delete-status")
def data_delete_status(
    ctx: typer.Context,
    request_id: str = typer.Argument(..., help="Deletion request ID."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Get the status of a data deletion request. GET /v1/data/deletion-request/{id}."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get(f"/v1/data/deletion-request/{request_id}")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_record(r.json(), json_output=json_output or state.should_json(), title=f"Deletion Request {request_id}")
