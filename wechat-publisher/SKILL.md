---
name: wechat-publisher
description: Posts content to WeChat Official Account (微信公众号) via API or Chrome CDP. Supports article posting (文章) with HTML, markdown, or plain text input, and image-text posting (贴图, formerly 图文) with multiple images. Use when user mentions "发布公众号", "post to wechat", "微信公众号", or "贴图/图文/文章".
---

# Post to WeChat Official Account

## Language

**Match user's language**: Respond in the same language the user uses. If user writes in Chinese, respond in Chinese. If user writes in English, respond in English.

## Script Directory

**Agent Execution**: Determine this SKILL.md directory as `SKILL_DIR`, then use `${SKILL_DIR}/scripts/<name>` (supports `.ts` and `.py`).

| Script | Purpose |
|--------|---------|
| `scripts/wechat-publish.ts` | Unified article entry: delegate to API or browser based on `wechat-publisher` defaults/current environment |
| `scripts/wechat-browser.ts` | Image-text posts (图文) |
| `scripts/wechat-article.ts` | Article posting via browser (文章) |
| `scripts/wechat-api.ts` | Article posting via API (文章) |
| `scripts/md-to-wechat.ts` | Legacy internal markdown renderer (compatibility path only) |
| `scripts/check-permissions.ts` | Verify environment & permissions |
| `scripts/generate-cover-image.py` | Generate topic-aligned cover image (`imgs/cover.png`) from markdown/title |
| `scripts/render-svg-cover.py` | Render custom SVG cover layouts to WeChat-safe PNG (prefer local resvg, fallback to Chrome) |

## Reproducibility Boundary

Before using this skill on a freshly cloned machine, treat setup in three layers:

1. **Repo-local reproducible layer**
   - install runtime deps
   - bootstrap repo-local config files
   - run doctor / environment checks
2. **Machine-local API layer**
   - requires real WeChat API credentials and current IP whitelist
3. **Machine-local browser layer**
   - requires Chrome login session and desktop automation permissions

Reference: [references/reproducibility.md](references/reproducibility.md)

**Recommended fresh-clone bootstrap**:

```bash
cd wechat-publisher
bun install
bun scripts/bootstrap-local.ts --project-root ..
bun scripts/check-permissions.ts --project-root ..
```

This bootstrap does **not** make API/browser publishing magically portable by itself.
It only makes the repo-local part reproducible:

- config file locations
- preferred formatter Python runtime
- runtime dependencies
- cover renderer availability
- dry-run / preflight checks

## Canonical Path

Treat this as the **only recommended article path** on a fresh clone:

```bash
cd wechat-publisher
bun install
bun scripts/bootstrap-local.ts --project-root ..
bun scripts/check-permissions.ts --project-root ..
bun scripts/wechat-publish.ts /abs/path/article.md --dry-run
```

Then choose the real publish mode:

- keep using `scripts/wechat-publish.ts` as the standard entry
- let it delegate to API or browser based on config / current environment
- expect Markdown input to be rendered through the repo-local `wechat-article-formatter` with `mist-blue`

If you need direct control:

- `scripts/wechat-api.ts <article.md>` is the direct API entry
- `scripts/wechat-article.ts --markdown <article.md>` is the direct browser entry

But these are still **secondary entries**. The canonical path is `scripts/wechat-publish.ts`.

## Incorrect Or Legacy Paths

Mark these as **non-standard** when helping users:

- Running `scripts/md-to-wechat.ts` directly as the primary flow
  - This is legacy compatibility only.
- Assuming `default/grace/simple/modern` are the active project themes
  - Standard repo-local publishing now normalizes these to `mist-blue`.
- Running `check-permissions.ts` before `bootstrap-local.ts`
  - You can get misleading results because the preferred formatter runtime may not exist yet.
- Publishing Markdown from a fresh clone before the formatter venv exists
  - This is the exact failure mode that previously caused “doctor passed but publish formatting still broke”.
- Treating API/browser publishing as fully repo-reproducible
  - Actual publish still depends on credentials, whitelist, login state, and desktop permissions.

## Preferences (EXTEND.md)

