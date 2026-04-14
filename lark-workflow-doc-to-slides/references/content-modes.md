# Content Modes

这个 workflow 只支持两种内容模式：

- `faithful`
- `report`

默认值：`report`

## Quick Selector

优先选 `faithful` 的场景：

- 技术设计文档
- 架构方案
- API / 实现 walkthrough
- 原文章节顺序本身很重要的材料

优先选 `report` 的场景：

- 周报 / 月报
- 项目进展汇报
- 向老板、干系人、评审会做汇报
- 原文很长，但会议里只需要关键信息和决策点

## Faithful Mode

目标：让 deck 仍然保留原文结构的可识别性。

允许：

- 保留原文章节顺序
- 把长段落压缩成 bullets
- 把一节拆成两三页 slides，只要顺序不乱
- 保留限制、假设、前提、 caveat

不允许：

- 为了“更像汇报”而重写原文论证逻辑
- 把关键限制条件改写成更乐观的管理摘要
- 把原文的风险和假设直接删掉

faithful 模式下的常见 deck 结构：

1. 封面
2. 背景 / 目标
3. 原文章节 A
4. 原文章节 B
5. 原文章节 C
6. 结论 / 待决策项

## Report Mode

目标：让 deck 更像“会议里拿来讲”的 presentation，而不是压缩后的文档。

允许：

- 按汇报逻辑重组内容
- 合并多个原文章节到一页
- 忽略纯附录型细节
- 把解释性内容转成“现状 / 问题 / 方案 / 风险 / 下一步”的结构

不允许：

- 捏造原文没有的信息
- 把原文明确写出的限制条件悄悄删掉
- 为了凑页数堆砌泛泛的管理话术

report 模式推荐结构：

1. 封面
2. 背景 / 目标
3. 现状 / 问题
4. 方案 / 进展
5. 关键执行细节
6. 价值 / 结果
7. 风险 / 待决策
8. 下一步

## Selection Rules

- 用户没有明确指定时，用 `report`
- 如果用户强调“按原文结构来”“不要改章节顺序”“这是方案文档”，优先 `faithful`
- 如果用户强调“拿去汇报”“给老板看”“做成 PPT 一页页讲”，优先 `report`
- append 模式也遵守相同选择规则，但更应偏向“只补本次新增内容”，不要借机重组整份旧 deck

## Authoring Implications

无论哪种模式，都必须先给用户看 outline，再继续 render / publish。

- `faithful`：outline 应显式映射原文 section
- `report`：outline 应显式体现汇报 storyline

如果模式选择不明显，先在 outline 说明里写清楚你采用的模式和理由，而不是静默假设。
