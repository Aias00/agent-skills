# First-Time Setup (toutiao-publisher)

## 1) Optional preference file

Create one of:

- Project-level: `.baoyu-skills/toutiao-publisher/EXTEND.md`
- User-level: `~/.baoyu-skills/toutiao-publisher/EXTEND.md`

Project-level has higher priority.

### Recommended template

```md
# toutiao-publisher defaults
default_headless: 0
default_no_cover: 0
default_raw: 0
default_debug_screenshots: 0
default_wait_seconds: 20
default_login_timeout_minutes: 10
default_auth_headless: 0
```

Boolean accepts: `1/0`, `true/false`, `yes/no`.

## 2) Run pre-flight checks

```bash
python scripts/run.py check_permissions.py
```

## 3) Login once

```bash
python scripts/run.py auth_manager.py setup
```

## 4) Publish test article (dry run)

```bash
python scripts/run.py publisher.py --title "测试标题" --content "测试内容" --dry-run
```

