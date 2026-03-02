# Cover Generation

Generate a topic-aligned cover image before publishing to WeChat.

## Script

```bash
python3 ./scripts/generate-cover-image.py --markdown ./article.md --out ./imgs/cover.png --bootstrap-pillow
```

## Inputs

- `--markdown`: markdown article path (recommended)
- `--title`: explicit title override
- `--summary`: subtitle override
- `--badge`: bottom badge text (default: `Observe • Plan • Act • Reflect`)
- `--size`: image size (default `900x383`, WeChat-friendly wide ratio)
- `--out`: output cover path (default `<markdown_dir>/imgs/cover.png`)
- `--bootstrap-pillow`: auto-create local venv and install Pillow when missing

## Output

- PNG cover image, default path: `imgs/cover.png`
- Designed for WeChat draft API `news` cover requirement

## Quality Checklist

- Cover title matches article title/theme
- Subtitle reflects first paragraph or article summary
- Ratio and safe area are consistent (avoid list-card clipping/letterbox)
- Contrast is readable on mobile
- Avoid unrelated screenshots as cover images

## Typical Flow

```bash
# 1) Generate cover
python3 ./scripts/generate-cover-image.py --markdown ./article.md --bootstrap-pillow

# 2) Publish with API
npx -y bun ./scripts/wechat-api.ts ./article.md --theme default
```

## Troubleshooting

- `Pillow is required`:
  - rerun with `--bootstrap-pillow`
- Font rendering looks wrong:
  - pass shorter title/subtitle or use `--title`/`--summary` overrides
- Cover still not aligned with topic:
  - set a clearer title/subtitle before regenerating
