#!/usr/bin/env python3
"""Fail if banned Chinese scaffolding patterns remain in prose."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("不是……而是……", re.compile(r"不是[^。！？\n]{0,80}而是")),
    ("不只是……而是……", re.compile(r"不只是[^。！？\n]{0,80}而是")),
    ("如果只", re.compile(r"如果只")),
    ("也就是说", re.compile(r"也就是说")),
    ("这一步很关键", re.compile(r"这一步很关键")),
]


@dataclass
class Hit:
    line_no: int
    label: str
    excerpt: str


def iter_prose_lines(text: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    in_fence = False
    for idx, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped.startswith(">"):
            continue
        lines.append((idx, raw))
    return lines


def find_hits(text: str) -> list[Hit]:
    hits: list[Hit] = []
    for line_no, line in iter_prose_lines(text):
        for label, pattern in PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            start = max(0, match.start() - 18)
            end = min(len(line), match.end() + 18)
            excerpt = line[start:end].strip()
            hits.append(Hit(line_no=line_no, label=label, excerpt=excerpt))
    return hits


def read_text(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    return sys.stdin.read()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check rewritten Chinese prose for banned scaffolding patterns."
    )
    parser.add_argument("--input", help="Path to the text or markdown file to check")
    args = parser.parse_args()

    text = read_text(args.input)
    hits = find_hits(text)

    if not hits:
        print("OK: no banned scaffolding patterns found in prose")
        return 0

    print("Blocked: banned scaffolding patterns found", file=sys.stderr)
    for hit in hits:
        print(
            f"line {hit.line_no}: {hit.label} -> {hit.excerpt}",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
