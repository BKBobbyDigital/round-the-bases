# Round the Bases

A daily baseball puzzle. One at-bat. Four pitches. Increasing difficulty.

```
1B  trivia        — multiple choice
2B  career arc    — multiple choice
3B  stat line     — free text (autocomplete)
HR  arsenal       — free text (autocomplete)
```

3 strikes per out, 3 outs per at-bat (9 wrong guesses max). Strikes carry
across pitches. Streaks and stats live in `localStorage`. Shareable grid:

```
Round the Bases #88
⚾⚾⚾⬜  Triple
9 swings · streak 12 🔥
```

## Layout

```
round-the-bases/
├── index.html              # vintage-style mockup, Screen 1
├── puzzles/                # daily puzzle JSONs, one per date
│   └── 2026-06-05.json
├── data/                   # curated content (CSV)
│   ├── curated_1b.csv      # trivia
│   ├── curated_2b.csv      # career arcs
│   ├── curated_3b.csv      # stat-line targets (player + season)
│   └── curated_hr.csv      # arsenal targets (pitcher + season)
└── scripts/
    └── generate_puzzle.py  # builds puzzles/YYYY-MM-DD.json
```

## Generating a puzzle

```bash
python scripts/generate_puzzle.py 2026-06-05
```

The script picks one row from each curated CSV (deterministic by date),
pulls Statcast data for the 3B/HR targets via `pybaseball`, and writes
the puzzle JSON. v0 leaves the Statcast helpers as stubs — flesh them
out once `pybaseball` is installed.

## Deploy

Static site, Netlify, deploy on git push. No backend.
