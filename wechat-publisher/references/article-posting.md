# Article Posting (文章发表)

Post markdown articles to WeChat Official Account with full formatting support.

## Usage

On a fresh clone, prepare the local runtime and project config first:

```bash
cd wechat-publisher
bun install
bun scripts/bootstrap-local.ts --project-root ..
bun scripts/check-permissions.ts --project-root ..
```

This makes the repo-local conversion/publish flow reproducible before you try API or browser posting.
`bootstrap-local.ts` now also prepares the repo-local `wechat-article-formatter/.venv`, so Markdown publishing will follow the same formatter path on another machine.

## Correct Process

Use this order by default:

```bash
cd wechat-publisher
bun install
bun scripts/bootstrap-local.ts --project-root ..
bun scripts/check-permissions.ts --project-root ..
bun scripts/wechat-publish.ts article.md --dry-run
```

Then:

- use `scripts/wechat-publish.ts article.md` as the standard entry
- let it route to API or browser
- expect Markdown to be rendered through the repo-local preferred formatter with `mist-blue`

## Direct But Still Supported Paths

Use these only when you intentionally need direct control:

- `scripts/wechat-api.ts article.md --dry-run`
- `scripts/wechat-article.ts --markdown article.md --submit`

These are supported, but they are not the primary documented path for fresh clones.

## Incorrect / Legacy Process

Do **not** treat these as the standard workflow:

- `scripts/md-to-wechat.ts article.md`
  - legacy internal renderer only
- using `default/grace/simple/modern` as if they were still the active project themes
  - standard publish now normalizes them to `mist-blue`
- skipping `bootstrap-local.ts` and going straight to markdown publish
  - this usually reproduces the old “formatter not installed / rendering path diverged” problem
- reading a successful doctor check as proof that API/browser publish will work
  - actual publish still depends on credentials, whitelist IP, Chrome login, and desktop permissions

Then use one of these:

```bash
# Standard entry: publish markdown through the preferred formatter path
npx -y bun ./scripts/wechat-publish.ts article.md --dry-run

# Direct API publish from markdown
npx -y bun ./scripts/wechat-api.ts article.md --theme mist-blue --dry-run

# Direct browser publish from markdown
npx -y bun ./scripts/wechat-article.ts --markdown article.md --theme mist-blue --submit
```

## Recommended source files

- Browser automation on article bundles: prefer `article-preview.md`
- Manual copy/paste into the WeChat editor: prefer `article-wechat.html`
- API publishing on article bundles: prefer `article-api.html`

If you only have one markdown source, keep the intended cover image inside the body image set and place it near the top.

## Capability Boundary

What is reproducible after clone + bootstrap:

- markdown → WeChat HTML
- cover path resolution
- dry-run command resolution
- repo-local config loading

What still depends on machine/account state:

- API publish: credentials + whitelist IP
- browser publish: Chrome login + desktop automation permissions

## Cover Generation (Recommended)

When cover image is missing or mismatched with article topic, choose one of these two flows:

### 1. Standard auto cover

```bash
python3 ./scripts/generate-cover-image.py \
  --markdown ./article.md \
  --out ./imgs/cover.png \
  --bootstrap-pillow
```

### 2. Custom SVG cover

```bash
python3 ./scripts/render-svg-cover.py \
  --svg ./imgs/cover.svg \
  --out ./imgs/cover.png \
  --size 900x383
```

Then publish by API/browser flow. API and browser scripts can now auto-pick:

- frontmatter `coverImage` / `featureImage` / `cover` / `image`
- `imgs/cover.svg`
- `imgs/cover.png`
- `images/cover-wide.png`
- `images/cover.png`

If the resolved cover is an SVG, the publish scripts render it to PNG automatically before upload.

## Browser cover behavior

- The stable browser path is not generic local upload; it is `从正文选择`
- Use the same file for `--cover` and one of the inline body images whenever deterministic cover behavior matters
- In generated article bundles, the most reliable setup is:
  1. publish `article-preview.md`
  2. insert the cover image as the first real inline body image
  3. let the script open the cover chooser and confirm the crop dialog
  4. if you use a custom SVG cover, render it to `imgs/cover.png` first so browser and API paths stay aligned

## Parameters

| Parameter | Description |
|-----------|-------------|
| `--markdown <path>` | Markdown file to convert and post |
| `--theme <name>` | Theme: `mist-blue` (recommended) or `ai-tech`; legacy names auto-normalize to `mist-blue` |
| `--title <text>` | Override title (auto-extracted from markdown) |
| `--author <name>` | Author name |
| `--summary <text>` | Article summary |
| `--html <path>` | Pre-rendered HTML file (alternative to markdown) |
| `--profile <dir>` | Chrome profile directory |

## Markdown Format

```markdown
---
title: Article Title
author: Author Name
---

# Title (becomes article title)

Regular paragraph with **bold** and *italic*.

## Section Header

![Image description](./image.png)

- List item 1
- List item 2

> Blockquote text

[Link text](https://example.com)
```

## Image Handling

1. **Parse**: Images in markdown are replaced with `WECHATIMGPH_N`
2. **Render**: HTML is generated with placeholders in text
3. **Paste**: HTML content is pasted into WeChat editor
4. **Replace**: For each placeholder:
   - Find and select the placeholder text
   - Scroll into view
   - Press Backspace to delete the placeholder
   - Paste the image from clipboard
5. **Cover**: If the resolved cover file matches one of the inline images:
   - Open `#js_cover_area`
   - Use `从正文选择`
   - Select that inline image
   - Wait for a visible crop confirmation button
   - Confirm crop and save draft

## Scripts

| Script | Purpose |
|--------|---------|
| `wechat-publish.ts` | Standard unified entry; routes markdown through repo-local formatter first |
| `wechat-article.ts` | Direct browser entry |
| `wechat-api.ts` | Direct API entry |
| `md-to-wechat.ts` | Legacy internal markdown renderer |
| `md/render.ts` | Legacy internal theme renderer |

## Example Session

```
User: /post-to-wechat --markdown ./article.md

Claude:
1. Parses markdown, finds 5 images
2. Generates HTML with placeholders
3. Opens Chrome, navigates to WeChat editor
4. Pastes HTML content
5. For each image:
   - Selects WECHATIMGPH_1
   - Scrolls into view
   - Presses Backspace to delete
   - Pastes image
6. Reports: "Article composed with 5 images."
```
