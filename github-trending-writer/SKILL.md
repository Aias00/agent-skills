---
name: github-trending-writer
description: Find GitHub Trending repositories, save readable repo source material locally, and draft Chinese articles in a review-first workflow. Use when the user wants to 看 GitHub Trending、整理热门开源项目、把仓库内容落成中文稿、或基于 Trending 项目做技术热点文章后再发布。
---

# GitHub Trending Writer

Use this skill when the user wants a repeatable workflow for:

- 从 GitHub Trending 找热门开源项目
- 把仓库 README 和趋势信息落到本地目录，供后续审阅
- 基于候选项目生成中文稿
- 按已经验证过的科技内容风格写“解读型”或“翻译整理型”文章
- 在用户审阅通过后，把候选目录里的成稿直接派发到微信公众号 / 小红书 / 头条

## Workflow

### Unified Entry

优先使用统一入口：

```bash
python3 /Users/aias/.codex/skills/github-trending-writer/scripts/run.py <command> [options]
```

支持的命令：

- `fetch`：抓取 GitHub Trending 候选并落盘
- `publish`：把已审阅候选直接交给 [$article-multi-publisher](/Users/aias/.codex/skills/article-multi-publisher/SKILL.md)

### 1. 抓取候选

#### 默认抓当天 Trending

```bash
python3 /Users/aias/.codex/skills/github-trending-writer/scripts/run.py fetch
```

#### 按语言或周期抓取

```bash
python3 /Users/aias/.codex/skills/github-trending-writer/scripts/run.py fetch \
  --language python \
  --since weekly \
  --limit 4
```

常用参数：

```bash
python3 /Users/aias/.codex/skills/github-trending-writer/scripts/run.py fetch \
  --language typescript \
  --since daily \
  --limit 5 \
  --output-dir "$(pwd)/tmp/github-trending-review/$(date +%Y-%m-%d)/curated"
```

底层脚本仍然可直接调用：

```bash
python3 /Users/aias/.codex/skills/github-trending-writer/scripts/fetch_github_trending.py
```

脚本会：

- 抓取 GitHub Trending 页面
- 解析仓库名、描述、语言、总 star、fork、今日新增 star
- 对候选仓库再交给 [$url-reader](/Users/aias/.codex/skills/url-reader/SKILL.md) 读取 README / 仓库主页内容
- 过滤明显的错误页、空白页或无效内容
- 为每个候选生成本地目录：
  - `content.md`
  - `raw.md`
  - `meta.json`
- 在输出根目录生成：
  - `manifest.json`
  - `README.md`
- 同时在终端输出编号列表，便于后续直接说“第 1 篇”

### 2. 向用户展示候选

优先展示：

- 编号
- 仓库名
- GitHub Trending 排名和周期
- 语言、总 star、今日新增
- 仓库链接
- 本地 `content.md` 路径

如果候选 README 明显无内容、错误页或只有占位文本，不要推荐给用户。

### 3. 读取选中的候选内容

用户选定某篇后：

1. 先读对应目录里的 `content.md`
2. 再读 [references/style-guide.md](references/style-guide.md)
3. 根据用户意图决定稿型：
   - 默认：`解读型`
   - 如果用户明确说“更想看原文”“翻成中文版本”“先翻译”，用 `翻译整理型`

### 4. 写稿后先做 Review，再给用户看修订稿

默认不要直接把首稿当成可发稿。

标准顺序是：

1. 先把主稿写到候选目录里
2. 对技术类仓库文章，立即调用 [$technical-article-review](/Users/aias/.codex/skills/technical-article-review/SKILL.md)
3. 除非用户明确要求 `review-only`、`只审不改`，否则直接按审阅意见修改源稿
4. 只把“review 后的修订稿”发给用户审阅，不要把未经 review 的首稿直接交给用户

推荐文件名：

- `article.md`：解读型主稿
- `translation-draft.zh.md`：翻译整理型主稿

默认行为：

- 写完技术文章后，review 是工作流的一部分，不是可选后处理
- 如果审阅发现阻塞项，不要停在报告；直接修稿，再把修订版交给用户
- 只有修订后的源稿，才应该进入 HTML / 封面 / 发布阶段

### 5. 审阅通过后再发布

如果用户确认内容可发，使用发布脚本把候选目录里的成稿直接交给 [$article-multi-publisher](/Users/aias/.codex/skills/article-multi-publisher/SKILL.md)。

```bash
python3 /Users/aias/.codex/skills/github-trending-writer/scripts/run.py publish <candidate-dir>
```

常用参数：

```bash
python3 /Users/aias/.codex/skills/github-trending-writer/scripts/run.py publish <candidate-dir> \
  --platforms wechat,xhs,toutiao \
  --dry-run
```

如果目录里同时存在多个草稿，优先顺序是：

1. `article.md`
2. `translation-draft.zh.md`
3. `review-draft.zh.md`

也可以显式指定：

```bash
python3 /Users/aias/.codex/skills/github-trending-writer/scripts/run.py publish <candidate-dir> \
  --source translation-draft.zh.md
```

如果你拿的是候选根目录，也可以直接按编号发：

```bash
python3 /Users/aias/.codex/skills/github-trending-writer/scripts/run.py publish <curated-root> \
  --index 1 \
  --source article.md
```

这对应聊天里的表达就是：

- “用第 1 篇”
- “发第 2 篇”
- “把第 3 篇翻译稿发出去”

发布边界：

- `github-trending-writer` 负责 Trending 候选发现、落盘、稿型约定和成稿选择
- 实际平台行为委托给 [$article-multi-publisher](/Users/aias/.codex/skills/article-multi-publisher/SKILL.md)
- 微信的封面、作者、API/browser 逻辑继续归 [$wechat-publisher](/Users/aias/.codex/skills/wechat-publisher/SKILL.md)
- 不要在 `github-trending-writer` 里重复实现平台特有规则

## Writing Rules

### 解读型

适用于：

- 用户想看“这个仓库为什么突然上 Trending”
- 用户更在意项目定位、价值和使用场景
- 用户要的是热点解读，而不是逐段翻 README

结构要求：

1. 标题用 `GitHub 热榜：...`
2. 顶部保留：
   - `[!AI] [!推荐]`
   - `::: info`
3. 开头先说“今天在 GitHub Trending 看到...”
4. 先解释“为什么值得看”
5. 再按 3-5 个判断展开
6. 文末保留仓库链接

### 翻译整理型

适用于：

- 用户明确说“更想看原文”
- 需要把 README 的原始信息保留得更完整
- 项目本身说明写得很好，不适合只写成评论

结构要求：

1. 开头仍沿用 `GitHub 热榜：...` 和信息卡
2. 先用 1-2 段解释“这个项目在做什么”
3. 主体按 README 或仓库结构做中文整理
4. 可以保留短英文原句，但不要堆大段英文
5. 结尾只补 1 小段解读，不要喧宾夺主

## Quality Bar

- 不要把 README 很弱的仓库硬写成深度项目分析
- 不要把 Trending 上榜误写成官方背书
- 不要虚构仓库没有的能力
- 如果本质上只是代码集合/模板/提示词仓库，要明确写清楚
- 区分仓库 README 的原始信息和你后补的解释
- 不要把“刚写完但还没 review 的首稿”当成可发稿

## Output Convention

候选目录推荐结构：

```text
candidate-dir/
├── content.md
├── raw.md
├── meta.json
├── article.md
└── translation-draft.zh.md
```

## References

- 风格说明： [references/style-guide.md](references/style-guide.md)
