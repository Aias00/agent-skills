---
name: chrome-extension-e2e-automation
description: "End-to-end Chrome extension automation skill. Use when a user wants one-command workflow from dev validation to Chrome Web Store release artifacts: manifest/JS checks, privacy-policy/.gitignore baseline, permission audit, deterministic ZIP packaging, store assets generation+validation, and bilingual (ZH/EN) CWS draft output."
---

# Chrome Extension E2E Automation

## Overview

Use this skill when the user asks for one-command automation across development checks and publish readiness.
This skill orchestrates existing Chrome extension skills into a single deterministic pipeline.

## When To Use

Trigger this skill when user intent matches:
- "全链路自动化"
- "一键发布准备"
- "开发完直接出发布包"
- "端到端生成发布物料"
- "one command pipeline for chrome extension release"

Typical targets:
- Any MV3 extension directory with `manifest.json`
- First release or update release preparation
- Teams that need repeatable outputs in `release/`

## Core Command

Run from anywhere:

```bash
python3 scripts/run_e2e_extension_pipeline.py \
  --root /abs/path/to/extension \
  --icon-source /abs/path/to/icon.png \
  --include-marquee
```

This command performs:
1. Extension icon bootstrap (`icons/icon16|48|128` + manifest mapping)
2. Dev checks (manifest JSON + JS syntax)
3. Popup UI audit (width guardrail, media reset check, icon quality)
4. Publish baseline prep (`privacy-policy.md`, `.gitignore`)
5. Permission audit
6. Deterministic ZIP packaging
7. Store assets generation + validation
8. Bilingual CWS listing draft generation
9. Pipeline summary output
10. Optional popup preview capture (`--capture-popup-preview`)

## Auto Behavior

- If `--icon-source` is not provided, it auto-tries manifest icons (`icons`, `action.default_icon`).
- If extension icons are missing, it auto-generates `icons/icon16.png`, `icons/icon48.png`, `icons/icon128.png`, and patches `manifest.json`.
- If assets are enabled and no `--inputs` are provided, it auto-runs screenshot capture with Playwright first (preferred path).
- This auto-capture priority applies even if old screenshots already exist under `release/store-assets/screenshots`.
- It runs popup UI quality audit by default and fails fast when popup width is too small or icon remains fallback style.
- Popup preview capture is optional and only runs when `--capture-popup-preview` is set.
- If Playwright is missing and no image input is provided, it fails with install instructions.

## Pass-Through Flags

Any unknown flags are forwarded to:

`chrome-extension-publish/scripts/run_full_release_pipeline.py`

Useful forwarded flags:
- `--inputs ...`
- `--capture-screenshots`
- `--skip-assets`
- `--skip-docs`
- `--mode source`
- `--zip-out ...`
- `--listing-out ...`

Wrapper-only flags:
- `--skip-icon-bootstrap`
- `--skip-dev-checks`
- `--skip-manifest-check`
- `--skip-js-check`
- `--no-auto-capture-if-no-inputs`
- `--skip-ui-audit`
- `--popup-audit-out ...`
- `--min-popup-width ...`
- `--capture-popup-preview`
- `--skip-popup-preview` (deprecated compatibility flag)
- `--popup-preview-out ...`
- `--popup-preview-size ...`
- `--popup-preview-headless`

Do not pass `--root`/`--manifest` as forwarded flags; use wrapper flags instead.

## Output Contract

Expected artifacts under extension root:
- `release/chrome-webstore.zip`
- `release/permission-audit.md`
- `release/popup-ui-audit.md`
- `release/store-assets/*`
- `release/cws-listing.zh-en.md`
- `release/full-release-summary.md`
- root `privacy-policy.md`

Optional artifact (only when `--capture-popup-preview` is used):
- `release/store-assets/screenshots/popup-preview-620x760.png`

## Guardrails

- Privacy policy canonical path is fixed: `privacy-policy.md` (root).
- Default packaging mode is `manifest` with transitive local dependency inclusion.
- Store icon must not silently degrade to screenshot-derived icon; explicit icon source is preferred.
- Listing content must contain both Chinese and English blocks.

## Scripts

- `scripts/run_e2e_extension_pipeline.py`: unified entrypoint.
- `scripts/audit_popup_ui.py`: popup width/icon/style guardrail checks.
- `scripts/capture_popup_preview.py`: optional real popup preview capture.

## References

- If pipeline fails, read [references/troubleshooting.md](references/troubleshooting.md).
