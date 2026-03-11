#!/usr/bin/env python3
"""
Load optional EXTEND.md preferences for toutiao-publisher.

Priority:
1) Project-level: <cwd>/.baoyu-skills/toutiao-publisher/EXTEND.md
2) User-level:    ~/.baoyu-skills/toutiao-publisher/EXTEND.md
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple


PROJECT_EXTEND = Path(".baoyu-skills/toutiao-publisher/EXTEND.md")
USER_EXTEND = Path.home() / ".baoyu-skills/toutiao-publisher/EXTEND.md"


def parse_extend_file(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    if not path.exists():
        return data

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if ":" in line:
            key, value = line.split(":", 1)
        elif "=" in line:
            key, value = line.split("=", 1)
        else:
            continue

        data[key.strip().lower()] = value.strip()

    return data


def find_extend_file() -> Optional[Path]:
    project = (Path.cwd() / PROJECT_EXTEND).resolve()
    if project.exists():
        return project
    if USER_EXTEND.exists():
        return USER_EXTEND
    return None


def load_extend_settings() -> Tuple[Optional[Path], Dict[str, str]]:
    path = find_extend_file()
    if not path:
        return None, {}
    return path, parse_extend_file(path)


def to_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    v = str(value).strip().lower()
    if v in {"1", "true", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "no", "n", "off"}:
        return False
    return default


def to_int(value: Optional[str], default: int) -> int:
    if value is None:
        return default
    try:
        return int(str(value).strip())
    except Exception:
        return default

