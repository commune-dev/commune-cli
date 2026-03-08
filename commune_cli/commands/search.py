"""commune search — full-text search across threads."""

from __future__ import annotations

from typing import Optional

import typer

from ..client import CommuneClient
from ..errors import api_error, auth_required_error, network_error
from ..output import print_list
from ..state import AppState

app = typer.Typer(help="Search threads.", no_args_is_help=True)


@app.command("threads")
def search_threads(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Full-text search query."),
    inbox_id: Optional[str] = typer.Option(None, "--inbox-id", help="Restrict search to this inbox."),
    domain_id: Optional[str] = typer.Option(None, "--domain-id", help="Restrict search to this domain."),
    limit: Optional[int] = typer.Option(None, "--limit", help="Maximum results to return."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Search threads by full-text query. GET /v1/search/threads."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/search/threads", params={
            "q": query,
            "inbox_id": inbox_id,
            "domain_id": domain_id,
            "limit": limit,
        })
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_list(
        r.json(),
        json_output=json_output or state.should_json(),
        title=f"Search: {query}",
        columns=[
            ("ID", "id"),
            ("Subject", "subject"),
            ("Status", "status"),
            ("Score", "score"),
            ("Last Activity", "lastActivityAt"),
        ],
    )
