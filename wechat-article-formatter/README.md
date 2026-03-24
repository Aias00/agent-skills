# WeChat Article Formatter

将 Markdown 文章转换为适配微信公众号发布的 HTML。

## Supported Themes

- `ai-tech`
- `mist-blue`

## Quick Start

```bash
cd wechat-article-formatter
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

.venv/bin/python scripts/markdown_to_html.py \
  --input /abs/path/article.md \
  --theme mist-blue \
  --preview
```

## Typical Usage

From the repository root:

```bash
wechat-article-formatter/.venv/bin/python \
  wechat-article-formatter/scripts/markdown_to_html.py \
  --input generated/article.md \
  --theme mist-blue \
  --output generated/article.html \
  --preview
```

## Notes

- Markdown is the source of truth.
- Review the article before generating final HTML for publishing.
- `mist-blue` is the preferred theme for technical long-form WeChat articles.

See:

- [SKILL.md](SKILL.md)
- [QUICKSTART.md](QUICKSTART.md)
- [EXAMPLES.md](EXAMPLES.md)
