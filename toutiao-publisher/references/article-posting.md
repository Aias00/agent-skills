# Article Posting Reference

## Supported input

- `--content <file>`: Markdown/text file path
- `--content <file.html>`: Use local HTML directly without Markdown conversion
- `--content "<text>"`: Inline text
- `--title "<title>"`: Required for reliable automated publish
- `--cover <path>`: Local cover image path
- If `--cover` is omitted, the script will auto-pick a nearby image from the article directory when possible
- For article packages, prefer `article-toutiao.md` as the publish source if it exists

## Local image handling

- `api_publisher.py` supports markdown image syntax such as `![封面图](images/cover.jpg)` and local HTML `<img src="images/...">`
- Before submit, local images are uploaded through Toutiao's authenticated material endpoint
- The final article payload uses Toutiao CDN image URLs, not local file paths
- This is the recommended way to publish image-rich markdown packages; do not rely on raw local markdown being rendered by the Toutiao editor itself

## Recommended commands

### Direct API publish (preferred)

```bash
python scripts/run.py api_publisher.py --title "标题" --content article.md
```

### Direct API publish with cover

```bash
python scripts/run.py api_publisher.py \
  --title "标题" \
  --content article.md \
  --cover ./assets/cover.png
```

### Direct API dry-run

```bash
python scripts/run.py api_publisher.py \
  --title "标题" \
  --content article.md \
  --dry-run
```

### Interactive publish (safer first run)

```bash
python scripts/run.py publisher.py --title "标题" --content article.md
```

### Automated publish

```bash
python scripts/run.py publisher.py \
  --title "标题" \
  --content article.md \
  --cover ./assets/cover.png \
  --headless
```

### Troubleshooting run with screenshots

```bash
python scripts/run.py publisher.py \
  --title "标题" \
  --content article.md \
  --debug-screenshots \
  --wait-seconds 30
```

Debug screenshots are written to: `data/debug_screenshots/`.

## Guidance

- Prefer `api_publisher.py` for normal article publishing.
- Keep `publisher.py` as a fallback when you need to inspect the page visually.
- If no `--cover` is provided, both publishers attempt nearby cover discovery from the article directory.
- If the article has local images under `images/`, publish with `api_publisher.py` so both cover and body images are uploaded together.
