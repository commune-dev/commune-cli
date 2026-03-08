"""commune dmarc — DMARC reporting."""

from __future__ import annotations

from typing import Optional

import typer

from ..client import CommuneClient
from ..errors import api_error, auth_required_error, network_error, validation_error
from ..output import print_list, print_record
from ..state import AppState

app = typer.Typer(help="DMARC reports and summary.", no_args_is_help=True)


@app.command("reports")
def dmarc_reports(
    ctx: typer.Context,
    domain: str = typer.Argument(..., help="Domain name to get DMARC reports for (e.g. example.com)."),
    limit: Optional[int] = typer.Option(None, "--limit", help="Maximum reports to return."),
    cursor: Optional[str] = typer.Option(None, "--cursor", help="Pagination cursor."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """List DMARC aggregate reports for a domain. GET /v1/dmarc/reports."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/dmarc/reports", params={
            "domain": domain,
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
        title=f"DMARC Reports: {domain}",
        columns=[
            ("ID", "id"),
            ("Reporter", "reporterOrg"),
            ("Start", "dateRangeBegin"),
            ("End", "dateRangeEnd"),
            ("Records", "recordCount"),
        ],
    )


@app.command("summary")
def dmarc_summary(
    ctx: typer.Context,
    domain: str = typer.Argument(..., help="Domain name to summarize (e.g. example.com)."),
    days: Optional[int] = typer.Option(None, "--days", help="Number of days to include (default: 30)."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Get a DMARC compliance summary for a domain. GET /v1/dmarc/summary."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/dmarc/summary", params={
            "domain": domain,
            "days": days,
        })
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_record(r.json(), json_output=json_output or state.should_json(), title=f"DMARC Summary: {domain}")
