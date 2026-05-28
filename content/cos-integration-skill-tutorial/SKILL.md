---
name: cos-integration
description: 腾讯云 COS 对象存储接入指南。Use when the user asks to 接入 COS、腾讯云存储、对象存储、上传文件到 COS、COS 签名、COS 跨域配置、COS 分片上传。
allowed-tools: Read, Write, Bash, WebFetch
---

# 腾讯云 COS 接入指南

引导完成腾讯云 COS 对象存储的接入，从认证配置到高级功能。

## When To Use

- "帮我接入腾讯云 COS"
- "COS 上传文件怎么写"
- "生成 COS 签名 URL"
- "COS 跨域报错怎么配"
- "大文件分片上传"
- "COS 临时密钥怎么获取"

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

加载方式：使用 Read 工具读取对应文件。

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

## Installation

将此 Skill 目录放到项目的 `.claude/skills/` 或全局 `~/.claude/skills/` 目录下。

```bash
# 项目级
cp -r cos-integration /path/to/your-project/.claude/skills/

# 全局
cp -r cos-integration ~/.claude/skills/
```

然后可以通过 `/cos-integration` 或自然语言触发。
