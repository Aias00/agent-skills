# 通过对话创建 Claude Code Skill：以腾讯云 COS 集成为例

> 不需要手工编写文件，直接告诉 AI 你想要什么 Skill。

**本文完整 Skill 代码**：https://github.com/Aias00/agent-skills/tree/main/content/cos-integration-skill-tutorial

---

很多人以为创建 Skill 需要手工编写 SKILL.md、规划目录结构、填充文档。实际上，Claude Code 提供了 `skill-creator` 这个官方插件，专门用于通过对话创建和改进 Skill。

**你只需要说"帮我创建一个 Skill"，AI 会自动引导你完成整个创建过程。**

这篇文章，我们演示如何通过 `skill-creator` 创建一个腾讯云 COS 集成 Skill。

---

## 一、skill-creator 是什么

`skill-creator` 是 Claude Code 的官方插件，用于：

- **创建新 Skill** —— 从零开始，通过对话生成
- **改进现有 Skill** —— 根据测试反馈迭代优化
- **优化触发描述** —— 自动测试并改进 description 字段

与手工编写相比，`skill-creator` 的优势：

| 维度 | 手工创建 | skill-creator |
|------|---------|---------------|
| 学习成本 | 需要学习 Skill 规范 | 直接描述需求 |
| 时间投入 | 1-2 小时 | 10-20 分钟 |
| 验证方式 | 手工测试 | 自动对比测试 |
| 迭代方式 | 手工编辑文件 | 继续对话即可 |

---

## 二、触发 Skill 创建

有两种方式：

**方式一：直接说需求**

```
帮我创建一个 Skill，用于接入腾讯云 COS 对象存储。
```

**方式二：显式调用**

```
/skill-creator

我想创建一个 Skill，帮我快速接入腾讯云 COS 对象存储。
当我说"接入 COS"或"上传文件到 COS"时，能自动加载相关文档和代码示例。
```

AI 会理解你的意图，开始询问细节：

### 第二步：确认 Skill 边界

AI 会问：

```
这个 Skill 需要覆盖哪些场景？
- 认证配置？
- 文件上传下载？
- 签名 URL？
- 跨域配置？
- 大文件分片？
```

你回答：

```
都需要。另外希望按阶段加载——刚接入时不需要看分片上传，
等到真正遇到大文件问题再加载相关内容。
```

AI 会帮你设计 Skill 结构：

```
这个 Skill 应该支持按需加载：

1. SKILL.md - 入口文件，判断用户处于哪个阶段
2. references/
   - auth.md - 认证配置
   - basics.md - 基础操作
   - advanced.md - 进阶功能（签名 URL、分片上传）
   - troubleshooting.md - 问题排查

这样用户问"跨域报错"时，只加载 troubleshooting.md，
不会一次性塞满上下文。
```

### 第三步：AI 生成 Skill 文件

确认结构后，`skill-creator` 会生成完整的文件：

**SKILL.md**：
```markdown
---
name: cos-integration
description: 腾讯云 COS 对象存储接入指南。Use when the user asks to 接入 COS、腾讯云存储、对象存储、上传文件到 COS、COS 签名、COS 跨域配置、COS 分片上传。
---

# 腾讯云 COS 接入指南

## When To Use

- "帮我接入腾讯云 COS"
- "COS 上传文件怎么写"
- "生成 COS 签名 URL"
- "COS 跨域报错怎么配"

## Workflow

1. 判断当前阶段（初始化/基础集成/进阶功能/问题排查）
2. 按需加载对应 references 文档
3. 提供具体指导或代码

## 阶段判断

| 阶段 | 特征 |
|------|------|
| 初始化 | 没有配置过 COS |
| 基础集成 | 已有配置，需要上传/下载代码 |
| 进阶功能 | 需要签名 URL、分片上传等 |
| 问题排查 | 遇到跨域、权限等问题 |

## References

按需加载，不要一次性全部读取：

- references/auth.md — 认证配置
- references/basics.md — 基础操作
- references/advanced.md — 进阶功能
- references/troubleshooting.md — 常见问题
```

