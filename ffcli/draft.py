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


def qb_verdict(rnd: int, gone: int, window: int | None = None) -> Verdict:
    """Apply the superflex QB count rule for a given round and QB count.

    window: QBs taken in the last 12 picks. The rate trigger (3+ in 12)
    overrides the count thresholds - this room's 2025 board sat at 8 gone for
    14 straight picks and then moved to 14 in twelve. Level cannot catch that.
    """
    rule = load("qb_rule")
    floor = rule["hard_floor_round"]

    trig = rule.get("run_trigger", {})
    if window is not None and rnd <= floor and window >= trig.get("qbs", 3):
        return Verdict(
            "TAKE_QB2_NOW",
            f"RUN DETECTED: {window} QBs inside the last {trig.get('window_picks', 12)} picks.",
            "The run has started. Take QB2 on this pick regardless of round or count. "
            "Rate overrides level.",
        )

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


def rb_verdict(rnd: int, held: int) -> Verdict:
    """Apply the RB floor rule (NEW 8/1). Mirrors the QB count rule - the 2025
    failure (first RB at pick 65 feeding three starting slots) had no rule to
    stop it."""
    gates = load("rb_rule")["rb_floor"]
    for g in gates:
        if rnd >= g["by_end_of_round"] and held < g["min_held"]:
            return Verdict(
                g["verdict_if_short"],
                f"{held} RB held at R{rnd}; floor is {g['min_held']} by end of R{g['by_end_of_round']}.",
                " ".join(str(g["note"]).split()),
            )
    nxt = next((g for g in gates if g["by_end_of_round"] >= rnd), None)
    detail = (f"Next gate: {nxt['min_held']} by end of R{nxt['by_end_of_round']}."
              if nxt else "All RB gates passed.")
    return Verdict("ON_TRACK", f"{held} RB held at R{rnd}.", detail)


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


def satisfiable(items: list[dict], rounds: int = 17) -> tuple[bool, str]:
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

    for cap in load("stack_caps"):
        if cap["team"] in cap_teams:
            out.append(f"\nCAP   {cap['team']} max {cap['max_starters']} starters (bye W{cap['bye']}). "
                       "Count before this pick - the Dec 4 deadline sits inside W13, no trading out later.")
    return "\n".join(out)


