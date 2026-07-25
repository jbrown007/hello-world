"""Draft-day decision engines: QB count rule and slot trees."""
from __future__ import annotations
from dataclasses import dataclass
from .config import load, league


@dataclass
class Verdict:
    action: str
    note: str
    detail: str = ""

    def __str__(self) -> str:
        out = f"[{self.action}] {self.note}"
        return f"{out}\n{self.detail}" if self.detail else out


def qb_verdict(rnd: int, gone: int) -> Verdict:
    """Apply the superflex QB count rule for a given round and QB count."""
    rule = load("qb_rule")
    floor = rule["hard_floor_round"]

    if rnd > floor:
        return Verdict(
            "PAST_FLOOR",
            f"You are past the Round {floor} hard floor.",
            "If QB2 is not on your roster, take one with this pick. Do not optimize.",
        )

    # The floor round itself. Without this, rnd == floor falls past every
    # threshold band and returns NORMAL - no urgency in the exact round the
    # floor bites. Bands only cover max_round 4 and 5.
    if rnd == floor:
        return Verdict(
            "TAKE_QB2_NOW",
            f"Round {floor} IS the hard floor.",
            f"{gone} QBs gone. This is your last pick inside the floor. "
            "If QB2 is not on your roster, take one with this pick.",
        )

    for band in rule["rules"]:
        if rnd <= band["max_round"]:
            for t in band["thresholds"]:
                if gone >= t["gone"]:
                    return Verdict(t["action"], t["note"], f"{gone} QBs gone by your Round {rnd} pick.")

    return Verdict(
        "NORMAL",
        f"No trigger at Round {rnd}. Hard floor is end of Round {floor}.",
        f"{gone} QBs gone.",
    )


def tree(slot: int) -> dict:
    """Return the draft branch for a given slot."""
    n = league()["teams"]
    if not 1 <= slot <= n:
        raise ValueError(f"slot must be between 1 and {n}")
    for branch in load("trees"):
        if slot in branch["slots"]:
            return branch
    raise ValueError(f"no branch covers slot {slot}")


def commitments_for(label: str) -> list[dict]:
    """Mandatory picks for a branch label: common set plus branch-specific."""
    data = load("commitments")
    return data["common"] + data["branches"].get(label, [])


def satisfiable(items: list[dict], rounds: int = 15) -> tuple[bool, str]:
    """Can one pick per round satisfy every commitment window?

    Earliest-deadline greedy, which is optimal for unit jobs with release
    times and deadlines: sort by deadline, give each commitment the first
    free round inside its window. Returns (ok, detail).
    """
    taken: dict[int, str] = {}
    for c in sorted(items, key=lambda c: (c["window"][1], c["window"][0])):
        lo, hi = c["window"]
        rnd = next((r for r in range(lo, min(hi, rounds) + 1) if r not in taken), None)
        if rnd is None:
            plan = ", ".join(f"R{r}={p}" for r, p in sorted(taken.items()))
            return False, f"no free round in R{lo}-R{hi} for '{c['pick']}' (already placed: {plan})"
        taken[rnd] = c["pick"]
    plan = " | ".join(f"R{r} {p}" for r, p in sorted(taken.items()))
    return True, plan


def _round_span(text: str) -> tuple[int, int] | None:
    """Parse round labels like '1', '2-3', '5-6', '1-2 turn'. None for RISK etc."""
    import re
    m = re.match(r"(\d+)(?:-(\d+))?", str(text).strip())
    if not m:
        return None
    lo = int(m.group(1))
    return lo, int(m.group(2) or lo)


