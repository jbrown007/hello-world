# ff2026 Session Handoff

August 2, 2026. This distills the July 25 - August 2 session that migrated the
framework into this repo, reconciled it against confirmed league settings, and
battle-tested it in two mock drafts. **This repo's `master` is the single
source of truth.** The original audit handoff this file replaces is in git
history (it described 20-man rosters and 23 checks - that world is gone).

The goal: Josh wins his 12-team full-PPR superflex league for the first time
in 15 years. Draft is **Sept 7, Labor Day**, slot unknown until that morning.

---

## 1. Where things stand

- **Suite: 34/34 checks** (`python3 tests/verify.py`). Every rule described
  below is enforced by a test, and every test was mutation-verified (break the
  rule, watch the test fail, restore).
- **All league settings confirmed 8/1** (data/league.yaml): 17-man roster,
  bench 7, zero IR, K + D/ST mandatory starters, FLEX = RB/WR (TE excluded),
  OP = second QB weekly, 14-week regular season, playoffs W15-17, Dec 4 trade
  deadline (inside Week 13), rolling waivers Tuesday night, weekly high-score
  payouts W1-12. Unverified but non-blocking: playoff team count (likely 6);
  FLEX exclusion read from a screenshot - confirm in settings text.
- **Watchlist: 23 rows, 15 Resolved / 8 Trending / 0 Unsettled** as of the
  8/2 camp watch.
- **CLI**: `ff settings|confirm|build|qb|rb|tree|room|draft|sheet|grade|bye|weekly`.
  `ff sheet --all` writes the printable per-branch draft scripts; `ff draft`
  is the live one-screen pick view; `ff grade` scores a finished draft.

## 2. The strategy, as it now stands

- **RB floor (data/rb_rule.yaml)**: 2 RBs by end of R4, 3 by R8, 5 by R12.
  Exists because Josh's 2025 draft (QB/QB/TE early, first RB at pick 65)
  produced 7th place. Non-negotiable; `ff rb --round N --held X`.
- **QB rule (data/qb_rule.yaml), retuned to the room's real 2025 board**:
  8 QBs gone through R4, ZERO in R5, six in R6. The room queues, then panics.
  So: QB1 by R3 (A/B/C branch map keys on whether an elite arm reaches your
  pick), **QB2 in R5-6 only** (earliest 5, hard floor 6 - R6 IS the run),
  QB3 mandatory R10-13 with a bye different from QB1/QB2 (OP starts a second
  QB weekly). **Run trigger: 3+ QBs inside any 12-pick window = take QB2 next
  pick regardless of count** (`ff qb --window`). EARLY slots: take QB2 at the
  R5 pick even though the count feels low - the run fires inside their
  23-pick R5->R6 gap.
- **Zero-slack ledger (data/commitments.yaml)**: 17 picks = 3 QB, 6 RB, 5 WR,
  1 TE (Warren), K, DST. Every dart must displace a named pick. The old
  Tier-3 stash names are a Week 1 waiver list, not draft targets.
- **TE is one-and-done**: FLEX excludes TE and OP belongs to QB2, so a TE2
  can never score. Warren R4-5, GATED: below 2 RBs at R5, RB wins, Warren is
  released, backfill TE R7-8. Never two TEs.
