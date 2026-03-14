#!/usr/bin/env python3
"""
Publish Toutiao articles via authenticated in-browser API calls.

This avoids the unstable front-end autosave flow used by the browser-only
publisher and submits the final article payload directly from an authenticated
page context.
"""

import argparse
import base64
import json
import mimetypes
import os
import random
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from patchright.sync_api import sync_playwright

from auth_manager import AuthManager
from browser_utils import BrowserFactory
from config import PUBLISH_URL
from md2html import convert as md_to_html, raw_text_to_html
from publisher import infer_cover_from_content_path, sanitize_html_fragment


def optimize_title(title: str) -> str:
    title = (title or "").strip()
    if len(title) > 30:
        return title[:30]
    if len(title) < 2:
        return (title + "...")[:30]
    return title


def strip_html_tags(html_text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html_text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def load_content(content_arg: str | None, raw: bool = False):
    content_path = None
    is_html = False
    content = content_arg or ""

    if content and os.path.exists(content):
        content_path = Path(content)
        is_html = content_path.suffix.lower() in {".html", ".htm"}
        content = content_path.read_text(encoding="utf-8")

    if is_html:
        final_html = sanitize_html_fragment(content)
    elif raw:
        final_html = raw_text_to_html(content)
    else:
        final_html = md_to_html(content)

    plain_text = strip_html_tags(final_html)
    return final_html, plain_text, content_path


def upload_cover(page, cover_path: str):
    file_path = Path(cover_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Cover image not found: {cover_path}")

    mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")

    result = page.evaluate(
        """async (payload) => {
          const bytes = Uint8Array.from(atob(payload.base64), c => c.charCodeAt(0));
          const blob = new Blob([bytes], { type: payload.mimeType });
          const file = new File([blob], payload.filename, { type: payload.mimeType });
          const form = new FormData();
          form.append('upfile', file);
          const resp = await fetch(
            '/mp/agw/article_material/photo/upload_picture?type=ueditor&pgc_watermark=1&action=uploadimage&encode=utf-8',
            { method: 'POST', body: form, credentials: 'include' }
          );
          return { status: resp.status, json: await resp.json() };
        }""",
        {
            "base64": encoded,
            "filename": file_path.name,
            "mimeType": mime_type,
        },
    )

    if result.get("status") != 200 or result.get("json", {}).get("code") != 0:
        raise RuntimeError(f"Cover upload failed: {json.dumps(result, ensure_ascii=False)}")

    data = result["json"]
    return {
        "id": 0,
        "url": data["url"],
        "uri": data.get("web_uri") or data.get("original"),
        "origin_uri": data.get("origin_web_uri") or data.get("original") or data.get("web_uri"),
        "ic_uri": "",
        "thumb_width": data.get("width", 0),
        "thumb_height": data.get("height", 0),
    }


def upload_inline_image(page, image_path: str) -> str:
    uploaded = upload_cover(page, image_path)
    return uploaded["url"]


def replace_local_images_with_uploaded_urls(page, final_html: str, content_path: Path | None) -> tuple[str, list[str]]:
    if not content_path:
        return final_html, []

    base_dir = content_path.parent
    uploaded_paths: dict[str, str] = {}
    uploaded_urls: list[str] = []

    def repl(match):
        full = match.group(0)
        src = match.group(3).strip()
        if re.match(r"^(https?:|data:)", src, flags=re.IGNORECASE):
            return full

        local_path = (base_dir / src).resolve()
        if not local_path.exists():
            print(f"⚠️ Inline image not found, removing tag: {src}")
            return ""

        local_key = str(local_path)
        if local_key not in uploaded_paths:
            uploaded_paths[local_key] = upload_inline_image(page, local_key)
            uploaded_urls.append(uploaded_paths[local_key])
            print(f"✅ Inline image uploaded: {local_path.name}")

        remote_url = uploaded_paths[local_key]
        return full.replace(src, remote_url)

    updated_html = re.sub(r"<img\b([^>]*?)src=(['\"])(.*?)\2([^>]*)>", repl, final_html, flags=re.IGNORECASE)
    return updated_html, uploaded_urls


def publish_article(page, payload: dict):
    result = page.evaluate(
        """async (payload) => {
          const form = new URLSearchParams();
          for (const [key, value] of Object.entries(payload)) {
            form.append(key, value);
          }
          const resp = await fetch(
            '/mp/agw/article/publish?source=mp&type=article&aid=1231&mp_publish_ab_val=0',
            {
              method: 'POST',
              credentials: 'include',
              headers: { 'content-type': 'application/x-www-form-urlencoded;charset=UTF-8' },
              body: form.toString(),
            }
          );
          return { status: resp.status, text: await resp.text() };
        }""",
        payload,
    )

    if result.get("status") != 200:
        raise RuntimeError(f"Publish request failed: {json.dumps(result, ensure_ascii=False)}")

    try:
        parsed = json.loads(result["text"])
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Unexpected publish response: {result['text'][:1000]}") from exc

    return parsed


def main():
    parser = argparse.ArgumentParser(description="Toutiao Article Publisher (API)")
    parser.add_argument("--title", help="Article title")
    parser.add_argument("--content", help="Article content (file path or inline text)")
    parser.add_argument("--cover", help="Path to cover image")
    parser.add_argument("--dry-run", action="store_true", help="Build payload only, do not publish")
    parser.add_argument("--no-cover", action="store_true", help="Publish with no cover")
    parser.add_argument("--raw", action=argparse.BooleanOptionalAction, default=False, help="Treat content as plain text")
    args = parser.parse_args()

    title = optimize_title(args.title or "")
    if not title:
        print("❌ Missing title")
        sys.exit(1)

    final_html, plain_text, content_path = load_content(args.content, raw=args.raw)
    if not final_html.strip():
        print("❌ Content is empty")
        sys.exit(1)

    cover_path = args.cover
    if not cover_path and not args.no_cover and content_path:
        cover_path = infer_cover_from_content_path(content_path)
        if cover_path:
            print(f"🖼️ Auto-resolved cover image: {cover_path}")

    auth_manager = AuthManager()

    with sync_playwright() as p:
        context = BrowserFactory.launch_persistent_context(p, headless=False)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(PUBLISH_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        current_url = page.evaluate("window.location.href")
        if "login" in current_url.lower():
            print("⚠️ Redirected to login page.")
            print("⏳ Waiting for user login (5 mins)...")
            print("   Please complete login in the browser window.")

            start_time = time.time()
            logged_in = False
            while time.time() - start_time < 300:
                for candidate in context.pages:
                    try:
                        candidate_url = candidate.url
                    except Exception:
                        continue

                    if (
                        "auth/page/login" not in candidate_url
                        and "mp.toutiao.com" in candidate_url
                    ) or "profile_v4" in candidate_url:
                        page = candidate
                        logged_in = True
                        break

                if logged_in:
                    break

                time.sleep(1)

            if not logged_in:
                print("❌ Login timeout. Please re-auth first.")
                context.close()
                sys.exit(1)

            print("✅ Detected login! Saving state...")
            try:
                auth_manager._save_browser_state(context)
                auth_manager._save_auth_info()
            except Exception as exc:
                print(f"⚠️ Failed to persist login state: {exc}")

            if PUBLISH_URL not in page.url:
                page.goto(PUBLISH_URL, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(5000)

            current_url = page.evaluate("window.location.href")
            if "login" in current_url.lower():
                print("❌ Redirected to login page. Please re-auth first.")
                context.close()
                sys.exit(1)

        final_html, inline_image_urls = replace_local_images_with_uploaded_urls(page, final_html, content_path)

        covers = []
        cover_type = 1
        if cover_path and not args.no_cover:
            covers = [upload_cover(page, cover_path)]
            cover_type = 2
            print("✅ Cover uploaded")

        title_id = f"{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        payload = {
            "title": title,
            "content": final_html,
            "activity_tag": "0",
            "title_id": title_id,
            "claim_origin": "0",
            "claim_exclusive": "0",
            "article_ad_type": "2",
            "is_fans_article": "0",
            "govern_forward": "0",
            "timer_status": "0",
            "timer_time": "",
            "praise": "0",
            "community_sync": "0",
            "qy_self_recommendation": "0",
            "pgc_feed_covers": json.dumps(covers, ensure_ascii=False),
            "tree_plan_article": "0",
            "save": "1",
            "source": "0",
            "disable_praise": "0",
            "trends_writing_tag": "0",
            "draft_form_data": json.dumps({"coverType": cover_type}, ensure_ascii=False),
            "extra": json.dumps(
                {
                    "content_source": 100000000402,
                    "content_word_cnt": len(plain_text),
                    "is_multi_title": 0,
                    "sub_titles": [],
                    "gd_ext": {
                        "entrance": "",
                        "from_page": "publisher_mp",
                        "enter_from": "PC",
                        "device_platform": "mp",
                        "is_message": 0,
                    },
                    "tuwen_wtt_transfer_switch": "0",
                },
                ensure_ascii=False,
            ),
        }

        if args.dry_run:
            print(json.dumps(
                {
                    "title": title,
                    "cover_path": cover_path,
                    "cover_type": cover_type,
                    "inline_image_count": len(inline_image_urls),
                    "payload_keys": sorted(payload.keys()),
                    "content_preview": plain_text[:300],
                },
                ensure_ascii=False,
                indent=2,
            ))
            context.close()
            return

        result = publish_article(page, payload)
        print(json.dumps(result, ensure_ascii=False))
        context.close()

        if result.get("code") != 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
