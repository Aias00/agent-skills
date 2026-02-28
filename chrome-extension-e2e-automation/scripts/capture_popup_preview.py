#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

EXTENSION_ID_ERROR = "Unable to resolve extension ID from service workers/pages."


def parse_size(value: str) -> tuple[int, int]:
    token = value.lower().strip().replace(" ", "")
    if "x" not in token:
        raise argparse.ArgumentTypeError("Size must be WIDTHxHEIGHT, e.g. 620x760")
    w_str, h_str = token.split("x", 1)
    try:
        width = int(w_str)
        height = int(h_str)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Size must use integers, e.g. 620x760") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("Width/height must be > 0")
    return width, height


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture a realistic popup preview screenshot from an unpacked extension."
    )
    parser.add_argument("--extension-root", required=True, help="Extension root directory (must contain manifest.json)")
    parser.add_argument("--manifest", default="manifest.json", help="Manifest path relative to extension root")
    parser.add_argument(
        "--out",
        default="release/store-assets/screenshots/popup-preview-620x760.png",
        help="Output screenshot path relative to extension root",
    )
    parser.add_argument("--size", type=parse_size, default=(620, 760), help="Viewport size, e.g. 620x760")
    parser.add_argument("--timeout-ms", type=int, default=15000, help="Playwright timeout in ms")
    parser.add_argument("--wait-ms", type=int, default=1200, help="Delay after navigation before screenshot")
    parser.add_argument("--headless", action="store_true", help="Use headless mode first, fallback to headed if needed")
    return parser.parse_args()


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
    raise RuntimeError(f"{EXTENSION_ID_ERROR} Verify extension loads correctly.{hint}")


def resolve_popup_relative_path(extension_root: Path, manifest_rel: str) -> str:
    manifest_path = (extension_root / manifest_rel).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    action = manifest.get("action")
    popup_rel = ""
    if isinstance(action, dict):
        value = action.get("default_popup")
        if isinstance(value, str):
            popup_rel = value.strip()
    if not popup_rel:
        raise ValueError("manifest.action.default_popup is missing; cannot capture popup preview.")
    popup_path = (extension_root / popup_rel).resolve()
    if not popup_path.is_file():
        raise FileNotFoundError(f"popup file not found: {popup_path}")
    return popup_rel


async def capture_once(
    *,
    extension_root: Path,
    popup_rel: str,
    out_path: Path,
    width: int,
    height: int,
    timeout_ms: int,
    wait_ms: int,
    headless: bool,
) -> None:
    from playwright.async_api import async_playwright

    with tempfile.TemporaryDirectory(prefix="popup-preview-user-data-") as user_data_dir:
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
                extension_id = await resolve_extension_id(context, timeout_ms, headless)
                page = await context.new_page()
                try:
                    await page.goto(
                        f"chrome-extension://{extension_id}/{popup_rel}",
                        wait_until="domcontentloaded",
                        timeout=timeout_ms,
                    )
                    if wait_ms > 0:
                        await page.wait_for_timeout(wait_ms)
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    await page.screenshot(path=str(out_path), full_page=False)
                finally:
                    await page.close()
            finally:
                await context.close()


async def capture(args: argparse.Namespace) -> int:
    try:
        import playwright  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "playwright is required. Install with `pip install playwright` and run `playwright install chromium`."
        ) from exc

    extension_root = Path(args.extension_root).expanduser().resolve()
    if not extension_root.is_dir():
        raise FileNotFoundError(f"Extension root not found: {extension_root}")
    if not (extension_root / args.manifest).is_file():
        raise FileNotFoundError(f"Manifest not found: {(extension_root / args.manifest).resolve()}")

    popup_rel = resolve_popup_relative_path(extension_root, args.manifest)
    out_path = (extension_root / args.out).resolve()
    width, height = args.size

    modes = [args.headless]
    if args.headless:
        modes.append(False)

    for idx, mode in enumerate(modes):
        try:
            await capture_once(
                extension_root=extension_root,
                popup_rel=popup_rel,
                out_path=out_path,
                width=width,
                height=height,
                timeout_ms=args.timeout_ms,
                wait_ms=args.wait_ms,
                headless=mode,
            )
            if args.headless and idx == 1:
                print("[WARN] popup preview fallback succeeded in headed mode.")
            print(f"[OK] popup preview: {out_path}")
            return 0
        except RuntimeError as exc:
            if args.headless and mode and EXTENSION_ID_ERROR in str(exc):
                print("[WARN] Unable to resolve extension ID in headless mode; retrying without --headless.")
                continue
            raise

    raise RuntimeError("popup preview capture failed.")


def main() -> int:
    args = parse_args()
    if args.timeout_ms < 1000 or args.wait_ms < 0:
        print("[ERROR] invalid timeout values", file=sys.stderr)
        return 1
    try:
        return asyncio.run(capture(args))
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
