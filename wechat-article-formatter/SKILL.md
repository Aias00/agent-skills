---
name: wechat-article-formatter
description: 将 Markdown 文章转换为适配微信公众号的 HTML。Use when the user asks to 美化文章、生成公众号 HTML、优化公众号格式、或把 Markdown 转成适合微信编辑器粘贴的 HTML。
allowed-tools: Read, Write, Bash
---

# WeChat Article Formatter

将 Markdown 文章转换为适配微信公众号发布的 HTML。

## Themes

支持两套主题：

- `ai-tech`：更偏 AI 展示感
- `mist-blue`：更克制的技术编辑风

如果项目已经统一使用“雾霾蓝”，默认优先：

```bash
--theme mist-blue
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
  --theme mist-blue \
  --output /abs/path/article.html \
  --preview
```

From inside the skill directory:

```bash
.venv/bin/python scripts/markdown_to_html.py \
  --input /abs/path/article.md \
  --theme mist-blue \
  --preview
```

## Workflow

1. 以 Markdown 作为 source of truth
2. 选择主题：
   - `mist-blue`：仓库解读、工程实践、长文
   - `ai-tech`：产品展示、模型介绍、AI 主题
3. 生成 HTML
4. 本地预览：
   - 图片是否加载
   - 列表和编号是否正常
   - 代码块是否可读
   - H1 是否已移除
5. 若项目有自定义色板，只在生成后做最小覆盖，不要继续维护另一套旧转换器

## Important Rules

- 先改 Markdown，再重新生成 HTML，不要长期手改派生 HTML。
- 公众号标题单独填写，HTML 只负责正文。
- 本地图片路径是否能直接用于后续发布，取决于下游发布 skill；转换器本身不负责上传图片。
- 如果文章刚写完首稿，先走 `technical-article-review`，再进入 HTML 生成。

## Common Commands

生成默认输出文件：

```bash
wechat-article-formatter/.venv/bin/python \
  wechat-article-formatter/scripts/markdown_to_html.py \
  --input article.md \
  --theme mist-blue
```

只做转换，不开预览：

```bash
wechat-article-formatter/.venv/bin/python \
  wechat-article-formatter/scripts/markdown_to_html.py \
  --input article.md \
  --theme ai-tech
```

## References

- 快速参考：[QUICKSTART.md](QUICKSTART.md)
- 使用示例：[EXAMPLES.md](EXAMPLES.md)
- 主题模板：`templates/`
