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


def qb_verdict(rnd: int, gone: int) -> Verdict:
    """Apply the superflex QB count rule for a given round and QB count."""
    rule = load("qb_rule")
    floor = rule["hard_floor_round"]

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


def tree(slot: int) -> dict:
    """Return the draft branch for a given slot."""
    n = league()["teams"]
    if not 1 <= slot <= n:
        raise ValueError(f"slot must be between 1 and {n}")
    for branch in load("trees"):
        if slot in branch["slots"]:
            return branch
    raise ValueError(f"no branch covers slot {slot}")
