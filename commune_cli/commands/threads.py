"""commune threads — thread management and conversation intelligence."""

from __future__ import annotations

import json
import re
import sys
from typing import List, Optional

import typer

from ..client import CommuneClient
from ..errors import api_error, auth_required_error, network_error, validation_error
from ..output import print_json, print_list, print_record, print_status, print_success
from ..state import AppState

app = typer.Typer(help="Thread management: list, read, tag, assign, and explore contacts.", no_args_is_help=True)
tags_app = typer.Typer(help="Manage thread tags.", no_args_is_help=True)
app.add_typer(tags_app, name="tags")


@app.command("list")
def threads_list(
    ctx: typer.Context,
    inbox_id: Optional[str] = typer.Option(None, "--inbox-id", help="Filter by inbox ID."),
    domain_id: Optional[str] = typer.Option(None, "--domain-id", help="Filter by domain ID."),
    limit: Optional[int] = typer.Option(None, "--limit", help="Maximum results to return."),
    cursor: Optional[str] = typer.Option(None, "--cursor", help="Pagination cursor."),
    order: Optional[str] = typer.Option(None, "--order", help="Sort order: asc or desc."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """List email threads. GET /v1/threads."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/threads", params={
            "inbox_id": inbox_id,
            "domain_id": domain_id,
            "limit": limit,
            "cursor": cursor,
            "order": order,
        })
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_list(
        r.json(),
        json_output=json_output or state.should_json(),
        title="Threads",
        columns=[
            ("ID", "id"),
            ("Subject", "subject"),
            ("Status", "status"),
            ("Participants", "participantCount"),
            ("Last Activity", "lastActivityAt"),
        ],
    )


def _get_sender(msg: dict) -> str:
    """Extract sender email from a message's participants list."""
    for p in msg.get("participants", []):
        if p.get("role") == "sender":
            return p.get("identity", "")
    return msg.get("from", "") or msg.get("sender", "")


def _get_recipients(msg: dict) -> str:
    """Extract To recipients as a comma-separated string."""
    to = [p.get("identity", "") for p in msg.get("participants", []) if p.get("role") == "to"]
    return ", ".join(to) or msg.get("to", "")


def _format_markdown(messages: list, thread_id: str, show_extracted: bool = False) -> str:
    """Format thread messages as clean markdown for LLM context injection."""
    lines = [f"# Thread: {thread_id}", ""]
    for msg in messages:
        sender = _get_sender(msg)
        recipients = _get_recipients(msg)
        date = msg.get("createdAt") or msg.get("created_at") or msg.get("date", "")
        direction = msg.get("direction", "")
        body = (
            msg.get("content")
            or msg.get("text")
            or msg.get("body")
            or msg.get("snippet", "")
        )
        lines.append("---")
        lines.append(f"**Direction:** {direction}")
        if sender:
            lines.append(f"**From:** {sender}")
        if recipients:
            lines.append(f"**To:** {recipients}")
        if date:
            lines.append(f"**Date:** {date}")
        lines.append("")
        lines.append(body)
        if show_extracted:
            extracted = (msg.get("metadata") or {}).get("extracted_data") or msg.get("extractedData")
            if extracted:
                lines.append("")
                lines.append("**Extracted fields:**")
                lines.append("```json")
                lines.append(json.dumps(extracted, indent=2))
                lines.append("```")
        lines.append("")
    return "\n".join(lines)


def _format_plain(messages: list, thread_id: str, show_extracted: bool = False) -> str:
    """Format thread messages as plain text."""
    lines = [f"Thread: {thread_id}", "=" * 60, ""]
    for msg in messages:
        sender = _get_sender(msg)
        date = msg.get("createdAt") or msg.get("created_at") or msg.get("date", "")
        direction = msg.get("direction", "")
        body = (
            msg.get("content")
            or msg.get("text")
            or msg.get("body")
            or msg.get("snippet", "")
        )
        if sender:
            lines.append(f"From: {sender}  |  {direction}  |  {date}")
        else:
            lines.append(f"{direction}  |  {date}")
        lines.append("-" * 40)
        lines.append(body)
        if show_extracted:
            extracted = (msg.get("metadata") or {}).get("extracted_data") or msg.get("extractedData")
            if extracted:
                lines.append(f"\nExtracted: {json.dumps(extracted)}")
        lines.append("")
    return "\n".join(lines)


@app.command("messages")
def threads_messages(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID."),
    limit: Optional[int] = typer.Option(None, "--limit", help="Maximum messages to return."),
    order: Optional[str] = typer.Option(None, "--order", help="Sort order: asc (oldest first) or desc."),
    cursor: Optional[str] = typer.Option(None, "--cursor", help="Pagination cursor."),
    format_: str = typer.Option(
        "table",
        "--format",
        help=(
            "Output format: table (default), markdown, plain. "
            "Use 'markdown' or 'plain' to format the full conversation "
            "for piping into an LLM prompt or saving to a file."
        ),
    ),
    extracted: bool = typer.Option(
        False,
        "--extracted",
        help=(
            "Include LLM-extracted structured fields from each message. "
            "Only populated when an extraction schema is configured on the inbox."
        ),
    ),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON."),
) -> None:
    """List messages in a thread. GET /v1/threads/{threadId}/messages.

    Use --format markdown to get a conversation formatted for LLM context:

      commune threads messages <thread_id> --format markdown | llm "draft a reply"

    Use --extracted to include structured data parsed from each message body.
    """
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    valid_formats = ("table", "markdown", "plain")
    if format_ not in valid_formats:
        validation_error(
            f"Invalid format '{format_}'. Must be one of: {', '.join(valid_formats)}.",
            json_output=json_output or state.should_json(),
        )

    client = CommuneClient.from_state(state)
    try:
        r = client.get(f"/v1/threads/{thread_id}/messages", params={
            "limit": limit,
            "order": order,
            "cursor": cursor,
        })
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    data = r.json()
    messages = data if isinstance(data, list) else data.get("data", [])

    if json_output or state.should_json():
        print_json(data)
        return

    if format_ == "markdown":
        sys.stdout.write(_format_markdown(messages, thread_id, show_extracted=extracted))
        sys.stdout.write("\n")
        return

    if format_ == "plain":
        sys.stdout.write(_format_plain(messages, thread_id, show_extracted=extracted))
        sys.stdout.write("\n")
        return

    # Default: rich table
    print_list(
        data,
        json_output=False,
        title=f"Messages in thread {thread_id}",
        columns=[
            ("ID", "id"),
            ("Direction", "direction"),
            ("From", "from"),
            ("Date", "createdAt"),
        ],
    )


@app.command("metadata")
def threads_metadata(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Get thread metadata: status, tags, assignment, participants. GET /v1/threads/{threadId}."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get(f"/v1/threads/{thread_id}")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_record(r.json(), json_output=json_output or state.should_json(), title=f"Thread {thread_id}")


VALID_STATUSES = ("open", "needs_reply", "waiting", "closed")


@app.command("set-status")
def threads_set_status(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID."),
    status: str = typer.Argument(..., help=f"New status. One of: {', '.join(VALID_STATUSES)}."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Set the status of a thread. PATCH /v1/threads/{threadId}.

    Valid statuses: open, needs_reply, waiting, closed.
    """
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    if status not in VALID_STATUSES:
        validation_error(f"Invalid status '{status}'. Must be one of: {', '.join(VALID_STATUSES)}.",
                         json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.patch(f"/v1/threads/{thread_id}", json={"status": status})
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    if json_output or state.should_json():
        print_json(r.json())
        return
    print_success(f"Thread [bold]{thread_id}[/bold] status → [bold]{status}[/bold]")


@app.command("assign")
def threads_assign(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID."),
    to: Optional[str] = typer.Option(None, "--to", help="User email or ID to assign to. Omit to unassign."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Assign a thread to a user or agent. PATCH /v1/threads/{threadId}."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.patch(f"/v1/threads/{thread_id}", json={"assignedTo": to})
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    if json_output or state.should_json():
        print_json(r.json())
        return
    if to:
        print_success(f"Thread [bold]{thread_id}[/bold] assigned to [bold]{to}[/bold].")
    else:
        print_success(f"Thread [bold]{thread_id}[/bold] unassigned.")


@app.command("contacts")
def threads_contacts(
    ctx: typer.Context,
    inbox_id: Optional[str] = typer.Option(
        None, "--inbox-id",
        help="Scope to contacts seen in a specific inbox.",
    ),
    domain_id: Optional[str] = typer.Option(
        None, "--domain-id",
        help="Scope to contacts seen in a specific domain.",
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit",
        help="Maximum number of contacts to return.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """List people extracted from your email conversations. GET /api/graph.

    Returns each unique person seen across your threads: their email, inferred
    role, company, sentiment, and how many threads they appear in.

    Requires business plan. Returns 403 on lower plans.

    Examples:

      commune threads contacts --inbox-id <id>

      commune threads contacts --json | jq '.[] | .email'
    """
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)

    params: dict = {}
    if inbox_id:
        params["inbox_ids"] = inbox_id
    elif domain_id:
        params["domain_id"] = domain_id

    try:
        r = client.get("/api/graph", params=params or None)
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    data = r.json()
    nodes = data.get("nodes", [])
    people = [n for n in nodes if n.get("type") == "person"]

    if limit:
        people = people[:limit]

    if json_output or state.should_json():
        print_json(people)
        return

    print_list(
        people,
        json_output=False,
        title=f"Contacts ({len(people)})",
        columns=[
            ("Email", "email"),
            ("Name", "label"),
            ("Company", "company"),
            ("Role", "role"),
            ("Sentiment", "sentiment"),
            ("Threads", "messageCount"),
            ("Last Active", "lastActive"),
        ],
    )


@app.command("companies")
def threads_companies(
    ctx: typer.Context,
    inbox_id: Optional[str] = typer.Option(
        None, "--inbox-id",
        help="Scope to companies seen in a specific inbox.",
    ),
    domain_id: Optional[str] = typer.Option(
        None, "--domain-id",
        help="Scope to companies seen in a specific domain.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """List companies inferred from your email conversations. GET /api/graph.

    Returns each company extracted from participant email domains and signatures,
    with aggregated thread count, contact count, and deal health signal.

    Requires business plan. Returns 403 on lower plans.

    Examples:

      commune threads companies

      commune threads companies --json | jq '.[] | {label, threadCount, dealHealth}'
    """
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)

    params: dict = {}
    if inbox_id:
        params["inbox_ids"] = inbox_id
    elif domain_id:
        params["domain_id"] = domain_id

    try:
        r = client.get("/api/graph", params=params or None)
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    data = r.json()
    nodes = data.get("nodes", [])
    companies = [n for n in nodes if n.get("type") == "company"]

    if json_output or state.should_json():
        print_json(companies)
        return

    print_list(
        companies,
        json_output=False,
        title=f"Companies ({len(companies)})",
        columns=[
            ("Company", "label"),
            ("Domain", "domain"),
            ("Contacts", "personCount"),
            ("Threads", "threadCount"),
            ("Deal Health", "dealHealth"),
        ],
    )


# ── tags subcommands ───────────────────────────────────────────────────────


@tags_app.command("add")
def tags_add(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID."),
    tags: List[str] = typer.Argument(..., help="Tags to add (space-separated)."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Add tags to a thread. POST /v1/threads/{threadId}/tags."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.post(f"/v1/threads/{thread_id}/tags", json={"tags": tags})
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    if json_output or state.should_json():
        print_json(r.json())
        return
    print_success(f"Tags added to thread [bold]{thread_id}[/bold]: {', '.join(tags)}")


@tags_app.command("remove")
def tags_remove(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID."),
    tags: List[str] = typer.Argument(..., help="Tags to remove (space-separated)."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Remove tags from a thread. POST /v1/threads/{threadId}/tags/remove."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.post(f"/v1/threads/{thread_id}/tags/remove", json={"tags": tags})
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    if json_output or state.should_json():
        print_json(r.json())
        return
    print_success(f"Tags removed from thread [bold]{thread_id}[/bold]: {', '.join(tags)}")
