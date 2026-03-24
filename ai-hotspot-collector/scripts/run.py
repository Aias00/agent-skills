#!/usr/bin/env python3
"""
Unified entry for ai-hotspot-collector helper scripts.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
FETCH_SCRIPT = SCRIPT_DIR / "fetch_all.py"
PUBLISH_SCRIPT = SCRIPT_DIR / "publish_candidate.py"

USAGE = """Usage:
  python3 ai-hotspot-collector/scripts/run.py fetch [fetch options]
  python3 ai-hotspot-collector/scripts/run.py publish <content-root-or-candidate-or-file> [publish options]

Commands:
  fetch    Aggregate candidates from multiple source skills
  publish  Publish an approved draft from the aggregated queue
"""


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help", "help"}:
        print(USAGE)
        return
    command = sys.argv[1].strip().lower()
    passthrough_args = sys.argv[2:]
    if command == "fetch":
        target = FETCH_SCRIPT
    elif command == "publish":
        target = PUBLISH_SCRIPT
    else:
        print(f"Unsupported command: {command}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        sys.exit(1)
    result = subprocess.run([sys.executable, str(target), *passthrough_args])
    if result.returncode != 0:
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