Use Bash to check EXTEND.md existence (priority order):

```bash
# Check project-level first
test -f .baoyu-skills/wechat-publisher/EXTEND.md && echo "project"

# Then user-level (cross-platform: $HOME works on macOS/Linux/WSL)
test -f "$HOME/.baoyu-skills/wechat-publisher/EXTEND.md" && echo "user"
```

┌────────────────────────────────────────────────────────┬───────────────────┐
│                          Path                          │     Location      │
├────────────────────────────────────────────────────────┼───────────────────┤
│ .baoyu-skills/wechat-publisher/EXTEND.md           │ Project directory │
├────────────────────────────────────────────────────────┼───────────────────┤
│ $HOME/.baoyu-skills/wechat-publisher/EXTEND.md     │ User home         │
└────────────────────────────────────────────────────────┴───────────────────┘

┌───────────┬───────────────────────────────────────────────────────────────────────────┐
│  Result   │                                  Action                                   │
├───────────┼───────────────────────────────────────────────────────────────────────────┤
│ Found     │ Read, parse, apply settings                                               │
├───────────┼───────────────────────────────────────────────────────────────────────────┤
│ Not found │ Run first-time setup ([references/config/first-time-setup.md](references/config/first-time-setup.md)) → Save → Continue │
└───────────┴───────────────────────────────────────────────────────────────────────────┘

**EXTEND.md Supports**: Default theme | Default color | Default publishing method (api/browser) | Default author | Default open-comment switch | Default fans-only-comment switch | Chrome profile path

First-time setup: [references/config/first-time-setup.md](references/config/first-time-setup.md)

**Minimum supported keys** (case-insensitive, accept `1/0` or `true/false`):

| Key | Default | Mapping |
|-----|---------|---------|
| `default_author` | empty | Fallback for `author` when CLI/frontmatter not provided |
| `need_open_comment` | `1` | `articles[].need_open_comment` in `draft/add` request |
| `only_fans_can_comment` | `0` | `articles[].only_fans_can_comment` in `draft/add` request |

**Recommended EXTEND.md example**:

```md
default_theme: mist-blue
default_publish_method: api
default_author: 宝玉
need_open_comment: 1
only_fans_can_comment: 0
chrome_profile_path: /path/to/chrome/profile
```

**Theme options**: `mist-blue` (recommended), `ai-tech` (alternate), legacy `default/grace/simple/modern` (auto-normalized to `mist-blue` in the standard path)

**Color presets**: only used by the legacy internal markdown renderer. The repo-local preferred formatter path ignores `default_color`.

**Value priority**:
1. CLI arguments
2. Frontmatter
3. EXTEND.md
4. Skill defaults

## Pre-flight Check (Optional)

Before first use, suggest running the environment check. User can skip if they prefer.

```bash
cd ${SKILL_DIR}
bun install
npx -y bun ${SKILL_DIR}/scripts/bootstrap-local.ts --project-root ..
npx -y bun ${SKILL_DIR}/scripts/check-permissions.ts --project-root ..
```

Checks: Chrome, profile isolation, Bun, Accessibility, clipboard, paste keystroke, API credentials, Chrome conflicts.

**If any check fails**, provide fix guidance per item:

| Check | Fix |
|-------|-----|
| Chrome | Install Chrome or set `WECHAT_BROWSER_CHROME_PATH` env var |
| Profile dir | Ensure `~/.local/share/wechat-browser-profile` is writable |
| Bun runtime | `curl -fsSL https://bun.sh/install \| bash` |
| Accessibility (macOS) | System Settings → Privacy & Security → Accessibility → enable terminal app |
| Clipboard copy | Ensure Swift/AppKit available (macOS Xcode CLI tools: `xcode-select --install`) |
| Paste keystroke (macOS) | Same as Accessibility fix above |
| Paste keystroke (Linux) | Install `xdotool` (X11) or `ydotool` (Wayland) |
| API credentials | Follow guided setup in Step 2, or manually set in `.baoyu-skills/.env` |
| Repo runtime deps | Run `cd wechat-publisher && bun install` |
| Project bootstrap files | Run `bun scripts/bootstrap-local.ts --project-root ..` from `wechat-publisher/` |

