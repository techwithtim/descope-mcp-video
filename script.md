# MCP Servers Explained (Then Build One Claude Can Log Into)

Sponsor: Descope Agentic Identity Hub (semi-dedicated). Code: `Desktop/descope-mcp-video`.
Target length: 18 to 22 minutes. Theory ~5 min, build ~6 min, Descope ~8 min.

## Title / thumbnail options

- What the f*** is an MCP server? (Build One in 20 Minutes)
- MCP Servers Explained: Everyone Skips This Part
- Your MCP Server Is Wide Open (Here's the Fix)
- How to Build an MCP Server Claude Can Actually Log Into

Thumbnail: Claude/Cursor logo on the left, a padlock or login screen in the middle, your face. Text: "NO AUTH?!" or "MCP EXPLAINED".

---

## PART 1: THEORY (fully scripted, ~5 min)

### Hook

So everybody is talking about MCP servers right now, Claude has them, Cursor has them, ChatGPT has them, and honestly the way most people explain them makes them sound way more complicated than they actually are. An MCP server is a program that gives an AI model a list of functions it's allowed to call. That's pretty much it. So in this video I'm going to break down exactly how they work, then we're going to build one from scratch in Python, and then we're going to do the part that almost every tutorial skips, which is putting it on the internet properly, with a real login screen, so Claude or Cursor can connect to it, sign in, and only do the things you actually allowed. And that last part is where things get a little bit interesting, because right now most MCP servers out there have no security at all, and I'll show you why that's a problem in a second.

### What MCP actually is

Okay so let me break this down as simply as possible. A language model on its own can't do anything. It can't read your files, it can't check your calendar, it can't query your database, all it can do is take text in and give text out. So if you want the model to do something, you have to give it tools, and a tool is really just a function with a name, a description, and some parameters. The model reads the list of tools, decides "okay I need to call this one," it sends back the name of the function and the arguments, your code runs the function, and you send the result back to the model.

Now the problem is that before MCP, every single app had to build that tool plumbing themselves, and it was different for every model. So if you built a GitHub integration for Claude, it didn't work in Cursor, it didn't work in ChatGPT, everybody was rewriting the same thing over and over again.

[SLIDE: model in the middle, four apps around it, four different plugs]

MCP is just a standard for that. Model Context Protocol. You write your tools once, as an MCP server, and any app that speaks MCP can use them. Claude, Cursor, VS Code, ChatGPT, whatever. People like to call it the USB-C of AI tools and honestly that's a pretty good way to think about it. One plug, works everywhere.

[SLIDE: same picture, one plug]

So there are two sides here. The MCP server is your code, it exposes the tools. The MCP client is the app the model lives in, so Claude Desktop, Cursor, and so on. When the client starts up it asks the server "what tools do you have," the server sends back a list with names and descriptions, and that list gets handed to the model. Then when the model wants to call one, the client sends a request to the server, the server runs the function, and sends the result back. It's all JSON going back and forth, and when we build ours you're going to see that it's really really simple.

[SLIDE: client asks "tools/list", server replies with list; client sends "tools/call", server replies with result]

### Local vs remote

Now, there are two ways an MCP server can run, and this is the part that actually matters for the rest of this video.

The first way is local. The client just launches your server as a subprocess on your machine and talks to it over standard input and output. So Claude Desktop literally runs "python my_server.py" and pipes JSON into it. This is what ninety percent of the tutorials show you, and it's great for personal stuff, because it's only on your computer, nobody else can touch it.

The second way is remote. Your server runs somewhere on the internet, it has a URL, and clients connect to it over HTTP. This is how every real product does it. The GitHub MCP server, the Notion one, Stripe, they're all just URLs. And this is what you want if you're building something for other people, or you want to use your tools from your laptop and your phone and a work machine.

[SLIDE: local = subprocess, remote = URL]

But the moment your server is a URL, you have a completely new problem that the local version never had.

### Access control

If your MCP server is on the internet, then anybody who has the URL can call your tools. And your tools do things. They read data, they write data, they delete data. So you now need to answer three questions on every single request. Who is calling this? What are they allowed to do? And who are they doing it on behalf of?

And here's the part that kind of shocked me when I looked into it. A security audit this year found that about a quarter of public MCP servers have no authentication at all. [Tim: verify, source in notes] And of the ones that do have something, most of them are using a static API key. So one long-lived secret, sitting in a config file, shared by everyone. Only a tiny fraction actually use proper OAuth.

Now why is a static key a problem? Well think about it. If five different agents are hitting your server with the same key, you can't tell them apart. You can't see which user told which agent to do what. And if one of them gets compromised, you can't revoke that one, you have to kill the key and break everybody. That's fine for a weekend project. It is not fine for anything real.

[SLIDE: one key, five agents, "which one is which?"]

So the MCP spec actually has an answer for this, and it's the same thing every serious API uses, which is OAuth. Specifically OAuth 2.1 with PKCE, and if that sounds scary, don't worry, I'm going to explain the whole thing in about sixty seconds, and then we're going to use a tool that does it for us, because you should not be building this yourself.

Here's how it works. Your MCP server does not do login. That's the key insight. When Claude tries to call your server without a token, your server just says "401, not authorized, and by the way, here is the URL of the place you go to log in." That place is called the authorization server. Claude goes there, the user sees a normal login screen, they sign in with Google or email or whatever, and then they see a consent screen, which is the "this app wants to read your notes and create notes, allow or deny" thing you've seen a hundred times. The user clicks allow, the authorization server hands Claude a token, and from then on Claude sends that token with every request. Your server checks the signature on the token, checks that it was actually meant for your server, checks what permissions are inside it, and then runs the tool.

[SLIDE: the 401 dance. Claude -> your server (401 + "go here") -> Descope login -> consent -> token -> Claude -> your server (200)]

And the permissions inside the token are called scopes. So you might have a "notes:read" scope and a "notes:write" scope, and you can say "this tool needs read, this tool needs write," and if the user only approved read, the write tool just fails, cleanly, and the client can even go back and ask for the missing permission.

The token also tells you who the user is, so now every tool call has a user ID attached to it, which means you can store data per user, you can log who did what, and you can revoke one specific person or one specific agent without touching anyone else. That's the difference between a demo and a product.

There's one more piece, which is that clients like Claude and Cursor need to register themselves with your authorization server before they can log in, and the spec has a thing called dynamic client registration for that, so they just do it automatically, you don't have to go set up Claude as an app by hand.

Now, you could build all of that yourself. The login page, the consent screen, the token signing, the client registration, the refresh logic, the revocation. Or you can plug in something that already does it, which is what we're going to do. So let's actually build this thing.

---

## PART 2: BUILD THE SERVER (bullets + demo notes, ~6 min)

### v1: local server

- `uv init`, `uv add fastmcp`. Show `notes_db.py` briefly (SQLite, three functions, don't dwell).
- Write `v1_local.py` live. Three tools: `list_my_notes`, `add_a_note`, `delete_a_note`. Point out it's just functions with a decorator, the docstring is what the model reads.
- [DEMO] Add to Cursor via `mcp.json` (command + args). Ask Cursor "add a note that says buy milk", "what are my notes". Show the tool call happening.
- [DEMO] Optional: run `test_client.py`-style stdio client to show the raw tool list JSON, ties back to the theory slide.

### v2: make it remote

- Only change: `mcp.run(transport="http", port=8000)`. That's it, it's now a URL.
- [DEMO] `uv run v2_remote.py`, then in Cursor switch config to `{"url": "http://localhost:8000/mcp"}`. Works the same.
- [DEMO] The problem, on camera: run `uv run test_client.py` from a second terminal (or a second laptop on the same wifi). It lists, adds and deletes notes with zero login. "Every note is shared. There is no user. If I put this on a server, anybody with the URL owns it."
- Transition: "So we need the 401 dance from earlier. We're not writing an authorization server. We're using Descope."

---

## PART 3: DESCOPE (bullets + demo notes, ~8 min)

### Sponsor read (scripted, ~45 sec)

Descope is the sponsor of this video and honestly they're a perfect fit here, because this is exactly what their Agentic Identity Hub is built for. It's an identity provider for AI agents and MCP servers. So it acts as the authorization server we just talked about, it handles the login screen, the consent screen, dynamic client registration so Claude and Cursor just work, per-tool scopes, and it gives every agent and every user a real identity you can see and revoke from a dashboard. It also has this thing called Connections, which is a vault that stores your users' Google or GitHub or Slack tokens so your agent can call those on their behalf without you ever storing a long-lived key, and I'll show you that at the end. They've got a free forever tier, link in the description, and if you want to talk to them about your use case there's a booking link down there too.

### Console setup

- [DEMO, screen record] Console -> Agentic Identity Hub -> MCP Servers -> + MCP Server. Name: notes.
- MCP Server URL: `http://localhost:8000/mcp`. Explain in one line: this goes inside the token as the audience, so a token for some other server can't be replayed against yours.
- Enable Dynamic Client Registration and CIMD. "This is the 'Claude registers itself' part."
- Scopes: `notes:read` "Read your notes", `notes:write` "Create and delete your notes". Point out the description is literally what the user sees on the consent screen.
- Copy the Well-Known URL into `.env`.

### Code

- `uv add descope-mcp python-dotenv`.
- Show the diff from v2 to v3 (keep it to three things on screen):
  1. `DescopeProvider(config_url=..., base_url=...)` passed as `auth=` to FastMCP. "This is the bouncer. Every request without a valid Descope token gets the 401 and the go-log-in-here header."
  2. `DescopeMCP(...)` init plus the `current_user()` helper: `get_access_token()` gives us the token FastMCP already verified, Descope's `validate_token` and `require_scopes` check audience and scopes. One helper, every tool calls it.
  3. Tools now do `owner=user_id` instead of `owner="local"`. "That one change is per-user data."
- Mention `whoami` tool: returns user id, client id, scopes. Useful for the demo.

### The flow, on camera

- [DEMO] `uv run v3_auth.py`, then the curl with no token. Pause on the `401` and the `WWW-Authenticate` header. Open the `.well-known/oauth-protected-resource/mcp` URL in the browser, show it points at Descope. "That's the whole discovery mechanism, two lines of JSON."
- [DEMO] `uv run test_client.py --oauth`. Browser pops, Descope login, consent screen with the two scopes and the descriptions you typed. Allow. Back in the terminal: tools list, `whoami` shows your user id and scopes, note gets added.
- [DEMO] Cursor: same `url` config as v2, click connect, same login + consent, goes green. "add a note", "list my notes". Then the money shot: open an incognito window, log in as a different user (a second email), list notes, they're empty. Per-user, no extra code.
- [DEMO] Scopes: reconnect, on the consent screen only allow `notes:read`. Ask Cursor to add a note. Show the `insufficient_scope` error coming back in the spec format. "The tool didn't crash, it told the client exactly which permission is missing."
- [DEMO] Console -> MCP Servers -> notes -> Clients. Show Cursor and the test client registered as separate clients with their own IDs. Revoke one. Show it get kicked out. "This is the thing static API keys can't do."

### Claude / going public (short)

- Claude custom connectors want a public HTTPS URL. Show `cloudflared tunnel --url http://localhost:8000` (or the VPS if you have it deployed), update MCP Server URL in console and `.env`, add the connector in Claude. Same login screen appears inside Claude.
- One line on the real deploy: Hostinger VPS, Caddy in front, domain, done. Don't go deep, link a previous VPS video.

### Bonus: Connections (~1 min, optional, cut if long)

- Problem: a tool that needs the user's GitHub. Normally you'd store a GitHub token somewhere. Don't.
- [DEMO] Console -> Connections -> GitHub template. Attach it to the `notes:read` scope. Now the consent screen also connects GitHub.
- Show `my_github_repos`: `get_connection_token(user_id, app_id, access_token=...)`, Descope hands back a fresh scoped GitHub token for that user, we call the GitHub API. "We never stored it, we never refresh it, and it's tied to the same identity as the MCP token."

---

## OUTRO (scripted)

So that's MCP servers. A list of functions, a standard way to describe them, and once you put it on the internet, a proper login in front of it so you actually know who's calling. All the code is on GitHub, link in the description, and the Descope free tier plus their booking link are down there too if you want to try this yourself. If you enjoyed this, make sure you like, subscribe, and I will see you in the next one.

---

## Description CTA (paste in)

Try Descope Agentic Identity Hub free: [Plug booking link from Descope]
Docs: https://docs.descope.com/agentic-identity-hub
Code from this video: [repo link]

## Filming notes

- Reset `notes.db` before each take (`rm notes.db`) so ids start at 1.
- Have a second Descope test user ready (any email, magic link) for the incognito moment.
- The "quarter of public MCP servers have no auth" line: from a 2026 audit cited in several writeups. Keep it as "about a quarter" and "most use static keys". Drop the exact 8.5% OAuth figure unless you find the primary source.
- If you cut for time, cut the Connections bonus first, then the cloudflared/Claude step. The Cursor flow alone shows everything Descope asked for.
