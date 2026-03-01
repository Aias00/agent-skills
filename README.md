# agent-skills

A skill library for Chrome extension development and Chrome Web Store release workflows.

## Skills in this repository

- `chrome-extension-dev`: Manifest V3 development guidance, templates, and API references.
- `chrome-extension-e2e-automation`: One-command integrated pipeline across dev checks and publish artifacts.
- `chrome-extension-publish`: Release checklist, CWS form templates, and asset validation scripts.
- `chrome-webstore-image-generator`: Generate and validate CWS listing images from source images.
- `chrome-extension-social-promo`: Generate bilingual social media promotion copy for extension launches/updates.

## End-to-end automation

From the `chrome-extension-publish` skill directory, run:

```bash
python3 scripts/run_full_release_pipeline.py \
  --root /abs/path/to/extension \
  --icon-source /abs/path/to/icon.png \
  --include-marquee
```

If `--inputs` is omitted, screenshots are auto-captured first by default.

This generates:
- `release/chrome-webstore.zip`
- `release/permission-audit.md`
- `release/popup-ui-audit.md`
- `release/store-assets/*`
- `release/store-assets/screenshots/popup-preview-620x760.png`
- `release/cws-listing.zh-en.md`
- `release/full-release-summary.md`

## Repository layout

```text
agent-skills/
├── chrome-extension-dev/
│   ├── SKILL.md
│   ├── assets/templates/
│   └── references/
├── chrome-extension-e2e-automation/
│   ├── SKILL.md
│   ├── scripts/
│   └── references/
├── chrome-extension-publish/
│   ├── SKILL.md
│   ├── scripts/
│   └── references/
├── chrome-extension-social-promo/
│   ├── SKILL.md
│   ├── scripts/
│   └── references/
└── chrome-webstore-image-generator/
    ├── SKILL.md
    ├── scripts/
    └── references/
```

## Quick maintenance checks

From the repository root:

```bash
python3 -m py_compile \
  chrome-extension-dev/assets/templates/resize_icons.py \
  chrome-extension-e2e-automation/scripts/run_e2e_extension_pipeline.py \
  chrome-extension-publish/scripts/audit_permissions.py \
  chrome-extension-publish/scripts/prepare_publish_basics.py \
  chrome-extension-publish/scripts/generate_publish_docs.py \
  chrome-extension-publish/scripts/run_full_release_pipeline.py \
  chrome-extension-publish/scripts/submit_cws_playwright.py \
  chrome-extension-publish/scripts/package_extension.py \
  chrome-extension-publish/scripts/generate_store_assets.py \
  chrome-extension-publish/scripts/validate_store_assets.py \
  chrome-extension-social-promo/scripts/generate_social_promo.py \
  chrome-webstore-image-generator/scripts/capture_extension_screenshots.py \
  chrome-webstore-image-generator/scripts/generate_store_assets.py \
  chrome-webstore-image-generator/scripts/validate_store_assets.py
```