## Image-Text Posting (图文)

For short posts with multiple images (up to 9):

```bash
npx -y bun ${SKILL_DIR}/scripts/wechat-browser.ts --markdown article.md --images ./images/
npx -y bun ${SKILL_DIR}/scripts/wechat-browser.ts --title "标题" --content "内容" --image img.png --submit
```

See [references/image-text-posting.md](references/image-text-posting.md) for details.

## Article Posting Workflow (文章)

Copy this checklist and check off items as you complete them:

```
Publishing Progress:
- [ ] Step 0: Load preferences (EXTEND.md)
- [ ] Step 0.5: Prepare article package for submission
- [ ] Step 1: Determine input type
- [ ] Step 2: Select method and configure credentials
- [ ] Step 3: Resolve theme/color and validate metadata
- [ ] Step 3.5: Auto-generate cover if missing
- [ ] Step 4: Publish to WeChat
- [ ] Step 5: Report completion
```

### Step 0: Load Preferences

Check and load EXTEND.md settings (see Preferences section above).

**CRITICAL**: If not found, complete first-time setup BEFORE any other steps or questions.

For a freshly cloned repo, prefer the deterministic bootstrap path first:

```bash
cd ${SKILL_DIR}
bun install
bun scripts/bootstrap-local.ts --project-root ..
bun scripts/check-permissions.ts --project-root ..
```

Only if the user wants interactive setup instead of copying templates should you fall back to the guided first-time setup flow.

Resolve and store these defaults for later steps:
- `default_theme` (default `mist-blue`)
- `default_color` (legacy internal renderer only; omit if not set)
- `default_author`
- `need_open_comment` (default `1`)
- `only_fans_can_comment` (default `0`)

The direct scripts also read `wechat-publisher/EXTEND.md`, so CLI runs stay aligned with these defaults even when the agent is not manually passing every field.

### Step 0.5: Prepare Article Package For Submission

For long technical articles, do NOT jump directly from markdown draft to WeChat publish.
Run this prep flow first:

1. **Review the article for technical publish readiness**
   - For technical posts, review the markdown with `technical-article-review` before formatting/publishing.
   - This applies even if the article was drafted just now in the same turn.
   - Focus on:
     - fact vs inference separation
     - whether time-sensitive numbers are caveated
     - whether at least one mechanism and one reproducible path are present
     - whether failure cases / boundaries are explicit
   - If the article reads like a good commentary but lacks reproducibility, revise the markdown first.
   - Unless the user explicitly asked for review-only, treat the review as a direct input to source revision in the same turn.
   - Do not move a first draft directly into HTML or WeChat publish just because the user asked for a WeChat article.

2. **Revise the markdown draft before HTML conversion**
   - Preferred fixes:
     - replace unsupported exact numbers with dated approximate values unless you can verify them
     - add a short “minimum prerequisites / how to run” section when the post discusses code or experiments
     - turn slogan paragraphs into mechanism + condition statements
     - reduce speculative wording around internal implementation details
     - add one concrete “first run” or “minimum workflow” path when the article is recommendation-heavy

3. **Confirm the review fixes landed in the source draft**
   - Before touching HTML, verify that the markdown source actually reflects the review conclusions.
   - Minimum check:
     - top blocking findings were fixed in the source article
     - newly added setup steps or commands are traceable to README, code, or docs
     - no old HTML was patched as a shortcut while markdown stayed stale

4. **Verify cover and inline images before publish**
   - Ensure the article bundle has:
     - one cover image at `imgs/cover.png` (or explicit `--cover`)
     - all inline images present on disk and referenced from the final markdown / HTML
   - Cover-specific checks:
     - preferred cover size is `900x383`
     - reserve a safe text area for title/subtitle; do not let chips or side cards overlap it
     - assume Chinese technical titles may need two full lines
   - For custom diagrams:
     - keep text within a safe inner area; do not let long labels touch card edges
     - prefer manual line breaks for long variable names such as `TIME_BUDGET`, `peak_vram_mb`, `evaluate_bpb`
     - export SVG to PNG using a tool/path that preserves the original canvas ratio
   - For custom SVG covers with Chinese text:
     - prefer `render-svg-cover.py` so the browser engine renders local fonts correctly
     - do not use thumbnail-style exporters or font-limited SVG renderers for the final publish cover
   - **Do not rely on thumbnail-style SVG export paths** that silently turn 16:9 diagrams into cropped square PNGs.

