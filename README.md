# agent-skills

A skill library for Chrome extension development and Chrome Web Store release workflows.

## Skills in this repository

- `chrome-extension-dev`: Manifest V3 development guidance, templates, and API references.
- `chrome-extension-publish`: Release checklist, CWS form templates, and asset validation scripts.
- `chrome-webstore-image-generator`: Generate and validate CWS listing images from source images.

## Repository layout

```text
agent-skills/
├── chrome-extension-dev/
│   ├── SKILL.md
│   ├── assets/templates/
│   └── references/
├── chrome-extension-publish/
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
  chrome-extension-publish/scripts/audit_permissions.py \
  chrome-extension-publish/scripts/package_extension.py \
  chrome-extension-publish/scripts/generate_store_assets.py \
  chrome-extension-publish/scripts/validate_store_assets.py \
  chrome-webstore-image-generator/scripts/capture_extension_screenshots.py \
  chrome-webstore-image-generator/scripts/generate_store_assets.py \
  chrome-webstore-image-generator/scripts/validate_store_assets.py
```
