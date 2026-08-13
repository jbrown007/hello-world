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

### August 1: league settings — ✅ DONE (FRAMEWORK_RECONCILIATION.md)
- ALL settings confirmed and migrated 8/2. The big corrections: **roster is
  17** (not 20 — bench is 7, zero slack), **K and D/ST are mandatory
  starters** (R16-17 picks), **regular season is 14 weeks** with playoffs
  W15-17. `ff confirm` reports clean.
- Consequences now live in the framework: **W14 is the seeding week and ARI +
  DAL are on bye in it** (never 2+, never a QB); the playoff window W15-17 has
  zero bye conflicts; W13 (IND bye) is the penultimate week with the **Dec 4
  trade deadline inside it** — Colts exposure cannot be traded away, cap
  enforced at the draft.
- 2025 draft board analyzed (DRAFT_BOARD_2025.md): thresholds retuned to the
  room's real behavior, **RB floor rule added** (2 by R4 / 3 by R8 / 5 by
  R12 — the 2025 7th-place fix), **QB2 confined to R5-6**, **3-in-12 run
  trigger** added. `ff rb` and `ff qb --window` are live.
- Still unverified (non-blocking): playoff team count (likely 6), and the
  FLEX read — **RESOLVED 8/9: FLEX = RB/WR/TE, tight ends ARE eligible.** The
  earlier "RB/WR only" was wrong and had been the sole basis for the
  no-TE2-ever rule; see HANDOFF section 2.

### ~August 13: preseason games begin
- Snap share, target share, and first-team reps become real data. Trending
  rows should start flipping. Treat beat-writer camp hype with the audit's
  rule: two independent sources for any status change.

### ~August 25: ADP pass
- Fill **RB Tier 2** in `data/rb_board.yaml` (still deliberately empty — now
  the single biggest data gap, since the RB floor makes RB timing the plan's
  spine).
- Refresh WR value-board gaps and ADP figures (single-source and stale by
  design until now). The QB thresholds are already recalibrated to the
  room's 2025 board; check them against current superflex ADP for drift only.
- Rerun `python3 tests/verify.py` after every data edit — the collision check
  will catch any round-plan conflict a recalibration introduces.

### ~Aug 29-30: roster cut-downs
- NFL teams cut to 53. Depth charts and committee answers finalize a week
  before your draft - the last big information event.

### September 5-6: final sweep
- Re-verify EVERY planned target after cuts: health, role, depth-chart spot.
  One camp-watch pass focused on the sheet's named players (Warren, Downs,
  Stevenson, Price, Black, Ward, the value board).
- Apply any last edits to the boards, run `python3 tests/verify.py`, then
  `ff sheet --all` and PRINT fresh sheets. Do not draft off a stale printout.

### September 7, draft morning
- Slot is revealed. Set `draft.slot` in `data/league.yaml`.
- Print the cheat sheet: `ff sheet` (or grab the pre-built
  `build/sheet_EARLY|MIDDLE|LATE.txt` from `ff sheet --all`).
- At the table, one command per pick:
  `ff draft --round R --gone G --slot N --window W --have "QB=1,RB=2,WR=2,warren,downs"`
  → tree step + QB verdict (with the 3-in-12 run trigger armed by `--window`)
  + HELD tally + only what you STILL OWE + board names + Colts cap, one
  screen. `--have` takes POS=N counts (the same numbers you write in the
  sheet's TALLY box) PLUS bare names for the board-specific picks - warren,
  downs. A named commitment only clears when you name it, so it cannot be
  wiped out by unrelated players at the same position.
- `ff` is on PATH after `bash setup.sh` - no venv activation, works from any
  directory. Verified 8/13. Re-run setup.sh after pulling if it ever misses.

### Week 1: switch to in-season mode
- Create `data/roster.yaml` from the drafted team.
- **BUILD the two in-season Routines** (Tuesday waiver brief, Sunday lineup
  check). Corrected 8/9: this file previously claimed they were "already
  created, sitting disabled" — they do not exist. Nothing in-season is built
  yet, and Week 1 lands days after the draft.
- The weekly loop is `ff weekly 1-4` (waivers → scan/trades → lineup lock →
  debrief), anchored to Tuesday-night rolling-priority processing. Rolling
  priority is a depleting asset: burn it only for season-long workhorse upside.

## Mock practice

All mocks are superflex format (confirmed by Josh 8/3) - the full plan
applies in every rep, no demotions. Mock 1 (7/25) was a 1-QB room; that
guidance is retired and lives in git history.

**Practice the whole plan:** QB1 branch map (by R3), QB2 in R5-6 with the
run trigger live, QB3 in R9-13 with bye triangulation, plus the layers that
always transfer - R1 elite RB discipline, RB floor gates, Warren at R4-5,
Downs at R7, the Colts cap count, the value/fade lists, and clock composure.

**Afterward:** `ff grade picks.txt --slot N` scores the run in full -
commitments hit per round, cap, byes, QB windows. (`--oneqb` stays in the
CLI but should not be needed again.) Record the round each QB left the
board: every mock is now a real QB-run curve for calibrating the room's
thresholds - previously the scarcest calibration data we had.

## Standing items
- Replace the stale 2-tab workbook in the Claude project with a fresh
  `ff build` output (the project copy predates Evans/Murray/Seahawks rows).
- Every factual claim in the watchlist traces to July web searches. The camp
  watch re-verifies as camps produce real reporting; nothing is "settled"
  until it survives two sources.
