# Reproducibility Boundary

`wechat-publisher` is **repo-local reusable**, but not “clone and publish with zero setup”.

Use this matrix:

## Level 1: Repo-Local Reproducible

These steps should behave the same on another machine after cloning the repository:

```bash
cd wechat-publisher
bun install
bun scripts/bootstrap-local.ts --project-root ..
bun scripts/check-permissions.ts --project-root ..
```

What this gives you:

- local runtime dependencies installed
- repo-local `wechat-article-formatter/.venv` with Python requirements
- repo-local `.baoyu-skills/wechat-publisher/EXTEND.md`
- repo-local `.baoyu-skills/.env.example`
- environment report for Chrome, Bun, profile isolation, API creds, and cover renderer

At this level, you should be able to reproduce:

- markdown → WeChat HTML conversion through the repo-local preferred formatter
- repo-local config loading
- inline image resolution
- cover generation checks
- dry-run command resolution

This level assumes the **correct process** is:

1. `bun install`
2. `bun scripts/bootstrap-local.ts --project-root ..`
3. `bun scripts/check-permissions.ts --project-root ..`
4. `bun scripts/wechat-publish.ts article.md --dry-run`

Do not treat these as reproducible paths:

- direct `md-to-wechat.ts` usage
- old theme names as active project defaults
- skipping the formatter runtime bootstrap

When another Codex instance is operating from this repo, it should treat the sequence above as an execution requirement, not as optional human guidance.

## Level 2: Machine-Local API Publishing

API publishing is **not fully repo-reproducible** because it depends on machine/network state.

Required on the target machine:

- real `WECHAT_APP_ID` and `WECHAT_APP_SECRET`
- `.baoyu-skills/.env` or shell env vars
- current outbound IP in WeChat API whitelist

Without these, API publishing will fail even if the repo is cloned correctly.

## Level 3: Machine-Local Browser Publishing

Browser publishing is also **not fully repo-reproducible** because it depends on desktop state.

Required on the target machine:

- Chrome or Edge
- working isolated profile directory
- valid WeChat Official Account login session
- desktop automation permissions
  - macOS: Accessibility / System Events
  - Linux: `xdotool` or `ydotool`

Without these, browser automation may fail or behave differently across machines.

## Cover Rendering Boundary

For custom SVG covers:

- preferred path: local `@resvg/resvg-js` renderer after `bun install`
- fallback path: Chrome renderer

If the machine falls back to Chrome, always verify the output image locally before publishing.

## Practical Rule

Treat `wechat-publisher` as:

- **reproducible for composition, conversion, and local preflight**
- **conditionally reproducible for actual publish**, depending on credentials, whitelist, and desktop/browser state
