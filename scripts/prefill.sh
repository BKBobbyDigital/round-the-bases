#!/usr/bin/env bash
# Pre-generate the next N days of puzzles so launch is buffered against
# a cron failure or rate limit. Default 14 days.
#
# Usage:
#   bash scripts/prefill.sh        # 14 days
#   bash scripts/prefill.sh 30     # custom horizon
#
# After running, `git add puzzles/ && git commit && git push` to ship.

set -euo pipefail
cd "$(dirname "$0")/.."

N=${1:-14}
echo "Pre-generating next $N day(s) of puzzles…"

for offset in $(seq 1 "$N"); do
  # Anchor "tomorrow" to ET, same as the cron.
  d=$(TZ='America/New_York' date -v+"${offset}d" +%Y-%m-%d 2>/dev/null \
    || TZ='America/New_York' date -d "+${offset} days" +%Y-%m-%d)
  if [ -f "puzzles/${d}.json" ]; then
    echo "  ✓ ${d} (already exists, skipping)"
    continue
  fi
  echo "  → ${d}"
  python3 scripts/generate_puzzle.py "${d}"
done

echo "Done."
