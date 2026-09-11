"""Hit the running server from the terminal.

    uv run test_client.py                # v2 (no auth)
    uv run test_client.py --oauth        # v3 (opens the browser for Descope login + consent)
    uv run test_client.py --oauth --url https://your-server.example.com/mcp

Handy for the "anyone with the URL can call this" moment in v2, and for showing the
OAuth flow from a plain terminal in v3 before you switch to Cursor / Claude.
"""

import asyncio
import sys

from fastmcp import Client

url = "http://localhost:8000/mcp"
if "--url" in sys.argv:
    url = sys.argv[sys.argv.index("--url") + 1]
auth = "oauth" if "--oauth" in sys.argv else None


async def main() -> None:
    async with Client(url, auth=auth) as client:
        tools = await client.list_tools()
        print("tools:", [t.name for t in tools])

        if any(t.name == "whoami" for t in tools):
            print("whoami:", (await client.call_tool("whoami")).data)

        print("add:", (await client.call_tool("add_a_note", {"text": "hello from the terminal"})).data)
        print("list:", (await client.call_tool("list_my_notes")).data)


asyncio.run(main())
