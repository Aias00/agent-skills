---
name: toutiao-publisher
description: Publish articles to Toutiao (头条号) with persistent login. Supports one-time auth setup, pre-flight checks, EXTEND.md preferences, browser automation, and direct authenticated API publishing for title/content/cover flows.
---

# Toutiao Publisher

## Language

Match the user's language for all prompts and completion reports.

## Script Directory

Determine this SKILL.md directory as `SKILL_DIR`, and run scripts via:

```bash
python ${SKILL_DIR}/scripts/run.py <script.py> [args...]
```

| Script | Purpose |
|---|---|
| `scripts/check_permissions.py` | Pre-flight environment checks |
| `scripts/auth_manager.py` | Login setup/status/validate/clear |
| `scripts/publisher.py` | Article publish automation |
| `scripts/api_publisher.py` | Direct article publish via authenticated in-page API |
| `scripts/extend_config.py` | EXTEND.md preference loading |

## When to Use

Trigger when user asks to:

- publish article to Toutiao / 今日头条 / 头条号
- setup or fix Toutiao login session
- automate title/content/cover filling on Toutiao publish page
- publish more reliably through the authenticated API path when browser autosave is unstable

## Preferences (EXTEND.md)

Load optional preferences (priority order):

1. Project-level: `.baoyu-skills/toutiao-publisher/EXTEND.md`
2. User-level: `~/.baoyu-skills/toutiao-publisher/EXTEND.md`

If none exists and user asks for stable defaults, follow:
[references/config/first-time-setup.md](references/config/first-time-setup.md)

Supported keys:

- `default_headless`
- `default_no_cover`
- `default_raw`
- `default_debug_screenshots`
- `default_wait_seconds`
- `default_login_timeout_minutes`
- `default_auth_headless`

Boolean accepts `1/0`, `true/false`, `yes/no`.

Value priority for publish/auth:

1. CLI args
2. EXTEND.md
3. Script defaults

## Workflow

Use this checklist:

```text
Toutiao Publishing Progress:
- [ ] Step 0: Load EXTEND.md preferences
- [ ] Step 1: Run pre-flight checks
- [ ] Step 2: Ensure authentication is valid
- [ ] Step 3: Resolve publish params (title/content/cover)
- [ ] Step 4: Execute publish flow
- [ ] Step 5: Report result + next actions
```

### Step 0: Load preferences

Scripts auto-load EXTEND.md. If found, mention the loaded file path.

### Step 1: Pre-flight checks

```bash
python ${SKILL_DIR}/scripts/run.py check_permissions.py
```

If check fails, provide specific fix items before continuing.

### Step 2: Authentication

First-time login:

```bash
python ${SKILL_DIR}/scripts/run.py auth_manager.py setup
```

Common management:

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

- Title is strongly recommended for automation success.
- Title length is auto-adjusted to Toutiao constraints (2-30 chars).
- `--content` accepts file path or inline text.
- If `--content` points to `.html`/`.htm`, the publisher uses that HTML directly.
- For generated article bundles, prefer `article-toutiao.md` over the generic `article.md` when both exist.
- `--cover` is optional; `--no-cover` can force no-cover mode.
- If `--cover` is omitted, the publisher will try nearby files like `images/01-cover.*`, `images/cover.*`, `images/cover-wide.*`, `cover.*`, or the first image under `images/`.
- Prefer the API publisher for direct article publishing because it uploads the cover and submits the final payload without relying on front-end autosave.
- The API publisher also uploads local inline images referenced from markdown/HTML and rewrites them to Toutiao-hosted image URLs before submit. This is the stable path when the article package contains local `images/...` assets.

### Step 4: Publish

Recommended API path:

```bash
python ${SKILL_DIR}/scripts/run.py api_publisher.py --title "标题" --content article.md
```

Explicit cover:

```bash
python ${SKILL_DIR}/scripts/run.py api_publisher.py --title "标题" --content article.md --cover ./cover.png
```

Dry-run / payload inspection:

```bash
python ${SKILL_DIR}/scripts/run.py api_publisher.py --title "标题" --content article.md --dry-run
```

Legacy browser automation:

```bash
python ${SKILL_DIR}/scripts/run.py publisher.py --title "标题" --content article.md
```

Automated/headless:

```bash
python ${SKILL_DIR}/scripts/run.py publisher.py --title "标题" --content article.md --cover ./cover.png --headless
```

Troubleshooting mode:

```bash
python ${SKILL_DIR}/scripts/run.py publisher.py --title "标题" --content article.md --debug-screenshots --wait-seconds 30
```

### Step 5: Completion report

Report:

- input type/path
- resolved options (`headless`, `no_cover`, `raw`)
- auth state usage (existing/new login)
- publish result (success/failure)
- if failed: exact failed phase and suggested retry command

## Security Notes

- `run.py` blocks path traversal and only executes scripts inside `scripts/`.
- Auth state is stored under skill `data/` and permissions are restricted on POSIX.
- Debug screenshots are disabled by default and only generated when explicitly enabled.
