#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DASHBOARD_URL = "https://chrome.google.com/webstore/devconsole"
DEFAULT_ITEM_URL_TEMPLATE = "https://chrome.google.com/webstore/devconsole/{item_id}/edit"
DEFAULT_USER_DATA_DIR = Path.home() / ".codex" / "chrome-webstore-playwright-profile"

SHORT_DESCRIPTION_PATTERNS = [
    r"short\s*description",
    r"\bsummary\b",
    r"简短.*描述",
    r"简要.*说明",
    r"简介",
]

LONG_DESCRIPTION_PATTERNS = [
    r"detailed\s*description",
    r"long\s*description",
    r"full\s*description",
    r"listing\s*description",
    r"描述",
    r"详细.*说明",
]

REVIEW_NOTES_PATTERNS = [
    r"review\s*notes",
    r"notes?\s*to\s*review",
    r"reviewer\s*notes",
    r"审核备注",
    r"审核说明",
    r"给审核团队",
]

PRIVACY_POLICY_URL_PATTERNS = [
    r"privacy\s*policy\s*url",
    r"privacy\s*policy",
    r"隐私政策.*url",
    r"隐私政策",
]

UPLOAD_BUTTON_PATTERNS = [
    r"add\s*new\s*item",
    r"upload\s*new\s*item",
    r"upload\s*new\s*content",
    r"upload.*package",
    r"replace.*package",
    r"upload.*zip",
    r"upload",
    r"上传新内容",
    r"添加新项",
    r"上传.*程序包",
    r"上传.*压缩包",
]

SAVE_BUTTON_PATTERNS = [
    r"save\s*draft",
    r"save\s*changes",
    r"\bsave\b",
    r"保存草稿",
    r"保存更改",
    r"保存",
]

SUBMIT_BUTTON_PATTERNS = [
    r"提请审核",
    r"提交以供审核",
    r"submit\s*for\s*review",
    r"\bsubmit\b",
    r"send\s*for\s*review",
    r"提交审核",
    r"提交审查",
    r"提交",
]

SUBMIT_CONFIRM_BUTTON_PATTERNS = [
    r"confirm",
    r"ok",
    r"submit",
    r"继续",
    r"确认",
]

REVIEW_STATUS_PATTERNS = [
    r"in\s*review",
    r"under\s*review",
    r"pending\s*review",
    r"审核中",
    r"待审核",
    r"已提交",
]

LOCALE_KEY = {"zh": "### ZH", "en": "### EN"}


@dataclass
class ListingDraft:
    short_summary: str
    long_description: str
    reviewer_notes: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Automate Chrome Web Store dashboard actions with Playwright: "
            "open console, upload package, fill listing/reviewer fields, and optionally submit for review."
        )
    )
    parser.add_argument("--root", default=".", help="Extension root directory (default: current directory)")
    parser.add_argument(
        "--zip",
        default="release/chrome-webstore.zip",
        help="Package zip path relative to --root (default: release/chrome-webstore.zip)",
    )
    parser.add_argument(
        "--listing",
        default="release/cws-listing.zh-en.md",
        help="Bilingual listing draft path relative to --root (default: release/cws-listing.zh-en.md)",
    )
    parser.add_argument("--item-id", default="", help="Chrome Web Store item id (optional; recommended for updates)")
    parser.add_argument(
        "--item-name",
        default="",
        help="Extension item name for dashboard auto-selection when --item-id is not provided",
    )
    parser.add_argument(
        "--dashboard-url",
        default=DEFAULT_DASHBOARD_URL,
        help=f"Developer dashboard URL (default: {DEFAULT_DASHBOARD_URL})",
    )
    parser.add_argument(
        "--item-url-template",
        default=DEFAULT_ITEM_URL_TEMPLATE,
        help=(
            "Item edit URL template. Must contain `{item_id}` placeholder. "
            f"(default: {DEFAULT_ITEM_URL_TEMPLATE})"
        ),
    )
    parser.add_argument("--locale", choices=["zh", "en"], default="en", help="Listing language to fill (default: en)")
    parser.add_argument("--review-notes", default="", help="Explicit reviewer notes override")
    parser.add_argument("--privacy-policy-url", default="", help="Privacy policy URL to fill (optional)")
    parser.add_argument(
        "--user-data-dir",
        default=str(DEFAULT_USER_DATA_DIR),
        help="Persistent Chromium user data dir for login session reuse",
    )
    parser.add_argument(
        "--cdp-url",
        default="",
        help="Connect to an existing local Chrome via CDP (e.g. http://127.0.0.1:9222)",
    )
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (not recommended for login/2FA)")
    parser.add_argument("--skip-upload", action="store_true", help="Skip zip upload automation")
    parser.add_argument("--skip-fill-listing", action="store_true", help="Skip auto-fill short/long description fields")
    parser.add_argument("--skip-fill-review-notes", action="store_true", help="Skip auto-fill reviewer notes")
    parser.add_argument("--skip-save", action="store_true", help="Skip clicking save button")
    parser.add_argument("--submit-for-review", action="store_true", help="Click submit-for-review button (destructive action)")
    parser.add_argument(
        "--login-timeout-ms",
        type=int,
        default=300000,
        help="Max wait time for login/session readiness (default: 300000)",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=25000,
        help="Navigation and control timeout (default: 25000)",
    )
    parser.add_argument(
        "--wait-ms",
        type=int,
        default=1200,
        help="General wait after critical actions (default: 1200)",
    )
    parser.add_argument(
        "--evidence-out",
        default="release/cws-submit-proof.png",
        help="Screenshot path relative to --root for final evidence (empty to disable)",
    )
    parser.add_argument(
        "--hold-ms",
        type=int,
        default=0,
        help="Keep browser open for extra review before close (default: 0)",
    )
    return parser.parse_args()


