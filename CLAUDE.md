# ff2026 — operating manual for this repo

Auto-loaded into every Claude Code session here. Read this first, then
`HANDOFF.md` for the full state. **`data/*.yaml` is the source of truth; the
code only reads it.** Never hardcode football facts in Python.

## The goal

Josh (team **Crushing Dreams**) wins his 12-team full-PPR **superflex**
league for the first time in 15 years. He finished 10th of 12 in 2025.

**Draft: Sunday Sept 6 2026, 9:00 PM EST. Slot 5 is LOCKED.**
Picks: **5, 20, 29, 44, 53, 68, 77, 92, 101, 116, 125, 140, 149, 164, 173,
188, 197.**

## First 60 seconds in a new session

```bash
pip install -r requirements.txt      # fresh containers lack openpyxl; 10 checks fail without it
python3 tests/verify.py              # MUST be all-green before you touch anything
bash setup.sh                        # puts `ff` on PATH, cwd-independent
ff targets                           # the round-by-round board for slot 5
ff mocks                             # error patterns across every logged rep
```

**Run `python3 tests/verify.py` after every data edit.** It is the guardrail
that catches YAML corruption, bye mismatches, ledger drift and round-plan
collisions. If you add a check, mutation-test it: break the rule, watch it
fail, restore. A check that passes on corrupt data is worse than none — that
has happened here twice and both times the fix was to assert section sizes,
not just contents.

## Your standing job: full prep ownership

Three recurring duties. Josh drives timing; you own correctness.

### 1. Mock drafts — the main loop

Every mock from here on is **slot 5**. Josh posts an ESPN results screenshot.

1. Transcribe to a picks file in the scratchpad: `ROUND POS TEAM Player Name`
2. `ff grade <file> --slot 5`
3. Read past the score. **The score is no longer the useful signal** — the
   last ten reps average 10.0/11. What matters is what the score cannot see:
   bye stacking, fades drafted, off-tier QB purchases, a starter on W14.
4. Append a rep to `data/mocks.yaml` with honest `notes` and `errors` tags.
5. Commit and push. One commit per rep.

### 2. Camp watch — on request ("camp watch")

Sweep every **Trending/Unsettled** row in `data/watchlist.yaml`, searching that
row's own `watch_for` trigger for last-48h news. **Two independent sources for
any status flip.** Prepend a dated note to the row's `notes`; edit only
`watchlist.yaml`. Single-source items get logged as directional, not acted on.

**THEN SWEEP THE NAMED COMMITMENTS TOO — added 8/29 after a real miss.** The
watchlist is not the board. Tyler Warren is taken at pick 53 in nine of nine
reps and strained his groin on Aug 19; five sweeps ran before it was noticed on
Aug 29, because he has no watchlist row. Neither did Kenneth Walker III, who
was drafted in eight of nine reps and had a foot issue on Aug 25. Sweeping only
watchlist rows structurally cannot see an injury to the most locked pick in the
framework.

So after the rows, run `ff targets` and health-check the **named** picks —
at minimum every player taken in 3+ reps (`data/rep_rosters/`) and everything
in the R1-R10 target lists. A player with no row who is drafted every single
rep is the most dangerous blind spot there is, precisely because nothing
prompts you to look. If one is hurt and has no row, **create the row** rather
than burying it in someone else's notes.

### 3. The calendar

- **Aug 25** — ADP pass. Re-price every board. `data/adp.yaml` has the last one
  and flags what is an ESTIMATE.
- **Aug 29-30** — post-cuts sweep; depth charts finalize.
- **Sept 4-5** — final sweep on every named target, then `ff sheet --all` and
  tell Josh to PRINT. Never draft off a stale sheet.
- **Week 1** — switch to in-season mode (not built yet, see open items).

## Autonomy — sanctioned by Josh, 8/16

**When a mock or new data reveals a flaw in a rule, change the rule.** Do not
wait for approval. Commit the change with the evidence in the message. This is
how the Downs window was tightened, Mahomes was demoted, and the Daniel Jones
refusal was widened. Explain what you changed and why in your reply.