5. **Regenerate the final HTML from the revised markdown**
   - If the source of truth is markdown, re-run the formatter after edits instead of patching old HTML by hand.
   - Then re-apply project visual styling if you use a custom article theme outside the formatter defaults.

6. **Do one final local verification pass**
   - Confirm:
     - title/summary/author metadata are correct
     - images load
     - lists and numbering render correctly
     - theme/colors did not fall back to formatter defaults unexpectedly

Only after this prep flow is complete should you proceed to Step 1 / Step 4 publishing.

### Step 1: Determine Input Type

| Input Type | Detection | Action |
|------------|-----------|--------|
| HTML file | Path ends with `.html`, file exists | Skip to Step 3 |
| Markdown file | Path ends with `.md`, file exists | Continue to Step 2 |
| Plain text | Not a file path, or file doesn't exist | Save to markdown, continue to Step 2 |

**HTML file preference**:
- If the article package contains `article-api.html`, use it for API publishing.
- If the article package contains `article-preview.md`, use it for browser automation publishing. This path keeps real image references and lets the browser workflow reinsert images reliably.
- `article-wechat.html` is the preferred file for manual copy/paste into the WeChat editor, not the first choice for browser automation.
- `article-api.html` should be considered the API-safe variant when long URLs, lists, or WeChat line-breaking quirks need special handling.
- For browser automation, the most reliable cover strategy is to keep the chosen cover image inside the article body as a real inline image, ideally near the top of `article-preview.md`.
- For custom HTML input, the browser script now auto-detects local `<img src>` paths relative to the HTML file. `data-local-path` is still acceptable, but no longer required for normal local image bundles.
- For markdown sources, standalone badge marker lines such as `[!AI] [!推荐]` are treated as source-side artifacts and stripped before rendering to WeChat HTML.

**Plain Text Handling**:

1. Generate slug from content (first 2-4 meaningful words, kebab-case)
2. Create directory and save file:

```bash
mkdir -p "$(pwd)/post-to-wechat/$(date +%Y-%m-%d)"
# Save content to: post-to-wechat/yyyy-MM-dd/[slug].md
```

3. Continue processing as markdown file

**Slug Examples**:
- "Understanding AI Models" → `understanding-ai-models`
- "人工智能的未来" → `ai-future` (translate to English for slug)

### Step 2: Select Publishing Method and Configure

**Ask publishing method** (unless specified in EXTEND.md or CLI):

| Method | Speed | Requirements |
|--------|-------|--------------|
| `api` (Recommended) | Fast | API credentials |
| `browser` | Slow | Chrome, login session |

**If API Selected - Check Credentials**:

```bash
# Check project-level
test -f .baoyu-skills/.env && grep -q "WECHAT_APP_ID" .baoyu-skills/.env && echo "project"

# Check user-level
test -f "$HOME/.baoyu-skills/.env" && grep -q "WECHAT_APP_ID" "$HOME/.baoyu-skills/.env" && echo "user"
```

**If Credentials Missing - Guide Setup**:

```
WeChat API credentials not found.

To obtain credentials:
1. Visit https://mp.weixin.qq.com
2. Go to: 开发 → 基本配置
3. Copy AppID and AppSecret

Where to save?
A) Project-level: .baoyu-skills/.env (this project only)
B) User-level: ~/.baoyu-skills/.env (all projects)
```

After location choice, prompt for values and write to `.env`:

```
WECHAT_APP_ID=<user_input>
WECHAT_APP_SECRET=<user_input>
```

### Step 3: Resolve Theme/Color and Validate Metadata

1. **Resolve theme** (first match wins, do NOT ask user if resolved):
   - CLI `--theme` argument
   - EXTEND.md `default_theme` (loaded in Step 0)
   - Fallback: `mist-blue`
   - If the resolved theme is `default` / `grace` / `simple` / `modern`, normalize it to `mist-blue` for the standard repo-local formatter path

