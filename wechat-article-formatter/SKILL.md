---
name: wechat-article-formatter
description: 将 Markdown 文章转换为适配微信公众号的 HTML。Use when the user asks to 美化文章、生成公众号 HTML、优化公众号格式、或把 Markdown 转成适合微信编辑器粘贴的 HTML。
allowed-tools: Read, Write, Bash
---

# WeChat Article Formatter

将 Markdown 文章转换为适配微信公众号发布的 HTML。

## Themes

支持六套主题（封面和文章配色对应）：

| 主题 | 封面 | 文章风格 | 适用场景 |
|------|------|---------|---------|
| `mist-blue` | 蓝灰 | 克制技术编辑风 | 仓库解读、工程实践、长文 |
| `ai-tech` | - | AI 展示感 | 产品展示、模型介绍、AI 主题 |
| `forest` | 绿色 | 清新自然 | 环保、健康、成长类内容 |
| `sunset` | 橙红 | 温暖活力 | 创意、设计、生活方式 |
| `slate` | 灰蓝 | 中性专业 | 企业、商业、技术文档 |
| `midnight` | 深蓝黑 | 暗色深邃 | 深度分析、夜间阅读 |

如果项目已经统一使用”AI 科技风”，默认优先：

```bash
--theme ai-tech
```

## Setup

From this skill directory:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Standard Command

From the repository root:

```bash
wechat-article-formatter/.venv/bin/python \
  wechat-article-formatter/scripts/markdown_to_html.py \
  --input /abs/path/article.md \
  --theme ai-tech \
  --output /abs/path/article.html \
  --preview
```

From inside the skill directory:

```bash
.venv/bin/python scripts/markdown_to_html.py \
  --input /abs/path/article.md \
  --theme ai-tech \
  --preview
```

## Workflow

1. 以 Markdown 作为 source of truth
2. 选择主题：
   - `ai-tech`：产品展示、模型介绍、AI 主题（默认）
   - `mist-blue`：仓库解读、工程实践、长文
3. 生成 HTML
4. 本地预览：
   - 图片是否加载
   - 列表和编号是否正常
   - 代码块是否可读
   - H1 是否已移除
5. 若项目有自定义色板，只在生成后做最小覆盖，不要继续维护另一套旧转换器

## Handoff Contract

Formatter output is a derived artifact, not a publish-ready verdict.

- For manual copy/paste, inspect the generated HTML locally before copying into WeChat.
- For API/browser publishing, pass the original Markdown to `wechat-publisher/scripts/wechat-publish.ts` unless the article package intentionally provides a dedicated API HTML file.
- For technical articles, run `technical-article-preflight` before publishing. The preflight owns review status, image readiness, cover checks, and final dry-run validation.

## Important Rules

- 先改 Markdown，再重新生成 HTML，不要长期手改派生 HTML。
- 公众号标题单独填写，HTML 只负责正文。
- 本地图片路径是否能直接用于后续发布，取决于下游发布 skill；转换器本身不负责上传图片。
- 如果文章刚写完首稿，先走 `technical-article-review`，再进入 HTML 生成。
- **链接格式**：所有外部链接使用原始链接格式（如 `https://example.com`），不要用 Markdown 链接语法（如 `[文本](URL)`）。这样在微信公众号中更清晰易读。

## Common Commands

生成默认输出文件：

```bash
wechat-article-formatter/.venv/bin/python \
  wechat-article-formatter/scripts/markdown_to_html.py \
  --input article.md \
  --theme ai-tech
```

只做转换，不开预览：

```bash
wechat-article-formatter/.venv/bin/python \
  wechat-article-formatter/scripts/markdown_to_html.py \
  --input article.md \
  --theme mist-blue
```

## References

- 快速参考：[QUICKSTART.md](QUICKSTART.md)
- 使用示例：[EXAMPLES.md](EXAMPLES.md)
- 主题模板：`templates/`
