# commune-cli

Official command-line interface for the [Commune](https://commune.email) email API.

Covers every API surface: domains, inboxes, messages, threads, attachments, search, delivery analytics, webhooks, DMARC, and data deletion.

---

## Install

```bash
pip install commune-cli
```

Requires Python ≥ 3.9.

---

## Quick Start

```bash
# Set your API key
export COMMUNE_API_KEY=comm_...

# Send an email
commune messages send \
  --to recipient@example.com \
  --subject "Hello from CLI" \
  --text "Sent from the terminal."

# List inboxes
commune inboxes list

# JSON output (automatic when stdout is piped)
commune inboxes list --json | jq '.data[].email'
```

---

## Authentication

Set your API key in one of these ways (highest priority wins):

| Priority | Source |
|----------|--------|
| 1 | `--api-key` flag |
| 2 | `COMMUNE_API_KEY` env var |
| 3 | `~/.commune/config.toml` → `api_key` |

Store permanently:

```bash
commune config set api_key comm_...
commune config show
```

---

## Output

- **TTY**: rich tables and panels with color
- **Piped / `--json`**: clean JSON to stdout; status messages to stderr

```bash
# JSON list format (always consistent)
commune threads list --json
# {"data": [...], "has_more": false, "next_cursor": null}
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | API / validation error |
| 2 | Auth error (401/403) |
| 3 | Not found (404) |
| 4 | Rate limit or plan gate (429/403) |
| 5 | Network / connection error |

---

## Error Format (stderr)

```json
{"error": {"code": "not_found", "message": "Inbox not found.", "status_code": 404}}
```

---

## Commands

```
commune
├── config
│   ├── set <key> <value>
│   ├── get <key>
│   ├── show [--reveal]
│   ├── unset <key>
│   └── path
│
├── domains
│   ├── list [--limit] [--cursor]
│   ├── get <domain-id>
│   ├── create <name>
│   ├── verify <domain-id>
│   └── records <domain-id>
│
├── inboxes
│   ├── list [--domain-id] [--limit] [--cursor]
│   ├── get <inbox-id>
│   ├── create [--local-part] [--domain-id] [--name] [--webhook-url]
│   ├── update <inbox-id> [--name] [--webhook-url]
│   ├── delete <inbox-id> --domain-id [--yes]
│   ├── set-webhook <inbox-id> --domain-id --url
│   └── extraction-schema
│       ├── set <inbox-id> --domain-id --schema <json>
│       └── remove <inbox-id> --domain-id
│
├── messages
│   ├── send --to --subject [--text] [--html] [--from] [--inbox-id] [--domain-id]
│   │        [--cc] [--bcc] [--reply-to] [--thread-id]
│   └── list [--inbox-id] [--domain-id] [--sender] [--limit] [--order] [--before] [--after]
│
├── threads
│   ├── list [--inbox-id] [--domain-id] [--limit] [--cursor] [--order]
│   ├── messages <thread-id> [--limit] [--order] [--cursor]
│   ├── metadata <thread-id>
│   ├── set-status <thread-id> <open|needs_reply|waiting|closed>
│   ├── assign <thread-id> [--to <user>]
│   └── tags
│       ├── add <thread-id> <tag...>
│       └── remove <thread-id> <tag...>
│
├── attachments
│   ├── upload <file>
│   ├── get <attachment-id>
│   └── url <attachment-id> [--expires-in]
│
├── search
│   └── threads <query> [--inbox-id] [--domain-id] [--limit]
│
├── delivery
│   ├── metrics [--domain-id] [--inbox-id] [--period]
│   ├── events [--domain-id] [--inbox-id] [--limit]
│   └── suppressions [--domain-id] [--inbox-id] [--limit]
│
├── webhooks
│   ├── list [--inbox-id] [--status] [--endpoint] [--limit]
│   ├── get <delivery-id>
│   ├── retry <delivery-id>
│   └── health
│
├── dmarc
│   ├── reports <domain> [--limit]
│   └── summary <domain> [--days]
│
└── data
    ├── delete-request [--email] [--inbox-id] [--domain-id]
    ├── delete-confirm <id> [--yes]
    └── delete-status <id>
```

---

## Global Flags

```
--api-key TEXT    API key (overrides env/config)
--base-url TEXT   API base URL (default: https://api.commune.email)
--json            Output raw JSON
--quiet / -q      Suppress status messages
--no-color        Disable color output
--version / -V    Show version and exit
```

---

## Config File

Stored at `~/.commune/config.toml` (or `$COMMUNE_CONFIG_DIR/config.toml`).
Created with `chmod 600` to protect your API key.

```toml
api_key = "comm_..."
base_url = "https://api.commune.email"
```

---

## Scripting

```bash
# Non-TTY → auto JSON
inboxes=$(commune inboxes list)
echo "$inboxes" | jq '.data[0].email'

# Pipe body from stdin
echo "Email body" | commune messages send \
  --to user@example.com \
  --subject "Automated" \
  --text -

# Exit code handling
if commune messages send --to user@example.com --subject Test --text "Hi" --json; then
  echo "Sent"
else
  echo "Failed: $?"
fi
```

Full API reference: https://docs.commune.email

---

## Ecosystem

| Package | Description |
|---------|-------------|
| [commune](https://github.com/shanjai-raj/commune) | Email & SMS infrastructure — self-hostable backend |
| [commune-ai](https://github.com/shanjai-raj/commune-ai) | TypeScript/Node.js SDK |
| [commune-python](https://github.com/shanjai-raj/commune-python) | Python SDK |
| [commune-mcp](https://github.com/shanjai-raj/commune-mcp) | MCP server for Claude Desktop, Cursor, Windsurf |
| **[commune-cli](https://github.com/shanjai-raj/commune-cli)** | **Command-line interface** |

## License

Apache-2.0
