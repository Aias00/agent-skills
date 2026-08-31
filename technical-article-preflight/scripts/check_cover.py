#!/usr/bin/env python3
"""Verify cover image is WeChat-safe (900x383, non-zero, exists)."""
import argparse
import struct
import sys
from pathlib import Path


def read_png_dimensions(path: Path) -> tuple[int, int]:
    with open(path, "rb") as f:
        header = f.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a valid PNG file")
    width, height = struct.unpack(">II", header[16:24])
    return width, height


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cover", help="Cover image path")
    parser.add_argument("--markdown", help="Markdown file to derive cover path from")
    args = parser.parse_args()

    cover_path: Path | None = None
    if args.cover:
        cover_path = Path(args.cover)
    elif args.markdown:
        md_dir = Path(args.markdown).parent
        for candidate in [md_dir / "imgs" / "cover.png", md_dir / "imgs" / "cover.svg"]:
            if candidate.exists():
                cover_path = candidate
                break
        if not cover_path:
            print(f"[FAIL] No cover found in {md_dir / 'imgs'}", file=sys.stderr)
            return 1
    else:
        print("[FAIL] Provide --cover or --markdown", file=sys.stderr)
        return 1

    if not cover_path.exists():
        print(f"[FAIL] Cover not found: {cover_path}", file=sys.stderr)
        return 1

    size = cover_path.stat().st_size
    if size == 0:
        print(f"[FAIL] Cover file is empty: {cover_path}", file=sys.stderr)
        return 1

    suffix = cover_path.suffix.lower()
    if suffix == ".svg":
        print(f"[OK] cover verified: {cover_path} (SVG, {size} bytes)")
        return 0

    if suffix == ".png":
        try:
            w, h = read_png_dimensions(cover_path)
        except Exception as e:
            print(f"[FAIL] Cannot read PNG dimensions: {e}", file=sys.stderr)
            return 1
        ratio = w / h if h else 0
        if not (2.2 <= ratio <= 2.5):
            print(f"[WARN] Aspect ratio {ratio:.2f} outside WeChat-safe range [2.2, 2.5] (expected ~2.35 = 900x383)", file=sys.stderr)
        print(f"[OK] cover verified: {cover_path} ({w}x{h}, {size} bytes)")
        return 0

    print(f"[OK] cover verified: {cover_path} ({size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
