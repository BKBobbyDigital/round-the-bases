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

def _split_name(player: str) -> tuple[str, str]:
    """'Clayton Kershaw' -> ('Clayton', 'Kershaw'); 'R.A. Dickey' -> ('R.A.', 'Dickey')."""
    parts = player.strip().split(" ", 1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def _normalize_for_match(s: str) -> str:
    """Lowercase, strip accents, drop punctuation/whitespace.

    Chadwick stores some Hispanic names with accents (Hernández, Acuña),
    while our CSVs and most US sources use the ASCII form. We compare on
    the ASCII-only, alphanumeric-only form so both sides match.
    """
    import re, unicodedata
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


_CHADWICK_CACHE = None
def _chadwick():
    global _CHADWICK_CACHE
    if _CHADWICK_CACHE is None:
        from pybaseball import chadwick_register
        df = chadwick_register(save=False)
        df = df[df["mlb_played_first"].notna()].copy()
        df["_first_norm"] = df["name_first"].fillna("").apply(_normalize_for_match)
        df["_last_norm"]  = df["name_last"].fillna("").apply(_normalize_for_match)
        _CHADWICK_CACHE = df
    return _CHADWICK_CACHE


def _mlbam_id(player: str) -> int:
    """Look up an MLBAM id with accent-insensitive matching against Chadwick."""
    first, last = _split_name(player)
    df = _chadwick()
    fn, ln = _normalize_for_match(first), _normalize_for_match(last)
    matches = df[df["_last_norm"] == ln]
    if not matches.empty:
        exact = matches[matches["_first_norm"] == fn]
        if not exact.empty: matches = exact
        else:
            partial = matches[matches["_first_norm"].str.contains(fn, na=False)]
            if not partial.empty: matches = partial
    if matches.empty:
        raise ValueError(f"player not found: {player!r}")
    if "mlb_played_last" in matches.columns:
        matches = matches.sort_values("mlb_played_last", ascending=False)
    return int(matches.iloc[0]["key_mlbam"])


def fetch_pitcher_arsenal(player: str, season: int) -> list[dict]:
    """Group pitch-level Statcast data into a usage/velo arsenal."""
    from pybaseball import statcast_pitcher
    pid = _mlbam_id(player)
    df = statcast_pitcher(f"{season}-03-01", f"{season}-11-15", pid)
    if df is None or df.empty:
        raise ValueError(f"no Statcast data: {player!r} {season}")
    df = df.dropna(subset=["pitch_type"])
    total = len(df)
    arsenal: list[dict] = []
    for pt, grp in df.groupby("pitch_type"):
        usage = round(len(grp) / total * 100)
        if usage < 2:                     # drop trace pitches
            continue
        name = grp["pitch_name"].dropna().iloc[0] if "pitch_name" in grp.columns and not grp["pitch_name"].dropna().empty else pt
        speed = round(float(grp["release_speed"].mean()), 1)
        arsenal.append({
            "emoji": PITCH_EMOJI.get(pt, "⚾"),
            "name": str(name),
            "speed": speed,
            "usage": usage,
        })
    arsenal.sort(key=lambda x: -x["usage"])
    return arsenal


def fetch_batter_stat_line(player: str, season: int) -> str:
    """Pull AVG / HR / RBI / SB for a player-season.

    Fangraphs blocks scrapers, so we try Baseball-Reference first,
    then fall back to the offline Lahman dataset.
    """
    needle = player.lower().strip()

    # Try Baseball-Reference.
    try:
        from pybaseball import batting_stats_bref
        df = batting_stats_bref(season)
        rows = df[df["Name"].str.lower().str.contains(needle, na=False)]
        if not rows.empty:
            r = rows.iloc[0]
            avg = f"{float(r['BA']):.3f}".lstrip("0")
            return f"{avg} / {int(r['HR'])} HR / {int(r['RBI'])} RBI / {int(r['SB'])} SB"
    except Exception:
        pass

    # Fall back to Lahman (offline, ships with pybaseball).
    from pybaseball.lahman import batting, people
    p = people()
    bat = batting()
    pid_rows = p[(p["nameFirst"] + " " + p["nameLast"]).str.lower() == needle]
    if pid_rows.empty:
        raise ValueError(f"batter not found in Lahman: {player!r}")
    pid = pid_rows.iloc[0]["playerID"]
    season_rows = bat[(bat["playerID"] == pid) & (bat["yearID"] == season)]
    if season_rows.empty:
        raise ValueError(f"no {season} season for {player!r} in Lahman")
    # Combine stints if traded mid-season.
    agg = season_rows[["AB", "H", "HR", "RBI", "SB"]].sum()
    avg_val = (agg["H"] / agg["AB"]) if agg["AB"] else 0.0
    avg = f"{avg_val:.3f}".lstrip("0")
    return f"{avg} / {int(agg['HR'])} HR / {int(agg['RBI'])} RBI / {int(agg['SB'])} SB"


# --- CURATED CSV LOADERS ------------------------------------------------------

def load_curated(name: str) -> list[dict]:
    """Load a curated CSV by name (e.g. 'curated_1b'). Empty list if missing."""
    p = DATA / f"{name}.csv"
    if not p.exists():
        return []
    with p.open() as f:
        return list(csv.DictReader(f))


def _answer_of(row: dict) -> str:
    """The canonical answer for a row — varies by tier CSV format."""
    return (row.get("answer") or row.get("player") or "").strip().lower()


def pick_for_date(rows: list[dict], date_str: str, salt: str,
                  recent_answers: set[str] | None = None,
                  retries: int = 16) -> dict | None:
    """
    Deterministic daily pick that avoids repeating any answer used in the
    recent window (default: last 7 days). When the first sha256-salted pick
    collides, we retry with a numeric suffix until we land on a fresh
    answer or exhaust the budget — still fully deterministic per (date,
    salt, recent_answers).
    """
    if not rows:
        return None
    import hashlib
    recent_answers = recent_answers or set()
    for attempt in range(retries):
        s = salt if attempt == 0 else f"{salt}#{attempt}"
        h = hashlib.sha256(f"{date_str}:{s}".encode()).hexdigest()
        candidate = rows[int(h[:8], 16) % len(rows)]
        if _answer_of(candidate) not in recent_answers:
            return candidate
    # All retries collided (unlikely with a 30-row pool and 7-day window).
    # Fall back to the unsalted pick rather than fail the build.
    h = hashlib.sha256(f"{date_str}:{salt}".encode()).hexdigest()
    return rows[int(h[:8], 16) % len(rows)]


def load_recent_answers(date_str: str, window: int = 7) -> dict[str, set[str]]:
    """Look at the previous `window` days of puzzles and bucket the answers
    by tier so the picker can avoid repeating any of them."""
    import datetime as dt
    out: dict[str, set[str]] = {"1B": set(), "2B": set(), "3B": set(), "HR": set()}
    today = dt.date.fromisoformat(date_str)
    for offset in range(1, window + 1):
        prior = (today - dt.timedelta(days=offset)).isoformat()
        p = PUZZLES / f"{prior}.json"
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue
        for pitch in data.get("pitches", []):
            tier = pitch.get("tier")
            ans = pitch.get("answer")
            if tier in out and ans:
                out[tier].add(ans.strip().lower())
    return out


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
    # Prefer the baked stat line — the CSV is the source of truth so the
    # pipeline doesn't depend on a flaky scraper for canonical stats.
    # Fall back to a live fetch only if the column is missing.
    stat_line = (row.get("stats") or "").strip() or fetch_batter_stat_line(row["player"], season)
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

    recent = load_recent_answers(date_str)

    pitches: list[Pitch] = []
    row = pick_for_date(rows_1b, date_str, "1b", recent["1B"])
    if row: pitches.append(build_1b(row))
    row = pick_for_date(rows_2b, date_str, "2b", recent["2B"])
    if row: pitches.append(build_2b(row))
    row = pick_for_date(rows_3b, date_str, "3b", recent["3B"])
    if row: pitches.append(build_3b(row))
    row = pick_for_date(rows_hr, date_str, "hr", recent["HR"])
    if row: pitches.append(build_hr(row))

    # Puzzle number = days since launch.
    launch = dt.date(2026, 6, 5)
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