def looks_like_cws_console_url(url: str) -> bool:
    token = url.lower()
    return (
        "devconsole" in token
        or "chromewebstore.google.com" in token
        or ("chrome.google.com/webstore" in token and "developer" in token)
    )


def looks_like_google_login(url: str) -> bool:
    token = url.lower()
    return "accounts.google.com" in token or "signin" in token


def collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def markdown_to_plain_text(value: str) -> str:
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"`([^`]+)`", r"\1", text)
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines).strip()


def extract_localized_block(markdown: str, section_heading: str, locale: str) -> str:
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    section_start = -1
    for idx, line in enumerate(lines):
        if line.strip().lower().startswith(f"## {section_heading.lower()}"):
            section_start = idx
            break
    if section_start < 0:
        return ""

    section_end = len(lines)
    for idx in range(section_start + 1, len(lines)):
        if lines[idx].strip().startswith("## "):
            section_end = idx
            break
    section_lines = lines[section_start + 1 : section_end]

    locale_marker = LOCALE_KEY[locale]
    locale_start = -1
    for idx, line in enumerate(section_lines):
        if line.strip() == locale_marker:
            locale_start = idx
            break
    if locale_start < 0:
        return ""

    locale_end = len(section_lines)
    for idx in range(locale_start + 1, len(section_lines)):
        token = section_lines[idx].strip()
        if token.startswith("### ") or token.startswith("## "):
            locale_end = idx
            break

    block = "\n".join(section_lines[locale_start + 1 : locale_end]).strip()
    return markdown_to_plain_text(block)


def build_listing_draft(listing_path: Path, locale: str, review_notes_override: str) -> ListingDraft:
    if not listing_path.is_file():
        print(f"[WARN] listing draft not found, auto-fill content unavailable: {listing_path}")
        return ListingDraft(short_summary="", long_description="", reviewer_notes=review_notes_override.strip())

    text = listing_path.read_text(encoding="utf-8", errors="ignore")
    fallback_locale = "zh" if locale == "en" else "en"

    short_summary = extract_localized_block(text, "1) Store Short Summary", locale)
    long_description = extract_localized_block(text, "2) Listing Description (Long)", locale)
    reviewer_notes = extract_localized_block(text, "7) Reviewer Notes", locale)

    if not short_summary:
        short_summary = extract_localized_block(text, "1) Store Short Summary", fallback_locale)
    if not long_description:
        long_description = extract_localized_block(text, "2) Listing Description (Long)", fallback_locale)
    if not reviewer_notes:
        reviewer_notes = extract_localized_block(text, "7) Reviewer Notes", fallback_locale)

    if review_notes_override.strip():
        reviewer_notes = review_notes_override.strip()

    short_summary = collapse_whitespace(short_summary)
    if len(short_summary) > 132:
        print("[WARN] short summary exceeds 132 chars, truncating for CWS form compatibility.")
        short_summary = short_summary[:132].rstrip()

    return ListingDraft(
        short_summary=short_summary,
        long_description=long_description.strip(),
        reviewer_notes=reviewer_notes.strip(),
    )


