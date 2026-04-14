#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


VALID_LAYOUTS = {
    "title-only",
    "title-body",
    "two-column",
    "bullets",
    "comparison",
    "timeline",
    "metrics",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve, validate, render, and publish doc-to-slides workflow artifacts."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    resolve = subparsers.add_parser("resolve-source")
    resolve.add_argument("--doc-url")
    resolve.add_argument("--doc-token")
    resolve.add_argument("--doc-name")
    resolve.add_argument("--run-dir", required=True)

    fetch = subparsers.add_parser("fetch")
    fetch.add_argument("--resolved-source", required=True)
    fetch.add_argument("--run-dir", required=True)

    validate = subparsers.add_parser("validate-outline")
    validate.add_argument("--outline", required=True)

    render = subparsers.add_parser("render")
    render.add_argument("--outline", required=True)
    render.add_argument("--run-dir", required=True)

    publish = subparsers.add_parser("publish")
    publish.add_argument("--outline", required=True)
    publish.add_argument("--slides-json", required=True)
    publish.add_argument("--run-dir", required=True)
    publish.add_argument("--target-slides-url")

    return parser.parse_args(argv)


def validate_outline(outline: dict) -> None:
    for slide in outline.get("slides", []):
        layout = slide.get("layout")
        if layout not in VALID_LAYOUTS:
            raise ValueError(f"invalid layout: {layout}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.command == "resolve-source":
        sources = [value for value in (args.doc_url, args.doc_token, args.doc_name) if value]
        if len(sources) != 1:
            raise SystemExit(2)
        return 0

    if args.command == "validate-outline":
        outline = json.loads(Path(args.outline).read_text(encoding="utf-8"))
        validate_outline(outline)
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
