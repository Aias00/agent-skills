---
name: ai-hotspot-collector
description: Aggregate AI-related candidates from multiple built-in source fetchers (TechCrunch, Engadget, Fast Company, Hacker News, GitHub Trending, The Verge), save them into one review queue, and draft Chinese Markdown articles in a review-first workflow. Use when the user wants to 收集 AI 热点、做 AI 新闻选题池、批量看多个来源今天有什么 AI 内容、或基于多来源热点写中文稿。
---

# AI Hotspot Collector

This skill is a **source aggregator**, not a site-specific scraper.

It now uses repo-local fetchers for the supported sources, then builds one combined review queue for drafting and publishing.

## What This Skill Delivers

- 从多个来源批量收集 AI 热点候选
- 把候选统一落到一个总目录里
- 自动识别跨来源的同事件候选并去重
- 为去重后的唯一事件生成全局编号和总 `manifest.json`
- 自动生成一篇 `00-今日AI热点速读.md` 总稿
- 自动复制候选配图到总稿 `images/` 目录，方便后续直接发布
- 让你可以直接说“第 3 篇”“先看 Engadget 那条”
- 在用户审阅通过后，把某一篇成稿直接派发到微信公众号 / 小红书 / 头条

默认输出位置：

- `content/{YYYY-MM-DD}/`

典型输出结构：

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
├── github-trending/
├── engadget/
└── fast-company/
```

## Built-in Sources

当前 repo 内置支持这些来源：

- `techcrunch`
- `the-verge`
- `hn`
- `github-trending`
- `engadget`
- `fast-company`

也就是说，它不再依赖 `~/.codex/skills/...` 下的来源 skill 才能运行。

## Workflow

### Unified Entry

优先使用统一入口：

```bash
python3 /Users/aias/Work/github/agent-skills/ai-hotspot-collector/scripts/run.py <command> [options]
```

支持的命令：

- `fetch`：批量调用多个来源 skill 抓取候选，并生成总 manifest
- 默认自动去重同事件候选
- 默认自动生成一篇“更自然的中文成文稿”版今日 AI 热点速读
- 默认自动复制首图作为总稿封面，并为各条热点补配图
- 默认 `--rewrite-mode auto`：如果存在 Gemini 或 OpenAI 兼容 API 配置，会对总稿做一次 LLM 重写润色；否则自动退回规则稿
- `publish`：对总候选里的某一篇已审稿内容执行多平台发布

### 1. 收集候选

默认抓全部来源：

```bash
python3 /Users/aias/Work/github/agent-skills/ai-hotspot-collector/scripts/run.py fetch
```

限制来源和每源条数：

```bash
python3 /Users/aias/Work/github/agent-skills/ai-hotspot-collector/scripts/run.py fetch \
  --sources hn,techcrunch,engadget \
  --limit-per-source 3
```

指定输出目录：

```bash
python3 /Users/aias/Work/github/agent-skills/ai-hotspot-collector/scripts/run.py fetch \
  --sources the-verge,fast-company \
  --limit-per-source 2 \
  --output-dir /Users/aias/Work/github/agent-skills/tmp/ai-hotspots/2026-03-11
```

执行结果：

- 每个来源单独落在一个子目录
- 总目录生成：
  - `00-今日AI热点速读.md`
  - `manifest.json`
  - `all_candidates.json`
  - `summary.json`
  - `README.md`
- 去重后的唯一事件会获得统一的全局编号

如需关闭默认行为：

```bash
python3 /Users/aias/Work/github/agent-skills/ai-hotspot-collector/scripts/run.py fetch \
  --keep-duplicates \
  --skip-digest
```

如果你要强制使用 API 重写：

```bash
python3 /Users/aias/Work/github/agent-skills/ai-hotspot-collector/scripts/run.py fetch \
  --rewrite-provider gemini \
  --rewrite-model gemini-2.5-flash \
  --rewrite-mode api
```

如果你要强制使用 OpenAI 兼容 API 重写：

```bash
python3 /Users/aias/Work/github/agent-skills/ai-hotspot-collector/scripts/run.py fetch \
  --rewrite-provider openai \
  --rewrite-mode api \
  --rewrite-model gpt-5-mini
```

如果你只想要规则稿，不做 LLM 润色：

```bash
python3 /Users/aias/Work/github/agent-skills/ai-hotspot-collector/scripts/run.py fetch \
  --rewrite-mode off
```

### 2. 向用户展示候选

优先展示：

- 全局编号
- 标题
- 来源
- 作者与发布时间
- 原文链接
- 本地 `content.md` 路径

如果某个来源抓取失败，也要展示在总统计里，但不要把失败来源伪装成“没有新闻”。

### 3. 读取选中的候选内容

用户选定某篇后：

1. 先读总 `manifest.json`
2. 定位候选目录里的 `content.md`
3. 再读 [references/article-template.md](references/article-template.md)
4. 如需写作风格提醒，再读 [references/platform-notes.md](references/platform-notes.md)

根据用户意图决定稿型：

- 默认：`解读型`
- 如果用户明确说“更想看原文”“翻成中文版本”“先翻译”，用 `翻译整理型`
- 如果用户要日报式汇总，可写成“速读合集”

### 4. 写稿并先给用户审阅

默认不要直接发布。

先把稿子写回候选目录，再给用户审阅。推荐文件名：

- `article.md`：解读型主稿
- `translation-draft.zh.md`：翻译整理型主稿
- `review-draft.zh.md`：偏评论的二次稿

### 5. 审阅通过后再发布

如果用户确认内容可发：

```bash
python3 /Users/aias/Work/github/agent-skills/ai-hotspot-collector/scripts/run.py publish <content-root> \
  --index 3 \
  --source article.md
```

常用参数：

```bash
python3 /Users/aias/Work/github/agent-skills/ai-hotspot-collector/scripts/run.py publish <content-root> \
  --index 3 \
  --platforms wechat,xhs,toutiao \
  --dry-run
```

如果目录里同时存在多个草稿，优先顺序是：

1. `article.md`
2. `translation-draft.zh.md`
3. `review-draft.zh.md`

也可以显式指定：

```bash
python3 /Users/aias/Work/github/agent-skills/ai-hotspot-collector/scripts/run.py publish <content-root> \
  --index 3 \
  --source translation-draft.zh.md
```

## Quality Bar

- 不要把聚合器当成单一来源
- 来源抓取逻辑现在在 repo 内部维护，不再依赖外部 skill 路径
- 不要把 RSS 摘要误写成完整报道
- 对跨平台重复事件，优先挑信息最完整的一篇做主稿
- 如果多篇只值得简述，改写成“速读合集”
- 如果启用了 LLM 重写，也不能删除图片、链接和来源信息
- Gemini 环境变量优先使用 `GEMINI_API_KEY`，也兼容 `GOOGLE_API_KEY`

## References

- 文章模板： [references/article-template.md](references/article-template.md)
- 来源编辑提示： [references/platform-notes.md](references/platform-notes.md)