def regexes(patterns: list[str]) -> list[re.Pattern[str]]:
    return [re.compile(pattern, flags=re.IGNORECASE) for pattern in patterns]


def guess_manifest_name(root: Path) -> str:
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        return ""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return ""
    name = manifest.get("name")
    return str(name).strip() if isinstance(name, str) else ""


async def open_item_by_name(page, item_name: str, timeout_ms: int, wait_ms: int) -> bool:
    if not item_name.strip():
        return False

    name_re = re.compile(re.escape(item_name.strip()), flags=re.IGNORECASE)
    for locator in (
        page.get_by_role("link", name=name_re),
        page.get_by_text(name_re),
    ):
        count = await locator.count()
        if count == 0:
            continue
        for idx in range(count):
            candidate = locator.nth(idx)
            try:
                if not await candidate.is_visible():
                    continue
                await candidate.click(timeout=timeout_ms)
                await page.wait_for_timeout(max(wait_ms, 800))
                return True
            except Exception:
                continue

    return False


async def wait_for_login(page, login_timeout_ms: int) -> None:
    print("[ACTION] waiting for Google login/session in opened browser...")
    elapsed = 0
    while elapsed <= login_timeout_ms:
        url = page.url or ""
        if looks_like_cws_console_url(url) and not looks_like_google_login(url):
            print(f"[OK] session ready: {url}")
            return
        await page.wait_for_timeout(1000)
        elapsed += 1000
    raise RuntimeError(
        "Login/session was not ready before timeout. "
        "Complete Google login/2FA manually and retry with a higher --login-timeout-ms."
    )


async def click_button_by_patterns(page, patterns: list[str], timeout_ms: int) -> bool:
    for pattern in regexes(patterns):
        locator = page.get_by_role("button", name=pattern)
        count = await locator.count()
        if count == 0:
            continue
        for idx in range(count):
            candidate = locator.nth(idx)
            try:
                if not await candidate.is_visible():
                    continue
                try:
                    await candidate.click(timeout=timeout_ms)
                except Exception:
                    await candidate.click(timeout=timeout_ms, force=True)
                return True
            except Exception:
                continue
    for pattern in regexes(patterns):
        locator = page.get_by_text(pattern)
        count = await locator.count()
        if count == 0:
            continue
        for idx in range(count):
            candidate = locator.nth(idx)
            try:
                if not await candidate.is_visible():
                    continue
                try:
                    await candidate.click(timeout=timeout_ms)
                except Exception:
                    await candidate.click(timeout=timeout_ms, force=True)
                return True
            except Exception:
                continue
    return False


async def fill_textbox_by_patterns(page, patterns: list[str], value: str, timeout_ms: int) -> bool:
    if not value.strip():
        return False

    for pattern in regexes(patterns):
        for getter in (
            lambda: page.get_by_label(pattern),
            lambda: page.get_by_role("textbox", name=pattern),
            lambda: page.get_by_placeholder(pattern),
        ):
            locator = getter()
            count = await locator.count()
            if count == 0:
                continue
            for idx in range(count):
                target = locator.nth(idx)
                try:
                    if not await target.is_visible():
                        continue
                    await target.click(timeout=timeout_ms)
                    await target.fill(value, timeout=timeout_ms)
                    return True
                except Exception:
                    continue

    generic = page.locator("textarea, input[type='text']")
    count = await generic.count()
    for idx in range(count):
        target = generic.nth(idx)
        try:
            if not await target.is_visible():
                continue
            attrs = " ".join(
                [
                    await target.get_attribute("aria-label") or "",
                    await target.get_attribute("name") or "",
                    await target.get_attribute("placeholder") or "",
                    await target.get_attribute("id") or "",
                ]
            ).strip()
            if not attrs:
                continue
            if any(regex.search(attrs) for regex in regexes(patterns)):
                await target.click(timeout=timeout_ms)
                await target.fill(value, timeout=timeout_ms)
                return True
        except Exception:
            continue

    return False


