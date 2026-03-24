# URL Reader

读取 URL 内容并保存为 Markdown 与本地图片。

## Quick Start

```bash
python3 url-reader/scripts/url_reader.py https://example.com/article --save
```

默认输出目录：

```text
url-reader/output/
```

## Strategy

1. Firecrawl
2. Jina Reader
3. Playwright

## Typical Use Cases

- 读取公众号文章
- 读取仓库主页或 README 网页
- 为技术文章准备本地素材
- 被其它写稿 skill 以模块方式调用

See [SKILL.md](SKILL.md) for details.
