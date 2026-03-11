---
name: tencent-dev-community-publisher
description: Publish articles to Tencent Developer Community (腾讯开发者社区) with persistent login. Supports pre-flight checks, one-time auth setup, EXTEND.md preferences, and browser automation for title/content/cover/publish workflow.
---

# Tencent Developer Community Publisher

## Language

Match the user's language for prompts, commands, and completion reports.

## Script Directory

Resolve this file's directory as `SKILL_DIR`, then run scripts via:

```bash
python ${SKILL_DIR}/scripts/run.py <script.py> [args...]
```

| Script | Purpose |
|---|---|
| `scripts/check_permissions.py` | Pre-flight checks |
| `scripts/auth_manager.py` | Login setup/status/validate/clear |
| `scripts/publisher.py` | Article publish automation |
| `scripts/extend_config.py` | EXTEND.md preference loading |

## When to Use

Trigger this skill when user asks to:

- publish article to Tencent Developer Community / 腾讯开发者社区
- setup or fix Tencent community login session
- automate title/content/cover filling on `cloud.tencent.com/developer/article/write`

## Preferences (EXTEND.md)

Load optional preferences in this order:

1. Project-level: `.baoyu-skills/tencent-dev-community-publisher/EXTEND.md`
2. User-level: `~/.baoyu-skills/tencent-dev-community-publisher/EXTEND.md`

If no file exists and user wants stable defaults, follow:
[references/config/first-time-setup.md](references/config/first-time-setup.md)

Supported keys:

- `default_headless`
- `default_no_cover`
- `default_raw`
- `default_debug_screenshots`
- `default_wait_seconds`
- `default_login_timeout_minutes`
- `default_auth_headless`

Boolean accepts: `1/0`, `true/false`, `yes/no`.

Priority for publish/auth options:

1. CLI args
2. EXTEND.md
3. Script defaults

## Workflow

```text
Tencent Community Publishing Progress:
- [ ] Step 0: Load EXTEND.md preferences
- [ ] Step 1: Run pre-flight checks
- [ ] Step 2: Ensure authentication is valid
- [ ] Step 3: Resolve publish params (title/content/cover)
- [ ] Step 4: Execute publish flow
- [ ] Step 5: Report result and next actions
```

### Step 1: Pre-flight checks

```bash
python ${SKILL_DIR}/scripts/run.py check_permissions.py
```

### Step 2: Authentication

First-time login:

```bash
python ${SKILL_DIR}/scripts/run.py auth_manager.py setup
```

Management commands:

```bash
python ${SKILL_DIR}/scripts/run.py auth_manager.py status
python ${SKILL_DIR}/scripts/run.py auth_manager.py validate
python ${SKILL_DIR}/scripts/run.py auth_manager.py clear
python ${SKILL_DIR}/scripts/run.py auth_manager.py reauth
```

### Step 3: Resolve publish params

Reference:
[references/article-posting.md](references/article-posting.md)

Rules:

- `--title` is strongly recommended.
- `--content` accepts file path or inline text.
- `--cover` is optional.
- `--no-cover` can force no-cover mode.
- When `--content` is a Markdown file that contains local image references like `![图](images/01.jpg)`, the publisher now uploads those body images in order and inserts them into the editor.
- If `--cover` points to the same image as the first Markdown image, the body insertion step skips that duplicate and keeps it only as cover.

### Step 4: Publish

Standard:

```bash
python ${SKILL_DIR}/scripts/run.py publisher.py --title "标题" --content article.md
```

Headless:

```bash
python ${SKILL_DIR}/scripts/run.py publisher.py --title "标题" --content article.md --headless
```

Debug mode:

```bash
python ${SKILL_DIR}/scripts/run.py publisher.py --title "标题" --content article.md --debug-screenshots --wait-seconds 30
```

### Step 5: Completion report

Report should include:

- input type/path
- resolved options (`headless`, `no_cover`, `raw`)
- auth state (existing/new login)
- publish result (success/failure)
- if failed: failed phase + retry command

## Security Notes

- `run.py` prevents path traversal and only executes scripts in `scripts/`.
- Auth state is stored in skill-local `data/`.
- Debug screenshots are off by default and created only when enabled.
