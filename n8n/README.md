# AI Hotspot n8n Workflows

This directory contains importable n8n workflows and Docker deployment files for the current article pipeline.

## Files

- `workflows/ai-hotspot-collector-portable.json`
  - Self-contained collector-only workflow.
  - Uses only n8n + Node runtime + network access.
  - Does not depend on repo scripts or pre-created workspace directories.
- `workflows/ai-hotspot-collector-only.json`
  - Docker-targeted collector-only workflow for:
    1. collect hotspots with `ai-hotspot-collector`
    2. generate the article package and platform-specific markdown files
    3. stop for manual review
  - This version now bootstraps the minimal Python dependency (`requests`) and creates output directories before running the collector.
- `workflows/ai-hotspot-review-first.json`
  - Docker-targeted review-first workflow for:
    1. collect hotspots with `ai-hotspot-collector`
    2. build platform-specific article bundle files
    3. optionally publish to WeChat, Xiaohongshu, Toutiao, and Tencent Developer Community
- `docker-compose.yml`
  - Start n8n with the runtime needed by the hotspot workflow.
- `docker/Dockerfile`
  - Custom n8n image with Python, Bun, Chromium, and publisher dependencies.
- `.env.example`
  - Environment variable template for LLM and publisher credentials.

## What the workflow does

The workflow delegates to:

- `/workspace/agent-skills/scripts/n8n_hotspot_bridge.py prepare`
- `/workspace/agent-skills/scripts/n8n_hotspot_bridge.py publish`

Those commands wrap the local skills and scripts already verified in this repo.

## Docker deploy

1. Copy env template:

   ```bash
   cp /Users/aias/Work/github/agent-skills/n8n/.env.example /Users/aias/Work/github/agent-skills/n8n/.env
   ```

2. Fill the required keys in `.env`.

3. Start n8n:

   ```bash
   cd /Users/aias/Work/github/agent-skills/n8n
   docker compose up --build
   ```

4. Open n8n and import one of:
   - `workflows/ai-hotspot-collector-portable.json`
   - `workflows/ai-hotspot-collector-only.json`
   - `workflows/ai-hotspot-review-first.json`

## Import

1. Open n8n.
2. Import the workflow you want.
3. Open the `Workflow Config` node and adjust defaults.

## Which workflow to use

- `ai-hotspot-collector-only.json`
  - Use this when you only want:
    - fetch hotspots
    - generate markdown/article bundle files
    - review manually later
  - Best when you can mount the repo into another n8n environment and allow the workflow to install a minimal Python dependency on first run.
- `ai-hotspot-collector-portable.json`
  - Use this when you want a cleaner version for other n8n environments.
  - It initializes output directories itself.
  - It does not rely on:
    - `python3`
    - `/workspace/agent-skills`
    - local repo scripts
- `ai-hotspot-review-first.json`
  - Use this when you want the same prepare step, plus optional publish after review.

## Recommended run mode

For `ai-hotspot-collector-portable.json`:

1. Import the workflow.
2. Adjust `outputRoot` in `Workflow Config` if needed.
3. Run the workflow.
4. Review the generated package under `outputRoot/<date>/<model>/`.

For `ai-hotspot-collector-only.json`:

1. Run the workflow.
2. Review the generated package under:
   - `/workspace/agent-skills/content/ai-hotspot-digests/...`

For `ai-hotspot-review-first.json`, use this in two passes:

1. First run with:
   - `autoPublish = false`
   - `existingPackageDir = ""`

   This collects sources, builds the article package, and stops for review.

2. Review the generated package under:
   - `/workspace/agent-skills/content/ai-hotspot-digests/...`

3. Run again with:
   - `autoPublish = true`
   - `existingPackageDir = <the reviewed package dir>`

   This skips collection and publishes the reviewed package.

## Important notes

- `dryRun = true` is safe for workflow validation.
- Tencent browser publishing is intentionally skipped during `dryRun` to avoid blocking n8n execution.
- Xiaohongshu and Toutiao are also skipped during `dryRun`, so the workflow can be validated before full browser/API credentials are ready.
- WeChat, Xiaohongshu, Toutiao, and Tencent still depend on the local logged-in/browser/API state already configured on this machine.
- In Docker, browser-backed login state should live under:
  - `/workspace/runtime/wechat-browser-profile`
  - `/workspace/runtime/xhs-profiles`
  - repo-local `toutiao-publisher/data/`
  - repo-local `tencent-dev-community-publisher/data/`
- Default rewrite model in the workflow is `gemini-3-pro-preview`, matching the current preferred output.

## Main config fields

- `sources`
  - Example: `hn,engadget,fast-company`
- `workspaceRoot`
  - Default: `/workspace/agent-skills`
- `limitPerSource`
- `rewriteProvider`
  - `gemini`, `openai`, or `auto`
- `rewriteMode`
  - `auto`, `off`, or `api`
- `rewriteModel`
- `autoPublish`
- `existingPackageDir`
- `platforms`
  - Default: `wechat,xhs,toutiao`
- `withTencent`
- `dryRun`
- `wechatAuthor`
- `wechatSummary`
- `wechatProfile`
  - Default: `/workspace/runtime/wechat-browser-profile`
- `xhsMode`
- `xhsTemplate`
- `xhsAccount`

## Output bundle files

The prepare step refreshes these files inside the package directory:

- `article.md`
- `article-preview.md`
- `article-xhs.md`
- `article-toutiao.md`
- `article-tencent.md`
- `bundle-metadata.json`

## Suggested extension

If you want scheduled publishing, duplicate the workflow and replace `Manual Trigger` with an n8n schedule trigger after validating the manual flow.