**references/auth.md**（AI 自动生成）：
```markdown
# COS 认证配置

## 获取密钥

### 永久密钥（开发环境）

1. 访问腾讯云 API 密钥管理
2. 获取 SecretId 和 SecretKey
3. 配置环境变量：
   ```bash
   COS_SECRET_ID=your-secret-id
   COS_SECRET_KEY=your-secret-key
   ```

### 临时密钥（生产环境推荐）

```javascript
const STS = require('qcloud-cos-sts');

STS.getCredential({
  secretId: process.env.COS_SECRET_ID,
  secretKey: process.env.COS_SECRET_KEY,
  policy: {
    version: '2.0',
    statement: [{
      action: ['name/cos:PutObject', 'name/cos:GetObject'],
      effect: 'allow',
      resource: ['qcs::cos:ap-guangzhou:uid/1250000000:mybucket/*']
    }]
  },
  durationSeconds: 3600
}, callback);
```

## SDK 初始化

```javascript
// Node.js
const COS = require('cos-nodejs-sdk-v5');
const cos = new COS({
  SecretId: process.env.COS_SECRET_ID,
  SecretKey: process.env.COS_SECRET_KEY
});

// 浏览器端
import COS from 'cos-js-sdk-v5';
const cos = new COS({
  getAuthorization: async (options, callback) => {
    const res = await fetch('/api/cos-credential');
    const { credentials, startTime, expiredTime } = await res.json();
    callback({
      TmpSecretId: credentials.tmpSecretId,
      TmpSecretKey: credentials.tmpSecretKey,
      SecurityToken: credentials.sessionToken,
      StartTime: startTime,
      ExpiredTime: expiredTime
    });
  }
});
```
```

其他 references 文档同理，AI 会根据你的需求自动生成完整内容。

### 第四步：测试验证

`skill-creator` 会创建测试用例，对比"有 Skill"和"无 Skill"的表现：

```
我准备了几个测试用例：
1. "帮我接入腾讯云 COS"
2. "COS 上传文件怎么写"
3. "COS 跨域报错怎么配"

现在运行对比测试，看看有 Skill 和无 Skill 的区别...
```

测试完成后，AI 会打开一个评审界面，让你查看：
- 每个测试用例的输出结果
- 有 Skill vs 无 Skill 的对比
- 定量指标（通过率、耗时）

### 第五步：迭代改进

根据测试反馈，继续对话优化：

```
测试发现第二个用例输出不够具体，需要补充分片上传的代码示例。
```

AI 会修改 Skill，然后重新测试。重复这个过程直到满意。

### 第六步：优化触发描述（可选）

Skill 完成后，`skill-creator` 可以自动优化 `description` 字段：

```
我来优化触发描述，生成 20 个测试查询，
看看哪些能正确触发，哪些会误触发...
```

这会运行一个优化循环，自动调整描述以提高触发准确率。

---

## 二、Skill 的关键设计原则

虽然 AI 帮你生成内容，但你需要理解关键设计原则，这样才能给出正确的需求。

### 2.1 Description 决定何时触发

`description` 字段决定 AI 何时加载这个 Skill：

```yaml
---
name: cos-integration
description: Use when the user asks to 接入 COS、腾讯云存储、对象存储、上传文件到 COS、COS 签名、COS 跨域配置
---
```

**要点**：
- 以 `Use when` 开头
- 列出具体的触发场景
- 包含中英文关键词
- 不要总结 Skill 的流程，只描述触发条件

### 2.2 References 按需加载

把大文档拆分成小文件，让 AI 按需加载：

```
references/
├── auth.md           # 认证阶段才加载
├── basics.md         # 基础操作阶段才加载
├── advanced.md       # 进阶功能阶段才加载
└── troubleshooting.md # 遇到问题才加载
```

