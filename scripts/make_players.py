"""
Dump every MLB player from pybaseball's Chadwick Bureau register as a
static JSON array used by the front-end autocomplete.

The Chadwick register has ~22k people; we filter to those who actually
appeared in MLB (mlb_played_first is set), which lands around 12k unique
'First Last' strings. That's plenty for any answer in the curated CSVs
and any era a stat-line puzzle might reference.

Run once after pybaseball updates its cached register; re-run when you
want the latest rookies in the dropdown.

Output:
    players.json   (UTF-8 JSON array of strings, sorted)
"""

from __future__ import annotations
import json
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "players.json"


def main() -> None:
    from pybaseball import chadwick_register
    df = chadwick_register(save=False)

    # MLB-only — drop everyone who never reached MLB.
    df = df[df["mlb_played_first"].notna()]

    # Build "First Last" strings, drop blanks/dupes.
    df = df.copy()
    df["name"] = (
        df["name_first"].fillna("").str.strip().str.title()
        + " "
        + df["name_last"].fillna("").str.strip().str.title()
    ).str.strip()
    names = sorted({n for n in df["name"] if len(n) > 1})

    # Lightweight title-casing fix-ups for known forms — Chadwick stores everything
    # lowercase, so 'r. a.' becomes 'R. A.' rather than the iconic 'R.A.'.
    fixups = {
        "R. A. Dickey": "R.A. Dickey",
        "C. C. Sabathia": "CC Sabathia",
        "J. T. Realmuto": "J.T. Realmuto",
        "J. D. Martinez": "J.D. Martinez",
        "J. P. Crawford": "J.P. Crawford",
        "A. J. Pollock": "A.J. Pollock",
        "A. J. Burnett": "A.J. Burnett",
        "B. J. Upton": "B.J. Upton",
    }
    names = [fixups.get(n, n) for n in names]
    names = sorted(set(names))

    OUT.write_text(json.dumps(names, ensure_ascii=False))
    kb = OUT.stat().st_size // 1024
    print(f"wrote players.json — {len(names):,} names ({kb} KB)")


if __name__ == "__main__":
    main()
