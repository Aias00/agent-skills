---
name: github-trending-writer
description: Find GitHub Trending repositories, save readable repo source material locally, and draft Chinese articles in a review-first workflow. Use when the user wants to 看 GitHub Trending、整理热门开源项目、把仓库内容落成中文稿、或基于 Trending 项目做技术热点文章后再发布。
---

# GitHub Trending Writer

Use this skill when the user wants one repeatable workflow for:

- 从 GitHub Trending 选项目
- 把仓库 README / 仓库页内容落到本地候选目录
- 基于候选目录写中文技术稿
- 先 review 再修稿
- 审阅通过后再交给平台发布 skill

## Unified Entry

From the repository root:

```bash
python3 github-trending-writer/scripts/run.py <command> [options]
```

Commands:

- `fetch`: 抓取 GitHub Trending 候选并落盘
- `publish`: 把已审阅候选交给 [article-multi-publisher](../article-multi-publisher/SKILL.md)

## Workflow

### 1. 抓取候选

默认抓当天 Trending：

```bash
python3 github-trending-writer/scripts/run.py fetch
```

按语言或周期抓取：

```bash
python3 github-trending-writer/scripts/run.py fetch \
  --language python \
  --since weekly \
  --limit 4
```

底层脚本也可直接调用：

```bash
python3 github-trending-writer/scripts/fetch_github_trending.py
```

抓取阶段会：

- 抓取 GitHub Trending 页面
- 解析仓库名、描述、语言、总 stars、forks、今日新增
- 使用 repo-local [url-reader](../url-reader/SKILL.md) 读取 README / 仓库页内容
- 过滤错误页、空白页或无效内容
- 为每个候选生成：
  - `content.md`
  - `raw.md`
  - `meta.json`
- 在输出根目录生成：
  - `manifest.json`
  - `README.md`

默认输出目录：

```text
tmp/github-trending-review/{YYYY-MM-DD}/curated/
```

### 2. 向用户展示候选

优先展示：

- 编号
- 仓库名
- Trending 周期
- 语言、总 stars、今日新增
- 仓库链接
- 本地 `content.md` 路径

如果 README 明显无内容、错误页或只有占位文本，不要推荐给用户。

### 3. 读取选中的候选内容

用户选定某篇后：

1. 先读对应目录里的 `content.md`
2. 再读 [references/style-guide.md](references/style-guide.md)
3. 根据用户意图决定稿型：
   - 默认：`解读型`
   - 用户明确说“更想看原文”“先翻译”时：`翻译整理型`

### 4. 写稿后先 Review，再给用户看修订稿

默认不要把首稿当成可发稿。

标准顺序：

1. 先把主稿写到候选目录
2. 立即调用 [technical-article-review](../technical-article-review/SKILL.md)
3. 除非用户明确要求 `review-only`、`只审不改`、`先给意见别动稿`，否则直接按审阅意见修改源稿
4. 只把 review 后的修订稿发给用户审阅

推荐文件名：

- `article.md`
- `translation-draft.zh.md`
- `review-draft.zh.md`

### 5. 审阅通过后再发布

```bash
python3 github-trending-writer/scripts/run.py publish <candidate-dir>
```

常用参数：

```bash
python3 github-trending-writer/scripts/run.py publish <candidate-dir> \
  --platforms wechat,xhs,toutiao \
  --dry-run
```

如果输入的是候选根目录，也可以按编号发：

```bash
python3 github-trending-writer/scripts/run.py publish <curated-root> \
  --index 1 \
  --source article.md
```

发布边界：

- `github-trending-writer` 只负责候选发现、落盘、写稿约定和成稿选择
- 实际平台发布委托给 [article-multi-publisher](../article-multi-publisher/SKILL.md)
- 微信平台的作者、封面、API/browser 逻辑继续归 [wechat-publisher](../wechat-publisher/SKILL.md)

## Writing Rules

### 解读型

适用于：

- 用户想知道“这个仓库为什么上 Trending”
- 更在意定位、价值和使用场景

要求：

1. 先说“这个仓库在解决什么问题”
2. 再讲“为什么最近火”
3. 再讲“适合谁”和“边界在哪里”
4. 文末保留仓库链接或仓库名

### 翻译整理型

适用于：

- 用户明确想看更完整的原始信息
- README 本身结构很好

要求：

1. 先用中文讲清仓库在做什么
2. 主体按 README 或目录结构整理
3. 结尾只补少量解释，不要喧宾夺主

## Quality Bar

- 不要把 README 很弱的仓库硬写成深度项目分析
- 不要把 Trending 上榜误写成官方背书
- 不要虚构仓库没有的能力
- 区分 README 原始信息和作者解读
- 不要把未 review 的首稿推进到 HTML / 封面 / 发布

## References

- 风格说明：[references/style-guide.md](references/style-guide.md)
