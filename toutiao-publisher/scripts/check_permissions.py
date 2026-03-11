#!/usr/bin/env python3
"""
Pre-flight checks for toutiao-publisher.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from pathlib import Path
from typing import List, Tuple

from config import DATA_DIR, BROWSER_STATE_DIR, BROWSER_PROFILE_DIR


Result = Tuple[str, bool, str]


def check_python_version() -> Result:
    ok = sys.version_info >= (3, 9)
    return (
        "Python version",
        ok,
        f"{sys.version.split()[0]} (need >= 3.9)",
    )


def check_module(module_name: str) -> Result:
    ok = importlib.util.find_spec(module_name) is not None
    return (f"Module: {module_name}", ok, "installed" if ok else "missing")


def check_dir_writable(path: Path, label: str) -> Result:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return (label, True, f"writable: {path}")
    except Exception as e:
        return (label, False, f"not writable: {path} ({e})")


def check_chrome_presence() -> Result:
    candidates = [
        shutil.which("google-chrome"),
        shutil.which("chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    found = next((c for c in candidates if c and os.path.exists(c)), None)
    return ("Chrome binary", bool(found), found or "not found in common locations")


def render(results: List[Result]) -> int:
    print("Toutiao Publisher Pre-flight")
    print("-" * 64)
    failed = 0
    for name, ok, info in results:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}: {info}")
        if not ok:
            failed += 1
    print("-" * 64)
    if failed:
        print(f"{failed} check(s) failed")
        return 1
    print("All checks passed")
    return 0


def main() -> int:
    results: List[Result] = [
        check_python_version(),
        check_module("patchright"),
        check_module("dotenv"),
        check_chrome_presence(),
        check_dir_writable(DATA_DIR, "Data directory"),
        check_dir_writable(BROWSER_STATE_DIR, "Browser state directory"),
        check_dir_writable(BROWSER_PROFILE_DIR, "Browser profile directory"),
    ]
    return render(results)


if __name__ == "__main__":
    raise SystemExit(main())

