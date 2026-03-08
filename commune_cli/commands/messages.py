"""commune messages — send and list emails."""

from __future__ import annotations

import sys
from typing import List, Optional

import typer

from ..client import CommuneClient
from ..errors import api_error, auth_required_error, network_error, validation_error
from ..output import print_json, print_list, print_record, print_success
from ..state import AppState

app = typer.Typer(help="Send and list emails.", no_args_is_help=True)


@app.command("send")
def messages_send(
    ctx: typer.Context,
    to: List[str] = typer.Option(..., "--to", help="Recipient email address (repeatable for multiple)."),
    subject: str = typer.Option(..., "--subject", help="Email subject line."),
    text: Optional[str] = typer.Option(
        None,
        "--text",
        help="Plain-text body. Use '-' to read from stdin.",
    ),
    html: Optional[str] = typer.Option(None, "--html", help="HTML body."),
    from_address: Optional[str] = typer.Option(
        None,
        "--from",
        help="Sender address. Must be an address in your org. Defaults to org default.",
    ),
    inbox_id: Optional[str] = typer.Option(None, "--inbox-id", help="Inbox ID to send from."),
    domain_id: Optional[str] = typer.Option(None, "--domain-id", help="Domain ID to send from."),
    cc: Optional[List[str]] = typer.Option(None, "--cc", help="CC address (repeatable)."),
    bcc: Optional[List[str]] = typer.Option(None, "--bcc", help="BCC address (repeatable)."),
    reply_to: Optional[str] = typer.Option(None, "--reply-to", help="Reply-To address."),
    thread_id: Optional[str] = typer.Option(
        None, "--thread-id",
        help=(
            "Reply into an existing thread. Pass the thread ID and the email will be "
            "threaded correctly — no need to repeat --to or --subject."
        ),
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Send an email. POST /v1/messages/send.

    To reply to an existing thread, pass --thread-id:

      commune messages send --thread-id <thread_id> --text "Got it, sending the contract now."

    Pipe body from stdin with --text -:

      echo "Hello" | commune messages send --to user@example.com --subject Hi --text -
    """
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    if not text and not html:
        validation_error("At least one of --text or --html is required.", json_output=json_output or state.should_json())

    # Stdin support
    if text == "-":
        text = sys.stdin.read()

    body: dict = {"to": to, "subject": subject}
    if text:
        body["text"] = text
    if html:
        body["html"] = html
    if from_address:
        body["from"] = from_address
    if inbox_id:
        body["inbox_id"] = inbox_id
    if domain_id:
        body["domain_id"] = domain_id
    if cc:
        body["cc"] = cc
    if bcc:
        body["bcc"] = bcc
    if reply_to:
        body["reply_to"] = reply_to
    if thread_id:
        body["thread_id"] = thread_id

    client = CommuneClient.from_state(state)
    try:
        r = client.post("/v1/messages/send", json=body)
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    data = r.json()
    if json_output or state.should_json():
        print_json(data)
        return

    msg_id = data.get("messageId") or data.get("id", "")
    print_success(f"Message sent. ID: [bold]{msg_id}[/bold]")


@app.command("list")
def messages_list(
    ctx: typer.Context,
    inbox_id: Optional[str] = typer.Option(None, "--inbox-id", help="Filter by inbox ID."),
    domain_id: Optional[str] = typer.Option(None, "--domain-id", help="Filter by domain ID."),
    sender: Optional[str] = typer.Option(None, "--sender", help="Filter by sender email address."),
    limit: Optional[int] = typer.Option(None, "--limit", help="Maximum results to return."),
    order: Optional[str] = typer.Option(None, "--order", help="Sort order: asc or desc."),
    before: Optional[str] = typer.Option(None, "--before", help="Return messages before this timestamp (ISO 8601)."),
    after: Optional[str] = typer.Option(None, "--after", help="Return messages after this timestamp (ISO 8601)."),
    cursor: Optional[str] = typer.Option(None, "--cursor", help="Pagination cursor."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """List messages. GET /v1/messages."""
    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/messages", params={
            "inbox_id": inbox_id,
            "domain_id": domain_id,
            "sender": sender,
            "limit": limit,
            "order": order,
            "before": before,
            "after": after,
            "cursor": cursor,
        })
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    print_list(
        r.json(),
        json_output=json_output or state.should_json(),
        title="Messages",
        columns=[
            ("ID", "id"),
            ("From", "from"),
            ("Subject", "subject"),
            ("Date", "date"),
            ("Thread", "threadId"),
        ],
    )
