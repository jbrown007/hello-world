#!/usr/bin/env python3
"""Automated integrity checks for the ff2026 framework.

Run first, before any manual review:

    cd ff2026 && python3 tests/verify.py

Exit code 0 means every structural check passed. It does NOT mean the football
analysis is correct - see HANDOFF.md for what still needs human eyes.
"""
from __future__ import annotations

import io
import subprocess
import sys
import traceback
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

NFL_TEAMS = {
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN", "DET",
    "GB", "HOU", "IND", "JAX", "KC", "LAC", "LAR", "LV", "MIA", "MIN", "NE",
    "NO", "NYG", "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WSH",
}

results: list[tuple[str, bool, str]] = []


def check(name):
    """Decorator that records pass/fail instead of raising."""
    def wrap(fn):
        try:
            detail = fn() or ""
            results.append((name, True, str(detail)))
        except AssertionError as e:
            results.append((name, False, str(e)))
        except Exception:
            results.append((name, False, traceback.format_exc(limit=2).strip().splitlines()[-1]))
        return fn
    return wrap


# --------------------------------------------------------------- data layer
@check("all YAML files parse")
def _():
    import yaml
    files = sorted((ROOT / "data").glob("*.yaml"))
    assert files, "no YAML files found in data/"
    for f in files:
        with f.open(encoding="utf-8") as fh:
            yaml.safe_load(fh)
    return f"{len(files)} files"


@check("league.yaml has every required key")
def _():
    from ffcli.config import league
    lg = league()
    for key in ("teams", "scoring", "superflex", "roster_size", "ir_slots",
                "starters", "draft", "waivers", "season", "payouts"):
        assert key in lg, f"missing top-level key: {key}"
    for key in ("regular_weeks", "playoff_start", "playoff_end"):
        assert key in lg["season"], f"missing season.{key}"
    return f"{lg['teams']} teams, superflex={lg['superflex']}, ir_slots={lg['ir_slots']}"


@check("byes.yaml covers all 32 NFL teams exactly once")
def _():
    from ffcli.config import byes
    seen: list[str] = []
    for teams in byes().values():
        seen += teams
    dupes = {t for t in seen if seen.count(t) > 1}
    assert not dupes, f"team on multiple byes: {sorted(dupes)}"
    missing = NFL_TEAMS - set(seen)
    unknown = set(seen) - NFL_TEAMS
    assert not missing, f"teams with no bye: {sorted(missing)}"
    assert not unknown, f"unrecognised abbreviations: {sorted(unknown)}"
    return f"{len(seen)} teams across {len(byes())} weeks"


@check("bye weeks fall in a plausible range")
def _():
    from ffcli.config import byes
    weeks = sorted(byes())
    assert min(weeks) >= 4, f"bye earlier than W4: {min(weeks)}"
    assert max(weeks) <= 14, f"bye later than W14: {max(weeks)}"
    return f"W{min(weeks)}-W{max(weeks)}, no byes in {sorted(set(range(min(weeks), max(weeks)+1)) - set(weeks))}"


@check("season settings are internally consistent")
def _():
    from ffcli.config import league, as_range
    s = league()["season"]
    reg = as_range(s["regular_weeks"])
    start = as_range(s["playoff_start"])
    end = as_range(s["playoff_end"])[0]
    for r in reg:
        for st in start:
            assert st > r, f"playoffs start W{st} but regular season runs {r} weeks - overlap"
            assert st <= end, f"playoff_start W{st} after playoff_end W{end}"
    return f"regular={reg}, playoff_start={start}, end=W{end}"


@check("watchlist rows have required fields")
def _():
    from ffcli.workbook import _load
    rows = _load("watchlist")
    assert rows, "watchlist is empty"
    required = ("priority", "pos", "team", "situation", "status", "confidence")
    for i, row in enumerate(rows, start=1):
        for k in required:
            assert k in row, f"row {i} missing '{k}'"
        assert str(row["status"]) in {"Resolved", "Trending", "Unsettled"}, \
            f"row {i} has unexpected status: {row['status']!r}"
    return f"{len(rows)} rows"


@check("screen covers exactly 32 teams, no duplicates")
def _():
    from ffcli.workbook import _load
    teams = _load("screen")
    names = [t["team"] for t in teams]
    assert len(names) == 32, f"expected 32 teams, found {len(names)}"
    dupes = {n for n in names if names.count(n) > 1}
    assert not dupes, f"duplicate teams: {sorted(dupes)}"
    return "32 teams"


