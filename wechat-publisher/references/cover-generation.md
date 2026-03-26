# Cover Generation

Generate a WeChat-safe cover image before publishing.

There are now two supported cover paths:

1. **Standard auto cover**
   - Start from markdown/title/summary
   - Output a topic-aligned PNG directly
   - Best when you just need a clean cover quickly

2. **Custom SVG cover**
   - Start from a hand-tuned SVG layout
   - Render the SVG to PNG with repo-local `resvg` when available
   - Fallback to Chrome only when `resvg` is unavailable
   - Best when the article needs a custom editorial cover or multiple visual blocks

## Path A: Standard Auto Cover

```bash
python3 ./scripts/generate-cover-image.py \
  --markdown ./article.md \
  --out ./imgs/cover.png \
  --bootstrap-pillow
```

### Inputs

- `--markdown`: markdown article path (recommended)
- `--title`: explicit title override
- `--summary`: subtitle override
- `--badge`: bottom badge text
- `--size`: image size, default `900x383`
- `--out`: output cover path, default `<markdown_dir>/imgs/cover.png`
- `--bootstrap-pillow`: auto-create local venv and install Pillow when missing

### When To Use

- The article does not need a custom composition
- You only need a stable, topic-aligned cover
- You want the simplest publish-ready flow

## Path B: Custom SVG Cover

Create a local `cover.svg` or `imgs/cover.svg`, then render it with the Chrome-based renderer:

```bash
python3 ./scripts/render-svg-cover.py \
  --svg ./imgs/cover.svg \
  --out ./imgs/cover.png \
  --size 900x383
```

### Why The Preferred Path Uses `resvg`

- More deterministic across machines after `bun install`
- Avoids thumbnail exporters that silently crop SVGs into squares
- Avoids browser screenshot quirks when the viewport and SVG canvas disagree

### Chrome Fallback

Chrome fallback still exists for machines without local `resvg`, but it should be treated as a compatibility path, not the primary reproducible path.
If Chrome fallback is used:

- verify the generated PNG locally before publishing
- do not assume identical output across machines

### Auto-Resolution In Publish Scripts

The publish scripts now understand these cover paths:

- explicit `--cover <path>`
- frontmatter: `coverImage`, `featureImage`, `cover`, `image`
- default files:
  - `imgs/cover.svg`
  - `imgs/cover.png`
  - `images/cover-wide.svg`
  - `images/cover-wide.png`
  - `images/cover.svg`
  - `images/cover.png`
  - `cover.svg`
  - `cover.png`

If the chosen cover is an SVG, `wechat-api.ts` and `wechat-article.ts` will now render it to a PNG automatically before upload.
On a fresh clone, run `bun install` in `wechat-publisher/` first so the local `resvg` renderer is available.

## Cover Layout Rules

- Keep the final cover at `900x383`
- Reserve a safe text box for the main title; do not let badges or side cards overlap it
- Treat Chinese technical titles as two-line content by default
- Keep subtitle to one or two short lines
- If the cover has a secondary info block, move it into a separate card instead of floating it over the title area
- Keep chip rows short; do not overfill the top line with too many labels
- Avoid unrelated screenshots as the cover

## Typical Flows

### Fast default flow

```bash
# 1) Generate a standard cover
python3 ./scripts/generate-cover-image.py --markdown ./article.md --bootstrap-pillow

# 2) Publish
npx -y bun ./scripts/wechat-api.ts ./article.md --theme mist-blue
```

### Custom editorial flow

```bash
# 1) Design or edit cover.svg

# 2) Render SVG to WeChat-safe PNG
python3 ./scripts/render-svg-cover.py --svg ./imgs/cover.svg --out ./imgs/cover.png --size 900x383

# 3) Publish with the same bundle
npx -y bun ./scripts/wechat-api.ts ./article.html --cover ./imgs/cover.svg
```

## Troubleshooting

- `Pillow is required`
  - rerun the default cover generator with `--bootstrap-pillow`
- Cover looks cropped or square
  - do not use thumbnail-style exporters such as `qlmanage -t`; use `render-svg-cover.py`
- Chinese text becomes boxes/tofu
  - first prefer the repo-local `resvg` path after `bun install`
  - if you must fall back to Chrome, verify fonts locally before publishing
- Font rendering or spacing still looks wrong
  - shorten title/subtitle or break the subtitle into two shorter lines
- Cover still feels too crowded
  - reduce chip count, shrink the right-side info block, and widen the title safe area
- Cover output differs across machines
  - run `bun install` in `wechat-publisher/`
  - confirm `@resvg/resvg-js` is installed
  - rerender and compare before publishing
