---
name: chrome-webstore-image-generator
description: Generate and validate Chrome Web Store listing image assets from one or more uploaded/local source images. Use when preparing extension publish graphics (icon, screenshots, small promo, optional marquee) and needing exact CWS-compliant dimensions with size-suffixed filenames.
---

# Chrome Webstore Image Generator

Generate Chrome Web Store listing images from one or more source files and validate them before submission.

## Quick Start

1. Collect absolute paths for one or more source images.
2. Generate assets with `scripts/generate_store_assets.py`.
3. Validate output with `scripts/validate_store_assets.py`.

## Generate Assets

Run from the skill directory:

```bash
python3 scripts/generate_store_assets.py \
  --inputs /abs/path/source-1.png /abs/path/source-2.jpg \
  --icon-source /abs/path/icon.png \
  --root /abs/project/release/store-assets \
  --include-marquee
```

Default behavior:

- Auto-pick icon source for `icon-128x128.png` from files with icon/logo-like names or near-square dimensions.
- Use the first input for `small-promo-440x280.png` unless `--small-promo-source` is provided.
- Use up to 5 non-icon input images for `screenshots/screenshot-<index>-<width>x<height>.png` (falls back to all inputs when needed).
- Produce screenshots at `1280x800` by default.
- Generate `marquee-1400x560.png` only when `--include-marquee` is set.
- If multiple inputs are all screenshot-like (not near-square), pass `--icon-source` explicitly.

Useful options:

- `--screenshot-size 640x400`: switch screenshot size to `640x400`.
- `--max-screenshots 3`: limit generated screenshots.
- `--icon-source`: explicitly set icon input (recommended).
- `--small-promo-source`, `--marquee-source`: override other output source images.

## Validate Assets

```bash
python3 scripts/validate_store_assets.py --root /abs/project/release/store-assets
```

Validation checks:

- `icon-128x128`: exactly `128x128` and format `PNG`
- `small-promo-440x280`: exactly `440x280`
- `marquee-1400x560`: exactly `1400x560` (optional)
- Screenshots: count `1-5`, each `1280x800` or `640x400`

## Source Specs

Read size and naming requirements in:

- `references/cws-image-specs.md`

## Notes

- This skill currently uses macOS `sips` for resizing/cropping.
- If user uploads images in chat, first resolve them to accessible local file paths, then pass those paths to the script.
