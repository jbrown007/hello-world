"""Bye-week auditing for a roster or a candidate group of teams.

Season settings may be unconfirmed (a list of candidate values). When they are,
warnings are emitted as CERTAIN (true under every scenario) or CONDITIONAL
(true under some), rather than guessing a single answer.
"""
from __future__ import annotations
from collections import defaultdict
from itertools import product

from .config import bye_of, league, as_range


def _scenarios(season: dict) -> list[dict]:
    """Cartesian product of every candidate value for unconfirmed settings."""
    keys = list(season)
    combos = product(*(as_range(season[k]) for k in keys))
    return [dict(zip(keys, c)) for c in combos]


def _label(hits: int, total: int) -> str:
    if hits == total:
        return "CERTAIN"
    return "CONDITIONAL"


def audit(teams: list[str], max_per_week: int = 2) -> dict:
    """Group teams by bye week; flag stacking, playoff and seeding conflicts."""
    lg = league()
    season = lg["season"]
    payout_weeks = lg["payouts"]["weekly_payout_weeks"]
    scenarios = _scenarios(season)
    n = len(scenarios)

    grouped: dict[int, list[str]] = defaultdict(list)
    unknown: list[str] = []
    for t in teams:
        wk = bye_of(t)
        (grouped[wk] if wk else unknown).append(t.upper())

    warnings: list[str] = []
    for wk in sorted(grouped):
        names = grouped[wk]
        joined = ", ".join(names)

        if len(names) > max_per_week:
            warnings.append(
                f"[CERTAIN]     W{wk}: {len(names)} players out ({joined}). Cap is {max_per_week}."
            )
            if wk <= payout_weeks:
                warnings.append(
                    f"[CERTAIN]     W{wk}: weekly high-score payout is unwinnable with {len(names)} out."
                )

        # playoff window
        in_playoffs = [s for s in scenarios if s["playoff_start"] <= wk <= s["playoff_end"]]
        if in_playoffs:
            starts = sorted({s["playoff_start"] for s in in_playoffs})
            cond = "" if len(in_playoffs) == n else f" (only if playoffs start W{'/W'.join(map(str, starts))})"
            warnings.append(
                f"[{_label(len(in_playoffs), n):<11}] W{wk}: PLAYOFF WINDOW{cond}. {joined} dark in a playoff game."
            )

        # seeding week - the last regular-season week decides the top-two bye
        seeding = [s for s in scenarios if s["regular_weeks"] == wk]
        if seeding:
            cond = "" if len(seeding) == n else f" (only if the regular season is {wk} weeks)"
            warnings.append(
                f"[{_label(len(seeding), n):<11}] W{wk}: SEEDING WEEK{cond} - decides the first-round bye. {joined} out."
            )

    return {
        "grouped": {k: v for k, v in sorted(grouped.items())},
        "unknown": unknown,
        "warnings": warnings,
        "scenarios": n,
    }