async def upload_package_zip(page, zip_path: Path, timeout_ms: int, wait_ms: int) -> bool:
    try:
        await page.wait_for_selector("input[type='file']", timeout=min(max(timeout_ms, 3000), 10000))
    except Exception:
        pass

    file_inputs = page.locator("input[type='file']")
    count = await file_inputs.count()
    for idx in range(count):
        candidate = file_inputs.nth(idx)
        try:
            accept = (await candidate.get_attribute("accept") or "").lower()
            if ".zip" in accept or "application/zip" in accept:
                await candidate.set_input_files(str(zip_path), timeout=timeout_ms)
                await page.wait_for_timeout(wait_ms)
                return True
        except Exception:
            continue

    if count > 0:
        try:
            await file_inputs.first.set_input_files(str(zip_path), timeout=timeout_ms)
            await page.wait_for_timeout(wait_ms)
            return True
        except Exception:
            pass

    for pattern in regexes(UPLOAD_BUTTON_PATTERNS):
        buttons = page.get_by_role("button", name=pattern)
        btn_count = await buttons.count()
        if btn_count == 0:
            continue
        for idx in range(btn_count):
            button = buttons.nth(idx)
            try:
                if not await button.is_visible():
                    continue
                async with page.expect_file_chooser(timeout=timeout_ms) as chooser_info:
                    await button.click(timeout=timeout_ms)
                chooser = await chooser_info.value
                await chooser.set_files(str(zip_path))
                await page.wait_for_timeout(wait_ms)
                return True
            except Exception:
                continue
    for pattern in regexes(UPLOAD_BUTTON_PATTERNS):
        controls = page.get_by_text(pattern)
        control_count = await controls.count()
        if control_count == 0:
            continue
        for idx in range(control_count):
            control = controls.nth(idx)
            try:
                if not await control.is_visible():
                    continue
                async with page.expect_file_chooser(timeout=timeout_ms) as chooser_info:
                    try:
                        await control.click(timeout=timeout_ms)
                    except Exception:
                        await control.click(timeout=timeout_ms, force=True)
                chooser = await chooser_info.value
                await chooser.set_files(str(zip_path))
                await page.wait_for_timeout(wait_ms)
                return True
            except Exception:
                continue
    return False