@check("qb_rule thresholds are monotonic and ordered")
def _():
    from ffcli.config import load
    rule = load("qb_rule")
    for band in rule["rules"]:
        gone = [t["gone"] for t in band["thresholds"]]
        assert gone == sorted(gone, reverse=True), \
            f"round<={band['max_round']} thresholds not descending: {gone}"
        assert gone[-1] == 0, f"round<={band['max_round']} has no catch-all 0 threshold"
    rounds = [b["max_round"] for b in rule["rules"]]
    assert rounds == sorted(rounds), f"rule bands out of order: {rounds}"
    assert rule["hard_floor_round"] >= max(rounds), "hard floor is before the last rule band"
    return f"{len(rule['rules'])} bands, floor R{rule['hard_floor_round']}"


@check("draft trees cover every slot exactly once")
def _():
    from ffcli.config import load, league
    n = league()["teams"]
    covered: list[int] = []
    for branch in load("trees"):
        covered += branch["slots"]
    dupes = {s for s in covered if covered.count(s) > 1}
    assert not dupes, f"slots in multiple branches: {sorted(dupes)}"
    missing = set(range(1, n + 1)) - set(covered)
    assert not missing, f"slots with no branch: {sorted(missing)}"
    return f"slots 1-{n} across {len(load('trees'))} branches"


# --------------------------------------------------------------- logic layer
@check("QB count rule returns a verdict at every boundary")
def _():
    from ffcli.draft import qb_verdict
    from ffcli.config import load
    floor = load("qb_rule")["hard_floor_round"]
    for rnd in range(1, floor + 3):
        for gone in (0, 9, 10, 13, 14, 16, 24):
            v = qb_verdict(rnd, gone)
            assert v.action, f"no action for round={rnd} gone={gone}"
    past = qb_verdict(floor + 1, 0)
    assert past.action == "PAST_FLOOR", f"expected PAST_FLOOR past R{floor}, got {past.action}"
    return f"tested R1-R{floor+2}"


@check("QB rule escalates as more QBs leave the board")
def _():
    from ffcli.draft import qb_verdict
    urgency = {"WAIT": 0, "WAIT_TO_6": 0, "NORMAL": 1, "BY_ROUND_6": 2, "TAKE_QB2_NOW": 3}
    for rnd in (4, 5):
        seen = [urgency[qb_verdict(rnd, g).action] for g in (0, 11, 13, 15, 17, 20)]
        assert seen == sorted(seen), f"round {rnd} urgency not monotonic: {seen}"
    return "monotonic at R4 and R5"


@check("bye audit flags a known-bad roster")
def _():
    from ffcli.byecheck import audit
    res = audit(["IND", "NYJ", "LV", "BAL"], max_per_week=2)
    assert res["warnings"], "four teams on the same bye produced no warning"
    assert 13 in res["grouped"], "W13 grouping missing"
    assert len(res["grouped"][13]) == 4, "expected 4 teams grouped in W13"
    return f"{len(res['warnings'])} warnings, {res['scenarios']} scenarios"


@check("bye audit stays quiet on a clean roster")
def _():
    from ffcli.byecheck import audit
    res = audit(["KC", "CIN", "BUF"], max_per_week=2)
    stack = [w for w in res["warnings"] if "Cap is" in w]
    assert not stack, f"false stacking warning: {stack}"
    return "no false positives"


@check("bye audit rejects nothing silently")
def _():
    from ffcli.byecheck import audit
    res = audit(["IND", "NOTATEAM"], max_per_week=2)
    assert "NOTATEAM" in res["unknown"], "unrecognised team was swallowed"
    return "unknown teams surfaced"


@check("every draft slot returns a branch")
def _():
    from ffcli.draft import tree
    from ffcli.config import league
    for slot in range(1, league()["teams"] + 1):
        b = tree(slot)
        assert b["steps"], f"slot {slot} branch has no steps"
    return "all slots resolve"


@check("weekly sessions 1-4 all render")
def _():
    from ffcli.weekly import session
    for n in (1, 2, 3, 4):
        text = session(n)
        assert "Bring:" in text and "paste this" in text, f"session {n} template malformed"
    return "4 sessions"


# --------------------------------------------------------------- build layer
@check("workbook builds and contains expected tabs")
def _():
    import openpyxl
    from ffcli.workbook import build
    out = build(ROOT / "build" / "_verify.xlsx")
    wb = openpyxl.load_workbook(out)
    for tab in ("Start Here", "Watchlist", "RB Board", "WR Board", "TE Board", "Screen"):
        assert tab in wb.sheetnames, f"missing tab: {tab}"
    ws = wb["Watchlist"]
    assert ws.max_row > 1, "watchlist tab has no data rows"
    assert ws.freeze_panes == "A2", "watchlist header not frozen"
    return f"{wb.sheetnames}, {ws.max_row - 1} rows"


