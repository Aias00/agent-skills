#!/usr/bin/env python3
"""Verify generated HTML structure: H1 removed, tags balanced."""
import argparse
import re
import sys
from pathlib import Path


def strip_code_blocks(html: str) -> str:
    html = re.sub(r"<pre[^>]*>.*?</pre>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<code[^>]*>.*?</code>", "", html, flags=re.DOTALL | re.IGNORECASE)
    return html


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", required=True)
    args = parser.parse_args()

    html_path = Path(args.html)
    if not html_path.exists():
        print(f"[FAIL] HTML not found: {html_path}", file=sys.stderr)
        return 1

    html = html_path.read_text(encoding="utf-8")
    errors: list[str] = []

    h1_count = len(re.findall(r"<h1[\s>]", html, re.IGNORECASE))
    if h1_count > 0:
        errors.append(f"H1 tags found: {h1_count} (expected 0 — formatter strips H1)")

    cleaned = strip_code_blocks(html)
    for tag in ["table", "pre", "blockquote", "ul", "ol", "div"]:
        opens = len(re.findall(rf"<{tag}[\s>]", cleaned, re.IGNORECASE))
        closes = len(re.findall(rf"</{tag}\s*>", cleaned, re.IGNORECASE))
        if opens != closes:
            errors.append(f"<{tag}> tag imbalance: {opens} open / {closes} close")

    if errors:
        for e in errors:
            print(f"[FAIL] {e}", file=sys.stderr)
        return 1

    print("[OK] html structure verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
