# Road to Sept 7 — Draft Prep Timeline

The framework is code-complete. Everything left is information that resolves
on a schedule. This file is the sequence; the daily camp-watch Routine works
through it automatically and opens PRs when something changes.

## Hard dates

### Now → July 29: camps open
- Colts and Vikings camps open **7/29**. The two highest-value open questions
  start resolving: Daniel Jones full-contact team reps (flips his row back to
  Resolved) and Kyler Murray vs J.J. McCarthy (the superflex QB1 / Jefferson
  stack decision).
- 7 watchlist rows are Trending/Unsettled. Each row's `watch_for` field is the
  exact trigger the camp watch searches for.

### August 1: confirm league settings
- Check the ESPN league settings and pin `regular_weeks` (12 or 13) and
  `playoff_start` (14 or 15) in `data/league.yaml` — replace each list with a
  single number.
- Then `ff confirm` reports clean and every CONDITIONAL bye warning sharpens
  to CERTAIN (or disappears). If `regular_weeks` is 13, the IND/BAL/NYJ/LV
  W13 bye lands in the seeding week — the stack cap becomes non-negotiable.

### ~August 13: preseason games begin
- Snap share, target share, and first-team reps become real data. Trending
  rows should start flipping. Treat beat-writer camp hype with the audit's
  rule: two independent sources for any status change.

### ~August 25: ADP pass (the big one)
- League draft board becomes available — recalibrate against the actual room:
  - Fill **RB Tier 2** in `data/rb_board.yaml` (deliberately left empty).
  - Pressure-test the **QB count-rule thresholds** (`data/qb_rule.yaml`) —
    they're calibrated to public ADP, and twelve veterans who've drafted
    together for a decade are not public ADP.
  - Refresh WR value-board gaps and every ADP figure (all single-source and
    stale by design until now).
- Rerun `python3 tests/verify.py` after every data edit — the collision check
  will catch any round-plan conflict a recalibration introduces.

### September 7, draft morning
- Slot is revealed. Set `draft.slot` in `data/league.yaml`.
- Print the cheat sheet: `ff sheet` (or grab the pre-built
  `build/sheet_EARLY|MIDDLE|LATE.txt` from `ff sheet --all`).
- At the table, one command per pick:
  `ff draft --round R --gone G` → tree step + QB verdict + due commitments +
  board names + Colts cap, one screen.

### Week 1: switch to in-season mode
- Create `data/roster.yaml` from the drafted team.
- Enable the two in-season Routines (Tuesday waiver brief, Sunday lineup
  check) — they're already created, sitting disabled.
- The weekly loop is `ff weekly 1-4` (waivers → scan/trades → lineup lock →
  debrief), anchored to Tuesday-night rolling-priority processing. Rolling
  priority is a depleting asset: burn it only for season-long workhorse upside.

## Standing items
- Replace the stale 2-tab workbook in the Claude project with a fresh
  `ff build` output (the project copy predates Evans/Murray/Seahawks rows).
- Every factual claim in the watchlist traces to July web searches. The camp
  watch re-verifies as camps produce real reporting; nothing is "settled"
  until it survives two sources.