2. **Resolve color** (first match wins):
   - CLI `--color` argument
   - EXTEND.md `default_color` (loaded in Step 0)
   - Treat as legacy-compat only; the standard repo-local formatter path ignores it

3. **Validate metadata** from frontmatter (markdown) or HTML meta tags (HTML input):

| Field | If Missing |
|-------|------------|
| Title | Prompt: "Enter title, or press Enter to auto-generate from content" |
| Summary | Prompt: "Enter summary, or press Enter to auto-generate (recommended for SEO)" |
| Author | Use fallback chain: CLI `--author` → frontmatter `author` → EXTEND.md `default_author` |

**Recommended practice**:
- Set `default_author` in `wechat-publisher/EXTEND.md` for the public account, instead of relying on empty author fields at publish time.
- If the article package is expected to be reused across platforms, prefer keeping platform-specific badges or labels out of the WeChat markdown source, or let `md-to-wechat.ts` strip standalone badge lines.

**Auto-Generation Logic**:
- **Title**: First H1/H2 heading, or first sentence
- **Summary**: First paragraph, truncated to 120 characters

4. **Cover Image Check** (required for API `article_type=news`):
   1. Use CLI `--cover` if provided.
   2. Else use frontmatter (`coverImage`, `featureImage`, `cover`, `image`).
   3. Else check article directory default path: `imgs/cover.png`.
   4. Else fallback to first inline content image.
   5. If still missing, auto-generate a cover image and continue:

```bash
python3 ${SKILL_DIR}/scripts/generate-cover-image.py \
  --markdown <markdown_file> \
  --out <article_dir>/imgs/cover.png \
  --bootstrap-pillow
```

   6. If the article package provides a custom SVG cover, prefer rendering that instead of generating a new generic PNG:

```bash
python3 ${SKILL_DIR}/scripts/render-svg-cover.py \
  --svg <article_dir>/imgs/cover.svg \
  --out <article_dir>/imgs/cover.png \
  --size 900x383
```

   7. `wechat-api.ts` and `wechat-article.ts` now auto-detect `cover.svg` variants and render them to PNG before upload.
   8. If auto-generation or SVG rendering fails, stop and request a manual cover image.

**Browser-mode cover note**:
- The current WeChat browser editor does not expose a stable plain file-input path for article covers.
- The reliable browser flow is `从正文选择`: the cover image should also exist in the article body.
- If you provide `--cover` for browser publishing, also make sure that same file is inserted inline in the article body. Otherwise cover upload may be unreliable on newer editor revisions.

### Step 4: Publish to WeChat

**CRITICAL**: Publishing scripts handle markdown conversion internally. Do NOT pre-convert markdown to HTML — pass the original markdown file directly. This ensures the API method renders images as `<img>` tags (for API upload) while the browser method uses placeholders (for paste-and-replace workflow).

**API method** (accepts `.md` or `.html`):

```bash
npx -y bun ${SKILL_DIR}/scripts/wechat-api.ts <file> --theme <theme> [--color <color>] [--title <title>] [--summary <summary>] [--author <author>] [--cover <cover_path>]
```

**Unified method dispatch** (preferred when another tool/skill is delegating WeChat publishing):

```bash
npx -y bun ${SKILL_DIR}/scripts/wechat-publish.ts <source> [--title <title>] [--summary <summary>] [--author <author>] [--cover <cover_path>]
```

Behavior:
- `wechat-publish.ts` chooses API or browser inside `wechat-publisher`.
- It reads `default_publish_method` from `wechat-publisher/EXTEND.md` when present.
- If no method is pinned, it prefers API when credentials exist, otherwise browser.
- If API is blocked by WeChat IP whitelist, it may fall back to browser publishing automatically.
- If the user explicitly asks for `api` or `browser`, obey that request even when EXTEND.md defaults differ.

When an article bundle already provides `article-api.html`, prefer passing that file directly to the API script.

For browser automation on generated article bundles, prefer `article-preview.md` over `article-wechat.html`.

