# agent-skills

Reusable skill library for three main workflows:

- Chrome extension development and Chrome Web Store release
- Content analysis → technical article review → WeChat-ready HTML → platform publishing
- Lark / Feishu document-to-slides workflow with outline review before publish

## Content Workflow Skills

These repo-local skills now form a reusable article pipeline:

- `github-trending-writer`: GitHub Trending 候选抓取、落盘、写稿入口
- `ai-hotspot-collector`: 多来源 AI 热点聚合与总稿入口
- `url-reader`: 读取网页 / README / 内容页并保存本地 Markdown
- `technical-article-review`: 技术稿审阅与直接修稿
- `technical-article-preflight`: 发文前预检
- `wechat-article-formatter`: Markdown → 微信公众号 HTML
- `wechat-publisher`: 微信公众号发布
- `article-multi-publisher`: 多平台分发封装

Related platform skills that are already present in this repository and are reused by the article pipeline:

- `post-to-xhs`
- `toutiao-publisher`
- `tencent-dev-community-publisher`

## Recommended Article Pipeline

For technical articles, use this order:

```text
source discovery / candidate fetch
→ markdown draft
→ technical-article-review
→ technical-article-preflight
→ wechat-article-formatter
→ wechat-publisher
```

Rules that now apply across the repo:

- First draft is not publish-ready by default.
- Review comes before HTML generation and publishing.
- Markdown is the source of truth for article revisions.
- Review findings are applied directly unless the user explicitly requests `review-only` or `只审不改`.

## Lark Workflow Skills

These repo-local skills cover document-to-slides orchestration on top of existing Lark capabilities:

- `lark-workflow-doc-to-slides`: 用 `doc_url` / `doc_token` / `doc_name` 解析来源文档，先生成可审阅 outline，再新建 Slides 或追加到已有 `target_slides_url`

## What Is Vendored vs Environment-Specific

Vendored into this repo:

- formatter
- URL reader
- multi-publisher wrapper
- WeChat publisher
- technical review / preflight chain

Still environment-specific:

- WeChat API credentials and IP whitelist
- Chrome / browser login state for browser automation
- Playwright / Chromium runtime
- Bun runtime for TypeScript-based publisher scripts
- Platform-specific browser profiles or API tokens

So this repository is now **repo-local reusable**, but not “zero-setup publish anywhere”:
you still need platform credentials and browser/runtime prerequisites on the target machine.

## Quick Start For The Article Chain

### 1. Prepare Python/Bun runtimes

```bash
python3 --version
bun --version
```

### 2. Install formatter dependencies

```bash
cd wechat-article-formatter
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

### 3. Generate WeChat HTML

```bash
wechat-article-formatter/.venv/bin/python \
  wechat-article-formatter/scripts/markdown_to_html.py \
  --input /abs/path/article.md \
  --theme mist-blue \
  --output /abs/path/article.html \
  --preview
```

### 4. Publish to WeChat

```bash
cd wechat-publisher
bun install
bun scripts/bootstrap-local.ts --project-root ..
bun scripts/check-permissions.ts --project-root ..
npx -y bun scripts/wechat-publish.ts /abs/path/article.md --dry-run
```

`bootstrap-local.ts` now prepares the repo-local `wechat-article-formatter/.venv`, so Markdown publish on another machine follows the same `mist-blue` formatter path by default.

Important boundary:

- repo-local conversion and preflight are reproducible after the bootstrap above
- actual API publish still depends on WeChat credentials + IP whitelist
- actual browser publish still depends on Chrome login + desktop automation permissions

## Chrome Extension Skills

The repository still includes the original Chrome extension workflow skills:

- `chrome-extension-dev`
- `chrome-extension-e2e-automation`
- `chrome-extension-publish`
- `chrome-extension-social-promo`
- `chrome-webstore-image-generator`

## Legacy Notice

`wechat-article-generator` is kept only for maintaining older tar.gz-style article packages.
For new work, prefer:

```text
technical-article-review
→ technical-article-preflight
→ wechat-article-formatter
→ wechat-publisher
```

## Repository Layout

```text
agent-skills/
├── lark-workflow-doc-to-slides/
├── github-trending-writer/
├── ai-hotspot-collector/
├── technical-article-review/
├── technical-article-preflight/
├── url-reader/
├── wechat-article-formatter/
├── wechat-publisher/
├── article-multi-publisher/
├── post-to-xhs/
├── toutiao-publisher/
├── tencent-dev-community-publisher/
├── chrome-extension-dev/
├── chrome-extension-e2e-automation/
├── chrome-extension-publish/
├── chrome-extension-social-promo/
├── chrome-webstore-image-generator/
└── code-review/
```
