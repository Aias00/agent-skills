# Workflow: Append Slides

适用场景：

- 用户要把文档内容追加到现有演示文稿
- 输入里包含 `target_slides_url`

append 模式的核心约束：**只新增，不改旧内容。**

## Inputs

必填：

- 一个且仅一个来源：`doc_url` / `doc_token` / `doc_name`
- `target_slides_url`

可选：

- `content_mode`
- `title`
- `max_slides`

默认：

- `target_mode = append`
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

来源解析与 new 模式相同：

- `doc_url`：直接继续
- `doc_token`：直接继续
- `doc_name`：搜索并在歧义时停下来让用户选择

先运行 `resolve-source`，生成 `resolved-source.json`。

补充约束：

- 搜索命中的 wiki 只算候选，不算已解析完成的 fetch target
- 如果最终选中的是 wiki，先按已安装 `lark-doc` skill 的规则解析到底层对象类型 / token，再继续 fetch

## Step 2: Resolve The Target Deck

`target_slides_url` 必须先解析成真实的 `xml_presentation_id`，再允许发布。

支持两种目标形式：

- `/slides/<xml_presentation_id>`：直接取 presentation id
- `/wiki/<wiki_token>`：先查询 wiki node，再按当前 refs / schema 确认它解析到 slides 对象，并使用返回的真实对象 token 作为 presentation id

解析规则：

- 如果 wiki 目标解析后不是 `slides` 类型，立即停止
- 如果 URL 既不是 `/slides/` 也不是 `/wiki/`，立即停止
- 解析失败时，禁止开始追加

文档约束：

- 这里不要假设自定义响应 envelope
- 以已安装 `lark-slides` skill 和 `lark-cli schema` 的当前返回字段为准

## Step 3: Fetch The Full Source Document

用 `fetch` 子命令抓取全文，并写入：

- `source.json`
- `source.md`

分页必须抓完整，不能只取首页内容。

## Step 4: Draft An Append-Safe Outline

append 模式的 outline 仍然先给用户审阅，但内容约束更严格。

必须在 `presentation` 中明确：

- `target_mode = "append"`
- `content_mode`
- 来源信息

append 模式默认只写“新增段落”或“新增章节”需要的页面，不重做整份 deck 的封面和目录。

如果确实要插入章节分隔页，应在对应 slide 上显式写：

```json
{
  "role": "cover",
  "section_divider": true,
  "layout": "title-only"
}
```

## Step 5: Avoid Duplicate Covers

默认禁止：

- 通用封面页
- 通用目录页
- 重复“汇报标题 / 项目名称 / 周报封面”页

只有当用户明确说“我就是要插入一个章节分隔页”时，才允许生成 section divider。

建议做法：

- 使用更像“章节页”的标题，而不是整份 deck 的封面文案
- 在对应 slide 上写 `section_divider: true`，明确这是有意为之

如果没有这个明确意图，append 模式第一张 slide 不应是 `role = cover`。

## Step 6: Hard Approval Gate

append 模式同样必须先停在 outline 审阅。

在用户明确确认前：

- 不要 render
- 不要 publish
- 不要向现有 deck 添加任何 slide

## Step 7: Validate, Render, Publish

用户确认后执行：

```bash
python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py validate-outline \
  --outline <run_dir>/outline.json

python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py render \
  --run-dir <run_dir> \
  --outline <run_dir>/outline.json

python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py publish \
  --run-dir <run_dir> \
  --outline <run_dir>/outline.json \
  --slides-json <run_dir>/slides.json \
  --target-slides-url <target_slides_url>
```

publish 阶段规则：

- 解析目标 presentation id
- 逐页调用 `lark-cli slides xml_presentation.slide create --as user`
- 只记录新增页的 `slide_ids`

## Safe Publication Rules

- 不删除原有 slide
- 不重排原有 slide
- 不覆盖原有 slide 内容
- 不把 append 流程伪装成“重新生成整套 deck”
- 如果中途失败，保留已成功追加的页面元数据，并如实报告部分成功

## Expected Result

冻结的 publish-result 契约：

- `target_mode = append`
- `xml_presentation_id`
- `slide_ids`
- `slides_added`
- `url`
- `run_dir`

## Stop Conditions

以下情况必须停止：

- `target_slides_url` 无法解析
- wiki 目标不是 slides
- 用户没有确认 outline
- outline 校验失败
- render 失败
- 追加到一半报错

append 模式出错时，不要自动回滚；保留产物，报告成功追加到第几页。
