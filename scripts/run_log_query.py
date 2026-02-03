#!/usr/bin/env python3
"""run_log_query - get recent run records or a specific episode.

Usage:
  python scripts/run_log_query.py --recent 10
  python scripts/run_log_query.py --episode <episode_id>
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.run_log import get_recent_runs, get_run_detail  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--recent", type=int, default=0, help="number of recent runs to show")
    ap.add_argument("--episode", default="", help="episode_id to detail")
    args = ap.parse_args()

    if args.episode:
        print(json.dumps(get_run_detail(args.episode), indent=2))
        return 0

    if args.recent:
        print(json.dumps(get_recent_runs(limit=args.recent), indent=2))
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
