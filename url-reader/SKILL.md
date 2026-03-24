---
name: url-reader
description: 智能读取任意 URL 内容并保存为 Markdown，支持微信公众号、小红书、头条、知乎、B 站等常见站点。Use when the user wants to 读取网页、保存网页内容、拉取文章正文、或为后续写稿准备本地 Markdown 和图片。
---

# URL Reader

一键读取 URL 内容，自动识别平台，并按 Firecrawl → Jina → Playwright 的顺序降级。

## Default Output

默认保存到：

```text
url-reader/output/
```

每次保存会创建一个日期_标题目录，例如：

```text
output/
└── 2026-03-24_文章标题/
    ├── content.md
    ├── img_01.jpg
    └── ...
```

## Standard Commands

只读取并打印：

```bash
python3 url-reader/scripts/url_reader.py https://example.com/article
```

读取并保存：

```bash
python3 url-reader/scripts/url_reader.py https://example.com/article --save
```

## Setup

```bash
python3 -m venv url-reader/.venv
url-reader/.venv/bin/python -m pip install firecrawl-py requests playwright
url-reader/.venv/bin/playwright install chromium
```

可选环境变量：

```bash
export FIRECRAWL_API_KEY="fc-..."
```

## Notes

- 微信公众号、微博、淘宝等站点可能需要 Playwright 登录态。
- 当该 skill 被其它 repo-local skill 以模块方式调用时，上游 skill 会自己决定输出目录。
- 默认输出目录已经改成 repo-local，不会再写死到某台机器的私人素材目录。
