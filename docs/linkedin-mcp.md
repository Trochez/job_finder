# LinkedIn MCP

## Setup

- MCP entry is configured in `opencode.json` as `linkedin`.
- Command: `uvx mcp-server-linkedin@latest`
- Timeout: `UV_HTTP_TIMEOUT=300`

## Auth status

- Status: authenticated
- Method: secure interactive browser login
- Verified on: 2026-07-17
- Current browser state: LinkedIn feed loads successfully

## Refresh auth

Use the server's interactive login flow when the session needs renewal:

```bash
uvx mcp-server-linkedin@latest --login
```

Do not store LinkedIn secrets in this repository.
