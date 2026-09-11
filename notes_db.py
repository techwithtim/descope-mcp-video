"""Tiny SQLite store used by every version of the server.

Every note has an owner. In v1/v2 the owner is always "local".
In v3 the owner is the user id that Descope puts in the token (the `sub` claim),
which is what gives every user their own private notes.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "notes.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS notes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL, text TEXT NOT NULL, "
        "created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    return conn


def list_notes(owner: str) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, text, created_at FROM notes WHERE owner = ? ORDER BY id", (owner,)
        ).fetchall()
    return [dict(r) for r in rows]


def add_note(owner: str, text: str) -> dict:
    with _conn() as conn:
        cur = conn.execute("INSERT INTO notes (owner, text) VALUES (?, ?)", (owner, text))
    return {"id": cur.lastrowid, "text": text}


def delete_note(owner: str, note_id: int) -> bool:
    with _conn() as conn:
        cur = conn.execute("DELETE FROM notes WHERE owner = ? AND id = ?", (owner, note_id))
    return cur.rowcount > 0
