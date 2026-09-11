# MCP Servers Explained + Descope (video build)

Three versions of the same "notes" MCP server, built in the order you show them on camera.

- Script: `script.md` (theory fully scripted, build + Descope as bullets)
- Brand-facing script (Google Doc): https://docs.google.com/document/d/1PCnNyEp0rB_m-_FViT_pYCKwViQmGUElSLTVpRmpPqQ/edit
- Theory slide deck: `presentation/index.html` (open locally, arrows to move, F for fullscreen) or https://clever-opera-nnya.here.now/

| File | What it is | Auth |
|---|---|---|
| `v1_local.py` | stdio server, Claude/Cursor launch it as a subprocess | none (local only) |
| `v2_remote.py` | same tools over Streamable HTTP at `http://localhost:8000/mcp` | none (the problem) |
| `v3_auth.py` | same tools, protected by Descope, notes stored per user, scopes per tool | Descope OAuth 2.1 |
| `test_client.py` | terminal client; `--oauth` triggers the browser login flow | |
| `notes_db.py` | SQLite helper shared by all three | |

Versions pinned on purpose: `fastmcp<4` and `mcp<2`, because `descope-mcp` 0.1.0 still imports
`FastMCP` from the old `mcp.server` path and breaks on `mcp` 2.x. Already done in `pyproject.toml`.

## Setup

```bash
uv sync
cp .env.example .env
```

## v1: local (stdio)

Cursor: `~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "notes": {
      "command": "uv",
      "args": ["run", "--directory", "C:/Users/User/Desktop/descope-mcp-video", "v1_local.py"]
    }
  }
}
```

Claude Desktop: same block in `%APPDATA%/Claude/claude_desktop_config.json`.

Or from the terminal, no editor needed:

```bash
uv run python -c "import asyncio; from fastmcp import Client; asyncio.run((lambda: Client('v1_local.py').__aenter__())())"
```

## v2: remote, no auth

```bash
uv run v2_remote.py
```

```bash
uv run test_client.py
```

Cursor: `{"notes": {"url": "http://localhost:8000/mcp"}}`. Point out that the same URL works from any machine
on the network and there is no "who" anywhere.

## v3: Descope

### Console (one time, about 2 minutes)

1. Sign up at https://www.descope.com (Free Forever tier) and open the console.
2. **Agentic Identity Hub -> MCP Servers -> + MCP Server**. Name it `notes`.
3. **MCP Server URL**: `http://localhost:8000/mcp` (change to the public URL when you deploy). This becomes the `aud` claim.
4. **Client registration**: enable **Dynamic Client Registration (DCR)** and **CIMD**. This is what lets Cursor / Claude register themselves.
5. **Scopes**: add
   - `notes:read`, consent text "Read your notes"
   - `notes:write`, consent text "Create and delete your notes"
   Leave both optional so you can demo denying one on the consent screen.
6. Expand **Connect your MCP server to Descope** and copy the **Well-Known URL**. Put it in `.env` as `DESCOPE_CONFIG_URL`.

### Run

```bash
uv run v3_auth.py
```

Show the 401 first:

```bash
curl -i -X POST http://localhost:8000/mcp -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\"}"
```

You get `401` and a `WWW-Authenticate` header pointing at
`http://localhost:8000/.well-known/oauth-protected-resource/mcp`, which lists Descope as the authorization server.
That header is the entire "how does Claude know where to log in" mechanism.

Then the real flow from the terminal (browser opens, Descope login, consent screen with the two scopes):

```bash
uv run test_client.py --oauth
```

Then Cursor: add `{"notes": {"url": "http://localhost:8000/mcp"}}`, click the server, it opens the browser for
login + consent, comes back green. Ask it "what notes do I have", "add a note", "delete note 2".

Claude (desktop or claude.ai) custom connectors need a public HTTPS URL. Fastest way for the demo:

```bash
cloudflared tunnel --url http://localhost:8000
```

Set `MCP_SERVER_URL` in `.env` and **MCP Server URL** in the console to `https://<tunnel>.trycloudflare.com/mcp`,
restart, then Claude -> Settings -> Connectors -> Add custom connector -> paste the URL.
For the real deploy do the same on the Hostinger VPS behind Caddy/nginx with a domain.

### Things to demo once logged in

- `whoami` shows the user id, the client id Cursor registered with, and the granted scopes.
- Log in as a second user (incognito) and show the notes are different: per-user data from the `sub` claim, zero extra code.
- On the consent screen approve only `notes:read`, then try `add_a_note`: you get the MCP-spec `insufficient_scope` error
  from `require_scopes`, and the client can re-prompt for the missing scope.
- Console -> MCP Servers -> notes -> Clients: see Cursor / Claude registered, revoke one, watch it get kicked out.

### Bonus: GitHub via Connections (optional)

1. **Agentic Identity Hub -> Connections -> + Connection -> GitHub**, follow the prompt to create a GitHub OAuth app,
   scope `repo` or `read:user`. Note the Connection id.
2. Under the `notes` MCP server scope `notes:read`, add that GitHub connection as a **connection scope** so the user
   connects GitHub during consent.
3. `GITHUB_CONNECTION_ID=<id>` in `.env`, restart. The `my_github_repos` tool appears. The server never sees a
   long-lived GitHub token; `get_connection_token` hands it a fresh one per call.

## Verify before filming

- After creating the MCP server, confirm the token `aud` includes both the project id and the MCP Server URL.
  FastMCP's `DescopeProvider` checks the project id; `descope_mcp.validate_token` checks the MCP Server URL.
  If one of them complains, the fix is either to leave MCP Server URL empty in the console and drop
  `mcp_server_url=` in `v3_auth.py`, or to pass a custom `token_verifier` to `DescopeProvider`.
- Which registration method Cursor / Claude use today (DCR vs CIMD). Enabling both covers it.
- Whether Claude Desktop accepts a `trycloudflare.com` URL as a custom connector (it should; it is HTTPS).
