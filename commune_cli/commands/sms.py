"""commune sms — send SMS and manage conversations."""

from __future__ import annotations

from typing import Optional
from urllib.parse import quote

import typer

from ..client import CommuneClient
from ..errors import api_error, auth_required_error, network_error, validation_error
from ..output import print_json, print_list, print_record, print_success
from ..state import AppState

app = typer.Typer(help="Send SMS and manage conversations.", no_args_is_help=True)


@app.command("send")
def sms_send(
    ctx: typer.Context,
    to: str = typer.Option(..., "--to", help="Recipient phone number in E.164 format (e.g. +1234567890)."),
    body: str = typer.Option(..., "--body", help="SMS message body."),
    phone_number_id: Optional[str] = typer.Option(
        None,
        "--phone-number-id",
        help="Phone number ID to send from. Uses org default if omitted.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Send an SMS message. POST /v1/sms/send."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    payload: dict = {"to": to, "body": body}
    if phone_number_id:
        payload["phone_number_id"] = phone_number_id

    client = CommuneClient.from_state(state)
    try:
        r = client.post("/v1/sms/send", json=payload)
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    data = r.json()
    if json_output or state.should_json():
        print_json(data)
        return

    msg_id = (data.get("data") or {}).get("message_id", "")
    print_success(f"SMS sent. ID: [bold]{msg_id}[/bold]")


@app.command("conversations")
def sms_conversations(
    ctx: typer.Context,
    phone_number_id: Optional[str] = typer.Option(
        None,
        "--phone-number-id",
        help="Filter by phone number ID.",
    ),
    limit: Optional[int] = typer.Option(20, "--limit", help="Maximum results to return."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """List SMS conversations. GET /v1/sms/conversations."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/sms/conversations", params={
            "phone_number_id": phone_number_id,
            "limit": limit,
        })
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_list(
        r.json(),
        json_output=json_output or state.should_json(),
        title="SMS Conversations",
        columns=[
            ("Remote Number", "remote_number"),
            ("Last Message", "last_message_preview"),
            ("Messages", "message_count"),
            ("Updated", "last_message_at"),
        ],
    )


@app.command("thread")
def sms_thread(
    ctx: typer.Context,
    remote_number: str = typer.Argument(..., help="Remote phone number (E.164, e.g. +1234567890)."),
    phone_number_id: str = typer.Option(
        ...,
        "--phone-number-id",
        help="Phone number ID for the conversation.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Get the message thread with a specific number. GET /v1/sms/conversations/{remoteNumber}."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    encoded = quote(remote_number, safe="")
    client = CommuneClient.from_state(state)
    try:
        r = client.get(
            f"/v1/sms/conversations/{encoded}",
            params={"phone_number_id": phone_number_id},
        )
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    data = r.json()
    if json_output or state.should_json():
        print_json(data)
        return

    messages = data if isinstance(data, list) else data.get("data", data)
    print_list(
        messages,
        json_output=False,
        title=f"Thread with {remote_number}",
        columns=[
            ("ID", "message_id"),
            ("Direction", "direction"),
            ("Body", "content"),
            ("Sent At", "created_at"),
        ],
    )


@app.command("search")
def sms_search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search query."),
    phone_number_id: Optional[str] = typer.Option(
        None,
        "--phone-number-id",
        help="Scope search to a specific phone number.",
    ),
    limit: Optional[int] = typer.Option(20, "--limit", help="Maximum results to return."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Search SMS messages. GET /v1/sms/search."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/sms/search", params={
            "q": query,
            "phone_number_id": phone_number_id,
            "limit": limit,
        })
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_list(
        r.json(),
        json_output=json_output or state.should_json(),
        title=f"SMS Search: {query}",
        columns=[
            ("ID", "message_id"),
            ("Direction", "direction"),
            ("Body", "content"),
            ("Date", "created_at"),
        ],
    )


@app.command("suppressions")
def sms_suppressions(
    ctx: typer.Context,
    phone_number_id: Optional[str] = typer.Option(
        None,
        "--phone-number-id",
        help="Filter by phone number ID.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """List SMS suppressed numbers (opted out via STOP). GET /v1/sms/suppressions."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/sms/suppressions", params={"phone_number_id": phone_number_id})
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_list(
        r.json(),
        json_output=json_output or state.should_json(),
        title="SMS Suppressions",
        columns=[
            ("Phone Number", "phone_number"),
            ("Reason", "reason"),
            ("Created", "created_at"),
        ],
    )


@app.command("remove-suppression")
def sms_remove_suppression(
    ctx: typer.Context,
    phone_number: str = typer.Argument(..., help="E.164 phone number to remove from suppression list (e.g. +15551234567)."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Remove a number from the SMS suppression list. DELETE /v1/sms/suppressions/{phoneNumber}."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    from urllib.parse import quote
    encoded = quote(phone_number, safe="")
    client = CommuneClient.from_state(state)
    try:
        r = client.delete(f"/v1/sms/suppressions/{encoded}")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    if json_output or state.should_json():
        from ..output import print_json
        print_json(r.json())
        return

    print_success(f"[bold]{phone_number}[/bold] removed from suppression list.")


def _format_sms_timestamp(ts_raw: str) -> str:
    """Parse an ISO 8601 timestamp and return HH:MM:SS. Falls back gracefully."""
    if not ts_raw:
        import time
        return time.strftime("%H:%M:%S")
    try:
        from datetime import datetime, timezone
        normalized = ts_raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        # Convert to local time for display
        local_dt = dt.astimezone()
        return local_dt.strftime("%H:%M:%S")
    except (ValueError, AttributeError):
        # Substring fallback for ISO strings that fromisoformat can't handle
        if "T" in ts_raw and len(ts_raw) >= 19:
            return ts_raw[11:19]
        import time
        return time.strftime("%H:%M:%S")


@app.command("listen")
def sms_listen(
    ctx: typer.Context,
    phone_number_id: Optional[str] = typer.Option(
        None,
        "--phone-number-id",
        help="Listen for events on a specific phone number. Omit to listen on all.",
    ),
    events: Optional[str] = typer.Option(
        None,
        "--events",
        help="Comma-separated event types to filter: sms.received,sms.sent,sms.status_updated (default: all SMS events).",
    ),
) -> None:
    """Stream SMS events in real time (like az logs). Ctrl+C to stop."""
    import time
    import json as _json
    import httpx
    from urllib.parse import urlencode
    from rich.console import Console

    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=False)

    console = Console()

    base_url = state.base_url or "https://api.commune.email"
    api_key = state.api_key or state.session_token or ""

    params: list[tuple[str, str]] = []
    if phone_number_id:
        params.append(("phone_number_id", phone_number_id))
    if events:
        params.append(("events", events))
    else:
        params.append(("events", "sms.received,sms.sent,sms.status_updated"))

    qs = urlencode(params)
    url = f"{base_url.rstrip('/')}/v1/events/stream?{qs}"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "text/event-stream"}

    label = f"phone number [bold]{phone_number_id}[/bold]" if phone_number_id else "all phone numbers"

    # Reconnection config: exponential backoff, max 5 attempts
    MAX_ATTEMPTS = 5
    BACKOFF_BASE = 1       # seconds; doubles each retry: 1 → 2 → 4 → 8 → 16
    HEARTBEAT_TIMEOUT = 35 # seconds; matches server heartbeat interval (30s) + 5s buffer

    attempt = 0

    while attempt <= MAX_ATTEMPTS:
        if attempt == 0:
            console.print(f"\n[dim]Listening for SMS events on {label}... (Ctrl+C to stop)[/dim]\n")
        else:
            wait = BACKOFF_BASE * (2 ** (attempt - 1))
            console.print(f"\n[yellow]Connection lost. Reconnecting in {wait}s (attempt {attempt}/{MAX_ATTEMPTS})...[/yellow]")
            time.sleep(wait)
            console.print(f"[dim]Reconnecting to event stream...[/dim]\n")

        try:
            # read timeout triggers if no bytes (including heartbeats) arrive within HEARTBEAT_TIMEOUT seconds
            timeout = httpx.Timeout(connect=10.0, read=HEARTBEAT_TIMEOUT, write=10.0, pool=None)
            with httpx.Client(timeout=timeout) as client:
                with client.stream("GET", url, headers=headers) as response:
                    if response.status_code != 200:
                        console.print(f"[red]Error {response.status_code}:[/red] {response.text}")
                        # Auth errors are fatal — no point retrying
                        if response.status_code in (401, 403):
                            raise SystemExit(1)
                        attempt += 1
                        continue

                    # Successful connection — reset backoff counter
                    attempt = 0
                    if not phone_number_id:
                        console.print(f"[green]Connected.[/green] Listening for events... (Ctrl+C to stop)\n")

                    event_type = None
                    for line in response.iter_lines():
                        if line.startswith("event:"):
                            event_type = line[6:].strip()
                        elif line.startswith("data:"):
                            raw = line[5:].strip()
                            if raw in ("[DONE]", ""):
                                continue
                            try:
                                data = _json.loads(raw)
                            except Exception:
                                continue

                            ts = _format_sms_timestamp(data.get("created_at", ""))
                            ev = event_type or data.get("type", "event")
                            from_num = data.get("from_number", data.get("from", ""))
                            to_num = data.get("to_number", data.get("to", ""))
                            body_text = data.get("content", data.get("body", ""))
                            status = data.get("delivery_status", "")

                            color = "green" if ev == "sms.received" else "blue" if ev == "sms.sent" else "yellow"
                            direction = f"[dim]{from_num}[/dim] → [dim]{to_num}[/dim]" if from_num and to_num else ""
                            status_str = f" · [dim]{status}[/dim]" if status else ""

                            console.print(
                                f"[[dim]{ts}[/dim]] [{color}]{ev:<20}[/{color}] {direction}{status_str}"
                            )
                            if body_text:
                                preview = body_text[:100] + ("…" if len(body_text) > 100 else "")
                                console.print(f"           [dim]\"{preview}\"[/dim]")
                        elif line == "":
                            event_type = None

                    # iter_lines() exhausted without exception — server closed the connection cleanly
                    # (e.g. graceful server restart). Treat as a disconnect and reconnect.
                    console.print(f"\n[yellow]Stream closed by server.[/yellow]")
                    attempt += 1
                    continue

        except KeyboardInterrupt:
            console.print("\n[dim]Stopped.[/dim]")
            return
        except httpx.ReadTimeout:
            console.print(f"\n[yellow]No data received for {HEARTBEAT_TIMEOUT}s — reconnecting...[/yellow]")
            attempt += 1
            continue
        except httpx.ConnectError as exc:
            console.print(f"\n[yellow]Connection failed: {exc}[/yellow]")
            attempt += 1
            continue
        except SystemExit:
            raise
        except Exception as exc:
            console.print(f"[red]Unexpected error:[/red] {exc}")
            attempt += 1
            continue

    console.print(f"[red]Failed to connect after {MAX_ATTEMPTS} attempts. Check your network and API key.[/red]")
    raise SystemExit(1)
