"""
Browser utilities for Tencent Developer Community Publisher.
"""

import json
import random
import time

from patchright.sync_api import BrowserContext, Page, Playwright

from config import BROWSER_ARGS, BROWSER_PROFILE_DIR, STATE_FILE, USER_AGENT


class BrowserFactory:
    """Factory for creating configured browser contexts."""

    @staticmethod
    def launch_persistent_context(
        playwright: Playwright,
        headless: bool = True,
        user_data_dir: str = str(BROWSER_PROFILE_DIR),
    ) -> BrowserContext:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="chrome",
            headless=headless,
            no_viewport=True,
            ignore_default_args=["--enable-automation"],
            user_agent=USER_AGENT,
            args=BROWSER_ARGS,
        )
        BrowserFactory._inject_cookies(context)
        return context

    @staticmethod
    def _inject_cookies(context: BrowserContext) -> None:
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                cookies = state.get("cookies") or []
                if cookies:
                    context.add_cookies(cookies)
            except Exception as e:
                print(f"⚠️ Could not load state.json cookies: {e}")


class StealthUtils:
    """Human-like interaction helpers."""

    @staticmethod
    def random_delay(min_ms: int = 120, max_ms: int = 480) -> None:
        time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))

    @staticmethod
    def human_type(page: Page, selector: str, text: str) -> bool:
        element = page.query_selector(selector)
        if not element:
            try:
                element = page.wait_for_selector(selector, timeout=2000)
            except Exception:
                return False

        try:
            element.click()
            for ch in text:
                element.type(ch, delay=random.uniform(20, 75))
                if random.random() < 0.04:
                    time.sleep(random.uniform(0.08, 0.25))
            return True
        except Exception:
            return False
