#!/usr/bin/env python3
"""
Publisher for Tencent Developer Community articles.
Automates title/content/cover fill and publish flow with resilient selectors.
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

from patchright.sync_api import Page, sync_playwright

sys.path.insert(0, str(Path(__file__).parent))

from auth_manager import AuthManager, is_authenticated_url, is_login_url
from browser_utils import BrowserFactory
from config import DEBUG_SCREENSHOT_DIR, PUBLISH_URL
from extend_config import load_extend_settings, to_bool, to_int
from md2html import convert as md_to_html
from md2html import raw_text_to_html


def clip_title(title: str) -> str:
    if not title:
        return title
    if len(title) > 80:
        truncated = title[:80]
        print(f"⚠️ Title too long, truncated to 80 chars: {truncated}")
        return truncated
    if len(title) < 2:
        fixed = f"{title}文章"
        print(f"⚠️ Title too short, expanded: {fixed}")
        return fixed
    return title


def build_summary(title: str, content_text: str, max_len: int = 120) -> str:
    source = (content_text or "").replace("\r\n", "\n")
    paragraphs = []
    for raw_line in source.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith("![") or line == "---":
            continue
        if line.startswith("> "):
            continue
        if line.startswith("*原文：") or line.startswith("*原文:"):
            continue
        if line.startswith("* ") or line.startswith("- "):
            continue
        line = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", line)
        line = re.sub(r"[*_`#>-]", "", line).strip()
        if len(line) >= 12:
            paragraphs.append(line)

    summary = " ".join(paragraphs[:2]).strip()
    if not summary:
        summary = title.strip()
    if len(summary) > max_len:
        summary = summary[: max_len - 1].rstrip() + "…"
    return summary


def _parse_local_markdown_image(line: str, content_source_path: Optional[str]) -> Optional[str]:
    if not content_source_path:
        return None
    match = re.fullmatch(r"!\[(.*?)\]\((.*?)\)", line.strip())
    if not match:
        return None
    src = match.group(2).strip()
    if re.match(r"^https?://", src, re.IGNORECASE):
        return None
    resolved = (Path(content_source_path).resolve().parent / src).resolve()
    return str(resolved) if resolved.exists() else None


def build_content_ops(
    content_text: str,
    content_source_path: Optional[str],
    body_title_to_skip: str = "",
    skip_image_path: Optional[str] = None,
) -> list[tuple[str, str]]:
    if not content_text:
        return []

    skip_image_resolved = str(Path(skip_image_path).resolve()) if skip_image_path else None
    lines = content_text.replace("\r\n", "\n").split("\n")
    ops: list[tuple[str, str]] = []
    buffer: list[str] = []
    skipped_first_title = False

    def flush_buffer() -> None:
        segment = "\n".join(buffer).strip("\n")
        buffer.clear()
        if segment.strip():
            ops.append(("html", segment))

    for line in lines:
        stripped = line.strip()
        if not skipped_first_title and body_title_to_skip and stripped == f"# {body_title_to_skip}":
            skipped_first_title = True
            continue

        image_path = _parse_local_markdown_image(line, content_source_path)
        if image_path:
            flush_buffer()
            if skip_image_resolved and str(Path(image_path).resolve()) == skip_image_resolved:
                continue
            ops.append(("image", image_path))
            continue

        buffer.append(line)

    flush_buffer()
    return ops


def screenshot(page: Page, enabled: bool, name: str) -> None:
    if not enabled:
        return
    try:
        DEBUG_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        out = DEBUG_SCREENSHOT_DIR / f"debug_{name}_{ts}.png"
        page.screenshot(path=str(out))
        print(f"📸 Saved screenshot: {out}")
    except Exception as e:
        print(f"⚠️ Screenshot failed: {e}")


def wait_login(page: Page, timeout_seconds: int = 300) -> bool:
    print("⏳ Waiting for manual login...")
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            u = page.url
            if is_authenticated_url(u):
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def first_visible_selector(page: Page, selectors) -> Optional[str]:
    for selector in selectors:
        try:
            loc = page.locator(selector).first
            if loc.count() > 0 and loc.is_visible():
                return selector
        except Exception:
            continue
    return None


def click_text_button(page: Page, texts, timeout_ms: int = 4000) -> bool:
    deadline = time.time() + (timeout_ms / 1000)
    while time.time() < deadline:
        for text in texts:
            try:
                loc = page.locator("button, a, div, span").filter(has_text=text).first
                if loc.count() > 0 and loc.is_visible():
                    loc.click(force=True)
                    return True
            except Exception:
                continue
        time.sleep(0.4)
    return False


def open_publish_panel(page: Page, timeout_ms: int = 8000) -> bool:
    deadline = time.time() + (timeout_ms / 1000)
    while time.time() < deadline:
        try:
            publish_btn = page.get_by_role("button", name="发布").first
            if publish_btn.count() > 0 and publish_btn.is_visible():
                publish_btn.click(force=True)
        except Exception:
            click_text_button(page, ["发布"], timeout_ms=1200)

        try:
            if page.get_by_text("发布文章").first.is_visible(timeout=800):
                return True
        except Exception:
            pass

        try:
            if page.get_by_text("确认发布").first.is_visible(timeout=800):
                return True
        except Exception:
            pass

        time.sleep(0.4)
    return False


def scroll_publish_panel_to_bottom(page: Page) -> None:
    try:
        page.evaluate(
            """() => {
                for (const el of Array.from(document.querySelectorAll('*'))) {
                    const st = window.getComputedStyle(el);
                    if ((st.overflowY === 'auto' || st.overflowY === 'scroll') &&
                        el.scrollHeight > el.clientHeight + 20) {
                        el.scrollTop = el.scrollHeight;
                    }
                }
                window.scrollTo(0, document.body.scrollHeight);
            }"""
        )
    except Exception:
        pass


def ensure_source_selected(page: Page) -> None:
    # Some publish panels require choosing source before confirm can be enabled.
    try:
        selected = page.evaluate(
            """() => {
                return !!document.querySelector('input[type="radio"]:checked');
            }"""
        )
        if selected:
            return
    except Exception:
        pass
    try:
        selected = page.evaluate(
            """() => {
                const radios = Array.from(document.querySelectorAll('input[type="radio"], input.c-radio'));
                if (!radios.length) return false;
                const first = radios[0];
                first.click();
                first.checked = true;
                first.dispatchEvent(new Event('input', { bubbles: true }));
                first.dispatchEvent(new Event('change', { bubbles: true }));
                return !!document.querySelector('input[type="radio"]:checked');
            }"""
        )
        if selected:
            return
    except Exception:
        pass

    click_text_button(page, ["原创"], timeout_ms=1500)


def _remaining_tag_slots(page: Page) -> Optional[int]:
    try:
        text = page.evaluate(
            """() => (document.body && document.body.innerText) ? document.body.innerText : ''"""
        )
        m = re.search(r"还可以添加\s*(\d+)\s*个标签", text or "")
        if not m:
            return None
        return int(m.group(1))
    except Exception:
        return None


def ensure_article_tag(page: Page, candidates) -> bool:
    before = _remaining_tag_slots(page)
    if before is not None and before < 5:
        return True

    def use_new_tags_input(keyword: str) -> bool:
        try:
            ok = page.evaluate(
                """(kw) => {
                    const inputs = Array.from(document.querySelectorAll('input.cdc-tags-input__input'));
                    const el = inputs[0];
                    if (!el) return false;
                    el.scrollIntoView({ block: 'center' });
                    el.focus();
                    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                    setter.call(el, '');
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    return document.activeElement === el;
                }""",
                keyword,
            )
            if not ok:
                return False
            page.wait_for_timeout(300)
            page.keyboard.type(keyword, delay=60)
            page.wait_for_timeout(900)
            page.keyboard.press("ArrowDown")
            page.keyboard.press("Enter")
            page.wait_for_timeout(1000)
            after = _remaining_tag_slots(page)
            return after is not None and after < 5
        except Exception:
            return False

    def use_legacy_tags_input(keyword: str) -> bool:
        try:
            tag_input = page.locator("input.com-2-tag-input").first
            if tag_input.count() == 0 or not tag_input.is_visible():
                return False
            tag_input.click()
            tag_input.fill(keyword)
            page.wait_for_timeout(700)
            page.keyboard.press("ArrowDown")
            page.keyboard.press("Enter")
            page.wait_for_timeout(700)
            after = _remaining_tag_slots(page)
            return after is not None and after < 5
        except Exception:
            return False

    for keyword in candidates:
        kw = (keyword or "").strip()
        if not kw:
            continue
        if use_new_tags_input(kw) or use_legacy_tags_input(kw):
            return True
    return False


def click_confirm_publish(page: Page, timeout_ms: int = 10000) -> bool:
    deadline = time.time() + (timeout_ms / 1000)
    while time.time() < deadline:
        scroll_publish_panel_to_bottom(page)
        try:
            btn = page.get_by_role("button", name="确认发布").first
            if btn.count() > 0:
                btn.scroll_into_view_if_needed(timeout=1500)
                if btn.is_visible():
                    if btn.is_disabled():
                        time.sleep(0.4)
                        continue
                    btn.click(force=True)
                    return True
        except Exception:
            pass

        try:
            btn = page.locator("button").filter(has_text="确认发布").first
            if btn.count() > 0 and btn.is_visible():
                btn.click(force=True)
                return True
        except Exception:
            pass

        try:
            clicked = page.evaluate(
                """() => {
                    const btn = Array.from(document.querySelectorAll('button')).find(
                        el => (el.innerText || '').includes('确认发布')
                    );
                    if (!btn || btn.disabled || btn.getAttribute('aria-disabled') === 'true') return false;
                    btn.click();
                    return true;
                }"""
            )
            if clicked:
                return True
        except Exception:
            pass

        time.sleep(0.5)
    return False


def can_confirm_publish(page: Page) -> bool:
    try:
        btn = page.get_by_role("button", name="确认发布").first
        if btn.count() > 0 and btn.is_visible():
            return not btn.is_disabled()
    except Exception:
        pass

    try:
        return bool(
            page.evaluate(
                """() => {
                    const btn = Array.from(document.querySelectorAll('button')).find(
                        el => (el.innerText || '').includes('确认发布')
                    );
                    return !!btn && !btn.disabled && btn.getAttribute('aria-disabled') !== 'true';
                }"""
            )
        )
    except Exception:
        return False


def fill_title(page: Page, title: str) -> bool:
    selectors = [
        'input[placeholder*="标题"]',
        'textarea[placeholder*="标题"]',
        'input[name*="title"]',
        'textarea[name*="title"]',
        '[data-testid*="title"] input',
    ]
    found = first_visible_selector(page, selectors)
    if found:
        try:
            loc = page.locator(found).first
            loc.click()
            loc.fill("")
            loc.type(title, delay=20)
            return True
        except Exception:
            pass

    try:
        ok = page.evaluate(
            """(payload) => {
                const value = payload.title;
                const candidates = Array.from(document.querySelectorAll('input, textarea'));
                for (const el of candidates) {
                    const ph = (el.getAttribute('placeholder') || '').toLowerCase();
                    const nm = (el.getAttribute('name') || '').toLowerCase();
                    if (ph.includes('标题') || nm.includes('title') || ph.includes('title')) {
                        el.focus();
                        el.value = value;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                }
                return false;
            }""",
            {"title": title},
        )
        return bool(ok)
    except Exception:
        return False


def fill_content(page: Page, html: str) -> bool:
    def current_word_count() -> int:
        try:
            text = page.evaluate(
                """() => (document.body && document.body.innerText) ? document.body.innerText : ''"""
            )
            m = re.search(r"(?:正文)?字数\s*[:：]\s*(\d+)(?:\s*/\s*50000)?", text or "")
            return int(m.group(1)) if m else 0
        except Exception:
            return 0

    selectors = [
        ".ql-editor",
        ".ProseMirror",
        "[contenteditable='true']",
        "div[role='textbox']",
        "article[contenteditable='true']",
    ]

    found = first_visible_selector(page, selectors)
    if not found:
        try:
            page.wait_for_timeout(1000)
            found = first_visible_selector(page, selectors)
        except Exception:
            pass

    if found:
        try:
            loc = page.locator(found).first
            loc.click(force=True)
            page.keyboard.press("ControlOrMeta+A")
            page.keyboard.press("Backspace")
        except Exception:
            pass

    try:
        ok = page.evaluate(
            """(payload) => {
                const html = payload.html;
                const candidates = Array.from(document.querySelectorAll('.ql-editor, .ProseMirror, [contenteditable="true"], div[role="textbox"], article[contenteditable="true"]'));
                const visible = candidates.find(el => {
                    const r = el.getBoundingClientRect();
                    const s = window.getComputedStyle(el);
                    return r.width > 5 && r.height > 5 && s.display !== 'none' && s.visibility !== 'hidden';
                });

                if (!visible) return false;
                visible.focus();

                try {
                    if ('value' in visible) {
                        visible.value = '';
                    } else {
                        visible.innerHTML = '';
                    }
                } catch (_) {}

                const success = document.execCommand('insertHTML', false, html);
                if (!success) {
                    visible.innerHTML = html;
                }

                visible.dispatchEvent(new Event('input', { bubbles: true }));
                visible.dispatchEvent(new Event('change', { bubbles: true }));
                return true;
            }""",
            {"html": html},
        )
        if bool(ok):
            page.wait_for_timeout(800)
            if current_word_count() > 0:
                return True
    except Exception:
        pass

    # Fallback for Draft.js-like editors where innerHTML mutation doesn't update internal state.
    try:
        if found:
            loc = page.locator(found).first
            loc.click(force=True)
            page.keyboard.press("ControlOrMeta+A")
            page.keyboard.press("Backspace")
            plain_text = re.sub(r"<[^>]+>", "", html or "")
            page.keyboard.insert_text(plain_text)
            page.wait_for_timeout(800)
            return current_word_count() > 0
    except Exception:
        pass

    return False


def insert_content_fragment(page: Page, html: str, replace: bool = False) -> bool:
    if not html:
        return True

    try:
        ok = page.evaluate(
            """(payload) => {
                const html = payload.html;
                const replace = payload.replace;
                const candidates = Array.from(document.querySelectorAll('.ql-editor, .ProseMirror, [contenteditable="true"], div[role="textbox"], article[contenteditable="true"]'));
                const editor = candidates.find(el => {
                    const r = el.getBoundingClientRect();
                    const s = window.getComputedStyle(el);
                    return r.width > 5 && r.height > 5 && s.display !== 'none' && s.visibility !== 'hidden';
                });
                if (!editor) return false;
                editor.focus();

                if (replace) {
                    try {
                        if ('value' in editor) editor.value = '';
                        else editor.innerHTML = '';
                    } catch (_) {}
                } else {
                    const sel = window.getSelection();
                    const range = document.createRange();
                    range.selectNodeContents(editor);
                    range.collapse(false);
                    sel.removeAllRanges();
                    sel.addRange(range);
                }

                const success = document.execCommand('insertHTML', false, html);
                if (!success) {
                    if (replace) editor.innerHTML = html;
                    else editor.insertAdjacentHTML('beforeend', html);
                }

                editor.dispatchEvent(new Event('input', { bubbles: true }));
                editor.dispatchEvent(new Event('change', { bubbles: true }));
                return true;
            }""",
            {"html": html, "replace": replace},
        )
        if ok:
            page.wait_for_timeout(500)
            return True
    except Exception:
        pass
    return False


def fill_summary(page: Page, summary: str) -> bool:
    selectors = [
        'textarea[placeholder*="摘要"]',
        ".editor-publish-drawer__textarea-main",
    ]
    found = first_visible_selector(page, selectors)
    if not found:
        return False

    try:
        loc = page.locator(found).first
        loc.click(force=True)
        loc.fill("")
        loc.type(summary, delay=15)
        return True
    except Exception:
        pass

    try:
        return bool(
            page.evaluate(
                """(payload) => {
                    const value = payload.summary;
                    const candidates = Array.from(document.querySelectorAll('textarea'));
                    const el = candidates.find(node => {
                        const ph = (node.getAttribute('placeholder') || '').toLowerCase();
                        const cls = node.className || '';
                        return ph.includes('摘要') || cls.includes('textarea-main');
                    });
                    if (!el) return false;
                    el.focus();
                    el.value = value;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    return true;
                }""",
                {"summary": summary},
            )
        )
    except Exception:
        return False


def count_body_images(page: Page) -> int:
    try:
        return int(
            page.evaluate(
                """() => {
                    const editor = document.querySelector('.ProseMirror, .ql-editor, [contenteditable="true"]');
                    return editor ? editor.querySelectorAll('img').length : 0;
                }"""
            )
        )
    except Exception:
        return 0


def upload_body_image(page: Page, image_path: str, timeout_ms: int = 20000) -> bool:
    if not os.path.exists(image_path):
        print(f"⚠️ Body image not found: {image_path}")
        return False

    prev_count = count_body_images(page)
    try:
        page.evaluate(
            """() => {
                const editor = document.querySelector('.ProseMirror, .ql-editor, [contenteditable="true"]');
                if (!editor) return;
                editor.focus();
                const sel = window.getSelection();
                const range = document.createRange();
                range.selectNodeContents(editor);
                range.collapse(false);
                sel.removeAllRanges();
                sel.addRange(range);
            }"""
        )
        page.wait_for_timeout(200)
        page.locator("text=插入").first.click(force=True)
        page.wait_for_timeout(300)
        with page.expect_file_chooser(timeout=4000) as fc_info:
            page.locator("li.cdc-tool-dropdown__item").filter(has_text="图片").first.click(force=True)
        fc_info.value.set_files(image_path)
    except Exception:
        return False

    deadline = time.time() + (timeout_ms / 1000)
    while time.time() < deadline:
        page.wait_for_timeout(500)
        try:
            state = page.evaluate(
                """() => {
                    const editor = document.querySelector('.ProseMirror, .ql-editor, [contenteditable="true"]');
                    const html = editor ? editor.innerHTML : '';
                    const bodyText = (document.body && document.body.innerText) ? document.body.innerText : '';
                    const imgCount = editor ? editor.querySelectorAll('img').length : 0;
                    return {
                        imgCount,
                        hasBlob: html.includes('blob:'),
                        loading: html.includes('图片载入中') || bodyText.includes('图片载入中'),
                    };
                }"""
            )
        except Exception:
            continue

        if state["imgCount"] > prev_count and not state["hasBlob"] and not state["loading"]:
            return True

    return False


def fill_content_with_local_images(
    page: Page,
    content_text: str,
    content_source_path: Optional[str],
    title: str,
    cover_image_path: Optional[str],
) -> bool:
    ops = build_content_ops(
        content_text=content_text,
        content_source_path=content_source_path,
        body_title_to_skip=title,
        skip_image_path=cover_image_path,
    )
    if not ops:
        return False

    inserted_any = False
    for kind, payload in ops:
        if kind == "html":
            html = md_to_html(payload)
            if not insert_content_fragment(page, html, replace=not inserted_any):
                return False
            inserted_any = True
            continue
        if kind == "image":
            if not upload_body_image(page, payload):
                return False
            inserted_any = True

    return inserted_any


def upload_cover(page: Page, cover_path: str) -> bool:
    if not os.path.exists(cover_path):
        print(f"⚠️ Cover image not found: {cover_path}")
        return False

    selectors = [
        "input[name='article-cover-image']",
        "input.col-editor-upload-input",
        "input[type='file'][name*='cover']",
        "input[type='file']",
    ]
    for selector in selectors:
        try:
            loc = page.locator(selector).first
            if loc.count() > 0:
                loc.set_input_files(cover_path)
                page.wait_for_timeout(1200)
                return True
        except Exception:
            continue

    print("⚠️ File input not found for cover upload")
    return False


def wait_cover_upload_complete(page: Page, timeout_ms: int = 20000) -> bool:
    deadline = time.time() + (timeout_ms / 1000)
    saw_busy = False
    while time.time() < deadline:
        try:
            text = page.evaluate(
                """() => (document.body && document.body.innerText) ? document.body.innerText : ''"""
            )
        except Exception:
            text = ""

        if "正在上传封面中，请稍候" in (text or ""):
            saw_busy = True
            time.sleep(0.5)
            continue

        if saw_busy:
            return True

        # If no busy indicator ever appeared, treat the uploader as settled
        # after a short grace period.
        time.sleep(0.5)
        if time.time() + 0.5 >= deadline:
            break

    return not saw_busy


def publish_once(
    title: Optional[str],
    content_text: Optional[str],
    content_source_path: Optional[str],
    cover_image_path: Optional[str],
    dry_run: bool,
    headless: bool,
    no_cover: bool,
    raw: bool,
    debug_screenshots: bool,
    wait_seconds: int,
) -> bool:
    resolved_title = clip_title(title or "")
    tag_candidates = []
    if resolved_title:
        for m in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", resolved_title):
            tag_candidates.append(m.lower())
    tag_candidates.extend(["agent", "ai", "开发", "技术"])
    # Preserve order while de-duplicating.
    tag_candidates = list(dict.fromkeys(tag_candidates))

    final_html = ""
    if content_text:
        print("🔄 Converting content to HTML...")
        final_html = raw_text_to_html(content_text) if raw else md_to_html(content_text)

    auth_manager = AuthManager()

    with sync_playwright() as p:
        context = BrowserFactory.launch_persistent_context(p, headless=headless)
        page = context.pages[0] if context.pages else context.new_page()

        try:
            print(f"🌐 Opening publish page: {PUBLISH_URL}")
            page.goto(PUBLISH_URL, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            if is_login_url(page.url):
                print("⚠️ Redirected to login")
                if headless:
                    print("❌ Headless mode cannot complete interactive login")
                    return False

                if not wait_login(page, timeout_seconds=300):
                    print("❌ Login timeout")
                    return False

                auth_manager._save_browser_state(context)
                auth_manager._save_auth_info()

                if not is_authenticated_url(page.url):
                    page.goto(PUBLISH_URL, timeout=60000, wait_until="domcontentloaded")
                    page.wait_for_timeout(2500)

            print("✅ Publish editor loaded")
            screenshot(page, debug_screenshots, "loaded")

            if resolved_title:
                print("✍️ Filling title...")
                if not fill_title(page, resolved_title):
                    print("⚠️ Could not confidently fill title field")
                screenshot(page, debug_screenshots, "after_title")

            if final_html:
                print("📝 Filling content...")
                used_structured = False
                if not raw and content_source_path and "![" in (content_text or ""):
                    used_structured = fill_content_with_local_images(
                        page=page,
                        content_text=content_text or "",
                        content_source_path=content_source_path,
                        title=resolved_title,
                        cover_image_path=cover_image_path,
                    )
                if not used_structured and not fill_content(page, final_html):
                    print("⚠️ Could not confidently fill content editor")
                page.wait_for_timeout(1200)
                screenshot(page, debug_screenshots, "after_content")

            if dry_run:
                print("🚧 Dry run: skipped final publish click")
                return True

            print("🚀 Opening publish panel...")
            opened = open_publish_panel(page, timeout_ms=7000)
            if not opened:
                print("❌ Could not open publish panel")
                screenshot(page, debug_screenshots, "publish_button_missing")
                return False

            ensure_source_selected(page)
            tag_ok = ensure_article_tag(page, tag_candidates)
            if tag_ok:
                print("✅ Tag selected")
            elif can_confirm_publish(page):
                print("⚠️ Could not reliably select article tag, but publish is still enabled")
            else:
                print("⚠️ Could not reliably select article tag")
                screenshot(page, debug_screenshots, "tag_missing")
                return False

            if cover_image_path:
                print(f"🖼️ Uploading cover: {cover_image_path}")
                ok = upload_cover(page, cover_image_path)
                print("✅ Cover uploaded" if ok else "⚠️ Cover upload may have failed")
                if ok:
                    settled = wait_cover_upload_complete(page, timeout_ms=20000)
                    print("✅ Cover upload settled" if settled else "⚠️ Cover upload may still be processing")
                page.wait_for_timeout(1200)
                screenshot(page, debug_screenshots, "after_cover")
            elif no_cover:
                print("🖼️ Selecting no-cover mode (if available)...")
                click_text_button(page, ["无封面", "不设置封面"], timeout_ms=2500)

            summary_text = build_summary(resolved_title, content_text or "")
            if summary_text:
                print("🧾 Filling summary...")
                ok = fill_summary(page, summary_text)
                print("✅ Summary filled" if ok else "⚠️ Summary fill may have failed")
                page.wait_for_timeout(800)

            page.wait_for_timeout(1200)
            print("🚀 Confirming publish...")
            confirmed = click_confirm_publish(page, timeout_ms=12000)
            if not confirmed:
                print("❌ Could not click confirm publish")
                screenshot(page, debug_screenshots, "confirm_publish_missing")
                return False

            page.wait_for_timeout(4000)
            screenshot(page, debug_screenshots, "after_publish")

            for text in ["发布成功", "提交成功", "已发布", "审核中", "审核通过"]:
                try:
                    if page.get_by_text(text).is_visible():
                        print(f"✨ Publish successful ({text})")
                        return True
                except Exception:
                    continue

            try:
                if "cloud.tencent.com/developer/article/write" not in (page.url or ""):
                    print(f"✅ Publish submitted (redirected): {page.url}")
                    return True
            except Exception:
                pass

            print("❌ Publish may not have been submitted (no success text and still on editor page)")
            return False

        except Exception as e:
            print(f"❌ Publishing failed: {e}")
            screenshot(page, debug_screenshots, "error")
            return False

        finally:
            if not headless and wait_seconds > 0:
                print(f"🔎 Keeping browser open for inspection: {wait_seconds}s")
                time.sleep(wait_seconds)
            context.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Tencent Developer Community Publisher")
    parser.add_argument("--title", help="Article title")
    parser.add_argument("--content", help="Article content (file path or inline text)")
    parser.add_argument("--cover", help="Path to cover image")
    parser.add_argument("--dry-run", action="store_true", help="Fill fields but do not publish")

    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Run in headless mode (default from EXTEND.md or false)",
    )
    parser.add_argument(
        "--no-cover",
        dest="no_cover",
        action="store_true",
        default=None,
        help="Select no-cover mode",
    )
    parser.add_argument(
        "--with-cover",
        dest="no_cover",
        action="store_false",
        help="Force with-cover mode",
    )
    parser.add_argument(
        "--raw",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Treat content as raw text (no markdown conversion)",
    )
    parser.add_argument(
        "--debug-screenshots",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Save debug screenshots",
    )
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=None,
        help="Keep browser open after run when non-headless",
    )

    args = parser.parse_args()
    extend_path, extend = load_extend_settings()

    if extend_path:
        print(f"⚙️ Loaded preferences from: {extend_path}")

    headless = args.headless if args.headless is not None else to_bool(extend.get("default_headless"), False)
    no_cover = args.no_cover if args.no_cover is not None else to_bool(extend.get("default_no_cover"), False)
    raw = args.raw if args.raw is not None else to_bool(extend.get("default_raw"), False)
    debug_screenshots = (
        args.debug_screenshots
        if args.debug_screenshots is not None
        else to_bool(extend.get("default_debug_screenshots"), False)
    )
    wait_seconds = (
        args.wait_seconds
        if args.wait_seconds is not None
        else to_int(extend.get("default_wait_seconds"), 0 if headless else 30)
    )

    print(
        "Resolved options: "
        f"headless={headless}, no_cover={no_cover}, raw={raw}, "
        f"debug_screenshots={debug_screenshots}, wait_seconds={wait_seconds}"
    )

    content = args.content
    content_source_path = None
    if content and os.path.exists(content):
        content_source_path = content
        with open(content, "r", encoding="utf-8") as f:
            content = f.read()

    success = publish_once(
        title=args.title,
        content_text=content,
        content_source_path=content_source_path,
        cover_image_path=args.cover,
        dry_run=args.dry_run,
        headless=headless,
        no_cover=no_cover,
        raw=raw,
        debug_screenshots=debug_screenshots,
        wait_seconds=max(wait_seconds, 0),
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
