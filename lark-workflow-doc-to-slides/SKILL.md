---
name: lark-workflow-doc-to-slides
version: 1.0.0
description: "文档转幻灯片工作流：把飞书文档或 Wiki 内容先整理成可审阅的 slide outline，经用户确认后新建 Slides 或追加到已有 Slides。适用于使用 doc_url、doc_token、doc_name 作为来源，或把文档内容追加到 target_slides_url 指向的现有演示文稿。"
metadata:
  requires:
    bins: ["lark-cli", "python3"]
---

# Lark Workflow Doc To Slides

把文档变成 PPT 时，先把“文档内容”变成“可审阅的大纲”，再把已批准的大纲变成 Slides。

适用触发语义：

- “把这篇文档转成飞书幻灯片 / PPT”
- “根据 `doc_url` / `doc_token` / `doc_name` 生成 Slides”
- “把这个 Wiki 做成汇报幻灯片”
- “把这篇文档追加到现有 Slides”
- “用 `target_slides_url` 继续往当前 deck 里加几页”

**CRITICAL — 开始前必须先读取已安装的 `lark-shared`、`lark-doc`、`lark-slides` skills；本机默认路径是 `~/.codex/skills/lark-shared/SKILL.md`、`~/.codex/skills/lark-doc/SKILL.md`、`~/.codex/skills/lark-slides/SKILL.md`。**

## Required Inputs

必须且只能提供一个来源标识：

- `doc_url`
- `doc_token`
- `doc_name`

可选输入：

- `target_slides_url`
- `content_mode`: `faithful` | `report`
- `title`
- `max_slides`

默认值：

- 未提供 `target_slides_url` 时，`target_mode = new`
- 提供了 `target_slides_url` 时，`target_mode = append`
- 未提供 `content_mode` 时，默认 `report`

## Workflow Invariants

- 必须先生成 outline，再做 XML render 和 Slides 发布。
- 用户未明确确认 outline 前，禁止创建新 deck，也禁止向已有 deck 追加页面。
- `doc_name` 命中多个候选时，必须停下来让用户选；禁止自动猜测。
- 搜索结果里的 wiki 命中只能当候选来源；在 fetch 前，必须先按已安装的 `lark-doc` 指南解析成底层对象类型 / token，不能把 wiki 搜索命中当成“已可直接抓取”的来源。
- append 模式只允许新增 slides；禁止重写、删除、重排已有页面。
- append 模式默认不生成通用“封面 / 目录”；只有用户明确要求新章节分隔页时，才允许带 `section_divider: true` 的 divider 页。

## Routing

- 无 `target_slides_url`：
  - 读取 [`references/workflow-new-slides.md`](references/workflow-new-slides.md)
  - 再读取 [`references/content-modes.md`](references/content-modes.md)
  - 再读取 [`references/slide-authoring-rules.md`](references/slide-authoring-rules.md)
- 有 `target_slides_url`：
  - 读取 [`references/workflow-append-slides.md`](references/workflow-append-slides.md)
  - 再读取 [`references/content-modes.md`](references/content-modes.md)
  - 再读取 [`references/slide-authoring-rules.md`](references/slide-authoring-rules.md)

## Execution Shape

执行脚本位于 `scripts/doc_to_slides.py`。工作流子命令：

```bash
python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py resolve-source ...
python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py fetch ...
python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py validate-outline ...
python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py render ...
python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py publish ...
```

运行目录约定：

```text
.lark-workflow-doc-to-slides/runs/<timestamp>-<slug>/
```

常见产物：

- `resolved-source.json`
- `source.json`
- `source.md`
- `outline.json`
- `slides.json`
- `render-summary.json`
- `publish-result.json`

`publish-result.json` 采用归一化的顶层字段：

- `target_mode`
- `xml_presentation_id`
- `url`
- `slide_ids`
- `slides_added`
- `run_dir`

## Operator Rules

- 用 AI 负责理解原文和写 outline；用脚本负责校验、渲染、发布。
- 生成 outline 时，优先对齐 `templates/outline.json` 的字段形状；每页 slide 保留显式布尔字段 `section_divider`，默认 `false`，append 模式需要章节分隔页时才设为 `true`。
- 发布阶段只允许使用现有 `lark-cli` 命令链；不存在 `slides +create-from-outline` 这种快捷命令。
- 如果权限或身份不对，按 `lark-shared` 规则先修正身份与授权，再继续工作流。
- 涉及 wiki source / wiki target 时，按当前已安装 refs / schema 查看真实返回字段，不要在 skill 文案里猜测自定义响应包裹层。
