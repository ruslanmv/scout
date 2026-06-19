# Scout MCP Server

Turn Scout into a **Model Context Protocol** server so any LLM — Claude Desktop,
or any MCP client — can call it to **brainstorm hot technical trends and what to
build next**, grounded in real GitHub / Hugging Face / news / job signals.

> "What should I build this month?" → the model calls Scout, sees what's
> actually trending for your goal and location, and proposes concrete projects.

## Tools

| Tool | What it does |
|------|--------------|
| `list_hot_trends(location, limit)` | Hottest developer/AI trends right now (global or by city). |
| `recommend_what_to_build(goal, profile, location, limit)` | Ranked things to build, each with a next move. |
| `brainstorm_project_ideas(topic, count)` | Concrete project blueprints (title, stack, deliverables). |
| `topic_deep_dive(topic, …)` | Full evidence, study plan, projects, risks for one topic. |
| `find_build_opportunities(location, goal, limit)` | High-value agents / MCP tools / datasets to create. |
| `search_trends(query, limit)` | Search topics by keyword/idea to ground brainstorming. |
| `generate_action_plan(topic, goal, profile, location)` | Live AI study→build→publish plan (OllaBridge Cloud). |

Also ships a prompt `brainstorm_next_build` and a resource `scout://trends/latest`.

## Install

```bash
pip install mcp          # the official MCP SDK (or: pip install -e ".[mcp]")
```

## Run

```bash
# stdio (what Claude Desktop and most clients use)
python -m scout_mcp

# or over HTTP (streamable-http)
python -m scout_mcp --http --host 127.0.0.1 --port 8765
```

Run from the repository root so the server can read the trend datasets.

## Connect from Claude Desktop

Add this to `claude_desktop_config.json`
(macOS: `~/Library/Application Support/Claude/`, Windows: `%APPDATA%\Claude\`):

```json
{
  "mcpServers": {
    "scout": {
      "command": "python",
      "args": ["-m", "scout_mcp"],
      "cwd": "/absolute/path/to/scout"
    }
  }
}
```

Restart Claude Desktop, then ask:

> "Use Scout to brainstorm what an AI engineer in San Francisco should build this
> month, then give me a first project for the strongest idea."

Claude will call `list_hot_trends` → `recommend_what_to_build` →
`brainstorm_project_ideas` and hand you a grounded shortlist.

## Notes

- Trend tools are deterministic and offline (they read `datasets/latest.json`).
- `generate_action_plan` makes a live AI call via OllaBridge Cloud and falls back
  to a deterministic plan if the gateway is off/unreachable — see
  [../docs/AI_AND_ADMIN.md](../docs/AI_AND_ADMIN.md).
- The package is named `scout_mcp` (not `mcp`) so it never shadows the SDK.
