"""In-season session templates for the four-session weekly loop."""
from __future__ import annotations
from .config import load

ROSTER_BLOCK = """QB:
RB:
WR:
TE:
FLEX/other:
Bench:"""

TEMPLATES = {
    1: "Week #:\nRoster changes since last week:\nAvailable worth a look (or 'scan leaguewide'):\nWeekend injury news:",
    2: "Trade offers received:\nTempted to buy:\nTempted to sell:\nTNF starters:\nNews to flag:",
    3: "Roster (if changed):\nInactives / morning injury news:\nMy close calls:",
    4: "Results:\nWhat surprised me (good):\nWhat surprised me (bad):",
}


def session(n: int) -> str:
    s = load("weekly")[n]
    lines = [
        f"SESSION {n}: {s['name']}",
        f"When: {s['when']}",
        f"Deadline: {s['deadline']}",
        "",
        "Bring:",
    ]
    lines += [f"  - {b}" for b in s["bring"]]
    lines += ["", f"Format rule: {s['rule']}", "", "--- paste this ---", TEMPLATES[n]]
    return "\n".join(lines)
