# First-Time Setup (tencent-dev-community-publisher)

## 1) Optional preference file

Create one of:

- Project-level: `.baoyu-skills/tencent-dev-community-publisher/EXTEND.md`
- User-level: `~/.baoyu-skills/tencent-dev-community-publisher/EXTEND.md`

Project-level takes priority.

### Recommended template

```md
# tencent-dev-community-publisher defaults
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

## 4) Dry-run publish test

```bash
python scripts/run.py publisher.py --title "测试标题" --content "测试内容" --dry-run
```
