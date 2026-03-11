# Article Posting Reference

## Supported input

- `--content <file>`: Markdown/text file path
- `--content "<text>"`: Inline text
- `--title "<title>"`: Recommended for automation stability
- `--cover <path>`: Local cover image path

## Markdown image behavior

- Local Markdown images such as `![配图](images/01.jpg)` are uploaded into the Tencent editor and inserted into the body in order.
- `--cover` is uploaded separately as the article cover.
- If the Markdown file also contains the same cover image path, the body upload step skips that duplicate image.
- Remote image links in Markdown are still converted as normal HTML images.

## Recommended commands

### Safe first run

```bash
python scripts/run.py publisher.py --title "测试标题" --content article.md --dry-run
```

### Standard publish

```bash
python scripts/run.py publisher.py --title "正式标题" --content article.md
```

### Headless publish

```bash
python scripts/run.py publisher.py --title "正式标题" --content article.md --headless
```

### Troubleshooting mode with screenshots

```bash
python scripts/run.py publisher.py --title "正式标题" --content article.md --debug-screenshots --wait-seconds 30
```

Debug screenshots output: `data/debug_screenshots/`.
