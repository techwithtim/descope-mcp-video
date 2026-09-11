"""Step 3: the remote server, now protected by Descope.

Run:  uv run v3_auth.py
URL:  http://localhost:8000/mcp

What changed vs v2:
  1. `auth=DescopeProvider(...)`  -> FastMCP rejects any request without a valid Descope token,
     and tells MCP clients (Cursor, Claude, VS Code) where to go log in (the 401 + .well-known dance).
  2. Every tool asks "who is this?" via get_access_token(), then uses Descope's SDK to
     enforce scopes and (optionally) fetch tokens for third-party services.
  3. Notes are stored per user (the `sub` claim), so two users never see each other's notes.
"""

import os

import httpx
from descope_mcp import DescopeMCP, InsufficientScopeError, get_connection_token, require_scopes, validate_token
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.descope import DescopeProvider
from fastmcp.server.dependencies import get_access_token

from notes_db import add_note, delete_note, list_notes

load_dotenv()

CONFIG_URL = os.environ["DESCOPE_CONFIG_URL"]
SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8000/mcp")
BASE_URL = SERVER_URL.removesuffix("/mcp")

# --- 1. The bouncer: FastMCP + Descope -------------------------------------------------
auth = DescopeProvider(
    config_url=CONFIG_URL,
    base_url=BASE_URL,
    scopes_supported=["notes:read", "notes:write"],  # advertised to clients during discovery
)
mcp = FastMCP("notes", auth=auth)

# --- 2. Descope's MCP SDK: scope checks + connection (third-party) tokens ---------------
DescopeMCP(well_known_url=CONFIG_URL, mcp_server_url=SERVER_URL)


def current_user(*scopes: str) -> tuple[str, str]:
    """Return (user_id, raw_token) for the caller, or raise if they lack the scopes."""
    tok = get_access_token()  # already signature-checked by DescopeProvider
    if tok is None:
        raise PermissionError("Authentication required")
    claims = validate_token(tok.token)  # Descope re-validates signature, expiry and audience
    claims.setdefault("scopes", tok.scopes)
    require_scopes(claims, list(scopes))  # raises InsufficientScopeError (MCP spec format)
    return claims.get("sub") or claims.get("userId"), tok.token


# --- 3. Tools -------------------------------------------------------------------------
@mcp.tool()
def whoami() -> dict:
    """Show who the server thinks you are and what you're allowed to do."""
    tok = get_access_token()
    if tok is None:
        return {"error": "Authentication required"}
    return {
        "user_id": tok.claims.get("sub") if tok.claims else None,
        "client_id": tok.client_id,
        "scopes": tok.scopes,
        "expires_at": tok.expires_at,
    }


@mcp.tool()
def list_my_notes() -> list[dict] | dict:
    """List the caller's notes. Requires notes:read."""
    try:
        user_id, _ = current_user("notes:read")
    except InsufficientScopeError as e:
        return e.to_json()
    return list_notes(owner=user_id)


@mcp.tool()
def add_a_note(text: str) -> dict:
    """Save a note for the caller. Requires notes:write."""
    try:
        user_id, _ = current_user("notes:write")
    except InsufficientScopeError as e:
        return e.to_json()
    return add_note(owner=user_id, text=text)


@mcp.tool()
def delete_a_note(note_id: int) -> str | dict:
    """Delete one of the caller's notes. Requires notes:write."""
    try:
        user_id, _ = current_user("notes:write")
    except InsufficientScopeError as e:
        return e.to_json()
    return "deleted" if delete_note(owner=user_id, note_id=note_id) else "not found"


# --- Bonus: a tool that needs the user's GitHub, without us ever storing a GitHub token ----
GITHUB_CONNECTION_ID = os.environ.get("GITHUB_CONNECTION_ID")

if GITHUB_CONNECTION_ID:

    @mcp.tool()
    async def my_github_repos(limit: int = 5) -> list[str] | dict:
        """List the caller's most recently updated GitHub repos. Requires notes:read."""
        try:
            user_id, mcp_token = current_user("notes:read")
        except InsufficientScopeError as e:
            return e.to_json()

        # Descope's Connections vault hands us a fresh, scoped GitHub token for THIS user.
        github_token = get_connection_token(
            user_id=user_id,
            app_id=GITHUB_CONNECTION_ID,
            access_token=mcp_token,  # policy is enforced against the caller's MCP token
        )
        async with httpx.AsyncClient() as http:
            r = await http.get(
                "https://api.github.com/user/repos",
                headers={"Authorization": f"Bearer {github_token}", "Accept": "application/vnd.github+json"},
                params={"sort": "updated", "per_page": limit},
            )
            r.raise_for_status()
        return [repo["full_name"] for repo in r.json()]


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
