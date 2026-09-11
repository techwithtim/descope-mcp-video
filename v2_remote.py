"""Step 2: the same server, but remote (Streamable HTTP) with NO auth.

Run:  uv run v2_remote.py
URL:  http://localhost:8000/mcp

Anyone who can reach that URL can list, add and delete notes. There is no idea of
"who" is calling, so every caller sees the same notes. This is the problem v3 fixes.
"""

from fastmcp import FastMCP

from notes_db import add_note, delete_note, list_notes

mcp = FastMCP("notes")


@mcp.tool()
def list_my_notes() -> list[dict]:
    """List all saved notes."""
    return list_notes(owner="local")


@mcp.tool()
def add_a_note(text: str) -> dict:
    """Save a new note."""
    return add_note(owner="local", text=text)


@mcp.tool()
def delete_a_note(note_id: int) -> str:
    """Delete a note by id."""
    return "deleted" if delete_note(owner="local", note_id=note_id) else "not found"


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
