---
name: article-pipeline-skill
description: 从 GitHub 仓库生成公众号文章并发布的完整流程。Use when the user asks to 读某个仓库写公众号文章、基于 GitHub 项目写文章、发公众号。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Article Pipeline Skill

从 GitHub 仓库 → 公众号草稿箱的完整文章生产流程。

## 流程总览

```text
1. 获取仓库信息（gh repo view / gh api readme）
2. 按写作规则写稿（references/writing-rules.md）
3. 跑 pipeline（banned check → HTML → 封面 → 预检 → dry-run）
4. 用户确认后发布
```

## Step 1: 获取仓库信息

```bash
gh repo view <owner/repo> --json name,description,url,stargazerCount,primaryLanguage,licenseInfo,homepageUrl,createdAt,updatedAt
gh api repos/<owner/repo>/readme --jq '.content' | base64 -d
```

- README 太简短时，读 docs 下的核心文档（architecture.md、guide 等）
- marketplace 类仓库用 raw.githubusercontent.com 拉 JSON 文件

## Step 2: 写稿

创建目录并写 Markdown：

```bash
mkdir -p content/<slug>/imgs
```

写作规则见 [references/writing-rules.md](references/writing-rules.md)。核心约束：

- 不提 stars、不提作者/赞助、不引用其他文章
- 禁用对比脚手架句式（完整清单见 references/banned-patterns.md）
- 安装方式只保留一条最简命令
- 每条特性讲完「是什么」要讲「带来什么效果」
- 结语收束，不预告下一篇

## Step 3: 跑 pipeline

```bash
bash scripts/article-pipeline.sh \
  --input content/<slug>/<slug>.md \
  --theme ai-tech \
  --cover
```

Pipeline 五步：banned 检查 → ai-tech HTML → 紫色封面（无 badge）→ 预检 → dry-run。

banned 检查失败时按报告逐条修复，重跑直到通过。

## Step 4: 预览与发布

```bash
open content/<slug>/<slug>.wechat-publisher.html
open content/<slug>/imgs/cover.png
```

用户确认后发布：

```bash
cd wechat-publisher && bun scripts/wechat-publish.ts \
  /绝对路径/content/<slug>/<slug>.wechat-publisher.html \
  --cover /绝对路径/content/<slug>/imgs/cover.png
```

## 可选：流程图配图

文章需要架构图时：

1. 手写 SVG（紫蓝配色，参考 Loop Engineering 流程图风格）
2. `python3 wechat-publisher/scripts/render-svg-cover.py --svg x.svg --out x.png --size WxH`
3. Markdown 里引用 PNG（公众号不支持 SVG）

## 故障处理

| 症状 | 处理 |
|------|------|
| 发布报 `invalid ip` | 让用户把当前出口 IP 加进公众号后台 IP 白名单 |
| banned 检查拦截 | 按 references/banned-patterns.md 改句式，不删内容 |
| 封面标题不对 | H1 变了要重跑 `--cover` |

## References

- [写作规则](references/writing-rules.md)
- [禁用句式清单](references/banned-patterns.md)
