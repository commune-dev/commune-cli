"""commune credits — credit balance and bundle management."""

from __future__ import annotations

import typer

from ..client import CommuneClient
from ..errors import api_error, auth_required_error, network_error
from ..output import print_list, print_record, print_success
from ..state import AppState

app = typer.Typer(help="Credit balance and available bundles.", no_args_is_help=True)


@app.command("balance")
def credits_balance(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Get current credit balance. GET /v1/credits."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/credits")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_record(r.json(), json_output=json_output or state.should_json(), title="Credit Balance")


@app.command("bundles")
def credits_bundles(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """List available credit bundles. GET /v1/credits/bundles."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/credits/bundles")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_list(
        r.json(),
        json_output=json_output or state.should_json(),
        title="Credit Bundles",
        columns=[
            ("ID", "id"),
            ("Credits", "credits"),
            ("Price", "price"),
            ("Description", "description"),
        ],
    )


@app.command("checkout")
def credits_checkout(
    ctx: typer.Context,
    bundle: str = typer.Argument(..., help="Bundle to purchase: starter, growth, or scale."),
    return_url: str = typer.Option(None, "--return-url", help="URL to redirect to after payment (optional)."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Create a Stripe checkout session to purchase credits. POST /v1/credits/checkout."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    payload: dict = {"bundle": bundle}
    if return_url:
        payload["return_url"] = return_url

    client = CommuneClient.from_state(state)
    try:
        r = client.post("/v1/credits/checkout", json=payload)
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    data = r.json()
    if json_output or state.should_json():
        from ..output import print_json
        print_json(data)
        return

    checkout_url = data.get("checkout_url") or data.get("checkoutUrl", "")
    credits = data.get("credits", "")
    price = data.get("price", "")
    print_success(f"Checkout session created for [bold]{bundle}[/bold] bundle ({credits} credits, ${price}).")
    typer.echo(f"\nOpen this URL in your browser to complete payment:\n{checkout_url}")
