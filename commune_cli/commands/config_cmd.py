"""commune config — manage CLI configuration and agent identity."""

from __future__ import annotations

import base64
import os
import re
import stat
from pathlib import Path
from typing import Optional

import typer

from ..config import KNOWN_KEYS, config_path, delete_value, get_value, load_config, mask, set_value
from ..output import print_json, print_kv, print_status, print_success, print_warning

app = typer.Typer(help="Manage CLI configuration and API keys.", no_args_is_help=True)

keys_app = typer.Typer(help="Manage API keys for your org.", no_args_is_help=True)
app.add_typer(keys_app, name="keys")


# ── config set / get / show / unset / path ─────────────────────────────────


@app.command("set")
def config_set(
    key: str = typer.Argument(..., help=f"Config key. Known keys: {', '.join(KNOWN_KEYS)}."),
    value: str = typer.Argument(..., help="Value to store."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Set a config key and persist to ~/.commune/config.toml."""
    if key not in KNOWN_KEYS:
        known = ", ".join(KNOWN_KEYS)
        print_warning(f"Unknown key '{key}'. Known keys: {known}")
    set_value(key, value)
    display = mask(value) if key == "api_key" else value
    print_success(f"Set {key} = {display}  ({config_path()})")
    if json_output:
        print_json({"key": key, "set": True})


@app.command("get")
def config_get(
    key: str = typer.Argument(..., help="Config key to retrieve."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Get a single config value."""
    value = get_value(key)
    if value is None:
        print_warning(f"Key '{key}' is not set in config.")
        raise typer.Exit(1)
    display = mask(value) if key == "api_key" else value
    from ..output import print_value
    print_value(display, json_output=json_output, key=key)


@app.command("show")
def config_show(
    reveal: bool = typer.Option(False, "--reveal", help="Show full api_key without masking."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Print all config values. Masks api_key unless --reveal is passed."""
    cfg = load_config()
    if not cfg:
        print_warning(f"No config file found at {config_path()}")
        raise typer.Exit(0)

    pairs: dict[str, str] = {}
    for k, v in cfg.items():
        if k == "api_key" and not reveal:
            pairs[k] = mask(v)
        else:
            pairs[k] = str(v)

    print_kv(pairs, json_output=json_output, title=f"Config  {config_path()}")


@app.command("unset")
def config_unset(
    key: str = typer.Argument(..., help="Config key to remove."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Remove a key from config."""
    removed = delete_value(key)
    if removed:
        print_success(f"Removed '{key}' from config.")
    else:
        print_warning(f"Key '{key}' was not set.")
    if json_output:
        print_json({"key": key, "removed": removed})


@app.command("path")
def config_path_cmd() -> None:
    """Print the path to the config file."""
    import sys
    sys.stdout.write(str(config_path()) + "\n")


# ── config register ─────────────────────────────────────────────────────────


@app.command("register")
def config_register(
    name: str = typer.Option(..., "--name", help="Agent display name (e.g. 'outbound-sdr')."),
    purpose: str = typer.Option(
        ..., "--purpose",
        help=(
            "What this agent does — 1–3 sentences, 20–2000 chars, at least 3 words. "
            "Example: 'send cold emails to SaaS founders and book sales calls'"
        ),
    ),
    org_name: str = typer.Option(..., "--org-name", help="Organization name (e.g. 'Acme AI')."),
    org_slug: str = typer.Option(
        ..., "--org-slug",
        help=(
            "Unique org slug — becomes your inbox address: slug@commune.email. "
            "Letters, numbers, hyphens, and underscores only."
        ),
    ),
    base_url_override: Optional[str] = typer.Option(
        None, "--base-url",
        envvar="COMMUNE_BASE_URL",
        help="API base URL. Default: https://api.commune.email",
        show_default=False,
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Self-register as an agent using Ed25519 keypair. No dashboard required.

    Generates a local Ed25519 keypair, completes the contextual challenge,
    provisions your inbox at slug@commune.email, creates an API key, and
    saves everything to ~/.commune/config.toml automatically.

    Example:

      commune config register \\
        --name "outbound-sdr" \\
        --purpose "send cold emails to SaaS founders and book sales calls" \\
        --org-name "Acme AI" \\
        --org-slug "acme-ai"
    """
    import httpx
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding, NoEncryption, PrivateFormat, PublicFormat,
    )
    from ..config import config_dir
    from ..errors import EXIT_ERROR, emit_error

    base_url = (base_url_override or "https://api.commune.email").rstrip("/")

    # 1. Generate Ed25519 keypair (raw 32-byte keys)
    private_key = Ed25519PrivateKey.generate()
    pub_raw = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    priv_raw = private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    pub_b64 = base64.b64encode(pub_raw).decode()    # 44 chars, standard base64 + padding
    priv_b64 = base64.b64encode(priv_raw).decode()

    if not json_output:
        print_status("[cyan]→[/cyan] Registering agent...")

    # 2. POST /v1/auth/agent-register
    try:
        r = httpx.post(
            f"{base_url}/v1/auth/agent-register",
            json={
                "agentName": name,
                "agentPurpose": purpose,
                "orgName": org_name,
                "orgSlug": org_slug,
                "publicKey": pub_b64,
            },
            timeout=30.0,
        )
    except Exception as exc:
        emit_error(str(exc), code="network_error", json_output=json_output)
        raise typer.Exit(5)

    if not r.is_success:
        from ..errors import api_error
        from ..client import CommuneClient
        # Re-use api_error via a minimal fake response wrapper
        api_error(r, json_output=json_output)

    reg_data = r.json()
    signup_token: str = reg_data["agentSignupToken"]
    challenge_text: str = reg_data["challenge"]["text"]

    # 3. Parse epoch marker from challenge text
    m = re.search(r"Include this exact string: ([0-9a-f]{16})", challenge_text)
    if not m:
        emit_error(
            "Could not parse epoch marker from challenge. Please contact support.",
            json_output=json_output,
        )
        raise typer.Exit(EXIT_ERROR)
    epoch_marker = m.group(1)

    # 4. Compute word count: words in purpose with 5+ alphabetical chars (matches backend exactly)
    word_count = sum(
        1 for w in purpose.strip().split()
        if len(re.sub(r"[^a-zA-Z]", "", w)) >= 5
    )

    # 5. Extract primary verb: first all-alpha word from purpose, lowercased
    verb = "process"
    for w in purpose.strip().split():
        alpha = re.sub(r"[^a-zA-Z]", "", w)
        if len(alpha) >= 2:
            verb = alpha.lower()
            break

    # 6. Construct and sign challengeResponse: "verb:wordCount:epochMarker"
    challenge_response = f"{verb}:{word_count}:{epoch_marker}"
    sig_bytes = private_key.sign(challenge_response.encode())
    sig_b64 = base64.b64encode(sig_bytes).decode()

    if not json_output:
        print_status("[cyan]→[/cyan] Completing challenge...")

    # 7. POST /v1/auth/agent-verify
    try:
        r2 = httpx.post(
            f"{base_url}/v1/auth/agent-verify",
            json={
                "agentSignupToken": signup_token,
                "challengeResponse": challenge_response,
                "signature": sig_b64,
            },
            timeout=30.0,
        )
    except Exception as exc:
        emit_error(str(exc), code="network_error", json_output=json_output)
        raise typer.Exit(5)

    if not r2.is_success:
        from ..errors import api_error
        api_error(r2, json_output=json_output)

    verify_data = r2.json()
    agent_id: str = verify_data["agentId"]
    inbox_email: str = verify_data["inboxEmail"]

    # Save private key + agent ID to ~/.commune/agent.key (owner-only permissions)
    agent_key_path = config_dir() / "agent.key"
    agent_key_path.write_text(
        f"agent_id={agent_id}\nprivate_key={priv_b64}\n",
        encoding="utf-8",
    )
    try:
        os.chmod(agent_key_path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass

    # Output
    if json_output:
        print_json({
            "agentId": agent_id,
            "inboxEmail": inbox_email,
            "keyFile": str(agent_key_path),
        })
        return

    print_success(f"Agent registered:  [bold]{agent_id}[/bold]")
    print_success(f"Inbox ready:       [bold]{inbox_email}[/bold]")
    print_warning(
        "Get your API key at commune.email/dashboard, then run:\n"
        "  commune config set api_key comm_..."
    )
    from rich.console import Console
    Console(stderr=True).print(f"\n[dim]Private key stored at: {agent_key_path}[/dim]")


# ── config status ───────────────────────────────────────────────────────────


@app.command("status")
def config_status(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Show org details, tier, and basic stats. GET /v1/agent/org."""
    from ..client import CommuneClient
    from ..errors import api_error, auth_required_error, network_error
    from ..state import AppState

    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)

    # Fetch org details
    org_data: dict = {}
    try:
        r = client.get("/v1/agent/org")
        if r.is_success:
            org_data = r.json()
    except Exception:
        pass

    # Always show local config regardless
    cfg = load_config()
    summary: dict = {
        "api_key": mask(cfg.get("api_key", "")),
        "base_url": cfg.get("base_url", "https://api.commune.email"),
        "config_file": str(config_path()),
    }
    if org_data:
        summary.update({
            "org_name": org_data.get("name", ""),
            "org_id": org_data.get("id", ""),
            "tier": org_data.get("tier", ""),
            "status": org_data.get("status", ""),
        })

    if json_output or state.should_json():
        print_json(summary)
        return

    print_kv(summary, json_output=False, title="Commune Status")


# ── config keys ─────────────────────────────────────────────────────────────


@keys_app.command("list")
def keys_list(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """List all API keys for your org. GET /v1/agent/api-keys."""
    from ..client import CommuneClient
    from ..errors import api_error, auth_required_error, network_error
    from ..state import AppState

    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    client = CommuneClient.from_state(state)
    try:
        r = client.get("/v1/agent/api-keys")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    from ..output import print_list
    print_list(
        r.json(),
        json_output=json_output or state.should_json(),
        title="API Keys",
        columns=[
            ("ID", "id"),
            ("Name", "name"),
            ("Prefix", "keyPrefix"),
            ("Status", "status"),
            ("Last Used", "lastUsedAt"),
            ("Created", "createdAt"),
        ],
    )



@keys_app.command("revoke")
def keys_revoke(
    ctx: typer.Context,
    key_id: str = typer.Argument(..., help="API key ID to revoke."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Revoke an API key. DELETE /v1/agent/api-keys/{keyId}.

    Revoked keys stop working immediately and cannot be un-revoked.
    """
    from ..client import CommuneClient
    from ..errors import api_error, auth_required_error, network_error
    from ..state import AppState

    state: AppState = ctx.obj or AppState()
    if not state.has_any_auth():
        auth_required_error(json_output=json_output or state.should_json())

    if not yes and not json_output and state.is_tty():
        confirm = typer.confirm(f"Revoke API key {key_id}? This cannot be undone.", default=False)
        if not confirm:
            raise typer.Exit(0)

    client = CommuneClient.from_state(state)
    try:
        r = client.delete(f"/v1/agent/api-keys/{key_id}")
    except Exception as exc:
        network_error(exc, json_output=json_output or state.should_json())

    if not r.is_success:
        api_error(r, json_output=json_output or state.should_json())

    if json_output or state.should_json():
        print_json(r.json() if r.content else {"revoked": True})
        return
    print_success(f"API key [bold]{key_id}[/bold] revoked.")


