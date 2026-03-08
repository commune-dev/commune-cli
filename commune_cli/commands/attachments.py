"""commune attachments — upload files and get download URLs."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..client import CommuneClient
from ..errors import api_error, auth_required_error, network_error, validation_error
from ..output import print_json, print_record, print_success
from ..state import AppState

app = typer.Typer(help="Attachment management.", no_args_is_help=True)


@app.command("upload")
def attachments_upload(
    ctx: typer.Context,
    file: Path = typer.Argument(..., help="Path to the file to upload.", exists=True, readable=True),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Upload a file as an attachment. POST /v1/attachments/upload.

    Returns an attachment ID that can be referenced when sending emails.
    """
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    file_path = Path(file)
    if not file_path.is_file():
        validation_error(f"File not found: {file}", json_output=json_output or state.should_json())

    import mimetypes
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type:
        mime_type = "application/octet-stream"

    file_data = file_path.read_bytes()

    client = CommuneClient.from_state(state)
    try:
        r = client.post(
            "/v1/attachments/upload",
            data=file_data,
            extra_headers={
                "Content-Type": mime_type,
                "X-Filename": file_path.name,
            },
        )
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    data = r.json()
    if json_output or state.should_json():
        print_json(data)
        return

    att_id = data.get("id") or data.get("attachmentId", "")
    print_success(f"Uploaded [bold]{file_path.name}[/bold]. Attachment ID: [cyan]{att_id}[/cyan]")


@app.command("get")
def attachments_get(
    ctx: typer.Context,
    attachment_id: str = typer.Argument(..., help="Attachment ID."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Get attachment metadata. GET /v1/attachments/{attachmentId}."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get(f"/v1/attachments/{attachment_id}")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_record(r.json(), json_output=json_output or state.should_json(), title="Attachment")


@app.command("url")
def attachments_url(
    ctx: typer.Context,
    attachment_id: str = typer.Argument(..., help="Attachment ID."),
    expires_in: Optional[int] = typer.Option(
        None,
        "--expires-in",
        help="URL expiry in seconds. Default: 3600.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Get a presigned download URL for an attachment. GET /v1/attachments/{attachmentId}/url."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    params: dict = {}
    if expires_in is not None:
        params["expires_in"] = expires_in

    try:
        r = client.get(f"/v1/attachments/{attachment_id}/url", params=params or None)
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    data = r.json()
    if json_output or state.should_json():
        print_json(data)
        return

    url = data.get("url", "")
    from ..output import print_value
    print_value(url, json_output=False, key="url")
