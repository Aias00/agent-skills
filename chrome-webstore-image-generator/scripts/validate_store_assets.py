#!/usr/bin/env python3
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

ALLOWED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
SOF_MARKERS = {
    0xC0,
    0xC1,
    0xC2,
    0xC3,
    0xC5,
    0xC6,
    0xC7,
    0xC9,
    0xCA,
    0xCB,
    0xCD,
    0xCE,
    0xCF,
}


def read_png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as f:
        header = f.read(24)
    if len(header) < 24:
        raise ValueError("PNG header too short")
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Invalid PNG signature")
    if header[12:16] != b"IHDR":
        raise ValueError("Missing PNG IHDR chunk")
    return struct.unpack(">II", header[16:24])


def read_jpeg_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as f:
        if f.read(2) != b"\xff\xd8":
            raise ValueError("Invalid JPEG signature")
        while True:
            marker_start = f.read(1)
            if not marker_start:
                break
            while marker_start == b"\xff":
                marker = f.read(1)
                if not marker:
                    break
                if marker != b"\xff":
                    break
                marker_start = marker
            if not marker:
                break
            marker_byte = marker[0]

            if marker_byte in (0xD8, 0xD9):
                continue

            seg_len_raw = f.read(2)
            if len(seg_len_raw) != 2:
                break
            seg_len = struct.unpack(">H", seg_len_raw)[0]
            if seg_len < 2:
                raise ValueError("Invalid JPEG segment length")

            if marker_byte in SOF_MARKERS:
                if len(f.read(1)) != 1:
                    raise ValueError("Invalid JPEG precision field")
                size_raw = f.read(4)
                if len(size_raw) != 4:
                    raise ValueError("Invalid JPEG frame size field")
                height, width = struct.unpack(">HH", size_raw)
                return width, height

            f.seek(seg_len - 2, 1)

    raise ValueError("Unable to locate JPEG size marker")


def get_image_size(path: Path) -> tuple[int, int]:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return read_png_size(path)
    if suffix in {".jpg", ".jpeg"}:
        return read_jpeg_size(path)
    raise ValueError(f"Unsupported image type: {suffix}")


def find_named_image(root: Path, stem: str) -> Path | None:
    for item in root.iterdir():
        if not item.is_file():
            continue
        if item.stem.lower() != stem.lower():
            continue
        if item.suffix.lower() not in ALLOWED_IMAGE_SUFFIXES:
            continue
        return item
    return None


def find_named_image_from_candidates(root: Path, stems: list[str]) -> Path | None:
    for stem in stems:
        found = find_named_image(root, stem)
        if found is not None:
            return found
    return None


def check_exact_size(errors: list[str], label: str, path: Path | None, expected: tuple[int, int]) -> None:
    if path is None:
        errors.append(f"{label}: missing")
        return
    try:
        width, height = get_image_size(path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{label}: unreadable image ({path}): {exc}")
        return
    if (width, height) != expected:
        errors.append(
            f"{label}: expected {expected[0]}x{expected[1]}, got {width}x{height} ({path.name})"
        )


def collect_screenshots(folder: Path) -> list[Path]:
    if not folder.exists() or not folder.is_dir():
        return []
    items: list[Path] = []
    for item in sorted(folder.iterdir()):
        if item.is_file() and item.suffix.lower() in ALLOWED_IMAGE_SUFFIXES:
            items.append(item)
    return items


def validate(root: Path) -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    notes: list[str] = []

    icon = find_named_image_from_candidates(root, ["icon-128x128", "icon-128"])
    small_promo = find_named_image_from_candidates(root, ["small-promo-440x280", "small-promo"])
    marquee = find_named_image_from_candidates(root, ["marquee-1400x560", "marquee"])

    if icon is not None and icon.stem == "icon-128":
        notes.append("legacy icon filename detected; prefer icon-128x128.png")
    if small_promo is not None and small_promo.stem == "small-promo":
        notes.append("legacy small promo filename detected; prefer small-promo-440x280.png")
    if marquee is not None and marquee.stem == "marquee":
        notes.append("legacy marquee filename detected; prefer marquee-1400x560.png")

    if icon is not None and icon.suffix.lower() != ".png":
        errors.append(f"store icon must be PNG: {icon.name}")

    check_exact_size(errors, "store icon (icon-128x128)", icon, (128, 128))
    check_exact_size(errors, "small promo (small-promo-440x280)", small_promo, (440, 280))

    if marquee is not None:
        check_exact_size(errors, "marquee promo (marquee-1400x560)", marquee, (1400, 560))
    else:
        notes.append("marquee promo is optional and not provided")

    screenshots = collect_screenshots(root / "screenshots")
    count = len(screenshots)
    if count < 1 or count > 5:
        errors.append(f"screenshots: expected 1-5 images, found {count} in {root / 'screenshots'}")
    else:
        for shot in screenshots:
            try:
                width, height = get_image_size(shot)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"screenshot unreadable: {shot}: {exc}")
                continue
            if (width, height) not in {(1280, 800), (640, 400)}:
                errors.append(
                    f"screenshot size invalid: {shot.name} is {width}x{height}, expected 1280x800 or 640x400"
                )

    return len(errors) == 0, errors, notes


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Chrome Web Store listing image assets.")
    parser.add_argument(
        "--root",
        default="release/store-assets",
        help="Asset root directory (default: release/store-assets)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        print(f"[FAIL] root directory not found: {root}")
        return 1

    ok, errors, notes = validate(root)

    if ok:
        print(f"[PASS] store asset validation passed: {root}")
    else:
        print(f"[FAIL] store asset validation failed: {root}")

    for note in notes:
        print(f"[NOTE] {note}")
    for err in errors:
        print(f"[ERROR] {err}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
