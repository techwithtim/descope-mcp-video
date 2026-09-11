"""Step 1: a plain MCP server, running locally over stdio.

Three tools over a tiny SQLite "notes" database. No network, no auth.
Claude Desktop / Cursor launch this file as a subprocess and talk to it over stdin/stdout.
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
    mcp.run()  # stdio by default