@check("workbook formulas are written as formulas")
def _():
    import openpyxl
    wb = openpyxl.load_workbook(ROOT / "build" / "_verify.xlsx")
    sh = wb["Start Here"]
    formulas = [
        sh.cell(r, c).value
        for r in range(1, 30) for c in range(1, 10)
        if isinstance(sh.cell(r, c).value, str) and sh.cell(r, c).value.startswith("=")
    ]
    assert formulas, "no formulas found - values may have been hardcoded"
    bad = [f for f in formulas if "Watchlist!" not in f]
    assert not bad, f"formulas not referencing Watchlist: {bad}"
    return f"{len(formulas)} formulas, all cross-referencing"


@check("board tabs are generated from the board YAML")
def _():
    """Regression: wr_board.yaml and te_board.yaml were orphaned - no code read
    them, so the workbook's board tabs could silently drift from the data."""
    import openpyxl
    from ffcli.config import load
    wb = openpyxl.load_workbook(ROOT / "build" / "_verify.xlsx")

    def text(sheet):
        return " | ".join(str(c.value) for row in wb[sheet].iter_rows() for c in row if c.value is not None)

    rb, wr, te = text("RB Board"), text("WR Board"), text("TE Board")
    for p in load("wr_board")["value_board"]:
        assert p["player"] in wr, f"WR Board tab missing {p['player']}"
    for path in load("te_board")["paths"]:
        assert path["name"] in te, f"TE Board tab missing path: {path['name']}"
    for p in load("rb_board")["targets"] + load("rb_board")["fades"]:
        assert p["player"] in rb, f"RB Board tab missing {p['player']}"
    assert "provenance" in rb.lower(), "RB Board missing provenance warning (synthesized data)"
    for sheet, board in (("WR Board", "wr_board"), ("TE Board", "te_board")):
        cap = load(board)["stack_cap"]
        assert f"max {cap['max_starters']} starters" in text(sheet), f"{sheet} missing stack cap"
    n_rb = len(load("rb_board")["targets"]) + len(load("rb_board")["fades"])
    return f"{n_rb} RBs, {len(load('wr_board')['value_board'])} WRs, {len(load('te_board')['paths'])} TE paths"


@check("CLI commands all exit cleanly")
def _():
    from ffcli.cli import main
    cases = [
        ["settings"], ["confirm"], ["qb", "--round", "4", "--gone", "15"],
        ["tree", "--slot", "1"], ["tree", "--slot", "12"],
        ["draft", "--round", "6", "--gone", "16", "--slot", "7"],
        ["sheet", "--slot", "1"], ["sheet", "--slot", "7"], ["sheet", "--slot", "12"],
        ["bye", "IND", "NYJ"], ["weekly", "1"], ["weekly", "4"],
    ]
    for argv in cases:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(argv)
        assert code == 0, f"`ff {' '.join(argv)}` exited {code}"
        assert buf.getvalue().strip(), f"`ff {' '.join(argv)}` printed nothing"
    return f"{len(cases)} commands"


