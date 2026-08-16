# ff2026

Superflex fantasy football toolkit. Data lives in YAML, code is presentation only.
Edit `data/*.yaml`, rerun `ff build`, and the workbook is regenerated from scratch.

## Auditing this framework

Run `python3 tests/verify.py` (23 structural checks), then read `HANDOFF.md`
for what still needs human verification.

## Install (WSL / Ubuntu)

```bash
cd ff2026
bash setup.sh
bash setup.sh   # puts `ff` on PATH; open a new terminal after
ff settings
```

## Commands

| Command | What it does |
|---|---|
| `ff settings` | Print league settings from `data/league.yaml` |
| `ff build` | Regenerate `build/2026_Camp_Watchlist.xlsx` from the YAML |
| `ff qb --round 4 --gone 15` | Apply the superflex QB count rule, return a verdict |
| `ff tree --slot 7` | Print your draft branch for that slot |
| `ff bye IND NYJ LV DAL` | Audit a roster for bye stacking and playoff conflicts |
| `ff weekly 1` | Print the Session 1 template to fill in |
| `ff confirm` | Show unconfirmed settings and exactly what each one changes |

## Draft day

```bash
ff tree --slot 7                 # slot revealed that morning
ff qb --round 4 --gone 15        # at every pick, count QBs gone
```

## Layout

```
data/          all facts and settings - edit these
  league.yaml    league settings, single source of truth
  byes.yaml      2026 NFL bye weeks
  qb_rule.yaml   count-rule thresholds (recalibrate in August)
  trees.yaml     draft branches by slot
  weekly.yaml    in-season session definitions
  watchlist.yaml the situation rows
  screen.yaml    32-team structural screen
ffcli/         code - you should rarely need to touch this
build/         generated output (gitignored)
```

## Notes

- `ff build` writes formulas as strings with no cached values. They compute the
  first time Excel or LibreOffice opens the file. That is expected.
- `ir_slots: 0` in league.yaml drives the stash logic. If the league ever adds
  IR, change it there and nothing else.
- **Unconfirmed settings are written as a list.** `playoff_start: [14, 15]` means
  "could be either". The bye audit then models every scenario and labels each
  warning `[CERTAIN]` (true under all of them) or `[CONDITIONAL]` (true under
  some, with the condition named). Replace the list with a single number and the
  warnings sharpen automatically. Run `ff confirm` to see what is still open and
  what each value changes.
- Two settings are currently open: `regular_weeks` (12 or 13) and `playoff_start`
  (14 or 15). Check them in the ESPN league settings.

## August recalibration

Pull the ESPN league draft board, count QBs taken by Round 4 last season, and
edit the thresholds in `data/qb_rule.yaml`. If your room took 16+ by Round 4,
shift every threshold a full round earlier. No code changes needed.
