#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ALLOWED_OUTPUT_SUFFIXES = {".png", ".jpg", ".jpeg"}

ICON_NAME = "icon-128x128.png"
SMALL_PROMO_NAME = "small-promo-440x280.png"
MARQUEE_NAME = "marquee-1400x560.png"

LEGACY_AND_CURRENT_ROOT_OUTPUTS = {
    "icon-128.png",
    ICON_NAME,
    "small-promo.png",
    SMALL_PROMO_NAME,
    "marquee.png",
    MARQUEE_NAME,
}

ICON_KEYWORDS = ("icon", "logo", "favicon", "appicon", "brand")
SCREENSHOT_KEYWORDS = ("screenshot", "screen-shot", "screen_shot", "capture", "screen", "shot")
SCREENSHOT_FILE_RE = re.compile(r"^screenshot-(\d+)-(\d+)x(\d+)\.png$", re.IGNORECASE)


def run(cmd: list[str]) -> str:
    completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return completed.stdout


def require_sips() -> None:
    if shutil.which("sips") is None:
        raise RuntimeError(
            "sips not found. This script currently targets macOS. "
            "Install/enable sips or use a Pillow-based workflow."
        )


def parse_sips_dimension(output: str, key: str) -> int:
    for line in output.splitlines():
        line = line.strip()
        if line.startswith(f"{key}:"):
            return int(line.split(":", 1)[1].strip())
    raise ValueError(f"Unable to parse {key} from sips output")


def read_image_size(path: Path) -> tuple[int, int]:
    out = run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)])
    width = parse_sips_dimension(out, "pixelWidth")
    height = parse_sips_dimension(out, "pixelHeight")
    return width, height


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def to_png(src: Path, out: Path) -> None:
    run(["sips", "-s", "format", "png", str(src), "--out", str(out)])


def cover_resize(src: Path, out: Path, target_w: int, target_h: int) -> None:
    src_w, src_h = read_image_size(src)
    if src_w <= 0 or src_h <= 0:
        raise ValueError(f"Invalid source dimensions: {src}")

    scale = max(target_w / src_w, target_h / src_h)
    resized_w = max(target_w, math.ceil(src_w * scale))
    resized_h = max(target_h, math.ceil(src_h * scale))

    with tempfile.TemporaryDirectory(prefix="cws-assets-") as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        png_src = tmp_dir_path / "source.png"
        png_scaled = tmp_dir_path / "scaled.png"

        to_png(src, png_src)
        run(
            [
                "sips",
                "-z",
                str(resized_h),
                str(resized_w),
                str(png_src),
                "--out",
                str(png_scaled),
            ]
        )
        run(
            [
                "sips",
                "-c",
                str(target_h),
                str(target_w),
                str(png_scaled),
                "--out",
                str(out),
            ]
        )


def parse_size(value: str) -> tuple[int, int]:
    token = value.lower().strip().replace(" ", "")
    if "x" not in token:
        raise argparse.ArgumentTypeError("Size must be WIDTHxHEIGHT, e.g. 1280x800")
    w_str, h_str = token.split("x", 1)
    try:
        width = int(w_str)
        height = int(h_str)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Size must use integers, e.g. 1280x800") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("Width/height must be > 0")
    return width, height


