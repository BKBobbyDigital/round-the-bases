"""
Generate a Round the Bases daily puzzle JSON.

Usage:
    python generate_puzzle.py 2026-06-05

Reads:
    data/curated_1b.csv     -- 1B trivia (multiple choice)
    data/curated_2b.csv     -- 2B career-arc clues (multiple choice)
    data/curated_3b.csv     -- 3B stat-line targets (player, season)
    data/curated_hr.csv     -- HR arsenal targets (pitcher, season)

For 3B and HR the script pulls stats from Statcast via pybaseball,
formats the pitch JSON, and writes puzzles/YYYY-MM-DD.json.

This is a v0 skeleton: the Statcast calls are wrapped behind helpers
that you can flesh out once pybaseball is installed.
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PUZZLES = ROOT / "puzzles"

# Day-of-week themes drive what kind of puzzle gets picked.
DAY_THEMES = {
    0: "Welcome to the Week",     # Monday
    1: "Pitcher's Day",
    2: "90s Nostalgia",
    3: "Leather Day",
    4: "Modern Era",
    5: "Weekend Warm-Up",
    6: "Stumper Sunday",
}

PITCH_EMOJI = {
    "FF": "🔥", "FA": "🔥",  # 4-seam / fastball
    "SI": "⚡",                # sinker
    "FC": "✂️",                # cutter
    "SL": "🪄",                # slider
    "ST": "🌪",                # sweeper
    "CU": "🌀", "KC": "🌀",    # curveballs
    "CH": "💨",                # changeup
    "FS": "🍴",                # splitter
    "KN": "🦋",                # knuckler
    "SV": "🌊",                # slurve
}


# --- DATA MODEL --------------------------------------------------------------

@dataclass
class Pitch:
    tier: str            # "1B" | "2B" | "3B" | "HR"
    type: str            # "trivia" | "career_arc" | "stat_line" | "arsenal"
    prompt: Any
    answer: str
    choices: list[str] = field(default_factory=list)
    openingHint: str | None = None
    progressiveHints: list[str] = field(default_factory=list)
    answerSeason: int | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v not in ([], None)}


@dataclass
class Puzzle:
    date: str
    puzzleNumber: int
    theme: str
    pitches: list[Pitch]

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "puzzleNumber": self.puzzleNumber,
            "theme": self.theme,
            "pitches": [p.to_dict() for p in self.pitches],
        }


# --- STATCAST HELPERS (stubs) ------------------------------------------------

def fetch_pitcher_arsenal(player: str, season: int) -> list[dict]:
    """
    Returns the pitcher's arsenal as a list of {emoji, name, speed, usage}.

    Real impl: use pybaseball.statcast_pitcher to pull pitch-level data,
    group by pitch_type, compute usage % and avg release_speed.
    """
    # TODO: replace with real pybaseball call.
    # from pybaseball import statcast_pitcher, playerid_lookup
    # ...
    raise NotImplementedError(
        f"fetch_pitcher_arsenal({player!r}, {season}) — wire up pybaseball"
    )


def fetch_batter_stat_line(player: str, season: int) -> str:
    """
    Returns a short stat line string like '.346 / 24 HR / 81 RBI / 32 SB'.

    Real impl: pybaseball.batting_stats(season) filtered by player.
    """
    raise NotImplementedError(
        f"fetch_batter_stat_line({player!r}, {season}) — wire up pybaseball"
    )


# --- CURATED CSV LOADERS ------------------------------------------------------

def load_curated(name: str) -> list[dict]:
    """Load a curated CSV by name (e.g. 'curated_1b'). Empty list if missing."""
    p = DATA / f"{name}.csv"
    if not p.exists():
        return []
    with p.open() as f:
        return list(csv.DictReader(f))


def pick_for_date(rows: list[dict], date_str: str, salt: str) -> dict | None:
    """
    Deterministic daily pick: same date + same salt → same row,
    so generation is reproducible.
    """
    if not rows:
        return None
    seed = sum(ord(c) for c in (date_str + salt))
    return rows[seed % len(rows)]


# --- PITCH BUILDERS -----------------------------------------------------------

def build_1b(row: dict) -> Pitch:
    choices = [c.strip() for c in row["choices"].split("|")]
    return Pitch(
        tier="1B", type="trivia",
        prompt=row["prompt"], choices=choices, answer=row["answer"],
    )


def build_2b(row: dict) -> Pitch:
    choices = [c.strip() for c in row["choices"].split("|")]
    return Pitch(
        tier="2B", type="career_arc",
        prompt=row["prompt"], choices=choices, answer=row["answer"],
    )


def build_3b(row: dict) -> Pitch:
    season = int(row["season"])
    stat_line = fetch_batter_stat_line(row["player"], season)
    hints = [h.strip() for h in row.get("hints", "").split("|") if h.strip()]
    return Pitch(
        tier="3B", type="stat_line",
        prompt=stat_line,
        openingHint=row.get("openingHint") or f"{season} season",
        progressiveHints=hints,
        answer=row["player"], answerSeason=season,
    )


def build_hr(row: dict) -> Pitch:
    season = int(row["season"])
    arsenal = fetch_pitcher_arsenal(row["player"], season)
    hints = [h.strip() for h in row.get("hints", "").split("|") if h.strip()]
    return Pitch(
        tier="HR", type="arsenal",
        prompt={"pitches": arsenal},
        openingHint=row.get("openingHint"),
        progressiveHints=hints,
        answer=row["player"], answerSeason=season,
    )


# --- DRIVER -------------------------------------------------------------------

def generate(date_str: str) -> Puzzle:
    import datetime as dt
    d = dt.date.fromisoformat(date_str)
    theme = DAY_THEMES[d.weekday()]

    rows_1b = load_curated("curated_1b")
    rows_2b = load_curated("curated_2b")
    rows_3b = load_curated("curated_3b")
    rows_hr = load_curated("curated_hr")

    pitches: list[Pitch] = []
    row = pick_for_date(rows_1b, date_str, "1b")
    if row: pitches.append(build_1b(row))
    row = pick_for_date(rows_2b, date_str, "2b")
    if row: pitches.append(build_2b(row))
    row = pick_for_date(rows_3b, date_str, "3b")
    if row: pitches.append(build_3b(row))
    row = pick_for_date(rows_hr, date_str, "hr")
    if row: pitches.append(build_hr(row))

    # Puzzle number = days since launch.
    launch = dt.date(2026, 3, 10)
    puzzle_no = (d - launch).days + 1

    return Puzzle(date_str, puzzle_no, theme, pitches)


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: generate_puzzle.py YYYY-MM-DD", file=sys.stderr)
        sys.exit(2)
    date_str = sys.argv[1]
    puzzle = generate(date_str)
    out = PUZZLES / f"{date_str}.json"
    out.write_text(json.dumps(puzzle.to_dict(), indent=2) + "\n")
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