Two limits: do not change a rule on a single rep unless the mechanism is
obvious, and never silently drop a rule — supersede it in writing.

## Invariants that must never break

- **Ledger: 3 QB / 6 RB / 5 WR / 1 TE / 1 K / 1 DST = 17.** Zero slack. Every
  dart displaces a named pick.
- **RB floor: 2 by R4, 3 by R8, 5 by R12.**
- **Bye cap: 2 players per week.** This is the oldest unfixed error — 16 of 20
  reps. `ff draft --teams "NE,LV,..."` prints the live tally and a DO NOT DRAFT
  list. In the 8/16 rep it would have blocked all four breaches.
- **W14 is the seeding week** (only DAL + ARI). Never 2+, never a QB, never the
  kicker, never the TE1.
- **W13 is spent before the draft starts** — Warren + Downs are both IND. That
  refuses Lamar, Geno, Garrett Wilson, Sadiq, Daniel Jones, Pierce, Jonathan
  Taylor and Bateman. See `targets.yaml` conflicts.
- **QB1/QB2/QB3 must hold three different byes.**
- **Buy QBs at tier.** `ff grade` prints REACH / at market / VALUE against
  `qb_board`. A commitment window checks WHEN, not WHICH.
- **K and D/ST at R16-17 only**, never sharing a bye, never Aubrey (DAL).

## The commands

| Command | What it does |
|---|---|
| `ff targets [--round N]` | Round-by-round named board for slot 5 + the conflict rules |
| `ff draft --round R --gone G --window W --have "..." --teams "..."` | Live pick screen. **Always pass `--teams`.** |
| `ff sheet [--all] [--format twocol\|long]` | Printable one-page plan |
| `ff grade <file> --slot 5` | Score a finished draft |
| `ff mocks` | Error patterns across all reps |
| `ff room [--slot N]` | Manager profiles, seat geometry, who picks in your gaps |
| `ff qb` / `ff rb` / `ff bye` / `ff weekly` | Rule engines |

## The room (2026 seats)

1 #TheMoneyTeam · 2 Trey Action Fake · 3 Shaun DeNiro · 4 Da LockDownGoon ·
**5 JOSH** · 6 Kleenex Gang · 7 Just call me CHAMP · 8 Easy money ·
9 Jag FLu · 10 Olave · 11 4 Time 13 · 12 Griddy Committee

Three seat facts that drive picks: **Kleenex (6) picks immediately after every
odd round** and is RB-hungry. **CHAMP (7) picks at 42, 55 and 66** and took
Tyler Warren in R6 last year. **Griddy (12) doubles at 60-61**, inside the
53→68 gap, and the 2025 QB run fired at picks 62-72 — which is why **pick 53 is
the last market-price QB2** and the decision pick of the draft.

## Open items — ask Josh

1. **Full ESPN board capture.** One mock, all 12 teams × 17 rounds, not just
   Josh's picks. Every public ADP host is egress-blocked here, so this is the
   only path to *measured* superflex ADP and would replace every ESTIMATE in
   `data/adp.yaml` — including where Warren really goes, which decides the
   Warren-vs-QB2 call at pick 53.
2. **Draft-day logistics.** Where is he drafting from on Sept 6? Terminal open
   for live `ff draft` calls, or printed sheet only? This changes what gets
   built in the final week.
3. **In-season scaffolding — nothing exists.** `data/roster.yaml`, a Tuesday
   waiver routine and a Sunday lineup routine. Week 1 lands days after the
   draft. `PREP.md` once wrongly claimed these were built; they are not.
4. **Playoff team count** still unverified (likely 6). Sets what W14 is worth.
5. **Camp-watch Routine is broken.** Its trigger has no `sources`, so fired
   sessions clone no repo. `update_trigger` cannot add them — it needs
   recreating in the claude.ai Routines UI. Camp watch works fine on request.
