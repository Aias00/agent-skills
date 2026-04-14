# Slide Authoring Rules

这些规则同时服务于 outline 编写和脚本校验。

## Core Principle

一页只讲一个主观点。

如果你发现一页需要同时解释背景、现状、方案、风险，说明这页已经过密，应该拆开。

## Required Outline Shape

每份 outline 至少要有：

- `presentation.title`
- `presentation.source.input_kind`
- `presentation.source.resolved_kind`
- `presentation.source.resolved_value`
- `presentation.target_mode`
- `presentation.content_mode`
- `slides[]`

每页 slide 至少要有：

- `no`
- `role`
- `section_divider`
- `title`
- `layout`
- `key_points`

`section_divider` 是显式布尔字段：

- 默认 `false`
- 只有 append 模式中被明确批准的章节分隔页才设为 `true`

## Density Budget

- 默认每页 `3` 到 `5` 个 key points
- `key_points` 超过 `5` 个时，优先拆页，不要继续堆字
- 单条 bullet 最好控制在两行视觉长度内
- 如果标题太长，优先改写标题，不要依赖缩小字号

推荐标题长度：

- 中文优先控制在 `18` 字以内
- 英文优先控制在 `10` 个词以内

## Layout Selection

支持的布局枚举：

- `title-only`
- `title-body`
- `two-column`
- `bullets`
- `comparison`
- `timeline`
- `metrics`

这份列表必须与脚本里的 `VALID_LAYOUTS` 保持一致；不要在文档里额外写出脚本未声明的 layout。

建议用法：

- `title-only`：封面或章节分隔页
- `title-body`：标准内容页
- `bullets`：一列要点页
- `two-column`：左右两块内容并列
- `comparison`：方案对比、差异说明
- `timeline`：时间线、里程碑、阶段推进
- `metrics`：指标卡、结果数据、关键数字

如果连续两页以上都是纯文本内容，至少要检查其中一页是否更适合改成：

- `comparison`
- `timeline`
- `metrics`

## Split Rules

出现以下任一情况时，应拆成多页：

- 超过 `5` 个要点
- 一页里混入两个以上主题
- 标题必须写成完整段落才能说清
- bullet 已经长到像小段正文
- 同一页既要讲“现状”又要讲“方案”还要讲“风险”

拆页优先级：

1. 先按主题拆
2. 再按时间顺序或因果关系拆
3. 最后才考虑压缩措辞

## New Deck Publish Rules

new 模式下：

- 始终先建空 deck
- 再逐页追加 slide XML

这条规则是发布规则，不是可选优化项。

原因：

- 新建 + 逐页追加更容易保留部分成功状态
- 对这个 workflow 来说，可恢复性比少一次命令更重要

## Append Mode Rules

append 模式默认只加“本次新增内容”的页面。

禁止默认生成：

- 通用封面
- 通用目录
- 重新介绍整份 deck 的背景页

只有在用户明确要求“插入新的章节页 / section divider”时，才允许以 `role = cover` 开头。

建议约束：

- 如果第一张是分隔页，在该 slide 上写 `section_divider: true`
- 分隔页文案应体现新增章节主题，不应复用整份 deck 的总标题

## Source Fidelity Rules

- `faithful` 模式下，优先保留原文的限制、假设、 caveat
- `report` 模式下，可以重排，但不能捏造原文没有的信息
- 无论哪种模式，涉及风险、约束、未决事项时，不要在 outline 阶段静默删除

## Review Gate Reminder

任何布局和密度规则，都不能跳过 workflow 的硬门：

- 先给用户看 outline
- 用户确认后再校验 / 渲染 / 发布