def room_report(slot: int | None = None) -> str:
    """The room model: manager profiles, and with a slot, who picks around you.

    Snake math for 12 teams: after your odd-round pick at slot s, every slot
    ABOVE s picks twice before you pick again; after an even-round pick, every
    slot BELOW s does. The double-pickers alternate sides each turn - that is
    who can snipe your queue.
    """
    room = load("room")
    n = league()["teams"]
    filled = [m for m in room["managers"] if not str(m["name"]).startswith("TBD")]
    out = [f"ROOM MODEL - {len(filled)}/{len(room['managers'])} managers profiled"]

    for m in room["managers"]:
        if str(m["name"]).startswith("TBD"):
            continue
        bits = [f"QB: {m['qb_habit']}", f"attention: {m['attention']}", f"trades: {m['trades']}"]
        if m.get("leans"):
            bits.append(f"leans: {m['leans']}")
        s26 = f" [slot {m['slot_2026']}]" if m.get("slot_2026") else ""
        out.append(f"  {m['name']}{s26}: " + " | ".join(bits))
        if m.get("notes"):
            out.append(f"      {m['notes']}")
    if not filled:
        out.append("  (all TBD - dump your read on each manager and Claude will fill this in)")

    lg = room["league"]
    out += ["", "LEAGUE READS"]
    out.append(f"  Sharpest: {', '.join(lg['sharpest']) or 'TBD'}")
    out.append(f"  2025 QB run: {' '.join(str(lg['qb_run_2025']).split())}")
    for p in lg["patterns"]:
        out.append(f"  Pattern: {p}")

    if slot:
        gap_after_odd = 2 * (n - slot)
        gap_after_even = 2 * (slot - 1)
        out += ["", f"SLOT {slot} GEOMETRY (snake, {n} teams)"]
        out.append(f"  After your ODD-round pick: {gap_after_odd} picks pass - slots {slot + 1}-{n} go twice."
                   if slot < n else "  After your ODD-round pick: you pick again immediately (the turn).")
        out.append(f"  After your EVEN-round pick: {gap_after_even} picks pass - slots 1-{slot - 1} go twice."
                   if slot > 1 else "  After your EVEN-round pick: you pick again immediately (the turn).")
        out.append(f"  R5/R6 turn: picks {4 * n + slot} and {6 * n + 1 - slot} - "
                   f"{2 * (n - slot)} picks apart. The 2025 QB run fired at picks 62-72.")
        by_slot = {m.get("slot_2026"): m for m in room["managers"] if m.get("slot_2026")}
        if by_slot:
            for s26 in (slot - 1, slot + 1):
                if s26 in by_slot:
                    m = by_slot[s26]
                    out.append(f"  Neighbor slot {s26}: {m['name']} (QB: {m['qb_habit']} - {m.get('leans', '')})")
            hoarders_above = [m["name"] for s, m in by_slot.items() if s > slot and m["qb_habit"] == "early_hoarder"]
            hoarders_below = [m["name"] for s, m in by_slot.items() if s < slot and m["qb_habit"] == "early_hoarder"]
            out.append(f"  QB hoarders who double-pick after your odd rounds: {', '.join(hoarders_above) or 'none known'}")
            out.append(f"  QB hoarders who double-pick after your even rounds: {', '.join(hoarders_below) or 'none known'}")
        else:
            out.append("  Fill slot_2026 fields on draft morning for neighbor analysis.")
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
        head = c["pick"].split("(")[0].strip().split()
        pos = "".join(ch for ch in head[0] if ch.isalpha()).upper()  # QB1->QB, DST->DST, K->K
        name_req = " ".join(head[1:])  # 'TE Tyler Warren' -> 'Tyler Warren'
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

    for cap in load("stack_caps"):
        n_cap = sum(1 for p in picks if p["team"] == cap["team"])
        verdict = "BREACH - over the cap" if n_cap > cap["max_starters"] else "ok"
        out.append(f"STACK CAP {cap['team']} (bye W{cap['bye']}): {n_cap} drafted vs cap {cap['max_starters']} - {verdict}")

    from .config import bye_of
    qb_byes: dict[int, list[str]] = {}
    for p in picks:
        if p["pos"] == "QB" and bye_of(p["team"]):
            qb_byes.setdefault(bye_of(p["team"]), []).append(p["player"])
    shared = {w: names for w, names in qb_byes.items() if len(names) > 1}
    if shared:
        for w, names in shared.items():
            out.append(f"QB TRIANGULATION FAIL: {' + '.join(names)} share bye W{w} - "
                       "QB1/QB2/QB3 must hold three different byes.")
    elif len(qb_byes) >= 2:
        out.append(f"QB triangulation ok: byes {', '.join(f'W{w}' for w in sorted(qb_byes))}.")

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
            out.append(f"W{w} SEEDING WEEK: {', '.join(b[w])} out in the week that decides the "
                       "first-round bye - never 2+, never a QB")
    for w in sorted(b):
        if any(st <= w <= season["playoff_end"] for st in as_range(season["playoff_start"])):
            out.append(f"W{w} PLAYOFF week: {', '.join(b[w])} dark in a playoff game")
    for cap in load("stack_caps"):
        out.append(f"W{cap['bye']} stack cap: {cap['team']} max {cap['max_starters']} - "
                   f"{' '.join(str(cap['resolved_note']).split())}")
    out.append("QB BYE TRIANGULATION: QB1, QB2, QB3 must hold three DIFFERENT bye weeks.")
    return out


def _qb_trigger_rows(rule: dict) -> list[tuple[int, int, str]]:
    """(round, gone, action) for every non-zero threshold in the count rule."""
    return [(band["max_round"], t["gone"], t["action"])
            for band in rule["rules"] for t in band["thresholds"] if t["gone"] > 0]


def _qb_triggers(rule: dict) -> set[int]:
    return {gone for _, gone, _ in _qb_trigger_rows(rule)}


