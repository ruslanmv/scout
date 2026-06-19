"""Scout MCP server — trend intelligence for any LLM.

Exposes Scout's trend data and AI planning as Model Context Protocol tools so an
assistant (Claude, or any MCP client) can brainstorm *what to build next* and
*which technical trends are hot*, grounded in real signals.

Run (stdio, for Claude Desktop and most clients):

    python -m scout_mcp

Run over HTTP (streamable-http):

    python -m scout_mcp --http --host 127.0.0.1 --port 8765
"""
from __future__ import annotations

import argparse
import json

from mcp.server.fastmcp import FastMCP

from scout_mcp import tools

mcp = FastMCP(
    "Scout Trend Intelligence",
    instructions=(
        "Scout turns real developer/AI signals (GitHub, Hugging Face, news, jobs) into "
        "concrete things to build. Use these tools to brainstorm hot technical trends and "
        "the next high-leverage project. Typical flow: list_hot_trends -> "
        "recommend_what_to_build -> brainstorm_project_ideas / generate_action_plan."
    ),
)


@mcp.tool()
def list_hot_trends(location: str = "Worldwide", limit: int = 10) -> dict:
    """List the hottest developer & AI technology trends right now, ranked by momentum.

    Use this to brainstorm what is gaining traction. `location` may be a city+country
    like "Rome, Italy" or "San Francisco, United States", or "Worldwide" for the global view.
    """
    return tools.list_hot_trends(location, limit)


@mcp.tool()
def recommend_what_to_build(goal: str = "build_portfolio", profile: str = "developer",
                            location: str = "Worldwide", limit: int = 6) -> dict:
    """Recommend concrete things to build for a goal and profile, ranked by opportunity.

    goal: build_portfolio | career | create_agents | startup | research.
    profile: developer | ai_engineer | student | founder | enterprise | agent.
    Each result includes a suggested next move (study, build, publish).
    """
    return tools.recommend_what_to_build(goal, profile, location, limit)


@mcp.tool()
def brainstorm_project_ideas(topic: str, count: int = 3) -> dict:
    """Brainstorm concrete, buildable project blueprints for a topic (by id or name).

    Returns title, level, stack, deliverables, and why each project is impressive —
    ideal for deciding exactly what to create next.
    """
    return tools.brainstorm_project_ideas(topic, count)


@mcp.tool()
def topic_deep_dive(topic: str, location: str = "Worldwide",
                    goal: str = "build_portfolio", profile: str = "developer") -> dict:
    """Full intelligence on one topic: what it is, evidence/signals, study plan,
    project blueprints, risks, and reusable agent/tool opportunities."""
    return tools.topic_deep_dive(topic, location, goal, profile)


@mcp.tool()
def find_build_opportunities(location: str = "Worldwide", goal: str = "create_agents",
                             limit: int = 8) -> dict:
    """Find high-value artifacts to create now — agents, MCP tools, and datasets — derived
    from current trends. This is the "what new thing should I build?" shortlist."""
    return tools.find_build_opportunities(location, goal, limit)


@mcp.tool()
def search_trends(query: str, limit: int = 10) -> dict:
    """Search Scout's trend topics by keyword or idea to ground brainstorming in real signals."""
    return tools.search_trends(query, limit)


@mcp.tool()
def generate_action_plan(topic: str, goal: str = "build_portfolio",
                         profile: str = "developer", location: str = "Worldwide") -> dict:
    """Generate a live AI "study -> build -> publish" action plan for a topic using Scout's AI
    engine (OllaBridge Cloud), grounded in real signals. Falls back to a deterministic plan if
    AI is disabled or the gateway is unreachable."""
    return tools.generate_action_plan(topic, goal, profile, location)


@mcp.resource("scout://trends/latest")
def latest_trends() -> str:
    """The current top global trends as JSON (a quick grounding snapshot)."""
    return json.dumps(tools.list_hot_trends("Worldwide", 20), ensure_ascii=False, indent=2)


@mcp.prompt()
def brainstorm_next_build(location: str = "Worldwide", goal: str = "build_portfolio",
                          profile: str = "developer") -> str:
    """A guided brainstorming prompt for choosing the next high-leverage thing to build."""
    return (
        f"You are brainstorming what a {profile} in {location} should build next for the goal "
        f"'{goal}'. Use the Scout tools to ground every suggestion in real data:\n"
        f"1. Call list_hot_trends(location='{location}') to see what is hot.\n"
        f"2. Call recommend_what_to_build(goal='{goal}', profile='{profile}', location='{location}').\n"
        f"3. Pick the 2-3 strongest and call brainstorm_project_ideas on each.\n"
        f"4. Optionally call generate_action_plan for the top pick.\n"
        f"Then present a short shortlist: each idea with why-now (cite the signals) and a concrete "
        f"first project to ship."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Scout MCP server")
    parser.add_argument("--http", action="store_true", help="Serve over streamable HTTP instead of stdio.")
    parser.add_argument("--host", default="127.0.0.1", help="Host for --http mode.")
    parser.add_argument("--port", type=int, default=8765, help="Port for --http mode.")
    args = parser.parse_args()

    if args.http:
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
