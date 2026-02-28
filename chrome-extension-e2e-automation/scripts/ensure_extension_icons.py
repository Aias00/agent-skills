#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import struct
import zlib
from pathlib import Path

REQUIRED_SIZES = (16, 48, 128)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Ensure extension runtime icons exist and manifest is wired to icons/icon16.png, "
            "icons/icon48.png, icons/icon128.png."
        )
    )
    parser.add_argument("--root", default=".", help="Extension root directory (default: current directory)")
    parser.add_argument("--manifest", default="manifest.json", help="Manifest path relative to --root")
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes without writing files")
    return parser.parse_args()


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack("!I", len(data))
        + kind
        + data
        + struct.pack("!I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


def write_png(path: Path, width: int, height: int, pixels: bytes) -> None:
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack("!IIBBBBB", width, height, 8, 6, 0, 0, 0)

    stride = width * 4
    scanlines = bytearray()
    for y in range(height):
        scanlines.append(0)
        scanlines.extend(pixels[y * stride : (y + 1) * stride])

    idat = zlib.compress(bytes(scanlines), level=9)
    png = signature + png_chunk(b"IHDR", ihdr) + png_chunk(b"IDAT", idat) + png_chunk(b"IEND", b"")
    path.write_bytes(png)


def palette_from_name(name: str) -> tuple[int, int, int]:
    seed = sum(ord(ch) for ch in name)
    r = 16 + (seed * 31) % 50
    g = 90 + (seed * 17) % 80
    b = 170 + (seed * 13) % 70
    return r, g, b


def render_icon(size: int, base_rgb: tuple[int, int, int]) -> bytes:
    cx = (size - 1) / 2.0
    cy = (size - 1) / 2.0
    radius = size * 0.47
    base_r, base_g, base_b = base_rgb

    out = bytearray(size * size * 4)
    for y in range(size):
        for x in range(size):
            dx = x - cx
            dy = y - cy
            dist = math.hypot(dx, dy)
            i = (y * size + x) * 4

            bg = 240 - int((y / max(1, size - 1)) * 20)
            r, g, b, a = bg, bg + 4, 248, 255

            if dist <= radius:
                t = min(1.0, dist / radius)
                r = int(base_r + 36 * t)
                g = int(base_g + 24 * t)
                b = int(base_b + 18 * t)

                # White bracket-like marks (visual cue for identifier/token)
                if size * 0.16 <= dist <= size * 0.27 and abs(dx) > size * 0.08:
                    r, g, b = 245, 249, 255
                if size * 0.32 <= dist <= size * 0.39 and abs(dy) < size * 0.04:
                    r, g, b = 245, 249, 255

            out[i : i + 4] = bytes((r, g, b, a))

    return bytes(out)


def manifest_has_required_icon_paths(manifest: dict) -> bool:
    icons = manifest.get("icons")
    if not isinstance(icons, dict):
        return False
    for size in ("16", "48", "128"):
        if icons.get(size) != f"icons/icon{size}.png":
            return False

    action = manifest.get("action")
    if not isinstance(action, dict):
        return False
    default_icon = action.get("default_icon")
    if not isinstance(default_icon, dict):
        return False
    for size in ("16", "48", "128"):
        if default_icon.get(size) != f"icons/icon{size}.png":
            return False
    return True


def files_exist(root: Path) -> bool:
    return all((root / "icons" / f"icon{size}.png").is_file() for size in REQUIRED_SIZES)


def ensure_icons(root: Path, manifest_rel: str, dry_run: bool) -> tuple[bool, list[str]]:
    manifest_path = (root / manifest_rel).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    changed = False
    logs: list[str] = []

    if manifest_has_required_icon_paths(manifest) and files_exist(root):
        logs.append("[OK] extension icons already configured")
        return changed, logs

    name = str(manifest.get("name", "Chrome Extension")).strip() or "Chrome Extension"
    base_rgb = palette_from_name(name)

    icons_dir = root / "icons"
    if not icons_dir.exists():
        changed = True
        logs.append(f"[PLAN] create directory: {icons_dir}")
        if not dry_run:
            icons_dir.mkdir(parents=True, exist_ok=True)

    for size in REQUIRED_SIZES:
        icon_path = icons_dir / f"icon{size}.png"
        if not icon_path.is_file():
            changed = True
            logs.append(f"[PLAN] generate icon: {icon_path}")
            if not dry_run:
                pixels = render_icon(size, base_rgb)
                write_png(icon_path, size, size, pixels)

    icons_map = {str(size): f"icons/icon{size}.png" for size in REQUIRED_SIZES}
    action = manifest.get("action") if isinstance(manifest.get("action"), dict) else {}
    current_icons = manifest.get("icons") if isinstance(manifest.get("icons"), dict) else {}
    current_action_icons = action.get("default_icon") if isinstance(action.get("default_icon"), dict) else {}

    if current_icons != icons_map or current_action_icons != icons_map:
        changed = True
        logs.append("[PLAN] update manifest icon mappings")
        if not dry_run:
            manifest["icons"] = icons_map
            action["default_icon"] = icons_map
            manifest["action"] = action
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not changed:
        logs.append("[OK] no icon changes needed")
    else:
        logs.append("[OK] icon bootstrap completed" if not dry_run else "[DRY-RUN] icon bootstrap planned")
    return changed, logs


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"[ERROR] root is not a directory: {root}")
        return 1

    try:
        changed, logs = ensure_icons(root, args.manifest, args.dry_run)
        for line in logs:
            print(line)
        print(f"[OK] changed: {int(changed)}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
