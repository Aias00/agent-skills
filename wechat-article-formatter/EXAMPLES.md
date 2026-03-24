# Examples

## 1. 技术长文转公众号 HTML

```bash
wechat-article-formatter/.venv/bin/python \
  wechat-article-formatter/scripts/markdown_to_html.py \
  --input generated/opencli-wechat-article.md \
  --theme mist-blue \
  --output generated/opencli-wechat-article.html \
  --preview
```

适用：

- 仓库解读
- 工程实践
- 技术评测

## 2. AI 展示型文章

```bash
wechat-article-formatter/.venv/bin/python \
  wechat-article-formatter/scripts/markdown_to_html.py \
  --input generated/model-overview.md \
  --theme ai-tech \
  --output generated/model-overview.html \
  --preview
```

适用：

- 模型介绍
- 产品演示
- 视觉展示感更强的内容

## 3. 与发布链路配合

推荐顺序：

1. `technical-article-review`
2. `technical-article-preflight`
3. `wechat-article-formatter`
4. `wechat-publisher`