**Draft management via API**:

```bash
npx -y bun ${SKILL_DIR}/scripts/wechat-api.ts --draft-list --count 10
npx -y bun ${SKILL_DIR}/scripts/wechat-api.ts --draft-delete <media_id>
npx -y bun ${SKILL_DIR}/scripts/wechat-api.ts --draft-delete-title "文章标题" --keep-latest 1 --dry-run
```

Recommended cleanup flow:
- First run `--draft-list` or `--draft-delete-title ... --dry-run`
- Verify which drafts would be kept vs deleted
- Then rerun without `--dry-run`

**API list rendering note**:
- WeChat's `draft/add` rendering for native `<ul>/<ol>` is inconsistent and may produce empty bullets or broken numbering in the editor preview.
- The API path should normalize article lists into paragraph-based bullet/number lines before publishing, instead of sending raw list tags when stable rendering matters.

**CRITICAL**: Always include `--theme` parameter. Never omit it, even if using `default`. Only include `--color` if explicitly set by user or EXTEND.md.

**`draft/add` payload rules**:
- Use endpoint: `POST https://api.weixin.qq.com/cgi-bin/draft/add?access_token=ACCESS_TOKEN`
- `article_type`: `news` (default) or `newspic`
- For `news`, include `thumb_media_id` (cover is required)
- Always resolve and send:
  - `need_open_comment` (default `1`)
  - `only_fans_can_comment` (default `0`)
- `author` resolution: CLI `--author` → frontmatter `author` → EXTEND.md `default_author`
- Cover fallback order for direct script use: `--cover` → frontmatter cover fields → `imgs/cover.png` → `images/cover-wide.png` → first inline image

If script parameters do not expose the two comment fields, still ensure final API request body includes resolved values.

**Browser method** (accepts `--markdown` or `--html`):

```bash
npx -y bun ${SKILL_DIR}/scripts/wechat-article.ts --markdown <markdown_file> --theme <theme> [--color <color>]
npx -y bun ${SKILL_DIR}/scripts/wechat-article.ts --html <html_file>
```

If `--profile`, `--author`, `--theme`, or `--color` are omitted, the browser script should fall back to `wechat-publisher/EXTEND.md` when those defaults are present.

**Browser cover behavior**:
- If the resolved cover image matches one of the inline article images, the browser script should open the cover chooser inside `#js_cover_area`, use `从正文选择`, select that image, and confirm the crop dialog.
- This is the preferred path for generated article bundles and current WeChat editor revisions.
- The crop step must wait for a visible `确认` or `完成` button before clicking; hidden dialog buttons are not reliable in newer editor revisions.
- If the cover image does not exist in body content, a separate local-cover upload may still be attempted, but it is less reliable than `从正文选择`.
- If WeChat API publishing is blocked by IP whitelist or unavailable, prefer the browser method with `article-preview.md`.
- For custom HTML bundles with relative local images, the browser script will now infer content images directly from `<img src>` and can reuse the first matching image as cover when `--cover` points to the same local file.

### Step 5: Completion Report

**For API method**, include draft management link:

```
WeChat Publishing Complete!

Input: [type] - [path]
Method: API
Theme: [theme name] [color if set]

Article:
• Title: [title]
• Summary: [summary]
• Images: [N] inline images
• Comments: [open/closed], [fans-only/all users]

Result:
✓ Draft saved to WeChat Official Account
• media_id: [media_id]

Next Steps:
→ Manage drafts: https://mp.weixin.qq.com (登录后进入「内容管理」→「草稿箱」)

Files created:
[• post-to-wechat/yyyy-MM-dd/slug.md (if plain text)]
[• slug.html (converted)]
```

**For Browser method**:

```
WeChat Publishing Complete!

Input: [type] - [path]
Method: Browser
Theme: [theme name] [color if set]

Article:
• Title: [title]
• Summary: [summary]
• Images: [N] inline images

Result:
✓ Draft saved to WeChat Official Account

Files created:
[• post-to-wechat/yyyy-MM-dd/slug.md (if plain text)]
[• slug.html (converted)]
```

