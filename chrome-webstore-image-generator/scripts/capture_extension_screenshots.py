#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_OUTPUT_SUFFIXES = {".png", ".jpg", ".jpeg"}
EXTENSION_ID_ERROR = "Unable to resolve extension ID from service workers/pages."


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


def clean_screenshots_dir(folder: Path) -> None:
    if not folder.exists():
        return
    for item in folder.iterdir():
        if item.is_file() and item.suffix.lower() in ALLOWED_OUTPUT_SUFFIXES:
            item.unlink()


def parse_extension_id(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme != "chrome-extension":
        return None
    return parsed.netloc or None


async def resolve_extension_id(context, timeout_ms: int, headless: bool) -> str:
    for worker in context.service_workers:
        ext_id = parse_extension_id(worker.url)
        if ext_id:
            return ext_id

    try:
        worker = await context.wait_for_event("serviceworker", timeout=timeout_ms)
        ext_id = parse_extension_id(worker.url)
        if ext_id:
            return ext_id
    except Exception:
        pass

    for page in context.pages:
        ext_id = parse_extension_id(page.url)
        if ext_id:
            return ext_id

    hint = ""
    if headless:
        hint = " Headless Chromium may not expose extension workers/pages; retry without --headless."
    raise RuntimeError(
        f"{EXTENSION_ID_ERROR} Verify the extension root is valid and loads in Chromium.{hint}"
    )


async def capture_once(
    *,
    extension_root: Path,
    shots_dir: Path,
    width: int,
    height: int,
    popup_rel: str,
    options_rel: str,
    args: argparse.Namespace,
    headless: bool,
) -> list[Path]:
    screenshots: list[Path] = []

    with tempfile.TemporaryDirectory(prefix="ext-shot-user-data-") as user_data_dir:
        from playwright.async_api import async_playwright

        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=headless,
                viewport={"width": width, "height": height},
                args=[
                    f"--disable-extensions-except={extension_root}",
                    f"--load-extension={extension_root}",
                ],
            )

            try:
                extension_id = await resolve_extension_id(context, args.timeout_ms, headless)

                index = 1

                async def snap(url: str, label: str) -> None:
                    nonlocal index
                    if index > args.max_screenshots:
                        return

                    page = await context.new_page()
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=args.timeout_ms)
                        if args.wait_ms > 0:
                            await page.wait_for_timeout(args.wait_ms)
                        out = shots_dir / f"screenshot-{index}-{width}x{height}.png"
                        await page.screenshot(path=str(out), full_page=args.full_page)
                        screenshots.append(out)
                        print(f"[OK] screenshot {index}: {label} -> {out.name}")
                        index += 1
                    finally:
                        await page.close()

                if not args.skip_popup and popup_rel:
                    popup_source = extension_root / popup_rel
                    if popup_source.is_file():
                        await snap(f"chrome-extension://{extension_id}/{popup_rel}", "popup")
                    else:
                        print(f"[WARN] popup path not found, skipped: {popup_source}")

                if options_rel and index <= args.max_screenshots:
                    options_source = extension_root / options_rel
                    if options_source.is_file():
                        await snap(f"chrome-extension://{extension_id}/{options_rel}", "options")
                    else:
                        print(f"[WARN] options path not found, skipped: {options_source}")

                for url in args.urls:
                    if index > args.max_screenshots:
                        break
                    await snap(url, url)
            finally:
                await context.close()

    return screenshots


async def capture(args: argparse.Namespace) -> int:
    try:
        from playwright.async_api import async_playwright
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "playwright is required. Install with `pip install playwright` and run `playwright install chromium`."
        ) from exc

    extension_root = Path(args.extension_root).expanduser().resolve()
    if not extension_root.is_dir():
        raise FileNotFoundError(f"Extension root not found: {extension_root}")
    if not (extension_root / "manifest.json").is_file():
        raise FileNotFoundError(f"manifest.json not found in extension root: {extension_root}")

    output_root = Path(args.root).expanduser().resolve()
    shots_dir = output_root / "screenshots"
    shots_dir.mkdir(parents=True, exist_ok=True)
    clean_screenshots_dir(shots_dir)

    width, height = args.screenshot_size

    popup_rel = args.popup_path.strip("/") if args.popup_path else ""
    options_rel = args.options_path.strip("/") if args.options_path else ""

    if args.skip_popup and not options_rel and not args.urls:
        raise ValueError("Nothing to capture. Provide --options-path and/or --urls when --skip-popup is set.")

    screenshots: list[Path] = []

    capture_modes = [args.headless]
    if args.headless:
        capture_modes.append(False)

    for idx, headless_mode in enumerate(capture_modes):
        clean_screenshots_dir(shots_dir)
        try:
            screenshots = await capture_once(
                extension_root=extension_root,
                shots_dir=shots_dir,
                width=width,
                height=height,
                popup_rel=popup_rel,
                options_rel=options_rel,
                args=args,
                headless=headless_mode,
            )
            if args.headless and idx == 1:
                print("[WARN] headless capture failed earlier; fallback to headed mode succeeded.")
            break
        except RuntimeError as exc:
            if args.headless and headless_mode and EXTENSION_ID_ERROR in str(exc):
                print("[WARN] Unable to resolve extension ID in headless mode; retrying without --headless.")
                continue
            raise

    if not screenshots:
        raise RuntimeError("No screenshots captured. Check paths/options and try again.")

    print(f"[OK] captured {len(screenshots)} screenshot(s) in: {shots_dir}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture extension screenshots with Playwright (popup/options/pages)."
    )
    parser.add_argument(
        "--extension-root",
        required=True,
        help="Absolute path to unpacked extension root (must contain manifest.json)",
    )
    parser.add_argument(
        "--root",
        default="release/store-assets",
        help="Output asset root directory (default: release/store-assets)",
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
        help="Maximum number of screenshots (default: 5)",
    )
    parser.add_argument(
        "--popup-path",
        default="popup.html",
        help="Popup page path relative to extension root (default: popup.html)",
    )
    parser.add_argument(
        "--skip-popup",
        action="store_true",
        help="Skip popup screenshot capture",
    )
    parser.add_argument(
        "--options-path",
        default="",
        help="Options page path relative to extension root (optional)",
    )
    parser.add_argument(
        "--urls",
        nargs="*",
        default=[],
        help="Additional page URLs to capture after extension pages",
    )
    parser.add_argument(
        "--wait-ms",
        type=int,
        default=1200,
        help="Delay after each page load before screenshot (default: 1200)",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=15000,
        help="Navigation/event timeout in ms (default: 15000)",
    )
    parser.add_argument(
        "--full-page",
        action="store_true",
        help="Capture full-page screenshots instead of viewport",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium in headless mode",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_screenshots < 1:
        print("[ERROR] --max-screenshots must be >= 1", file=sys.stderr)
        return 1
    if args.wait_ms < 0 or args.timeout_ms < 1:
        print("[ERROR] invalid wait/timeout values", file=sys.stderr)
        return 1

    try:
        return asyncio.run(capture(args))
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
