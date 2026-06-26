"""commune phone-numbers — phone number management."""

from __future__ import annotations

from typing import Optional

import typer

from ..client import CommuneClient
from ..errors import api_error, auth_required_error, network_error
from ..output import print_list, print_record, print_success
from ..state import AppState

app = typer.Typer(help="Phone number management: list, get, provision, release, settings.", no_args_is_help=True)


@app.command("list")
def phone_numbers_list(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """List all phone numbers in your organization. GET /v1/phone-numbers."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/phone-numbers")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_list(
        r.json(),
        json_output=json_output or state.should_json(),
        title="Phone Numbers",
        columns=[
            ("ID", "id"),
            ("Number", "phoneNumber"),
            ("Friendly Name", "friendlyName"),
            ("Status", "status"),
            ("Created", "createdAt"),
        ],
    )


@app.command("get")
def phone_numbers_get(
    ctx: typer.Context,
    phone_number_id: str = typer.Argument(..., help="Phone number ID."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Get a specific phone number. GET /v1/phone-numbers/{phoneNumberId}."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get(f"/v1/phone-numbers/{phone_number_id}")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_record(r.json(), json_output=json_output or state.should_json(), title="Phone Number")


@app.command("available")
def phone_numbers_available(
    ctx: typer.Context,
    type: Optional[str] = typer.Option("TollFree", "--type", help="Number type: TollFree or Local."),
    country: Optional[str] = typer.Option("US", "--country", help="Two-letter country code."),
    limit: Optional[int] = typer.Option(20, "--limit", help="Maximum results to return."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """List available phone numbers to purchase. GET /v1/phone-numbers/available."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/phone-numbers/available", params={
            "type": type,
            "country": country,
            "limit": limit,
        })
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_list(
        r.json(),
        json_output=json_output or state.should_json(),
        title="Available Phone Numbers",
        columns=[
            ("Number", "phoneNumber"),
            ("Friendly Name", "friendlyName"),
            ("Region", "region"),
            ("Locality", "locality"),
        ],
    )


@app.command("provision")
def phone_numbers_provision(
    ctx: typer.Context,
    phone_number: Optional[str] = typer.Option(None, "--phone-number", help="Specific E.164 number to buy (e.g. +18005551234). Auto-selected if omitted."),
    type: Optional[str] = typer.Option("tollfree", "--type", help="Number type: tollfree or local."),
    country: Optional[str] = typer.Option("US", "--country", help="Two-letter country code."),
    friendly_name: Optional[str] = typer.Option(None, "--friendly-name", help="Human-readable label for this number."),
    area_code: Optional[str] = typer.Option(None, "--area-code", help="Preferred area code (local numbers only)."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Purchase/provision a phone number for SMS. POST /v1/phone-numbers."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    payload: dict = {"type": type, "country": country}
    if phone_number:
        payload["phone_number"] = phone_number
    if friendly_name:
        payload["friendly_name"] = friendly_name
    if area_code:
        payload["area_code"] = area_code

    client = CommuneClient.from_state(state)
    try:
        r = client.post("/v1/phone-numbers", json=payload)
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_record(r.json(), json_output=json_output or state.should_json(), title="Provisioned Phone Number")


@app.command("release")
def phone_numbers_release(
    ctx: typer.Context,
    phone_number_id: str = typer.Argument(..., help="Phone number ID to release."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Release a provisioned phone number. DELETE /v1/phone-numbers/{id}."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    if not yes:
        typer.confirm(
            f"Are you sure you want to release phone number {phone_number_id}? This cannot be undone.",
            abort=True,
        )

    client = CommuneClient.from_state(state)
    try:
        r = client.delete(f"/v1/phone-numbers/{phone_number_id}")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    if json_output or state.should_json():
        from ..output import print_json
        print_json(r.json())
        return

    print_success(f"Phone number [bold]{phone_number_id}[/bold] released.")


@app.command("settings")
def phone_numbers_settings(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Get SMS quota settings for your organization. GET /v1/phone-settings."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/phone-settings")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_record(r.json(), json_output=json_output or state.should_json(), title="SMS Settings")


@app.command("update")
def phone_numbers_update(
    ctx: typer.Context,
    phone_number_id: str = typer.Argument(..., help="Phone number ID to update."),
    friendly_name: Optional[str] = typer.Option(None, "--friendly-name", help="Human-readable label for this number."),
    auto_reply: Optional[str] = typer.Option(None, "--auto-reply", help="Auto-reply message body (empty string to disable)."),
    auto_reply_enabled: Optional[bool] = typer.Option(None, "--auto-reply-enabled/--no-auto-reply-enabled", help="Enable or disable auto-reply."),
    webhook_endpoint: Optional[str] = typer.Option(None, "--webhook-endpoint", help="HTTPS URL to receive SMS event webhooks."),
    webhook_secret: Optional[str] = typer.Option(None, "--webhook-secret", help="Webhook signing secret."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Update a phone number's settings. PATCH /v1/phone-numbers/{id}."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    payload: dict = {}
    if friendly_name is not None:
        payload["friendly_name"] = friendly_name
    if auto_reply is not None or auto_reply_enabled is not None:
        auto_reply_obj: dict = {}
        if auto_reply_enabled is not None:
            auto_reply_obj["enabled"] = auto_reply_enabled
        if auto_reply is not None:
            auto_reply_obj["body"] = auto_reply
        payload["auto_reply"] = auto_reply_obj
    if webhook_endpoint is not None:
        webhook: dict = {"endpoint": webhook_endpoint}
        if webhook_secret is not None:
            webhook["secret"] = webhook_secret
        payload["webhook"] = webhook

    if not payload:
        from ..errors import validation_error
        validation_error("No fields to update. Provide at least one option.", json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.patch(f"/v1/phone-numbers/{phone_number_id}", json=payload)
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_record(r.json(), json_output=json_output or state.should_json(), title="Updated Phone Number")


@app.command("set-allow-list")
def phone_numbers_set_allow_list(
    ctx: typer.Context,
    phone_number_id: str = typer.Argument(..., help="Phone number ID."),
    numbers: list[str] = typer.Option(..., "--number", help="E.164 number to allow (repeat for multiple, e.g. --number +15551234567 --number +15559876543). Pass no --number flags to clear."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Set allow list for a phone number (only listed numbers can message it). PUT /v1/phone-numbers/{id}/allow-list."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.put(f"/v1/phone-numbers/{phone_number_id}/allow-list", json={"numbers": numbers})
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_record(r.json(), json_output=json_output or state.should_json(), title="Updated Phone Number")


@app.command("set-block-list")
def phone_numbers_set_block_list(
    ctx: typer.Context,
    phone_number_id: str = typer.Argument(..., help="Phone number ID."),
    numbers: list[str] = typer.Option(..., "--number", help="E.164 number to block (repeat for multiple). Pass no --number flags to clear."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Set block list for a phone number (listed numbers are rejected). PUT /v1/phone-numbers/{id}/block-list."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.put(f"/v1/phone-numbers/{phone_number_id}/block-list", json={"numbers": numbers})
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_record(r.json(), json_output=json_output or state.should_json(), title="Updated Phone Number")
