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


def parse_picks(text: str) -> list[dict]:
    """Parse a picks file: one pick per line, 'ROUND POS TEAM Player Name'."""
    picks = []
    for ln, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 4:
            raise ValueError(f"line {ln}: expected 'ROUND POS TEAM Player Name', got {line!r}")
        picks.append({"round": int(parts[0]), "pos": parts[1].upper(),
                      "team": parts[2].upper(), "player": " ".join(parts[3:])})
    return picks


def grade(picks: list[dict], label: str, oneqb: bool = False) -> str:
    """Score a drafted roster against the branch's commitments.

    oneqb demotes QB commitments to observation-only - the superflex QB
    urgency does not apply in a standard 1-QB practice room.
    """
    from .byecheck import audit

    items = sorted(commitments_for(label), key=lambda c: (c["window"][1], c["window"][0]))
    used: set[int] = set()
    lines, hits, graded = [], 0, 0
    for c in items:
        pos = c["pick"][:2].upper()
        head = c["pick"].split("(")[0].strip()
        name_req = head[2:].lstrip("0123456789").strip()  # 'TE Tyler Warren' -> 'Tyler Warren'
        lo, hi = c["window"]
        is_obs = oneqb and pos == "QB"

        match = next((i for i, p in enumerate(picks)
                      if i not in used and p["pos"] == pos and lo <= p["round"] <= hi
                      and (not name_req or name_req.split()[-1].lower() in p["player"].lower())),
                     None)
        near = None if match is not None or not name_req else next(
            (i for i, p in enumerate(picks)
             if i not in used and p["pos"] == pos and lo <= p["round"] <= hi), None)

        win = f"R{lo}-R{hi}"
        if match is not None:
            used.add(match)
            p = picks[match]
            tag = "OBS " if is_obs else "HIT "
            lines.append(f"  {tag}  {win:<8} {c['pick']:<28} -> R{p['round']} {p['player']}")
        elif near is not None:
            used.add(near)
            p = picks[near]
            tag = "OBS " if is_obs else "NEAR"
            lines.append(f"  {tag}  {win:<8} {c['pick']:<28} R{p['round']} {pos} was {p['player']} - plan called {name_req}")
        else:
            tag = "OBS " if is_obs else "MISS"
            lines.append(f"  {tag}  {win:<8} {c['pick']:<28} no matching pick in window")
        if not is_obs:
            graded += 1
            hits += match is not None

    out = [f"GRADE - {label} branch, {len(picks)} picks", "", "COMMITMENTS"]
    out += lines
    obs_n = sum(1 for c in items if oneqb and c["pick"][:2].upper() == "QB")
    out.append(f"\nSCORE {hits}/{graded} commitments hit"
               + (f" ({obs_n} QB items observation-only, 1-QB room)" if obs_n else ""))

    cap = load("te_board")["stack_cap"]
    n_cap = sum(1 for p in picks if p["team"] == cap["team"])
    verdict = "BREACH - over the cap" if n_cap > cap["max_starters"] else "ok"
    out.append(f"STACK CAP {cap['team']} (bye W{cap['bye']}): {n_cap} drafted vs cap {cap['max_starters']} - {verdict}")

    # Full team list WITH duplicates - three Cardinals are three players out,
    # not one. audit() counts occurrences.
    res = audit([p["team"] for p in picks], max_per_week=cap["max_starters"])
    out.append("\nBYES")
    for wk, names in sorted(res["grouped"].items()):
        out.append(f"  W{wk:<3} {', '.join(names)}")
    if res["unknown"]:
        out.append(f"  ??   unknown teams: {', '.join(res['unknown'])}")
    for w in res["warnings"]:
        out.append(f"  ! {w}")
    return "\n".join(out)


def _bye(team: str) -> str:
    from .config import bye_of
    wk = bye_of(team)
    return f"bye W{wk}" if wk else "bye ?"