def draft_screen(slot: int, rnd: int, gone: int) -> str:
    """One screen for a live pick: tree step, QB verdict, commitments, boards."""
    br = tree(slot)
    label = br["label"]
    out = [f"=== ROUND {rnd} | slot {slot} ({label}) | {gone} QBs gone ==="]

    step = next((s for s in br["steps"]
                 if (_round_span(s["round"]) or (0, -1))[0] <= rnd <= (_round_span(s["round"]) or (0, -1))[1]), None)
    out.append(f"\nTREE  {step['round']}: {step['do']}" if step else "\nTREE  (no step covers this round)")

    out.append(f"\nQB    {qb_verdict(rnd, gone)}")

    lines = []
    for c in commitments_for(label):
        lo, hi = c["window"]
        if hi < rnd:
            lines.append(f"  !! OVERDUE  {c['pick']} (window was R{lo}-R{hi})")
        elif hi == rnd:
            lines.append(f"  >> DUE NOW  {c['pick']} (last round of window)")
        elif lo <= rnd:
            lines.append(f"  -  open     {c['pick']} (R{lo}-R{hi})")
    out.append("\nMUST-HAVES at this pick (skip any already rostered):")
    out.append("\n".join(lines) if lines else "  none in window")

    board_lines, cap_teams = [], set()
    for p in load("wr_board")["value_board"]:
        span = _round_span(p.get("round"))
        if span and span[0] <= rnd <= span[1]:
            tag = " [VALUE-ONLY]" if "not mandatory" in str(p.get("note", "")) else ""
            board_lines.append(f"  WR  {p['player']} ({p['team']}){tag}")
            cap_teams.add(p["team"])
    for p in load("rb_board")["targets"]:
        span = _round_span(p.get("round"))
        if span and span[0] <= rnd <= span[1]:
            board_lines.append(f"  RB  {p['player']} ({p['team']}) [value-if-available]")
            cap_teams.add(p["team"])
    if 4 <= rnd <= 5:
        board_lines.append("  TE  Tyler Warren (IND) - the call, R4-5")
        cap_teams.add("IND")
    if board_lines:
        out.append("\nBOARD names listed for this round:")
        out.append("\n".join(board_lines))

    cap = load("te_board")["stack_cap"]
    if cap["team"] in cap_teams:
        out.append(f"\nCAP   {cap['team']} max {cap['max_starters']} starters (bye W{cap['bye']}). "
                   "Count your Colts before this pick.")
    return "\n".join(out)


def sheet(slot: int) -> str:
    """Printable one-page plan for a slot's branch."""
    br = tree(slot)
    label = br["label"]
    cap = load("te_board")["stack_cap"]
    rule = load("qb_rule")
    ok, plan = satisfiable(commitments_for(label))

    out = [
        f"FF2026 DRAFT SHEET - {label} (slots {min(br['slots'])}-{max(br['slots'])})",
        "=" * 72,
        f"HARD RULES: QB2 by end of R{rule['hard_floor_round']}. "
        f"QB3 in R{rule['qb3_rounds'][0]}-{rule['qb3_rounds'][1]} (zero IR). "
        f"Max {cap['max_starters']} {cap['team']} starters (bye W{cap['bye']}).",
        "",
        "TREE",
    ]
    for s in br["steps"]:
        out.append(f"  {s['round']:<12} {s['do']}")
    out += ["", f"COMMITMENTS ({'satisfiable' if ok else 'NOT SATISFIABLE'})"]
    for c in sorted(commitments_for(label), key=lambda c: c["window"]):
        lo, hi = c["window"]
        out.append(f"  R{lo}-R{hi:<4} {c['pick']:<28} ({c['source']})")
    out += ["  One workable order: " + plan if ok else "  !! " + plan, "", "VALUE (take if they fall, never over a commitment)"]
    for p in load("wr_board")["value_board"]:
        flag = str(p.get("flag") or p.get("note") or "").split(".")[0]
        out.append(f"  R{p.get('round', '?'):<5} WR {p['player']:<22} {p['team']:<4} {flag}")
    for p in load("rb_board")["targets"]:
        out.append(f"  R{p.get('round') or '?':<5} RB {p['player']:<22} {p['team']:<4} {str(p['why']).split('.')[0][:60]}")
    out += ["", "FADES"]
    for p in load("rb_board")["fades"]:
        out.append(f"  {p['player']} ({p['team']}, {p.get('adp') or 'ADP n/a'}) - {str(p['why']).split('.')[0]}")
    out += ["", "TIEBREAK: " + str(rule["stack_tiebreak"]).strip(),
            "TIER GAP: " + str(rule["tier_beats_round"]).strip()]
    return "\n".join(out)