async def run_submit(args: argparse.Namespace) -> int:
    try:
        from playwright.async_api import async_playwright
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "playwright is required. Install with `pip install playwright` and run `playwright install chromium`."
        ) from exc

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"root is not a directory: {root}")

    zip_path = (root / args.zip).resolve()
    listing_path = (root / args.listing).resolve()
    evidence_out = (root / args.evidence_out).resolve() if args.evidence_out else None
    user_data_dir = Path(args.user_data_dir).expanduser().resolve()
    manifest_name = guess_manifest_name(root)

    if not args.skip_upload and not zip_path.is_file():
        raise FileNotFoundError(f"zip not found for upload: {zip_path}")

    if "{item_id}" not in args.item_url_template:
        raise ValueError("--item-url-template must include `{item_id}` placeholder")
    if args.login_timeout_ms < 1000 or args.timeout_ms < 1000 or args.wait_ms < 0:
        raise ValueError("invalid timeout values")
    if args.hold_ms < 0:
        raise ValueError("--hold-ms must be >= 0")

    draft = build_listing_draft(listing_path, args.locale, args.review_notes)

    async with async_playwright() as playwright:
        context = None
        browser = None
        created_context = False
        created_page = False
        page = None

        if args.cdp_url.strip():
            print(f"[STEP] connect via CDP: {args.cdp_url.strip()}")
            browser = await playwright.chromium.connect_over_cdp(args.cdp_url.strip(), timeout=args.timeout_ms)
            if browser.contexts:
                context = browser.contexts[0]
            else:
                context = await browser.new_context(viewport={"width": 1600, "height": 1100})
                created_context = True
            had_page = bool(context.pages)
            page = context.pages[0] if had_page else await context.new_page()
            created_page = not had_page
        else:
            user_data_dir.mkdir(parents=True, exist_ok=True)
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=args.headless,
                viewport={"width": 1600, "height": 1100},
            )
            page = context.pages[0] if context.pages else await context.new_page()

        try:
            if page is None:
                raise RuntimeError("failed to resolve browser page")
            page.set_default_timeout(args.timeout_ms)

            print(f"[STEP] open dashboard: {args.dashboard_url}")
            await page.goto(args.dashboard_url, wait_until="domcontentloaded", timeout=args.timeout_ms)
            await wait_for_login(page, args.login_timeout_ms)

            if args.item_id.strip():
                item_url = args.item_url_template.format(item_id=args.item_id.strip())
                print(f"[STEP] open item edit page: {item_url}")
                await page.goto(item_url, wait_until="domcontentloaded", timeout=args.timeout_ms)
                if args.wait_ms > 0:
                    await page.wait_for_timeout(args.wait_ms)
            else:
                target_name = args.item_name.strip() or manifest_name
                if target_name:
                    print(f"[STEP] auto-select item by name: {target_name}")
                    opened = await open_item_by_name(page, target_name, args.timeout_ms, args.wait_ms)
                    if not opened:
                        print(
                            "[WARN] failed to auto-open item by name from dashboard; "
                            "navigate to target item page manually in browser."
                        )
                else:
                    print("[WARN] --item-id is empty and manifest name is unavailable; open target item page manually.")
                await page.wait_for_timeout(max(args.wait_ms, 1000))

            if not args.skip_upload:
                print(f"[STEP] upload zip: {zip_path}")
                uploaded = await upload_package_zip(page, zip_path, args.timeout_ms, args.wait_ms)
                if uploaded:
                    print("[OK] package upload input was set.")
                else:
                    print(
                        "[WARN] upload control was not found automatically. "
                        "Please upload manually in the opened browser before submitting."
                    )

            if not args.skip_fill_listing:
                print(f"[STEP] fill listing fields (locale={args.locale})")
                short_ok = await fill_textbox_by_patterns(
                    page,
                    SHORT_DESCRIPTION_PATTERNS,
                    draft.short_summary,
                    args.timeout_ms,
                )
                long_ok = await fill_textbox_by_patterns(
                    page,
                    LONG_DESCRIPTION_PATTERNS,
                    draft.long_description,
                    args.timeout_ms,
                )
                privacy_ok = False
                if args.privacy_policy_url.strip():
                    privacy_ok = await fill_textbox_by_patterns(
                        page,
                        PRIVACY_POLICY_URL_PATTERNS,
                        args.privacy_policy_url.strip(),
                        args.timeout_ms,
                    )
                print(f"[OK] short summary filled: {short_ok}")
                print(f"[OK] long description filled: {long_ok}")
                if args.privacy_policy_url.strip():
                    print(f"[OK] privacy policy URL filled: {privacy_ok}")

            if not args.skip_fill_review_notes:
                print("[STEP] fill reviewer notes")
                notes_ok = await fill_textbox_by_patterns(
                    page,
                    REVIEW_NOTES_PATTERNS,
                    draft.reviewer_notes,
                    args.timeout_ms,
                )
                print(f"[OK] reviewer notes filled: {notes_ok}")

            if not args.skip_save:
                print("[STEP] save listing draft")
                saved = await click_button_by_patterns(page, SAVE_BUTTON_PATTERNS, args.timeout_ms)
                print(f"[OK] save click triggered: {saved}")
                if args.wait_ms > 0:
                    await page.wait_for_timeout(args.wait_ms)

            if args.submit_for_review:
                print("[STEP] submit for review")
                submitted = await click_button_by_patterns(page, SUBMIT_BUTTON_PATTERNS, args.timeout_ms)
                if not submitted:
                    raise RuntimeError(
                        "Submit button was not found automatically. "
                        "Use manual submit in browser or adjust selectors."
                    )
                await page.wait_for_timeout(max(args.wait_ms, 1000))
                _ = await click_button_by_patterns(page, SUBMIT_CONFIRM_BUTTON_PATTERNS, args.timeout_ms)

                status_found = False
                for pattern in regexes(REVIEW_STATUS_PATTERNS):
                    locator = page.get_by_text(pattern)
                    if await locator.count() > 0:
                        status_found = True
                        break
                print(f"[OK] submit click triggered: {submitted}")
                print(f"[OK] review-status marker detected: {status_found}")
            else:
                print("[INFO] final submit not executed (use --submit-for-review to enable).")

            if evidence_out is not None:
                evidence_out.parent.mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=str(evidence_out), full_page=True)
                print(f"[OK] evidence screenshot: {evidence_out}")

            if args.hold_ms > 0:
                await page.wait_for_timeout(args.hold_ms)
            return 0
        finally:
            if args.cdp_url.strip():
                if created_page and page is not None:
                    try:
                        await page.close()
                    except Exception:
                        pass
                if created_context and context is not None:
                    try:
                        await context.close()
                    except Exception:
                        pass
                if browser is not None:
                    try:
                        await browser.close()
                    except Exception:
                        pass
            else:
                if context is not None:
                    await context.close()


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(run_submit(args))
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