def _targets_at(rnd: int) -> list[str]:
    """Board names in play at a round, each with team and bye."""
    names = []
    for p in load("wr_board")["value_board"]:
        span = _round_span(p.get("round"))
        if span and span[0] <= rnd <= span[1]:
            tag = " VALUE-ONLY, never over a commitment" if "not mandatory" in str(p.get("note", "")) else ""
            flag = f" [{p['flag']}]" if p.get("flag") else ""
            names.append(f"WR {p['player']} ({p['team']}, {_bye(p['team'])}){flag}{tag}")
    for p in load("rb_board")["targets"]:
        span = _round_span(p.get("round"))
        if span and span[0] <= rnd <= span[1]:
            names.append(f"RB {p['player']} ({p['team']}, {_bye(p['team'])}) value-if-available")
    if 4 <= rnd <= 5:
        names.append(f"TE Tyler Warren (IND, {_bye('IND')}) THE CALL")
    return names


def _bye_danger_lines() -> list[str]:
    """The bye weeks that can sink the season, computed from live settings."""
    from .config import byes, league, as_range
    b = byes()
    season = league()["season"]
    out = []
    worst = max(b.items(), key=lambda kv: len(kv[1]))
    out.append(f"W{worst[0]} six-team bye: {', '.join(worst[1])}")
    for w in as_range(season["regular_weeks"]):
        if b.get(w):
            out.append(f"W{w} SEEDING WEEK candidate: {', '.join(b[w])} out - decides the first-round bye")
    for w in sorted(b):
        if any(st <= w <= season["playoff_end"] for st in as_range(season["playoff_start"])):
            out.append(f"W{w} PLAYOFF candidate: {', '.join(b[w])} dark in a possible playoff game - never 2+, never a QB")
    return out


def sheet(slot: int) -> str:
    """Self-sufficient printable draft script for a slot's branch.

    Designed to be used alone under a pick clock: byes inline on every name,
    a tally grid to mark before confirming each pick, and the commitments
    merged into a single R1-R15 walk - no cross-referencing.
    """
    from .config import byes
    br = tree(slot)
    label = br["label"]
    cap = load("te_board")["stack_cap"]
    rule = load("qb_rule")
    commits = commitments_for(label)
    ok, plan = satisfiable(commits)

    out = [
        f"FF2026 DRAFT SHEET - {label} (slots {min(br['slots'])}-{max(br['slots'])})",
        "=" * 78,
        f"HARD RULES: QB2 by end of R{rule['hard_floor_round']}. "
        f"QB3 in R{rule['qb3_rounds'][0]}-{rule['qb3_rounds'][1]} (zero IR). "
        f"Max {cap['max_starters']} {cap['team']} starters ({cap['team']} {_bye(cap['team'])}).",
        "",
        "BYE TALLY - write every pick's bye here BEFORE confirming it. Cap 2 per week.",
        "  " + "   ".join(f"W{w} [ ][ ]" for w in sorted(byes())),
        "DANGER WEEKS:",
    ]
    out += [f"  ! {line}" for line in _bye_danger_lines()]

    out += ["", "ROUND SCRIPT", "-" * 78]
    steps = [(s, _round_span(s["round"])) for s in br["steps"]]
    for rnd in range(1, 16):
        step = next((s for s, span in steps if span and span[0] == rnd), None)
        body = []
        if step:
            body.append(f"PLAN {step['round']}: {step['do']}")
        if rnd == 1:
            body.append(f"PIVOT: {load('wr_board')['round_plan'][1]}")
        for c in commits:
            lo, hi = c["window"]
            if hi == rnd:
                body.append(f"MUST by end of this round: {c['pick']}")
            elif lo == rnd and lo != hi:
                body.append(f"window opens: {c['pick']} (R{lo}-R{hi})")
        for t in _targets_at(rnd):
            body.append(f"target: {t}")
        if not body:
            body.append("free pick - best value, check the bye tally first")
        out.append(f"  R{rnd:<3} " + body[0])
        out += [f"       {b}" for b in body[1:]]
    out += ["", f"COMMITMENT ORDER ({'satisfiable' if ok else 'NOT SATISFIABLE'}): {plan}"]

    out += ["", "FADES - let someone else pay"]
    for p in load("rb_board")["fades"]:
        out.append(f"  {p['player']} ({p['team']}, {p.get('adp') or 'ADP n/a'}) - {str(p['why']).split('. ')[0]}")
    out += ["", "TIEBREAK: " + str(rule["stack_tiebreak"]).strip(),
            "TIER GAP: " + str(rule["tier_beats_round"]).strip()]
    return "\n".join(out)
