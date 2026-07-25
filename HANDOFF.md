# Audit Handoff: ff2026

You are auditing a fantasy football draft-prep framework built for a single
user (Josh) over one long session in late July 2026. Your job is to find what
is wrong, not to confirm what is right.

**Read this whole file before touching anything.** Section 3 is the highest-value
part — it is a record of errors that were actually made during construction, and
the same failure modes are likely to recur in places nobody caught.

---

## 1. What this is

A superflex fantasy football draft toolkit with two artifacts:

| Artifact | What it is |
|---|---|
| `2026_Camp_Watchlist.xlsx` | 7-tab workbook. The thing the user actually reads on draft day. |
| `ff2026/` (this package) | Python CLI + YAML data. Regenerates a 3-tab subset of the workbook and runs draft-day decision logic. |

**Important asymmetry:** the workbook has 7 tabs. The package regenerates only 3
(Start Here, Watchlist, Screen). The RB Board, WR Board, TE Board and Draft Trees
tabs exist **only** in the xlsx and were built by one-off scripts that are not in
this package. That is a known gap, not a bug to fix silently — flag it and ask
before rewriting.

League context that drives every decision:
- 12 teams, full PPR, **superflex** (optional 2QB start)
- 20-man roster, **zero IR slots** (this constrains a lot of the advice)
- Snake draft, Labor Day Sept 7, **draft slot unknown until that morning**
- **Rolling waiver priority**, Tuesday-night processing
- Payouts split between season-long and weekly high score
- Redraft only

---

## 2. Start here

```bash
cd ff2026
bash setup.sh && source .venv/bin/activate
python3 tests/verify.py
```

23 structural checks. All should pass. If any fail, stop and fix before manual
review — a data-layer failure invalidates everything downstream.

**What verify.py does NOT check:** whether any football claim is true. Every
factual assertion in this framework came from web searches, not from a verified
database. That is section 4.

---

## 3. Error record from construction

These are real mistakes made while building this. Assume similar ones survive.

### 3a. A silent data bug the test suite caught

`byes.yaml` had New Orleans written as unquoted `NO`, which YAML parses as the
boolean `false`. New Orleans silently disappeared from the bye map and every
Saints bye-week check returned nothing. Fixed by quoting it.

**Why this matters to you:** it was invisible in every manual read-through and
survived until an automated check specifically counted teams. Look for the same
class of problem elsewhere — silent type coercion, empty strings that should be
values, defaults that mask missing data.

### 3b. Factual errors that were made and corrected

| Claim | Reality | How it was caught |
|---|---|---|
| Mike Evans still on Tampa Bay | Signed with the 49ers in free agency | Later search contradicted an earlier one |
| Kirk Cousins not on the Raiders | He is — 1yr/$20M guaranteed | Later search |
| Mike McDaniel is Chargers head coach | He is the **offensive coordinator**; Jim Harbaugh is HC | Coaching-changes search |
| TreVeyon Henderson resolved the Patriots backfield | Still a committee; Stevenson projected to start | Dedicated search |
| "7 teams still TBV on the Screen" | Actually 22 | Direct query of the file |
| Week 13 byes threaten the playoffs | They land in the regular season | User supplied playoff weeks |

Pattern worth noting: **a prior verification pass being wrong is not rare here.**
Two of the above were "corrections" that were themselves wrong. Do not treat a
confident note in the Notes column as verified.

### 3c. Code bugs introduced and fixed

- Tuple index error from inconsistent row lengths in a build script
- String-escaping syntax error (`\'` inside single-quoted strings)
- Three separate `str.replace()` patch anchors that silently failed on
  indentation mismatch — **one shipped a no-op `ff confirm` command that printed
  nothing and returned 0.** Silent failure, not a crash.

**Check for other silent no-ops.** Any command that exits 0 with no output is suspect.

---

## 4. What needs human verification

### 4a. Factual claims (highest risk)

