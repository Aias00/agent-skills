---
name: ai-hotspot-collector
description: Aggregate AI-related candidates from multiple built-in source fetchers (TechCrunch, Engadget, Fast Company, Hacker News, GitHub Trending, The Verge), save them into one review queue, and draft Chinese Markdown articles in a review-first workflow. Use when the user wants to 收集 AI 热点、做 AI 新闻选题池、批量看多个来源今天有什么 AI 内容、或基于多来源热点写中文稿。
---

# AI Hotspot Collector

This skill is a **source aggregator**, not a site-specific scraper.

It uses repo-local fetchers, merges candidates into one queue, and hands approved drafts to the local publishing chain.

## Unified Entry

From the repository root:

```bash
python3 ai-hotspot-collector/scripts/run.py <command> [options]
```

Commands:

- `fetch`: 批量抓取多个来源并生成总 manifest
- `publish`: 把某一篇已审稿内容交给 [article-multi-publisher](../article-multi-publisher/SKILL.md)

## What It Produces

默认输出到：

```text
content/{YYYY-MM-DD}/
```

典型结构：

```text
content/{date}/
├── 00-今日AI热点速读.md
├── images/
├── manifest.json
├── all_candidates.json
├── summary.json
├── README.md
├── techcrunch/
├── the-verge/
├── hn/
├── twitter/
├── github-trending/
├── engadget/
└── fast-company/
```

## Workflow

### 1. 收集候选

默认抓全部来源：

```bash
python3 ai-hotspot-collector/scripts/run.py fetch
```

限制来源和每源条数：

```bash
python3 ai-hotspot-collector/scripts/run.py fetch \
  --sources hn,techcrunch,engadget \
  --limit-per-source 3
```

抓取阶段会：

- 为每个来源生成子目录
- 去重同事件候选
- 生成统一 `manifest.json`
- 生成总稿 `00-今日AI热点速读.md`
- 复制首图和关键配图到总稿 `images/`

### 2. 向用户展示候选

优先展示：

- 全局编号
- 标题
- 来源
- 作者与发布时间
- 原文链接
- 本地 `content.md` 路径

如果某个来源抓取失败，也要在总统计里说明，不要把失败伪装成“没有新闻”。

### 3. 写稿并先给用户审阅

默认先把稿子写回候选目录，再给用户审阅。

推荐文件名：

- `article.md`
- `translation-draft.zh.md`
- `review-draft.zh.md`

如果是技术类文章，默认先走 [technical-article-review](../technical-article-review/SKILL.md)，再把修订稿给用户看。

### 4. 审阅通过后再发布

```bash
python3 ai-hotspot-collector/scripts/run.py publish <content-root> \
  --index 3 \
  --source article.md
```

常用参数：

```bash
python3 ai-hotspot-collector/scripts/run.py publish <content-root> \
  --index 3 \
  --platforms wechat,xhs,toutiao \
  --dry-run
```

## Quality Bar

- 不要把聚合器当成单一来源
- 来源抓取逻辑已内置在 repo 内，不依赖外部 source skill 才能运行
- 不要把 RSS 摘要误写成完整报道
- 跨平台重复事件优先挑信息最完整的一篇做主稿
- 如果启用了 LLM 重写，也不能删除图片、链接和来源信息

## References

- 文章模板：[references/article-template.md](references/article-template.md)
- 来源编辑提示：[references/platform-notes.md](references/platform-notes.md)
