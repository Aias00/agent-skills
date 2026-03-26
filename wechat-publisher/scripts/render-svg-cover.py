#!/usr/bin/env python3
"""Render a local SVG cover to PNG using Chrome headless.

Why this exists:
- WeChat covers should stay in a wide 900x383 ratio.
- Thumbnail-style exporters can silently crop SVGs into squares.
- Font-limited SVG renderers may replace Chinese glyphs with tofu boxes.

This script uses the local browser engine to render the SVG, so custom CJK
typography and layout behave much closer to the final WeChat preview.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import re
import socketserver
import subprocess
import sys
import threading
import time
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
RESVG_PKG = SKILL_DIR / "node_modules" / "@resvg" / "resvg-js"


def parse_size(size: str) -> tuple[int, int]:
    raw = (size or "").strip().lower()
    if "x" not in raw:
        raise ValueError("Invalid size. Use WIDTHxHEIGHT, e.g. 900x383")
    w_raw, h_raw = raw.split("x", 1)
    width = int(w_raw)
    height = int(h_raw)
    if width <= 0 or height <= 0:
        raise ValueError("Width and height must be positive")
    return width, height


def parse_numeric(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", value)
    if not match:
        return None
    return max(1, round(float(match.group(1))))


def detect_svg_size(svg_path: Path) -> tuple[int, int] | None:
    try:
        root = ET.fromstring(svg_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    width = parse_numeric(root.attrib.get("width"))
    height = parse_numeric(root.attrib.get("height"))
    if width and height:
        return width, height

    view_box = root.attrib.get("viewBox") or root.attrib.get("viewbox")
    if view_box:
        parts = re.split(r"[\s,]+", view_box.strip())
        if len(parts) == 4:
            vb_width = parse_numeric(parts[2])
            vb_height = parse_numeric(parts[3])
            if vb_width and vb_height:
                return vb_width, vb_height
    return None


def resolve_chrome_path(explicit: str | None) -> str:
    candidates = [
        explicit,
        os.environ.get("WECHAT_BROWSER_CHROME_PATH"),
        os.environ.get("CHROME_PATH"),
        Path.home().joinpath(".local/bin/chrome"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        if path.exists():
            return str(path)

    raise FileNotFoundError(
        "Chrome not found. Set WECHAT_BROWSER_CHROME_PATH or install Google Chrome / Microsoft Edge."
    )


def resolve_js_runtime() -> str | None:
    candidates = [
        os.environ.get("WECHAT_JS_RUNTIME"),
        "node",
        "bun",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        result = subprocess.run(
            [candidate, "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return candidate
    return None


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # pragma: no cover
        return


def start_http_server(directory: Path) -> tuple[socketserver.TCPServer, int]:
    handler = functools.partial(QuietHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, int(server.server_address[1])


def render_svg_to_png_via_resvg(svg_path: Path, out_path: Path, width: int) -> bool:
    if not RESVG_PKG.exists():
        return False

    runtime = resolve_js_runtime()
    if not runtime:
        return False

    js = f"""
const fs = require("node:fs");
const {{ Resvg }} = require({json.dumps(str(RESVG_PKG))});
const svg = fs.readFileSync({json.dumps(str(svg_path))}, "utf8");
const resvg = new Resvg(svg, {{ fitTo: {{ mode: "width", value: {width} }} }});
const pngData = resvg.render();
fs.writeFileSync({json.dumps(str(out_path))}, pngData.asPng());
"""

    result = subprocess.run(
        [runtime, "-e", js],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"resvg render failed: {stderr}")
    if not out_path.exists():
        raise RuntimeError(f"Rendered cover missing: {out_path}")
    return True


def build_wrapper_html(svg_name: str, width: int, height: int) -> str:
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
      html, body {{
        margin: 0;
        padding: 0;
        width: {width}px;
        height: {height}px;
        overflow: hidden;
        background: transparent;
      }}
      img {{
        display: block;
        width: {width}px;
        height: {height}px;
        object-fit: fill;
      }}
    </style>
  </head>
  <body>
    <img src="{quote(svg_name)}" alt="cover" />
  </body>
</html>
"""


def render_svg_to_png(svg_path: Path, out_path: Path, width: int, height: int, chrome_path: str) -> None:
    server, port = start_http_server(svg_path.parent)
    wrapper_path: Path | None = None
    try:
        time.sleep(0.15)
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".html",
            prefix="svg-cover-",
            dir=svg_path.parent,
            encoding="utf-8",
            delete=False,
        ) as handle:
            handle.write(build_wrapper_html(svg_path.name, width, height))
            wrapper_path = Path(handle.name)

        url = f"http://127.0.0.1:{port}/{quote(wrapper_path.name)}"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            chrome_path,
            "--headless",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            "--no-first-run",
            "--no-default-browser-check",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=1200",
            f"--window-size={width},{height}",
            f"--screenshot={out_path}",
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            stderr = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(f"Chrome render failed: {stderr}")
        if not out_path.exists():
            raise RuntimeError(f"Output PNG not found: {out_path}")
    finally:
        if wrapper_path and wrapper_path.exists():
            wrapper_path.unlink(missing_ok=True)
        server.shutdown()
        server.server_close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a local SVG cover to PNG via Chrome headless")
    parser.add_argument("--svg", required=True, help="Input SVG file")
    parser.add_argument("--out", help="Output PNG path; default: same name with .png")
    parser.add_argument("--size", help="Output size WIDTHxHEIGHT; defaults to SVG width/height or 900x383")
    parser.add_argument("--chrome", help="Chrome binary path override")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    svg_path = Path(args.svg).expanduser().resolve()
    if not svg_path.exists():
        print(f"[ERROR] SVG not found: {svg_path}", file=sys.stderr)
        return 1

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
    else:
        out_path = svg_path.with_suffix(".png")

    if args.size:
        width, height = parse_size(args.size)
    else:
        width, height = detect_svg_size(svg_path) or (900, 383)

    try:
        if render_svg_to_png_via_resvg(svg_path, out_path, width):
            print("[OK] svg cover rendered via resvg")
            print(f"[OUT] {out_path}")
            print(f"[SIZE] {width}x{height}")
            return 0

        chrome_path = resolve_chrome_path(args.chrome)
        render_svg_to_png(svg_path, out_path, width, height, chrome_path)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print("[OK] svg cover rendered")
    print(f"[OUT] {out_path}")
    print(f"[SIZE] {width}x{height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
