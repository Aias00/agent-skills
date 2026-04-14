# Workflow: New Slides

适用场景：

- 用户要从 `doc_url`、`doc_token` 或 `doc_name` 生成一份新的飞书 Slides
- 当前没有 `target_slides_url`

## Inputs

必填：

- 一个且仅一个来源：`doc_url` / `doc_token` / `doc_name`

可选：

- `content_mode`: `faithful` 或 `report`
- `title`
- `max_slides`

默认：

- `target_mode = new`
- `content_mode = report`

## Required Reading

开始执行前：

1. 先读 `../SKILL.md`
2. 再读已安装的 `~/.codex/skills/lark-shared/SKILL.md`
3. 再读已安装的 `~/.codex/skills/lark-doc/SKILL.md`
4. 再读已安装的 `~/.codex/skills/lark-slides/SKILL.md`
5. 再读 `content-modes.md`
6. 再读 `slide-authoring-rules.md`

## Step 1: Resolve The Source

先把来源归一化成一个明确可抓取的文档目标。

- `doc_url`：直接进入抓取
- `doc_token`：直接进入抓取
- `doc_name`：先搜索，再按结果处理

`doc_name` 规则：

- `0` 个候选：停止，要求用户补充更精确的名称
- `1` 个明确候选：自动继续
- `>1` 个可信候选：停止，要求用户从候选列表中明确选择

补充约束：

- 搜索结果里的 wiki URL 只是候选命中，不等于已经拿到了可直接 `docs +fetch` 的底层对象
- 如果候选是 wiki，需要先按已安装 `lark-doc` skill 的规则解析到底层对象类型 / token，再继续 fetch
- 不要在这里假设“search 命中的 wiki 一定能直接抓取”

先执行：

```bash
python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py resolve-source \
  --run-dir <run_dir> \
  --doc-url <url>
```

或：

```bash
python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py resolve-source \
  --run-dir <run_dir> \
  --doc-token <token>
```

或：

```bash
python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py resolve-source \
  --run-dir <run_dir> \
  --doc-name "<document name>"
```

期望产物：

- `resolved-source.json`

## Step 2: Fetch The Full Document

抓取全文，不是只抓第一页。

```bash
python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py fetch \
  --run-dir <run_dir> \
  --resolved-source <run_dir>/resolved-source.json
```

执行要求：

- 使用 `lark-cli docs +fetch --as user --format json`
- 如果返回 `has_more`，必须继续翻页直到全文抓完
- 把结构化结果写入 `source.json`
- 把聚合后的 Markdown 写入 `source.md`

## Step 3: Choose The Content Mode

按 [`content-modes.md`](content-modes.md) 选择模式：

- `faithful`：原文结构应保持可识别
- `report`：默认，按汇报逻辑重组

如果用户没有指定，默认 `report`。不要把默认值写得模糊。

## Step 4: Draft The Outline

基于 `source.md` 起草 `outline.json`，并遵守 [`slide-authoring-rules.md`](slide-authoring-rules.md)。

最少要包含：

- `presentation.title`
- `presentation.source`
- `presentation.target_mode = "new"`
- `presentation.content_mode`
- `slides[]`
- 每页的 `no`、`role`、`section_divider`、`title`、`layout`、`key_points`

建议输出一个给用户审阅的摘要：

```text
[PPT 标题] — [目标受众 / 汇报语境]
1. [封面]
2. [背景 / 目标]
3. [现状 / 问题]
4. [方案 / 进展]
5. [风险 / 决策]
6. [下一步]
```

## Step 5: Hard Approval Gate

这一步必须停下来。

在用户明确回复“确认 / 可以生成 / 继续发布 / approve outline”之前：

- 不要运行 `validate-outline`
- 不要运行 `render`
- 不要运行 `publish`
- 不要创建任何 Slides 资源

## Step 6: Validate And Render

用户确认 outline 后，再进入脚本阶段：

```bash
python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py validate-outline \
  --outline <run_dir>/outline.json

python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py render \
  --run-dir <run_dir> \
  --outline <run_dir>/outline.json
```

期望产物：

- `slides.json`
- `render-summary.json`

## Step 7: Publish A New Deck

发布规则是固定的：

- `<= 10` 页：优先 `lark-cli slides +create --as user --title ... --slides ...`
- `> 10` 页：先 `lark-cli slides +create --as user --title ...` 创建空 deck，再循环 `lark-cli slides xml_presentation.slide create --as user`

执行：

```bash
python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py publish \
  --run-dir <run_dir> \
  --outline <run_dir>/outline.json \
  --slides-json <run_dir>/slides.json
```

冻结的 publish-result 契约：

- `target_mode = new`
- 新 deck 的 `xml_presentation_id`
- `url`
- `slide_ids`
- `slides_added`
- `run_dir`
- `publish-result.json`

## Stop Conditions

遇到以下情况必须停止，不要强行继续：

- 来源无法解析
- `doc_name` 有多个候选但用户尚未选择
- 抓取未完成或权限不足
- outline 校验失败
- XML render 失败
- 发布只完成了一部分页面

如果发布部分成功，也要保留 `run_dir` 和已返回的 `slide_ids`，不要假装整次发布完成。