## Detailed References

| Topic | Reference |
|-------|-----------|
| Image-text parameters, auto-compression | [references/image-text-posting.md](references/image-text-posting.md) |
| Article themes, image handling | [references/article-posting.md](references/article-posting.md) |
| Cover image generation | [references/cover-generation.md](references/cover-generation.md) |

## Feature Comparison

| Feature | Image-Text | Article (API) | Article (Browser) |
|---------|------------|---------------|-------------------|
| Plain text input | ✗ | ✓ | ✓ |
| HTML input | ✗ | ✓ | ✓ |
| Markdown input | Title/content | ✓ | ✓ |
| Multiple images | ✓ (up to 9) | ✓ (inline) | ✓ (inline) |
| Themes | ✗ | ✓ | ✓ |
| Auto-generate metadata | ✗ | ✓ | ✓ |
| Default cover fallback (`imgs/cover.svg`, `imgs/cover.png`, `images/cover-wide.png`) | ✗ | ✓ | ✓ |
| Comment control (`need_open_comment`, `only_fans_can_comment`) | ✗ | ✓ | ✗ |
| Requires Chrome | ✓ | ✗ | ✓ |
| Requires API credentials | ✗ | ✓ | ✗ |
| Speed | Medium | Fast | Slow |

**Browser article best practice**:
- Use `article-preview.md` as the browser source.
- Keep the intended cover image inside the body image set.
- Prefer the same file for `--cover` and the first inline image when deterministic cover behavior matters.

## Prerequisites

**For API method**:
- WeChat Official Account API credentials
- Guided setup in Step 2, or manually set in `.baoyu-skills/.env`

**For Browser method**:
- Google Chrome
- First run: log in to WeChat Official Account (session preserved)

**Config File Locations** (priority order):
1. Environment variables
2. `<cwd>/.baoyu-skills/.env`
3. `~/.baoyu-skills/.env`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Missing API credentials | Follow guided setup in Step 2 |
| Access token error | Check if API credentials are valid and not expired |
| Not logged in (browser) | First run opens browser - scan QR to log in |
| Chrome not found | Set `WECHAT_BROWSER_CHROME_PATH` env var |
| Title/summary missing | Use auto-generation or provide manually |
| No cover image | Add frontmatter cover or place `imgs/cover.png` / `imgs/cover.svg` in the article directory |
| Cover style mismatched topic | Run `scripts/generate-cover-image.py --markdown <file> --bootstrap-pillow` for a standard cover, or create `imgs/cover.svg` and render it with `scripts/render-svg-cover.py` |
| Cover script missing Pillow | Re-run with `--bootstrap-pillow` to auto-create venv and install Pillow |
| SVG cover looks cropped or squeezed | Re-render with `scripts/render-svg-cover.py`; do not use thumbnail-style exporters like `qlmanage -t` |
| SVG cover shows missing Chinese glyphs | Use the Chrome-based SVG renderer; avoid font-limited renderers for CJK covers |
| Wrong comment defaults | Check `EXTEND.md` keys `need_open_comment` and `only_fans_can_comment` |
| Paste fails | Check system clipboard permissions |
| API returns `invalid ip` | Switch to browser publishing or add the current egress IP to the WeChat API whitelist |
| API article shows empty bullets or broken numbering | Normalize native `<ul>/<ol>` into paragraph-based list lines before `draft/add`; do not rely on raw list tags for final WeChat rendering |
| Browser HTML input loses local images | Use the updated browser script that auto-detects local `<img src>` paths, or add `data-local-path` explicitly for non-standard bundles |
| Inline diagram looks cropped or text is cut off | Re-export SVG to PNG with the original aspect ratio preserved; verify labels stay inside the card safe area before publishing |
| Draft card shows a gray placeholder instead of a cover | Re-publish with `article-preview.md` and ensure the cover image also exists as an inline body image so the browser script can use `从正文选择` |
| Browser draft has body images but no cover | Use the same local image as both `--cover` and the first inserted body image; current stable browser flow depends on selecting cover from body content |

## Extension Support

Custom configurations via EXTEND.md. See **Preferences** section for paths and supported options.
