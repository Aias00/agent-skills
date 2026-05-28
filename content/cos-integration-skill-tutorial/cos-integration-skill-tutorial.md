# 从零开发 Claude Code Skill：以腾讯云 COS 集成为例

> 一个 Skill 让 AI 记住了所有接入细节，从此告别"挤牙膏"式对话。

**完整代码**：[GitHub - cos-integration-skill-tutorial](https://github.com/Aias00/agent-skills/tree/main/content/cos-integration-skill-tutorial)

---

你有没有经历过这样的对话：

```
用户：帮我接入腾讯云 COS 存储
AI：好的，腾讯云 COS 是对象存储服务...
用户：这些我知道，我需要具体的接入步骤
AI：首先注册账号，创建存储桶...
用户：账号和桶都有了，签名 URL 怎么生成？
AI：签名 URL 需要 SecretKey...
用户：这些我也配置了，跨域怎么配？分片上传怎么做？
```

每次接入第三方服务，都要经历这种"挤牙膏"式的对话。

问题的根源在于：AI 缺乏结构化的、可按需检索的知识。它要么泛泛介绍基础知识，要么等你一步步追问才能给出具体方案。

**Skills 可以彻底解决这个问题**——把接入知识按阶段组织好，AI 能够根据你的当前进度，自动加载对应的内容。

这篇文章，我们从零开发一个 `cos-integration` Skill，让它能够：

1. 识别你处于接入的哪个阶段（认证、基础操作、进阶功能、问题排查）
2. 按需加载对应文档，不一次性塞满上下文
3. 引导你完成完整接入流程，不遗漏任何关键配置

---

## 一、为什么用 Skill 而不是 CLAUDE.md

在动手之前，先想清楚一个问题：为什么不直接把这些知识写进项目的 CLAUDE.md？

两者有关键区别：

| 维度 | CLAUDE.md | Skill |
|------|-----------|-------|
| 加载时机 | 每次对话都加载 | 按需调用 |
| 内容性质 | 项目规范、约定 | 工作流程、知识库 |
| 上下文占用 | 始终占用 | 用完即释放 |
| 适用范围 | 单项目 | 可跨项目复用 |

腾讯云 COS 的接入知识有明显特点：
- 不是每个项目都需要
- 不同项目可能处于不同接入阶段
- 文档内容较长（涵盖认证、API、跨域、分片上传等多个主题）

**结论**：这类知识做成 Skill 更合适，按需加载，不浪费上下文。

---

## 二、Skill 目录结构

一个完整的 Skill 通常包含：

```
cos-integration/
├── SKILL.md              # 主入口：工作流定义、路由逻辑
└── references/           # 参考文档（按需加载）
    ├── auth.md           # 认证配置
    ├── basics.md         # 基础操作
    ├── advanced.md       # 进阶功能
    └── troubleshooting.md # 常见问题
```

**设计原则**：
- `SKILL.md` 负责判断用户阶段、路由到对应文档
- `references/` 目录按主题拆分，每个文件独立可读
- AI 不会一次性加载所有文档，而是按需读取

---

## 三、编写 SKILL.md 主入口

`SKILL.md` 是 Skill 的入口文件，包含 frontmatter 元信息和工作流定义。

### 3.1 Frontmatter 配置

```markdown
---
name: cos-integration
description: 腾讯云 COS 对象存储接入指南。Use when the user asks to 接入 COS、腾讯云存储、对象存储、上传文件到 COS、COS 签名、COS 跨域配置。
allowed-tools: Read, Write, Bash, WebFetch
---
```

**关键字段解析**：

- `name`：Skill 调用名称，用户可以通过 `/cos-integration` 直接触发
- `description`：描述触发条件，AI 会根据这个判断何时调用。**必须包含中英文关键词**
- `allowed-tools`：限制 Skill 可使用的工具，避免过度权限

### 3.2 工作流定义

```markdown
# 腾讯云 COS 接入指南

引导完成腾讯云 COS 对象存储的接入，从认证配置到高级功能。

## When To Use

- "帮我接入腾讯云 COS"
- "COS 上传文件怎么写"
- "生成 COS 签名 URL"
- "COS 跨域报错怎么配"
- "大文件分片上传"

## Workflow

```text
COS Integration Flow:
- [ ] Step 1: 判断当前阶段
- [ ] Step 2: 按需加载参考文档
- [ ] Step 3: 提供具体指导或代码
- [ ] Step 4: 确认配置正确性
```

### Step 1: 判断当前阶段

通过对话或代码检查，判断用户处于哪个阶段：

| 阶段 | 特征 |
|------|------|
| 初始化 | 没有配置过 COS，需要创建存储桶、获取密钥 |
| 基础集成 | 已有配置，需要上传/下载代码 |
| 进阶功能 | 基础功能已通，需要签名 URL、分片上传等 |
| 问题排查 | 遇到跨域、权限、限流等问题 |

### Step 2: 按需加载参考文档

根据阶段加载对应文档：

- 初始化 → 加载 `references/auth.md`
- 基础集成 → 加载 `references/basics.md`
- 进阶功能 → 加载 `references/advanced.md`
- 问题排查 → 加载 `references/troubleshooting.md`

**加载方式**：使用 Read 工具读取对应文件。

### Step 3: 提供具体指导或代码

根据加载的文档内容，提供：
- 配置步骤
- 示例代码
- 注意事项

### Step 4: 确认配置正确性

- 是否配置了正确的权限
- 是否处理了错误情况
- 是否遵循最佳实践

## References

按需加载，不要一次性全部读取：

- [references/auth.md](references/auth.md) — 认证配置
- [references/basics.md](references/basics.md) — 基础操作
- [references/advanced.md](references/advanced.md) — 进阶功能
- [references/troubleshooting.md](references/troubleshooting.md) — 常见问题
```

**设计要点**：

1. **Workflow 分步骤**：清晰的流程引导，而非堆砌文档
2. **阶段判断表**：帮助 AI 快速定位用户状态
3. **References 列表**：明确告知 AI 要按需加载

---

## 四、编写 references 文档

references 目录存放具体知识，每个文件聚焦一个主题。

### 4.1 auth.md — 认证配置

这个文件回答"如何配置 COS 认证"的问题：

```markdown
# COS 认证配置

## 前置条件

1. 腾讯云账号，已完成实名认证
2. 开通 COS 服务

## 获取密钥

### 方式一：永久密钥（开发/测试环境）

1. 访问腾讯云 API 密钥管理
2. 创建密钥，获取 SecretId 和 SecretKey
3. 配置环境变量：

```bash
# .env
COS_SECRET_ID=your-secret-id
COS_SECRET_KEY=your-secret-key
```

### 方式二：临时密钥（生产环境推荐）

通过 STS 服务获取临时密钥，有效期可控：

```javascript
// 后端生成临时密钥
const STS = require('qcloud-cos-sts');

STS.getCredential({
  secretId: process.env.COS_SECRET_ID,
  secretKey: process.env.COS_SECRET_KEY,
  policy: {
    version: '2.0',
    statement: [{
      action: ['name/cos:PutObject', 'name/cos:GetObject'],
      effect: 'allow',
      resource: ['qcs::cos:ap-guangzhou:uid/1250000000:examplebucket-1250000000/*']
    }]
  },
  durationSeconds: 3600 // 有效期 1 小时
}, (err, data) => {
  if (err) return console.error(err);
  // data.credentials.tmpSecretId
  // data.credentials.tmpSecretKey
  // data.credentials.sessionToken
});
```

## 创建存储桶

1. 访问 COS 控制台
2. 创建存储桶，选择地域和访问权限
3. 记录存储桶名称和地域

## SDK 初始化

### Node.js

```bash
npm install cos-nodejs-sdk-v5
```

```javascript
const COS = require('cos-nodejs-sdk-v5');

const cos = new COS({
  SecretId: process.env.COS_SECRET_ID,
  SecretKey: process.env.COS_SECRET_KEY
});
```

### 浏览器端

```javascript
import COS from 'cos-js-sdk-v5';

const cos = new COS({
  getAuthorization: async (options, callback) => {
    // 从后端获取临时密钥
    const res = await fetch('/api/cos-credential');
    const { credentials } = await res.json();
    callback({
      TmpSecretId: credentials.tmpSecretId,
      TmpSecretKey: credentials.tmpSecretKey,
      SecurityToken: credentials.sessionToken,
      StartTime: credentials.startTime,
      ExpiredTime: credentials.expiredTime
    });
  }
});
```

## 安全建议

- 永远不要在前端暴露永久密钥
- 生产环境必须使用临时密钥
- 按"最小权限"原则配置 STS policy
- 定期轮换密钥
```

### 4.2 basics.md — 基础操作

上传、下载、删除、列表操作：

```markdown
# COS 基础操作

## 上传文件

### 简单上传（< 5MB）

```javascript
cos.putObject({
  Bucket: 'examplebucket-1250000000',
  Region: 'ap-guangzhou',
  Key: 'uploads/avatar.jpg',
  Body: file,
  onProgress: (progressData) => {
    console.log(`进度: ${Math.round(progressData.percent * 100)}%`);
  }
}, (err, data) => {
  if (err) {
    console.error('上传失败:', err);
    return;
  }
  console.log('文件地址:', `https://${data.Location}`);
});
```

### 下载文件

```javascript
cos.getObject({
  Bucket: 'examplebucket-1250000000',
  Region: 'ap-guangzhou',
  Key: 'uploads/avatar.jpg'
}, (err, data) => {
  if (err) return console.error('下载失败:', err);
  // data.Body 是文件内容
});
```

### 删除文件

```javascript
cos.deleteObject({
  Bucket: 'examplebucket-1250000000',
  Region: 'ap-guangzhou',
  Key: 'uploads/avatar.jpg'
}, (err) => {
  if (err) console.error('删除失败:', err);
});
```

### 列出文件

```javascript
cos.getBucket({
  Bucket: 'examplebucket-1250000000',
  Region: 'ap-guangzhou',
  Prefix: 'uploads/'
}, (err, data) => {
  if (err) return console.error(err);
  data.Contents.forEach(item => {
    console.log(item.Key, item.Size);
  });
});
```

## 文件路径设计建议

```
uploads/
├── avatars/
│   └── {user_id}.jpg
├── documents/
│   └── {date}/{uuid}.pdf
└── temp/
    └── {timestamp}_{random}.tmp
```

- 使用有意义的目录前缀
- 避免文件名冲突（UUID / 时间戳）
- 临时文件单独目录，定期清理
```

### 4.3 advanced.md — 进阶功能

签名 URL、分片上传、批量操作：

```markdown
# COS 进阶功能

## 签名 URL（临时访问链接）

适用场景：生成有时限的文件访问链接，无需暴露密钥。

```javascript
cos.getObjectUrl({
  Bucket: 'examplebucket-1250000000',
  Region: 'ap-guangzhou',
  Key: 'private/report.pdf',
  Sign: true,
  Expires: 3600 // 1小时有效
}, (err, data) => {
  if (err) return console.error(err);
  console.log('临时访问链接:', data.Url);
});
```

**使用场景**：
- 私有文件分享
- 下载链接有效期控制
- 避免文件被永久公开

## 分片上传（大文件）

SDK 提供 `uploadFile` 方法，自动判断是否需要分片上传（默认 > 1MB 分片）：

```javascript
cos.uploadFile({
  Bucket: 'examplebucket-1250000000',
  Region: 'ap-guangzhou',
  Key: 'videos/demo.mp4',
  FilePath: '/local/path/demo.mp4', // Node.js：本地文件路径
  // Body: file, // 浏览器端：File 对象
  SliceSize: 1024 * 1024 * 5, // 超过 5MB 启用分片上传
  onProgress: (progressData) => {
    console.log(`上传进度: ${Math.round(progressData.percent * 100)}%`);
  }
}, (err, data) => {
  if (err) console.error('上传失败:', err);
  else console.log('文件地址:', `https://${data.Location}`);
});
```

**断点续传**：分片上传支持中断后继续，SDK 自动记录进度。

**Node.js 与浏览器端区别**：
- Node.js：使用 `FilePath` 指定本地文件路径
- 浏览器端：使用 `Body` 传入 File 对象

## 文件元数据

```javascript
cos.putObject({
  Bucket: 'examplebucket-1250000000',
  Region: 'ap-guangzhou',
  Key: 'images/photo.jpg',
  Body: file,
  Headers: {
    'x-cos-meta-author': '张三',
    'Cache-Control': 'max-age=31536000'
  }
}, callback);
```
```

### 4.4 troubleshooting.md — 常见问题

跨域、权限、限流等问题的排查：

```markdown
# COS 常见问题排查

## 跨域错误（CORS）

**错误表现**：
```
Access to XMLHttpRequest has been blocked by CORS policy
```

**解决方案**：

在 COS 控制台配置跨域规则：

1. 进入存储桶 → 基础配置 → 跨域访问 CORS 设置
2. 添加规则：
   - 来源 Origin：`https://yourdomain.com`
   - 操作 Methods：GET, PUT, POST, DELETE, HEAD
   - Allow-Headers：`*`
   - Expose-Headers：`ETag, x-cos-request-id`
   - 超时 Max-Age：`3600`

**注意**：配置后需等待几分钟生效。

## 权限不足（403 Access Denied）

**原因**：
- SecretKey 错误或过期
- 存储桶权限配置错误
- 临时密钥权限范围不足

**排查步骤**：

1. 检查密钥是否正确
2. 检查存储桶访问权限（私有/公有）
3. 检查临时密钥的 policy 是否包含所需 action

## 文件上传成功但无法访问

**原因**：文件权限问题

**解决**：上传时指定 ACL

```javascript
cos.putObject({
  Bucket: 'examplebucket-1250000000',
  Region: 'ap-guangzhou',
  Key: 'public/avatar.jpg',
  Body: file,
  ACL: 'public-read' // 公有读
}, callback);
```

## 上传超时

**原因**：文件过大或网络不稳定

**解决**：
- 使用分片上传
- 增加超时时间

```javascript
const cos = new COS({
  Timeout: 60000 // 60秒
});
```

## 限流（503 Slow Down）

**原因**：请求频率超过限制

**解决**：
- 实现请求队列
- 添加重试逻辑

```javascript
async function uploadWithRetry(params, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      return await cos.putObject(params).promise();
    } catch (err) {
      if (err.statusCode === 503 && i < retries - 1) {
        await new Promise(r => setTimeout(r, 1000 * (i + 1)));
        continue;
      }
      throw err;
    }
  }
}
```
```

---

## 五、安装与使用

Skill 写好后，需要安装到 Claude Code 才能使用。

### 5.1 安装方式

**方式一：项目级安装**

将 `cos-integration` 目录放在项目的 `.claude/skills/` 下：

```
your-project/
└── .claude/
    └── skills/
        └── cos-integration/
            ├── SKILL.md
            └── references/
```

**方式二：全局安装**

放到 `~/.claude/skills/` 目录：

```
~/.claude/skills/
└── cos-integration/
    ├── SKILL.md
    └── references/
```

**方式三：符号链接**

如果你在多个项目间复用 Skill：

```bash
ln -s /path/to/cos-integration ~/.claude/skills/cos-integration
```

### 5.2 使用方式

安装完成后，在 Claude Code 中直接使用：

```
# 直接触发
/cos-integration

# 自然语言触发
"帮我接入腾讯云 COS"
"COS 跨域报错怎么配"
"生成一个 COS 签名 URL"
```

AI 会自动：
1. 判断你处于哪个阶段
2. 加载对应的参考文档
3. 提供具体的代码和配置

---

## 六、最佳实践总结

开发这个 Skill 的过程中，有几个关键经验：

### 6.1 知识分层原则

把知识分层，不要全部塞进一个文件：

| 层级 | 内容 | 加载时机 |
|------|------|---------|
| SKILL.md | 工作流、路由逻辑 | 始终加载 |
| auth.md | 认证配置 | 初始化阶段 |
| basics.md | 基础操作 | 基础集成阶段 |
| advanced.md | 进阶功能 | 进阶功能阶段 |
| troubleshooting.md | 问题排查 | 遇到问题时 |

### 6.2 触发词设计

`description` 字段要覆盖用户可能的表达方式：

```yaml
description: 腾讯云 COS 对象存储接入指南。Use when the user asks to 接入 COS、腾讯云存储、对象存储、上传文件到 COS、COS 签名、COS 跨域配置。
```

- 中文名称：腾讯云 COS、腾讯云存储
- 通用术语：对象存储、上传文件
- 具体操作：签名、跨域配置

### 6.3 阶段判断逻辑

在 SKILL.md 中明确阶段判断标准，帮助 AI 快速定位：

```markdown
| 阶段 | 特征 |
|------|------|
| 初始化 | 没有配置过 COS，需要创建存储桶、获取密钥 |
| 基础集成 | 已有配置，需要上传/下载代码 |
| 进阶功能 | 基础功能已通，需要签名 URL、分片上传等 |
| 问题排查 | 遇到跨域、权限、限流等问题 |
```

### 6.4 保持文档独立可读

每个 reference 文件应该独立可读，不依赖其他文件：

- 包含完整的代码示例
- 包含必要的上下文说明
- 包含常见问题解答

---

## 七、扩展思路

这个 Skill 还可以继续扩展：

**增加更多云服务商**：

```
cos-integration/
├── SKILL.md
└── references/
    ├── tencent-cos/
    │   ├── auth.md
    │   ├── basics.md
    │   └── ...
    ├── aliyun-oss/
    │   ├── auth.md
    │   ├── basics.md
    │   └── ...
    └── qiniu/
        └── ...
```

**增加最佳实践**：

- 文件命名规范
- 权限模型设计
- 成本优化策略
- 监控告警配置

**增加代码模板**：

- NestJS 集成模板
- Next.js 集成模板
- 小程序集成模板

---

## 总结

这篇文章我们从零开发了一个腾讯云 COS 集成 Skill，核心思路是：

1. **知识分层**：SKILL.md 负责路由，references 负责具体知识
2. **按需加载**：根据用户阶段加载对应文档，不浪费上下文
3. **阶段判断**：明确定义各阶段特征，帮助 AI 快速定位

这个模式可以复用到其他第三方服务集成：
- 支付服务（微信支付、支付宝）
- 短信服务（阿里云、腾讯云）
- 地图服务（高德、百度）
- AI 服务（OpenAI、通义千问）

**Skills 让 AI 记住了所有接入细节，从此告别"挤牙膏"式对话。**
