"""ff - fantasy football command line toolkit."""
from __future__ import annotations
import argparse
import signal
import sys

# Let `ff weekly 1 | head` exit quietly instead of raising BrokenPipeError.
try:
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (AttributeError, ValueError):  # Windows / non-main thread
    pass
from . import __version__
from .config import league, byes, bye_of, unconfirmed, as_range
from .draft import qb_verdict, rb_verdict, tree, draft_screen, sheet, grade, parse_picks, room_report
from .byecheck import audit
from .weekly import session
from .workbook import build


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="ff", description="2026 fantasy football toolkit")
    p.add_argument("--version", action="version", version=f"ff {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("settings", help="print league settings")
    sub.add_parser("confirm", help="show unconfirmed settings and what each one changes")

    b = sub.add_parser("build", help="regenerate the Excel workbook from data/")
    b.add_argument("-o", "--out", default=None)

    q = sub.add_parser("qb", help="apply the superflex QB count rule")
    q.add_argument("--round", type=int, required=True)
    q.add_argument("--gone", type=int, required=True, help="QBs already off the board")
    q.add_argument("--window", type=int, default=None,
                   help="QBs taken in the last 12 picks; 3+ fires the run trigger")

    rb = sub.add_parser("rb", help="apply the RB floor rule")
    rb.add_argument("--round", type=int, required=True)
    rb.add_argument("--held", type=int, required=True, help="RBs currently on your roster")

    t = sub.add_parser("tree", help="print the draft branch for your slot")
    t.add_argument("--slot", type=int, default=None)

    rm = sub.add_parser("room", help="manager profiles; with --slot, who picks around you")
    rm.add_argument("--slot", type=int, default=None)

    d = sub.add_parser("draft", help="live pick screen: tree + QB rule + commitments + board, one view")
    d.add_argument("--round", type=int, required=True)
    d.add_argument("--gone", type=int, required=True, help="QBs already off the board")
    d.add_argument("--slot", type=int, default=None)

    s = sub.add_parser("sheet", help="printable one-page draft plan for a slot")
    s.add_argument("--slot", type=int, default=None)
    s.add_argument("--all", action="store_true", help="write every branch to build/sheet_*.txt")

    g = sub.add_parser("grade", help="score a drafted roster against the plan's commitments")
    g.add_argument("file", help="picks file: one 'ROUND POS TEAM Player Name' per line")
    g.add_argument("--slot", type=int, default=None)
    g.add_argument("--oneqb", action="store_true",
                   help="1-QB practice room: QB commitments become observation-only")

    y = sub.add_parser("bye", help="audit bye weeks for a set of teams")
    y.add_argument("teams", nargs="+", help="team abbreviations, e.g. IND NYJ LV")
    y.add_argument("--max", type=int, default=2, help="max starters allowed on one bye")

    w = sub.add_parser("weekly", help="print an in-season session template")
    w.add_argument("n", type=int, choices=[1, 2, 3, 4])

    a = p.parse_args(argv)

    if a.cmd == "settings":
        lg = league()
        for k, v in lg.items():
            print(f"{k}: {v}")

    elif a.cmd == "build":
        out = build(a.out)
        print(f"built: {out}")
        print("NOTE: formulas have no cached values until Excel or LibreOffice opens the file.")

    elif a.cmd == "qb":
        print(qb_verdict(a.round, a.gone, a.window))

    elif a.cmd == "rb":
        print(rb_verdict(a.round, a.held))

    elif a.cmd == "room":
        print(room_report(a.slot or league()["draft"].get("slot")))

    elif a.cmd == "tree":
        slot = a.slot or league()["draft"].get("slot")
        if not slot:
            print("No slot set. Pass --slot N or set draft.slot in data/league.yaml.")
            return 1
        br = tree(slot)
        print(f"SLOT {slot} - {br['label']} (covers {br['slots']})\n")
        for s in br["steps"]:
            print(f"  {s['round']:<12} {s['do']}")

    elif a.cmd == "draft":
        slot = a.slot or league()["draft"].get("slot")
        if not slot:
            print("No slot set. Pass --slot N or set draft.slot in data/league.yaml.")
            return 1
        print(draft_screen(slot, a.round, a.gone))

    elif a.cmd == "sheet":
        if a.all:
            from .config import ROOT
            from .draft import tree as _tree
            outdir = ROOT / "build"
            outdir.mkdir(parents=True, exist_ok=True)
            done = set()
            for slot in range(1, league()["teams"] + 1):
                label = _tree(slot)["label"]
                if label in done:
                    continue
                done.add(label)
                path = outdir / f"sheet_{label}.txt"
                path.write_text(sheet(slot) + "\n", encoding="utf-8")
                print(f"wrote: {path}")
        else:
            slot = a.slot or league()["draft"].get("slot")
            if not slot:
                print("No slot set. Pass --slot N, --all, or set draft.slot in data/league.yaml.")
                return 1
            print(sheet(slot))

    elif a.cmd == "grade":
        slot = a.slot or league()["draft"].get("slot")
        if not slot:
            print("No slot set. Pass --slot N or set draft.slot in data/league.yaml.")
            return 1
        import pathlib
        picks = parse_picks(pathlib.Path(a.file).read_text(encoding="utf-8"))
        print(grade(picks, tree(slot)["label"], oneqb=a.oneqb))

    elif a.cmd == "confirm":
        pend = league()["season"]["playoff_end"]
        miss = unconfirmed()
        if not miss:
            print("All season settings confirmed.")
            return 0
        print(f"{len(miss)} setting(s) unconfirmed. Warnings stay CONDITIONAL until fixed.\n")
        impact = {
            "regular_weeks":
                "Sets the seeding week - the last regular-season week, which decides the\n"
                "     top-two first-round bye.\n"
                "       12 -> W12 has NO byes league-wide. Seeding week is completely clean.\n"
                "       13 -> BAL, NYJ, IND, LV are out in the week that decides your bye.",
            "playoff_start":
                f"Sets the playoff window (through W{pend}). Byes end in W14, so:\n"
                "       14 -> DAL and ARI are dark in your first playoff game. Fade both.\n"
                "       15 -> zero bye conflicts anywhere in your playoffs. Nothing to avoid.",
        }
        for k, vals in miss.items():
            print(f"  {k}: currently {vals}")
            print(f"     {impact.get(k, 'No modelled impact.')}\n")
        print("Fix in data/league.yaml, then rerun `ff bye ...`.")


    elif a.cmd == "bye":
        res = audit(a.teams, a.max)
        for wk, names in res["grouped"].items():
            print(f"  W{wk:<3} {', '.join(names)}")
        if res["unknown"]:
            print(f"  ??   unknown: {', '.join(res['unknown'])}")
        if res["warnings"]:
            print("\nWARNINGS")
            for x in res["warnings"]:
                print(f"  ! {x}")
        else:
            print("\nNo conflicts.")
        if res["scenarios"] > 1:
            print(f"\n({res['scenarios']} scenarios modelled - run `ff confirm` to narrow them.)")

    elif a.cmd == "weekly":
        print(session(a.n))

    return 0


if __name__ == "__main__":
    sys.exit(main())
