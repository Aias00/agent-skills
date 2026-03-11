"""
Configuration for Tencent Developer Community Publisher Skill
"""

from pathlib import Path

# Paths
SKILL_DIR = Path(__file__).parent.parent
DATA_DIR = SKILL_DIR / "data"
BROWSER_STATE_DIR = DATA_DIR / "browser_state"
BROWSER_PROFILE_DIR = BROWSER_STATE_DIR / "browser_profile"
STATE_FILE = BROWSER_STATE_DIR / "state.json"
AUTH_INFO_FILE = DATA_DIR / "auth_info.json"
DEBUG_SCREENSHOT_DIR = DATA_DIR / "debug_screenshots"

# URLs
PUBLISH_URL = "https://cloud.tencent.com/developer/article/write"
LOGIN_URL = "https://cloud.tencent.com/login?s_url=https%3A%2F%2Fcloud.tencent.com%2Fdeveloper%2Farticle%2Fwrite"
HOME_URL = "https://cloud.tencent.com/developer"

# Browser Configuration
BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--no-first-run",
    "--no-default-browser-check",
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Timeouts
LOGIN_TIMEOUT_MINUTES = 10
PAGE_LOAD_TIMEOUT = 30000
DEFAULT_TIMEOUT = 30000
