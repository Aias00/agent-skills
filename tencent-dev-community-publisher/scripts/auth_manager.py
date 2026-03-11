#!/usr/bin/env python3
"""
Authentication manager for Tencent Developer Community Publisher.
Handles login setup/status/validate/clear with persistent browser state.
"""

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, Tuple

from patchright.sync_api import BrowserContext, sync_playwright

sys.path.insert(0, str(Path(__file__).parent))

from browser_utils import BrowserFactory
from config import AUTH_INFO_FILE, BROWSER_STATE_DIR, DATA_DIR, HOME_URL, LOGIN_URL, PUBLISH_URL, STATE_FILE
from extend_config import load_extend_settings, to_bool, to_int


def is_login_url(url: str) -> bool:
    return "cloud.tencent.com/login" in (url or "")


def is_authenticated_url(url: str) -> bool:
    u = url or ""
    return "cloud.tencent.com/developer" in u and not is_login_url(u)


class AuthManager:
    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        BROWSER_STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.state_file = STATE_FILE
        self.auth_info_file = AUTH_INFO_FILE
        self.browser_state_dir = BROWSER_STATE_DIR

    def _profile_cookie_db(self) -> Path:
        return self.browser_state_dir / "browser_profile" / "Default" / "Cookies"

    def has_profile_auth_state(self) -> bool:
        return self._profile_cookie_db().exists()

    def is_authenticated(self) -> bool:
        if not self.state_file.exists():
            return False

        age_days = (time.time() - self.state_file.stat().st_mtime) / 86400
        if age_days > 7:
            print(f"⚠️ Browser state is {age_days:.1f} days old; re-auth may be needed")
        return True

    def get_auth_info(self) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "authenticated": self.is_authenticated(),
            "state_file": str(self.state_file),
            "state_exists": self.state_file.exists(),
            "profile_cookie_db": str(self._profile_cookie_db()),
            "profile_cookie_db_exists": self.has_profile_auth_state(),
        }

        if self.auth_info_file.exists():
            try:
                with open(self.auth_info_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                info.update(saved)
            except Exception:
                pass

        if info["state_exists"]:
            info["state_age_hours"] = (time.time() - self.state_file.stat().st_mtime) / 3600

        return info

    def setup_auth(self, headless: bool = False, timeout_minutes: int = 10) -> bool:
        print("🔐 Starting Tencent Developer auth setup...")
        print(f"  Timeout: {timeout_minutes} minutes")

        playwright = None
        context = None
        try:
            playwright = sync_playwright().start()
            context = BrowserFactory.launch_persistent_context(playwright, headless=headless)

            page = context.new_page()
            page.goto(LOGIN_URL, wait_until="domcontentloaded")

            if is_authenticated_url(page.url):
                print("  ✅ Already authenticated")
                self._save_browser_state(context)
                self._save_auth_info()
                return True

            print("\n  ⏳ Please log in to Tencent Developer Community...")
            print("  (Scan QR code or use account login in opened browser)")
            print(f"  💡 After login, open: {PUBLISH_URL}")

            start_time = time.time()
            last_wait_log_second = -1

            while time.time() - start_time < timeout_minutes * 60:
                elapsed = int(time.time() - start_time)
                if elapsed % 15 == 0 and elapsed != last_wait_log_second:
                    last_wait_log_second = elapsed
                    print(f"  ...waiting ({elapsed}s)")

                ok, detected_url = self._scan_context_authenticated(context)
                if ok:
                    print(f"  ✅ Login successful! (Detected URL: {detected_url})")
                    time.sleep(2)
                    self._save_browser_state(context)
                    self._save_auth_info()
                    return True

                time.sleep(1)

            print("  ❌ Timeout waiting for successful login")
            return False

        except Exception as e:
            print(f"  ❌ Error during auth setup: {e}")
            return False

        finally:
            if context:
                try:
                    context.close()
                except Exception:
                    pass
            if playwright:
                try:
                    playwright.stop()
                except Exception:
                    pass

    def _scan_context_authenticated(self, context: BrowserContext) -> Tuple[bool, str]:
        for p in context.pages:
            try:
                current_url = p.url
                if is_authenticated_url(current_url):
                    return True, current_url
            except Exception:
                continue
        return False, ""

    def validate_auth(self) -> bool:
        if not self.state_file.exists() and not self.has_profile_auth_state():
            return False

        print("🔍 Validating authentication...")
        playwright = None
        context = None
        try:
            playwright = sync_playwright().start()
            context = BrowserFactory.launch_persistent_context(playwright, headless=True)
            page = context.new_page()
            page.goto(PUBLISH_URL, wait_until="domcontentloaded", timeout=30000)

            if is_login_url(page.url):
                print("  ❌ Authentication is invalid (redirected to login)")
                return False

            if is_authenticated_url(page.url):
                print("  ✅ Authentication is valid")
                if not self.state_file.exists():
                    self._save_browser_state(context)
                    self._save_auth_info()
                    print("  💾 Auto-saved browser state from existing profile login")
                return True

            print(f"  ⚠️ Unknown validation URL: {page.url}")
            return False

        except Exception as e:
            print(f"  ❌ Validation failed: {e}")
            return False

        finally:
            if context:
                try:
                    context.close()
                except Exception:
                    pass
            if playwright:
                try:
                    playwright.stop()
                except Exception:
                    pass

    def clear_auth(self) -> bool:
        print("🗑️ Clearing authentication data...")
        try:
            if self.state_file.exists():
                self.state_file.unlink()
                print("  ✅ Removed browser state")

            if self.auth_info_file.exists():
                self.auth_info_file.unlink()
                print("  ✅ Removed auth info")

            if self.browser_state_dir.exists():
                shutil.rmtree(self.browser_state_dir)
                self.browser_state_dir.mkdir(parents=True, exist_ok=True)
                print("  ✅ Cleared browser profile directory")

            return True
        except Exception as e:
            print(f"  ❌ Failed to clear auth data: {e}")
            return False

    def re_auth(self, headless: bool = False, timeout_minutes: int = 10) -> bool:
        print("🔄 Starting re-authentication...")
        self.clear_auth()
        return self.setup_auth(headless=headless, timeout_minutes=timeout_minutes)

    def _save_browser_state(self, context: BrowserContext) -> None:
        context.storage_state(path=str(self.state_file))
        self._harden_file_permissions(self.state_file)
        print(f"  💾 Saved browser state: {self.state_file}")

    def _save_auth_info(self) -> None:
        info = {
            "authenticated_at": time.time(),
            "authenticated_at_iso": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(self.auth_info_file, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2)
        self._harden_file_permissions(self.auth_info_file)

    @staticmethod
    def _harden_file_permissions(path: Path) -> None:
        if os.name == "nt":
            return
        try:
            path.chmod(0o600)
        except Exception as e:
            print(f"  ⚠️ Could not harden permissions for {path}: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage Tencent Developer auth state")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    setup_parser = subparsers.add_parser("setup", help="Setup authentication")
    setup_parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Run in headless mode (default from EXTEND.md or false)",
    )
    setup_parser.add_argument("--timeout", type=int, default=None, help="Login timeout in minutes")

    subparsers.add_parser("status", help="Check authentication status")
    subparsers.add_parser("validate", help="Validate authentication")
    subparsers.add_parser("clear", help="Clear authentication")

    reauth_parser = subparsers.add_parser("reauth", help="Re-authenticate")
    reauth_parser.add_argument("--timeout", type=int, default=None, help="Login timeout in minutes")

    args = parser.parse_args()
    extend_path, extend = load_extend_settings()
    if extend_path:
        print(f"⚙️ Loaded preferences from: {extend_path}")

    auth = AuthManager()

    if args.command == "setup":
        headless = args.headless if args.headless is not None else to_bool(extend.get("default_auth_headless"), False)
        timeout = args.timeout if args.timeout is not None else to_int(extend.get("default_login_timeout_minutes"), 10)
        if auth.setup_auth(headless=headless, timeout_minutes=timeout):
            print("\n✅ Authentication setup complete")
        else:
            print("\n❌ Authentication setup failed")
            sys.exit(1)

    elif args.command == "status":
        info = auth.get_auth_info()
        print("\n🔐 Authentication Status:")
        print(f"  Authenticated: {'Yes' if info['authenticated'] else 'No'}")
        if info.get("profile_cookie_db_exists"):
            print("  Profile cookies: Present")
        if info.get("state_age_hours") is not None:
            print(f"  State age: {info['state_age_hours']:.1f} hours")
        if info.get("authenticated_at_iso"):
            print(f"  Last auth: {info['authenticated_at_iso']}")
        print(f"  State file: {info['state_file']}")

    elif args.command == "validate":
        if auth.validate_auth():
            print("Authentication is valid and working")
        else:
            print("Authentication is invalid or expired")
            print("Run: auth_manager.py setup")
            sys.exit(1)

    elif args.command == "clear":
        if auth.clear_auth():
            print("Authentication cleared")
        else:
            sys.exit(1)

    elif args.command == "reauth":
        timeout = args.timeout if args.timeout is not None else to_int(extend.get("default_login_timeout_minutes"), 10)
        if auth.re_auth(timeout_minutes=timeout):
            print("\n✅ Re-authentication complete")
        else:
            print("\n❌ Re-authentication failed")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
