"""Load league settings and reference data from data/*.yaml."""
from __future__ import annotations
import pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def load(name: str):
    path = DATA / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"missing data file: {path}")
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def league() -> dict:
    return load("league")


def byes() -> dict[int, list[str]]:
    return {int(k): v for k, v in load("byes").items()}


def bye_of(team: str) -> int | None:
    """Bye week for a team abbreviation, or None."""
    team = team.upper().strip()
    for wk, teams in byes().items():
        if team in teams:
            return wk
    return None


def as_range(value) -> list[int]:
    """Normalise a setting that may be a scalar or an unconfirmed list."""
    if isinstance(value, (list, tuple)):
        return [int(v) for v in value]
    return [int(value)]


def is_confirmed(value) -> bool:
    """True when a setting has been narrowed to a single value."""
    return len(as_range(value)) == 1


def unconfirmed() -> dict[str, list[int]]:
    """Every season setting still carrying more than one candidate value."""
    season = league()["season"]
    return {k: as_range(v) for k, v in season.items() if not is_confirmed(v)}