@check("package imports with no side effects")
def _():
    out = subprocess.run(
        [sys.executable, "-c", "import ffcli, ffcli.cli, ffcli.draft, ffcli.byecheck, ffcli.workbook, ffcli.weekly"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr.strip().splitlines()[-1] if out.stderr else "import failed"
    assert not out.stdout.strip(), f"import printed to stdout: {out.stdout!r}"
    return "clean import"


# --------------------------------------------------------------- consistency
@check("watchlist teams resolve to real bye weeks")
def _():
    from ffcli.workbook import _load
    from ffcli.config import bye_of
    NAME = {
        "Titans": "TEN", "Buccaneers": "TB", "Saints": "NO", "Colts": "IND",
        "Jets": "NYJ", "Raiders": "LV", "Cardinals": "ARI", "Commanders": "WSH",
        "Broncos": "DEN", "Patriots": "NE", "49ers": "SF", "Dolphins": "MIA",
        "Browns": "CLE", "Chargers": "LAC", "Vikings": "MIN", "Seahawks": "SEA",
    }
    unmapped = []
    for row in _load("watchlist"):
        team = str(row.get("team", "")).strip()
        ab = NAME.get(team)
        if ab is None:
            unmapped.append(team)
            continue
        assert bye_of(ab), f"{team} ({ab}) has no bye week"
    return f"unmapped (expected for multi-team rows): {sorted(set(unmapped))}" if unmapped else "all mapped"


@check("no watchlist row claims a bye that contradicts byes.yaml")
def _():
    from ffcli.workbook import _load
    from ffcli.config import bye_of
    NAME = {
        "Titans": "TEN", "Buccaneers": "TB", "Saints": "NO", "Colts": "IND",
        "Jets": "NYJ", "Raiders": "LV", "Cardinals": "ARI", "Commanders": "WSH",
        "Broncos": "DEN", "Patriots": "NE", "49ers": "SF", "Dolphins": "MIA",
        "Browns": "CLE", "Chargers": "LAC", "Vikings": "MIN", "Seahawks": "SEA",
    }
    bad = []
    for row in _load("watchlist"):
        ab = NAME.get(str(row.get("team", "")).strip())
        stated = row.get("bye")
        if ab and isinstance(stated, int) and bye_of(ab) != stated:
            bad.append(f"{row['team']}: row says W{stated}, byes.yaml says W{bye_of(ab)}")
    assert not bad, "; ".join(bad)
    return "watchlist byes agree with byes.yaml"


@check("unconfirmed settings are reported, not silently defaulted")
def _():
    from ffcli.config import unconfirmed, league, as_range
    pending = unconfirmed()
    s = league()["season"]
    for key in ("regular_weeks", "playoff_start"):
        if len(as_range(s[key])) > 1:
            assert key in pending, f"{key} is a range but not reported by unconfirmed()"
    return f"pending: {sorted(pending) or 'none'}"


@check("round-plan commitments are satisfiable in every branch")
def _():
    """Regression: the boards once committed seven picks to six rounds (audit
    2a) and nothing noticed. Commitments are now data; this proves each
    branch's full set fits one-pick-per-round."""
    from ffcli.draft import commitments_for, satisfiable
    from ffcli.config import load
    details = []
    for label in load("commitments")["branches"]:
        items = commitments_for(label)
        for c in items:
            lo, hi = c["window"]
            assert 1 <= lo <= hi <= 15, f"{label}: bad window {c['window']} for {c['pick']}"
        ok, detail = satisfiable(items)
        assert ok, f"{label}: {detail}"
        details.append(f"{label}={len(items)}")
    assert details, "no branches in commitments.yaml"
    return ", ".join(details) + " commitments, all schedulable"


@check("stack caps agree across boards")
def _():
    """Regression: the IND cap lived only on the TE board while the WR board
    steered into four Colts (audit 2c). Both boards carry it; they must match."""
    from ffcli.config import load
    wr, te = load("wr_board")["stack_cap"], load("te_board")["stack_cap"]
    for k in ("team", "bye", "max_starters"):
        assert wr[k] == te[k], f"stack_cap.{k} differs: wr={wr[k]!r} te={te[k]!r}"
    return f"{wr['team']} max {wr['max_starters']}, bye W{wr['bye']}, both boards"


@check("QB rule urgency never dips between a trigger round and the floor")
def _():
    """Regression: rnd == hard_floor_round fell past every threshold band and
    returned NORMAL, so Round 6 gave no urgency at any QB count."""
    from ffcli.draft import qb_verdict
    from ffcli.config import load
    floor = load("qb_rule")["hard_floor_round"]
    for gone in (0, 10, 14, 16, 20, 24):
        v = qb_verdict(floor, gone).action
        assert v != "NORMAL", f"R{floor} gone={gone} returned NORMAL at the hard floor"
    hot = [r for r in range(1, floor + 2) if qb_verdict(r, 24).action == "NORMAL"]
    assert not hot, f"NORMAL at max QB count in rounds {hot}"
    return f"floor R{floor} triggers at every count"


@check("dashboard counts every status value present in the data")
def _():
    """Regression: Status has three values but the dashboard only counted two,
    hiding every Trending row from the At a Glance totals."""
    from ffcli.config import load
    import ffcli.workbook as wbmod, inspect
    used = {s for s in ("Unsettled", "Trending", "Resolved")
            if f'"{s}"' in inspect.getsource(wbmod._start_here)}
    present = {r.get("status") for r in load("watchlist") if r.get("status")}
    missing = present - used
    assert not missing, f"status values in data but not counted on dashboard: {sorted(missing)}"
    return f"{len(present)} status values, all counted"


# --------------------------------------------------------------- report
def report() -> int:
    width = max(len(n) for n, _, _ in results) + 2
    passed = sum(1 for _, ok, _ in results if ok)
    print("=" * (width + 40))
    print("ff2026 verification")
    print("=" * (width + 40))
    for name, ok, detail in results:
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name:<{width}} {detail}")
    print("-" * (width + 40))
    print(f"{passed}/{len(results)} checks passed")
    if passed != len(results):
        print("\nStructural failures above. Fix before manual review.")
        return 1
    print("\nStructure is sound. This does NOT validate the football analysis -")
    print("see HANDOFF.md for what still needs human verification.")
    return 0


if __name__ == "__main__":
    sys.exit(report())
