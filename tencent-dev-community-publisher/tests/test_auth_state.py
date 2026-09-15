import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import auth_manager
import browser_utils


class FakeContext:
    def __init__(self, page=None):
        self.added_cookies = []
        self._page = page

    def add_cookies(self, cookies):
        self.added_cookies.extend(cookies)

    def new_page(self):
        return self._page

    def close(self):
        pass


class FakePage:
    def __init__(self, url):
        self.url = url

    def goto(self, *_args, **_kwargs):
        return None


class AuthStateTests(unittest.TestCase):
    def test_existing_profile_is_not_overwritten_by_cached_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            profile = root / "profile"
            cookie_db = profile / "Default" / "Cookies"
            cookie_db.parent.mkdir(parents=True)
            cookie_db.touch()
            state_file = root / "state.json"
            state_file.write_text(
                json.dumps({"cookies": [{"name": "stale", "value": "1"}]}),
                encoding="utf-8",
            )

            context = FakeContext()
            playwright = SimpleNamespace(
                chromium=SimpleNamespace(
                    launch_persistent_context=Mock(return_value=context)
                )
            )

            with patch.object(browser_utils, "STATE_FILE", state_file):
                browser_utils.BrowserFactory.launch_persistent_context(
                    playwright,
                    user_data_dir=str(profile),
                )

            self.assertEqual(context.added_cookies, [])

    def test_state_restore_can_be_disabled_for_interactive_login(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_file = root / "state.json"
            state_file.write_text(
                json.dumps({"cookies": [{"name": "stale", "value": "1"}]}),
                encoding="utf-8",
            )
            context = FakeContext()
            playwright = SimpleNamespace(
                chromium=SimpleNamespace(
                    launch_persistent_context=Mock(return_value=context)
                )
            )

            with patch.object(browser_utils, "STATE_FILE", state_file):
                browser_utils.BrowserFactory.launch_persistent_context(
                    playwright,
                    user_data_dir=str(root / "profile"),
                    restore_state=False,
                )

            self.assertEqual(context.added_cookies, [])

    def test_cached_state_is_restored_when_profile_was_initially_empty(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            profile = root / "profile"
            state_file = root / "state.json"
            cached_cookies = [{"name": "cached", "value": "1"}]
            state_file.write_text(
                json.dumps({"cookies": cached_cookies}),
                encoding="utf-8",
            )
            context = FakeContext()

            def launch_context(**_kwargs):
                cookie_db = profile / "Default" / "Cookies"
                cookie_db.parent.mkdir(parents=True)
                cookie_db.touch()
                return context

            playwright = SimpleNamespace(
                chromium=SimpleNamespace(launch_persistent_context=launch_context)
            )

            with patch.object(browser_utils, "STATE_FILE", state_file):
                browser_utils.BrowserFactory.launch_persistent_context(
                    playwright,
                    user_data_dir=str(profile),
                )

            self.assertEqual(context.added_cookies, cached_cookies)

    def test_successful_validation_refreshes_cached_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manager = auth_manager.AuthManager.__new__(auth_manager.AuthManager)
            manager.state_file = root / "state.json"
            manager.state_file.write_text("{}", encoding="utf-8")
            manager.auth_info_file = root / "auth_info.json"
            manager.browser_state_dir = root / "browser_state"

            page = FakePage("https://cloud.tencent.com/developer/article/write-new")
            context = FakeContext(page)
            playwright = Mock()
            starter = Mock()
            starter.start.return_value = playwright

            with (
                patch.object(auth_manager, "sync_playwright", return_value=starter),
                patch.object(
                    auth_manager.BrowserFactory,
                    "launch_persistent_context",
                    return_value=context,
                ),
                patch.object(manager, "_save_browser_state") as save_state,
                patch.object(manager, "_save_auth_info") as save_auth_info,
            ):
                self.assertTrue(manager.validate_auth())

            save_state.assert_called_once_with(context)
            save_auth_info.assert_called_once_with()

    def test_status_uses_live_validation(self):
        manager = Mock()
        manager.validate_auth.return_value = False
        manager.get_auth_info.return_value = {
            "authenticated": True,
            "state_file": "/tmp/state.json",
            "state_exists": True,
            "profile_cookie_db_exists": True,
            "state_age_hours": 1.0,
        }

        output = io.StringIO()
        with (
            patch.object(auth_manager, "AuthManager", return_value=manager),
            patch.object(auth_manager, "load_extend_settings", return_value=(None, {})),
            patch.object(sys, "argv", ["auth_manager.py", "status"]),
            redirect_stdout(output),
        ):
            auth_manager.main()

        manager.validate_auth.assert_called_once_with()
        self.assertIn("Authenticated: No", output.getvalue())


if __name__ == "__main__":
    unittest.main()
