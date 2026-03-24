# Quickstart

## 1. 安装依赖

```bash
cd wechat-article-formatter
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## 2. 转换文章

```bash
.venv/bin/python scripts/markdown_to_html.py \
  --input /abs/path/article.md \
  --theme mist-blue \
  --preview
```

## 3. 主题选择

| 场景 | 主题 |
|------|------|
| 技术长文 / 仓库解读 / 工程实践 | `mist-blue` |
| AI 展示页 / 模型介绍 / 产品感更强的文章 | `ai-tech` |

## 4. 最小检查

- 图片是否加载
- H1 是否已被移除
- 列表和编号是否正常
- 代码块是否可读
- 主题是否符合预期

## 5. 推荐流程

1. 先 review Markdown
2. 再生成 HTML
3. 再交给 `wechat-publisher`