def sheet(slot: int) -> str:
    """Self-sufficient printable draft script for a slot's branch.

    Designed to be used alone under a pick clock: byes inline on every name,
    a tally grid to mark before confirming each pick, and the commitments
    merged into a single R1-R15 walk - no cross-referencing.
    """
    from .config import byes
    br = tree(slot)
    label = br["label"]
    cap = load("stack_caps")[0]
    rule = load("qb_rule")
    commits = commitments_for(label)
    ok, plan = satisfiable(commits)

    out = [
        f"FF2026 DRAFT SHEET - {label} (slots {min(br['slots'])}-{max(br['slots'])})",
        "=" * 78,
        f"HARD RULES: RB floor 2 by R4 / 3 by R8 / 5 by R12. "
        f"QB2 in R{rule['qb2_earliest_round']}-{rule['hard_floor_round']} only. "
        f"QB3 in R{rule['qb3_rounds'][0]}-{rule['qb3_rounds'][1]}. "
        f"Max {cap['max_starters']} {cap['team']} starters ({cap['team']} {_bye(cap['team'])}). "
        "K + DST in R16-17, never earlier, no backups.",
        f"RUN TRIGGER: {rule['run_trigger']['qbs']}+ QBs inside any "
        f"{rule['run_trigger']['window_picks']} picks = the run started -> take QB2 NEXT pick, "
        "overrides everything. Use the QB tally to see it live.",
        "PERSONAL STARS (2025 lesson - each must survive camp verification): "
        + "; ".join(f"{s['pos']} {s['player']} ({s['team']}, {_bye(s['team'])})"
                    for s in load("lessons")["stars"]),
        "",
        "BYE TALLY - write every pick's bye here BEFORE confirming it. Cap 2 per week.",
        "  " + "   ".join(f"W{w} [ ][ ]" for w in sorted(byes())),
        "",
        "QB COUNT TALLY - tick every QB taken by ANYONE in the room. ! marks fire the rule:",
        "  " + " ".join(f"{n}[{'!' if n in _qb_triggers(rule) else ' '}]" for n in range(1, 25)),
    ] + [f"  ! at {gone} gone by your R{rnd} pick -> {action}"
         for rnd, gone, action in sorted(_qb_trigger_rows(rule))] + [
        f"  Floor: QB2 in hand by end of R{rule['hard_floor_round']} at ANY count. No exceptions.",
        "",
        "DANGER WEEKS:",
    ]
    out += [f"  ! {line}" for line in _bye_danger_lines()]

    out += ["", "QB1 BRANCH MAP - which fires depends on the board at your pick, not your slot",
            "  (elite = top-6 arm; six were gone by pick 23 in 2025, all rushing/elite-volume)"]
    for b in load("commitments")["branch_map"]:
        out.append(f"  {b['id']}: {b['fires']}")
        out.append(f"     {b['map']}")

    out += ["", "ROUND SCRIPT", "-" * 78]
    steps = [(s, _round_span(s["round"])) for s in br["steps"]]
    rb_gates = {g["by_end_of_round"]: g for g in load("rb_rule")["rb_floor"]}
    for rnd in range(1, 18):
        step = next((s for s, span in steps if span and span[0] == rnd), None)
        body = []
        if step:
            body.append(f"PLAN {step['round']}: {step['do']}")
        if rnd in rb_gates:
            g = rb_gates[rnd]
            body.append(f"RB FLOOR GATE: {g['min_held']} RBs in hand by the END of this round "
                        f"or next pick is {g['verdict_if_short']}.")
        if rnd == 5:
            body.append("WARREN GATE: below 2 RBs arriving here -> RB wins, Warren released, "
                        "backfill TE R7-8. NO TE2 ever (FLEX excludes TE).")
        if rnd == 8:
            body.append(f"DEPTH LEDGER: {' '.join(str(load('commitments')['depth_fill']).split())}")
        if rnd == 14:
            body.append(f"JOSH RULE: {' '.join(str(load('lessons')['draft']['qb4_dart']).split())}")
        if rnd == 16:
            body.append(f"JOSH RULE: {' '.join(str(load('lessons')['draft']['kicker']).split())}")
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