Every NFL claim traces to a July 2026 web search. None was cross-checked against
a second independent source unless noted. The constructing model's training data
ends May 2026, so it **cannot** independently verify 2026 offseason events.

Spot-check these specifically, since decisions hang on them:

1. **Kyler Murray to Minnesota** and the open competition with J.J. McCarthy
2. **Fernando Mendoza No. 1 overall to the Raiders**; Cousins likely starting
3. **Daniel Jones fully cleared** from the Achilles tear
4. **A.J. Brown traded to New England** (this one is asserted from a single source)
5. **Tyler Warren's Round 4 valuation** and Pittman's 111 vacated targets
6. All **ADP figures** — Henderson RB21, Stevenson RB28, Sadiq TE20, the WR
   value board gaps (+15/+14/+12). Single-source, and ADP moves weekly.
7. **2026 bye weeks** — verify the full 32-team map against nfl.com directly.
   A wrong bye week silently corrupts the audit logic.

### 4b. Internal consistency

- Do the RB, WR and TE round plans collide? Each was built separately. The QB
  plan claims Rounds 2-4, the RB board claims Rounds 2-3, the WR board claims
  Rounds 2-4 and 8-11, the TE board claims Round 4-5. **Verify a real draft can
  actually satisfy all four.** This is the most likely place for an unnoticed
  contradiction.
- The Indy stack warning (max 2 Colts, W13 bye) appears on the TE Board. Does it
  also need to appear on the QB and WR boards, which independently recommend
  Jones, Downs and Pierce?
- `Start Here` dashboard COUNTIF formulas reference `Watchlist!$A$` and `$L$`.
  A column was inserted mid-build and formulas were re-pointed by hand. Verify
  they still target the right columns.

### 4c. Strategic logic

- The QB count-rule thresholds (14 gone by R4, 16 by R5) are **asserted, not
  derived.** They are calibrated to public superflex ADP, which may not match a
  12-team league of decade-long veterans. Josh will supply his league's real
  draft board in late August. Judge whether the thresholds are defensible as an
  interim.
- The claim "the QB pool is deep this year, so wait" contradicts the user's own
  stated instinct to grab two QBs early. The reasoning is in `data/qb_rule.yaml`.
  **Pressure-test it.** If it is wrong, it is the single most costly error here.
- TE Board argues Josh's punt strategy fails because he is punting with one
  player and has zero IR. Verify the reasoning and the Tyler Warren
  recommendation that follows from it.

### 4d. Known open items — do NOT flag these as bugs

- `regular_weeks: [12, 13]` and `playoff_start: [14, 15]` are **intentionally**
  ranges. The user confirms them August 1. `ff confirm` explains the impact. The
  bye audit models all four scenarios and labels warnings CERTAIN vs CONDITIONAL.
- 22 of 32 teams on the Screen tab have TBV cells. Intentional — verifying them
  before camp reports exist would mean guessing.
- 7 of 22 watchlist rows are Trending/Unsettled. Expected to resolve during camp.
- The package regenerates 3 of 7 tabs. See section 1.

---

## 5. What "clean and working" means

- [ ] `python3 tests/verify.py` → 23/23
- [ ] Every CLI command produces sensible output, no silent no-ops
- [ ] Generated workbook opens in Excel with formulas computing (they have no
      cached values until first open — that is expected, not a bug)
- [ ] Bye map verified against nfl.com, all 32 teams
- [ ] The four round plans are mutually satisfiable in a real 12-team snake
- [ ] Spot-checked factual claims in 4a hold up
- [ ] The wait-on-QB thesis survives scrutiny

## 6. If you find something

Report it plainly. Do not repair the football analysis silently — the user needs
to know which of his draft-day decisions changed and why. Code bugs can be fixed
directly; strategic disagreements should be surfaced with reasoning so he can
decide.

The user is technical, prefers direct language, and would rather hear "this is
wrong and here's why" than a hedge.
