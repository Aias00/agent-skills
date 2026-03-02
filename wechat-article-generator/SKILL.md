---
name: wechat-article-generator
description: Generate WeChat article deliverables from topic or markdown, convert to WeChat-friendly HTML, organize images, and package artifacts for publishing.
---

# WeChat Article Generator

## 适用场景

当用户要“生成公众号文章发布包”时使用本 skill，目标是一次产出可交付文件：
- `article.md`
- `article-wechat.html`
- `images/`
- `README.txt`
- `{slug}.tar.gz`

## 核心能力

1. 从主题生成 Markdown 草稿（可直接编辑）
2. 将 Markdown 转换为微信兼容 HTML（`<p>` + inline style）
3. 组织封面图/配图到标准目录
4. 生成发布说明并打包 `tar.gz`

## 快速命令

### 1) 从主题一键生成

```bash
python3 scripts/generate_wechat_article_package.py \
  "Chrome 扩展自动化发布实战" \
  --root ./wechat-articles
```

### 2) 基于现有 Markdown 生成

```bash
python3 scripts/generate_wechat_article_package.py \
  --md-in /abs/path/article.md \
  --title "Chrome 扩展自动化发布实战" \
  --root ./wechat-articles
```

### 3) 带图片生成（推荐）

```bash
python3 scripts/generate_wechat_article_package.py \
  "AI 工作流实战" \
  --cover /abs/path/cover.png \
  --images /abs/path/img1.png /abs/path/img2.png \
  --root ./wechat-articles
```

### 4) 仅做 Markdown → HTML 转换

```bash
python3 scripts/markdown-to-wechat.py /abs/path/article.md --out /abs/path/article-wechat.html
```

## 输出约定

默认输出到 `--root` 指定目录：

```text
wechat-articles/
├── <slug>/
│   ├── article.md
│   ├── article-wechat.html
│   ├── README.txt
│   └── images/
│       ├── cover.*
│       ├── image-1.*
│       └── ...
└── <slug>.tar.gz
```

若 `slug` 冲突，默认自动追加序号（`-2`, `-3`...）。

## 工作规则

- 默认不自动发布到公众号后台，只生成发布包。
- 若用户未提供图片，仍生成结构化目录，并在 `images/README.txt` 提示补图。
- 转换脚本会对普通文本做 HTML 转义，避免原始标签注入。
- 允许 `http/https/mailto` 链接，其它协议会被降级为 `#`。

## 参数建议

- `--title`：用于自定义文章标题
- `--slug`：用于固定目录名/包名
- `--overwrite`：覆盖已有同名目录
- `--no-package`：只生成目录，不打包

## 备注

如果用户额外要求“生成配图内容”，可先用图像生成类 skill 产图，再把路径传给 `--cover/--images`，最后由本 skill 统一打包。