def validate_source(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Source image not found: {path}")


def has_icon_keyword(path: Path) -> bool:
    stem = path.stem.lower().replace("_", "-")
    return any(keyword in stem for keyword in ICON_KEYWORDS)


def has_screenshot_keyword(path: Path) -> bool:
    stem = path.stem.lower().replace("_", "-")
    return any(keyword in stem for keyword in SCREENSHOT_KEYWORDS)


def pick_icon_source(input_paths: list[Path], allow_icon_fallback: bool) -> Path:
    scored_by_keyword: list[tuple[float, int, int, Path]] = []
    scored_by_shape: list[tuple[float, int, int, Path]] = []

    for index, path in enumerate(input_paths):
        width, height = read_image_size(path)
        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid source dimensions: {path}")

        square_delta = abs((width / height) - 1.0)
        min_side = min(width, height)
        score = (square_delta, min_side, index, path)

        if has_icon_keyword(path):
            scored_by_keyword.append(score)
        if square_delta <= 0.2:
            scored_by_shape.append(score)

    def pick_best(candidates: list[tuple[float, int, int, Path]]) -> Path:
        best = min(candidates, key=lambda item: (item[0], -item[1], item[2]))
        return best[3]

    if scored_by_keyword:
        return pick_best(scored_by_keyword)
    if scored_by_shape:
        candidate = pick_best(scored_by_shape)
        if has_screenshot_keyword(candidate):
            raise ValueError(
                "Icon source looks like a screenshot by filename. "
                "Pass --icon-source with a dedicated icon/logo, or rename source file."
            )
        return candidate
    if len(input_paths) == 1:
        if allow_icon_fallback:
            print(
                "[WARN] Unable to infer icon source from a square/icon-like file. "
                "Using the only provided input as icon source due to --allow-icon-fallback.",
                file=sys.stderr,
            )
            return input_paths[0]
        raise ValueError(
            "Unable to infer icon source from a single non-icon input. "
            "Pass --icon-source with a dedicated icon/logo (recommended). "
            "If you really want fallback behavior, add --allow-icon-fallback."
        )

    raise ValueError(
        "Unable to infer icon source from multiple non-square inputs. "
        "Pass --icon-source with a dedicated icon or logo image."
    )


def clean_screenshots_dir(folder: Path, preserve: set[Path] | None = None) -> None:
    keep = {path.resolve() for path in (preserve or set())}
    if not folder.exists():
        return
    for item in folder.iterdir():
        if not item.is_file() or item.suffix.lower() not in ALLOWED_OUTPUT_SUFFIXES:
            continue
        if item.resolve() in keep:
            continue
        item.unlink()


def list_existing_screenshots(folder: Path) -> list[tuple[int, Path]]:
    if not folder.exists():
        return []
    snapshots: list[tuple[int, Path]] = []
    for item in folder.iterdir():
        if not item.is_file():
            continue
        matched = SCREENSHOT_FILE_RE.match(item.name)
        if not matched:
            continue
        snapshots.append((int(matched.group(1)), item))
    return sorted(snapshots, key=lambda item: item[0])


def clean_root_outputs(root: Path) -> None:
    if not root.exists():
        return
    for name in LEGACY_AND_CURRENT_ROOT_OUTPUTS:
        candidate = root / name
        if candidate.exists() and candidate.is_file():
            candidate.unlink()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate Chrome Web Store listing assets from one or more source images "
            "(icon-128x128, screenshots, small-promo-440x280, optional marquee-1400x560)."
        )
    )
    parser.add_argument(
        "--inputs",
        nargs="+",
        required=True,
        help=(
            "One or more source image paths. Icon source is auto-selected from icon/logo-like "
            "or near-square inputs unless --icon-source is provided."
        ),
    )
    parser.add_argument(
        "--root",
        default="release/store-assets",
        help="Output root directory (default: release/store-assets)",
    )
    parser.add_argument(
        "--screenshot-size",
        type=parse_size,
        default=(1280, 800),
        help="Screenshot size, e.g. 1280x800 or 640x400 (default: 1280x800)",
    )
    parser.add_argument(
        "--max-screenshots",
        type=int,
        default=5,
        help="Maximum screenshots to generate from inputs (default: 5)",
    )
    parser.add_argument(
        "--include-marquee",
        action="store_true",
        help="Generate optional marquee-1400x560.png",
    )
    parser.add_argument(
        "--icon-source",
        help="Explicit source image for icon-128x128.png (recommended when inputs are screenshots)",
    )
    parser.add_argument(
        "--allow-icon-fallback",
        action="store_true",
        help=(
            "Allow single-input fallback for icon selection when no icon/logo-like source is detected. "
            "Use only when you intentionally want icon derived from the sole input."
        ),
    )
    parser.add_argument(
        "--small-promo-source",
        help="Override source image for small-promo-440x280.png",
    )
    parser.add_argument(
        "--marquee-source",
        help="Override source image for marquee-1400x560.png",
    )
    parser.add_argument(
        "--append-screenshots",
        action="store_true",
        help=(
            "Deprecated compatibility flag. Append is now the default screenshot behavior."
        ),
    )
    parser.add_argument(
        "--overwrite-screenshots",
        action="store_true",
        help=(
            "Clear existing screenshots and regenerate from screenshot-1. "
            "Use this when deterministic replacement is preferred."
        ),
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    require_sips()

    if args.max_screenshots < 1:
        print("[ERROR] --max-screenshots must be >= 1", file=sys.stderr)
        return 1

    input_paths = [Path(p).expanduser().resolve() for p in args.inputs]
    for p in input_paths:
        validate_source(p)

    root = Path(args.root).expanduser().resolve()
    shots_dir = root / "screenshots"
    ensure_dir(root)
    ensure_dir(shots_dir)
    clean_root_outputs(root)

    append_mode = not args.overwrite_screenshots
    if args.append_screenshots and args.overwrite_screenshots:
        print(
            "[WARN] Both --append-screenshots and --overwrite-screenshots were provided; "
            "using overwrite mode.",
            file=sys.stderr,
        )

    existing: list[tuple[int, Path]] = []
    existing_count = 0
    next_index = 1
    available_slots = args.max_screenshots
    if append_mode:
        existing = list_existing_screenshots(shots_dir)
        existing_count = len(existing)
        next_index = existing[-1][0] + 1 if existing else 1
        available_slots = max(0, args.max_screenshots - existing_count)
    else:
        clean_screenshots_dir(shots_dir, preserve=set(input_paths))

    first = input_paths[0]
    icon_source = (
        Path(args.icon_source).expanduser().resolve()
        if args.icon_source
        else pick_icon_source(input_paths, allow_icon_fallback=args.allow_icon_fallback)
    )
    small_promo_source = (
        Path(args.small_promo_source).expanduser().resolve() if args.small_promo_source else first
    )
    marquee_source = Path(args.marquee_source).expanduser().resolve() if args.marquee_source else first

    for p in (icon_source, small_promo_source, marquee_source):
        validate_source(p)

    icon_out = root / ICON_NAME
    small_promo_out = root / SMALL_PROMO_NAME

    cover_resize(icon_source, icon_out, 128, 128)
    cover_resize(small_promo_source, small_promo_out, 440, 280)

    if args.include_marquee:
        cover_resize(marquee_source, root / MARQUEE_NAME, 1400, 560)

    screenshot_w, screenshot_h = args.screenshot_size
    screenshot_candidates = input_paths
    if len(input_paths) > 1:
        screenshot_candidates = [path for path in input_paths if path != icon_source]
        if not screenshot_candidates:
            screenshot_candidates = input_paths
    if append_mode and existing:
        existing_paths = {path.resolve() for _, path in existing}
        screenshot_candidates = [path for path in screenshot_candidates if path.resolve() not in existing_paths]

    screenshot_sources = screenshot_candidates[:available_slots]
    if not screenshot_sources:
        if append_mode and existing_count > 0:
            print(
                "[WARN] No new screenshot sources appended; keeping existing screenshots as-is.",
                file=sys.stderr,
            )
        else:
            raise ValueError("No screenshot sources available. Provide at least one image input.")

    for offset, src in enumerate(screenshot_sources):
        index = next_index + offset
        out = shots_dir / f"screenshot-{index}-{screenshot_w}x{screenshot_h}.png"
        cover_resize(src, out, screenshot_w, screenshot_h)

    print(f"[OK] generated assets in: {root}")
    print(f"[OK] icon source: {icon_source.name}")
    print(f"[OK] icon: {icon_out.name} (128x128)")
    print(f"[OK] small promo: {small_promo_out.name} (440x280)")
    if args.include_marquee:
        print(f"[OK] marquee: {MARQUEE_NAME} (1400x560)")
    if append_mode:
        print(
            f"[OK] screenshots appended: +{len(screenshot_sources)} "
            f"(total {existing_count + len(screenshot_sources)}/{args.max_screenshots}) "
            f"@ {screenshot_w}x{screenshot_h}"
        )
    else:
        print(f"[OK] screenshots: {len(screenshot_sources)} @ {screenshot_w}x{screenshot_h}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