- **Fixed windows**: Warren R4-5, Downs R7 (+15 target-rank/ADP gap, the
  board's best documented mispricing), K/DST R16-17 only.
- **Stack cap (data/stack_caps.yaml, single source)**: max 2 IND starters.
  W13 (IND bye) is the penultimate seeding-stretch week AND holds the Dec 4
  deadline - Colts exposure cannot be traded away. Enforce at the draft.
- **Bye danger (auto-computed on the sheets)**: W14 is the SEEDING WEEK with
  ARI + DAL on bye - never 2+, never a QB. W11 six-team bye. Playoffs W15-17
  are bye-free.
- **Josh's carried lessons (data/lessons.yaml)**: Week-5 patience in-season;
  top-3 K at R16-17 (K is mandatory); QB4 only via in-season churn; stars
  Nacua (R1 pivot), St. Brown (unplaced - verify), Caleb Williams (verified
  8/2, on the R5-6 QB2 candidate list with Cam Ward - he went QB13/pick 70
  in this room in 2025).

## 3. What the two mocks taught

- **Mock 1 (slot 5, 1-QB room, 7/25)**: structure held, but drafted a
  4-starter W14 bye stack with the co-pilot watching. Lessons: live
  back-and-forth is not viable under a pick clock -> the sheets became
  self-sufficient (bye tally grid, QB count tally, round script); duplicate
  teams must count as separate players in the bye audit (bug found by real
  data).
- **Mock 2 (slot 4, superflex, 17 rounds, 8/2)**: graded 6/11. RB floor
  discipline is FIXED (floor met at R3, 6/5 split, K/DST on time). New
  failure layer: QB/TE windows - R6-tier arms (Dak, J.Love) bought at R2/R4,
  which cascaded into no WR by R4, no TE in window then TWO TEs later, a
  board fade (Pollard) in Downs's R7 window, and NO QB3 with QB1's bye on
  the W14 seeding week. **Mock 3 has one job: the windows.** ESPN's letter
  grade measures generic value, not the plan - ignore it.
- Meta-lesson: each rep fixes one layer. Byes -> fixed. RB floor -> fixed.
  QB/TE windows -> next.

## 4. Operating procedures

- **Camp watch** (run on request; say "camp watch"): search each
  Trending/Unsettled row's `watch_for` + team/player news, last 48h.
  Two independent sources for any status flip; single-source goes in notes
  as UNCONFIRMED with date + source. Only edit data/watchlist.yaml. Branch
  `claude/camp-watch` from origin/master, run the suite (must stay green),
  push, PR titled "Camp watch: watchlist updates" - **never self-merge**.
  Scheduled automation is still blocked on an MCP permission
  (claude-code-remote create_trigger/send_later return "requires approval");
  if that gets fixed, arm a daily 7am ET fresh-session Routine with the
  same procedure.
- **Repo flow**: work on `claude/setup-github-wsl-5uucrx` restarted from
  origin/master after each merge. PRs only when Josh asks; Josh says
  "merge". Commit style: what + why, mutation-test note.
- **Sheets**: after ANY data edit -> run suite -> `ff sheet --all` ->
  re-deliver. Never let Josh draft off a stale printout.

## 5. Agenda to Sept 7

| When | What |
|---|---|
| Done 8/2 | **Room model FILLED** from the 2025 board (managerprofiles.md): all 11 profiled, threat board set (Trey Action Fake / #TheMoneyTeam / Shaun DeNiro), reps corrected by data (CHAMP is anchor-QB not QB-early but IS Warren competition; Jag FLu is the R2-3 QB threat; Griddy counts as 2 QBs at turns; Easy money / Kleenex hoarding reps unconfirmed). Remaining room gaps: R9+ of the 2025 board, final standings, draft-order method. |
| ~Aug 15 | Vikings name a starter (Murray favorite, split reps as of 8/2). Highest-value open row. Also watch: Jones vs Richardson REP SHARE (health resolved 8/2, share is the open question), Browns QB, Dolphins QB, Commanders/Giants rookie depth charts. |
| ~Aug 25 | **RB Tier 2 fill** (rb_board tier 2 is deliberately empty - Jeremiyah Love went R2/R3 in both mocks and the boards don't know him; biggest data gap) + ADP refresh (Price's ADP spiking - discount closing). |
| Aug 29-30 | NFL cut-downs - depth charts finalize. |
| Sept 5-6 | Final sweep of every named target post-cuts, suite, `ff sheet --all`, PRINT. |
| Sept 7 | Slot revealed -> set `draft.slot` + `slot_2026` fields in room.yaml -> `ff room --slot N` for neighbor/snipe analysis -> draft off the printed sheet. |
| Post-draft | data/roster.yaml, in-season loop (Tue waiver brief before rolling-priority processing, Sunday lineup check, Week-5 patience, zero-IR triage, trade windows vs the Dec 4 deadline, weekly-payout ceiling game). |

Also open: one more mock (windows-focused); superflex mock draft-board
screenshots if available (second QB-run curve for calibration); playoff team
count + FLEX text verification; the durable audit lessons still apply -
assumptions die on contact with confirmed settings, orphaned data drifts,
a confident note is not a verified note.