**好处**：
- 节省上下文
- 加快响应速度
- 避免 AI 被无关内容干扰

### 2.3 Workflow 引导行为

在 SKILL.md 中写清楚工作流程：

```markdown
## Workflow

1. 判断当前阶段
2. 按需加载对应 references 文档
3. 提供具体指导或代码
4. 确认配置正确性
```

AI 会按照这个流程执行，不会遗漏步骤。

---

## 三、对话创建 Skill 的最佳实践

### 3.1 明确触发场景

告诉 AI 什么时候应该用这个 Skill：

```
用户可能会这样问：
- "接入 COS"
- "上传文件到腾讯云"
- "COS 跨域报错"
- "大文件上传怎么做"
```

AI 会把这些场景写入 `description`。

### 3.2 提供示例代码

如果已有代码，直接发给 AI：

```
这是我之前写的 COS 上传代码：
[粘贴代码]

把它整合到 Skill 里。
```

AI 会把你的代码整合到 references 文档中。

### 3.3 指定知识来源

告诉 AI 参考哪些文档：

```
腾讯云 COS 官方文档：
- Node.js SDK: https://cloud.tencent.com/document/product/436/8629
- JavaScript SDK: https://cloud.tencent.com/document/product/436/11459
```

AI 会参考这些文档生成更准确的内容。

### 3.4 迭代改进

Skill 不是一次写完就固定的。发现问题后继续对话：

```
刚才的 Skill 漏了"断点续传"的场景，帮我补充一下。
```

```
references/troubleshooting.md 里缺少"签名错误"的排查，加上。
```

---

## 四、实际效果演示

Skill 创建完成后，使用时是这样：

**场景 1：初次接入**

```
你：帮我接入腾讯云 COS
AI：（加载 auth.md）
    需要先获取密钥。你是开发环境还是生产环境？
你：开发环境
AI：访问腾讯云 API 密钥管理，创建密钥...
```

**场景 2：遇到问题**

```
你：COS 跨域报错了
AI：（加载 troubleshooting.md）
    这是跨域配置问题。进入存储桶 → 基础配置 → 跨域访问 CORS 设置...
```

**场景 3：进阶功能**

```
你：生成一个有时效的下载链接
AI：（加载 advanced.md）
    使用签名 URL。代码如下...
```

---

## 五、两种创建方式对比

Claude Code 提供两种 Skill 创建方式：

| 维度 | skill-creator（对话式） | writing-skills（TDD 式） |
|------|------------------------|------------------------|
| 来源 | Claude 官方插件 | Superpowers 社区 |
| 核心理念 | 描述需求 → 生成 → 测试 → 迭代 | 先写失败测试 → 再写 Skill → 验证通过 |
| 学习成本 | 低，直接描述需求 | 高，需要理解 TDD 流程 |
| 时间投入 | 10-20 分钟 | 1-2 小时 |
| 测试方式 | 对比有/无 Skill 的输出 | 压力场景测试，观察 AI 行为 |
| 适用场景 | 知识库、API 集成、工作流程 | 纪律执行、规则强制、行为约束 |

**skill-creator 适用场景**：
- 接入第三方服务（支付、短信、存储、地图等）
- 固定工作流程（代码审查、部署流程、故障排查）
- 知识库类需求（API 参考、最佳实践）

**writing-skills 适用场景**：
- 需要强制 AI 遵守特定规则（如 TDD、代码审查）
- 需要防止 AI 在压力下"偷懒"或"走捷径"
- 需要验证 AI 行为的可预测性

---

## 六、开始创建你的第一个 Skill

现在就试试：

```
帮我创建一个 Skill，用于 [你的需求]。
触发场景是 [用户可能说的话]。
需要覆盖 [具体内容]。
```

AI 会引导你完成剩余步骤。

**记住**：Skill 的核心是让 AI 在正确的时机做正确的事。你只需要说清楚"什么时候"和"做什么"，剩下的交给 AI。
