---
title: Claude Code 自动化工作流实战：构建内容生产流水线
description: 以内容生产为例，系统讲解 Hooks、MCP、Skills 三驾马车的组合使用，搭建从写作到发布的完整自动化链路。
github_code: https://github.com/Aias00/agent-skills/tree/main/content/claude-code-automation-workflow-advanced/code-examples
---

## 先说结论

Claude Code 的自动化能力由三驾马车构成：**Hooks** 负责事件触发，**MCP** 负责外部能力扩展，**Skills** 负责任务封装复用。理解它们的边界和组合方式，就能搭建出真正省心的自动化工作流。

这篇文章以一个真实场景——「从 Markdown 草稿到公众号发布」——为线索，给出完整可复制的配置文件和代码。**所有代码示例都在 [GitHub 仓库](https://github.com/Aias00/agent-skills/tree/main/content/claude-code-automation-workflow-advanced/code-examples) 中，可以直接下载使用。**

---

## 一、自动化工作流的三驾马车

很多同学问我：「我想让 Claude Code 自动帮我做事，到底该用 Hooks、MCP 还是 Skills？」

答案是：它们不是互斥的，而是各司其职。

### 1.1 Hooks：零成本的事件触发器

Hooks 是 Claude Code 的生命周期钩子。你不需要启动额外进程，只需要在 `settings.json` 里配置一下，Claude 就会在特定时机自动执行你的脚本。

**典型用途：**

| 钩子 | 触发时机 | 典型用途 |
|------|----------|----------|
| `PreToolUse` | 调用工具前 | 拦截危险命令、自动加参数 |
| `PostToolUse` | 调用工具后 | 记录日志、通知 |
| `Stop` | 会话结束时 | 自动保存、清理、汇总 |

**最简示例——会话结束时自动保存：**

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "git add . && git commit -m 'auto: save'"
          }
        ]
      }
    ]
  }
}
```

> 📦 **完整配置：** [`hooks-stop-auto-save.json`](https://github.com/Aias00/agent-skills/blob/main/content/claude-code-automation-workflow-advanced/code-examples/hooks-stop-auto-save.json)

**注意：** `Stop` 钩子不支持 matcher。只有 `PreToolUse` 和 `PostToolUse` 支持 matcher 来匹配工具名称。

**Hooks 的限制：**
- 只能「触发时执行」，无法持久化状态
- 无法访问 Claude 的内部上下文（比如对话历史）
- 脚本执行时间不宜过长（默认 60 秒超时）

### 1.2 MCP：给 Claude 装上外部能力的插件

MCP（Model Context Protocol）是 Anthropic 推出的标准化协议，让 Claude 能够访问外部数据和工具。

**典型用途：**

| MCP Server | 能力 |
|------------|------|
| `filesystem` | 读写本地文件（受限目录） |
| `postgres` | 查询 PostgreSQL 数据库 |
| `brave-search` | 网络搜索 |
| `puppeteer` | 浏览器自动化 |

**配置示例：**

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/you/articles"]
    }
  }
}
```

> 📦 **完整配置：** [`mcp-servers.json`](https://github.com/Aias00/agent-skills/blob/main/content/claude-code-automation-workflow-advanced/code-examples/mcp-servers.json)

**MCP 的成本：**
- 每个 MCP server 都是一个独立进程，占用内存
- 启动需要时间（几十毫秒到几秒）
- 需要额外的权限配置

### 1.3 Skills：可复用的任务封装

Skills 是把复杂的多步骤任务打包成可复用的模块。一个 Skill 就是一个目录，里面有一份 `SKILL.md` 文件描述任务流程。

**最小化 Skill 结构：**

```
~/.claude/skills/article-init/
├── SKILL.md          # 技能描述与执行步骤
├── scripts/          # 配套脚本（可选）
└── references/       # 参考文档（可选）
```

**SKILL.md 核心结构：**

```markdown
---
name: article-init
description: 从模板创建新文章
triggers:
  - "创建文章"
  - "新文章"
---

## 执行步骤
1. 询问用户文章主题和类型
2. 在 articles/workspaces/ 下创建目录
3. 从模板复制初始文件结构
...
```

> 📦 **完整示例：** [`article-init-SKILL.md`](https://github.com/Aias00/agent-skills/blob/main/content/claude-code-automation-workflow-advanced/code-examples/article-init-SKILL.md)

### 1.4 选型决策树

```
需要访问外部数据/工具？
├── 是 → 用 MCP
└── 否 → 只是触发时执行脚本？
         ├── 是 → 用 Hooks
         └── 否 → 多步骤任务需要复用？
                  ├── 是 → 用 Skills
                  └── 否 → 直接对话就够了
```

**三者可以组合使用：**
- Hook 触发 Skill 执行（会话结束时自动审阅）
- Skill 内部调用 MCP（审阅时查询数据库）
- MCP 结果触发 Hook（查询完成后发送通知）

---

## 二、场景拆解：内容生产的四个阶段

自动化不是「一个指令搞定所有」。越是复杂的流程，越需要拆解。

### 2.1 拆解原则

好的拆解要满足三个条件：
1. **清晰的输入输出**——每个阶段接收什么、产出什么，一目了然
2. **可独立调试**——出了问题能快速定位是哪个阶段
3. **可灵活组合**——今天只自动化两个阶段，明天再加一个，互不影响

### 2.2 四阶段流程图

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   写作      │───▶│   审阅      │───▶│   格式化    │───▶│   发布      │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      │                  │                  │                  │
      ▼                  ▼                  ▼                  ▼
 灵感/素材          Markdown草稿       审阅报告+修订稿      多平台HTML       文章链接
```

### 2.3 各阶段详解

| 阶段 | 输入 | 输出 | 自动化点 | 现有工具 |
|------|------|------|----------|----------|
| 写作 | 灵感、素材 | Markdown 草稿 | 自动保存、版本管理 | `article-init`（需创建） |
| 审阅 | Markdown 草稿 | 审阅报告 + 修订稿 | 技术检查、禁用词扫描 | `technical-article-review` |
| 格式化 | 修订后的 Markdown | 平台适配的 HTML | MD→HTML、主题注入 | `wechat-article-formatter` |
| 发布 | HTML + 封面图 | 文章链接 | 封面生成、API 推送 | `wechat-publisher` |

---

## 三、实战：搭建文章生产流水线

### 3.1 环境准备

```bash
# 格式化工具
cd wechat-article-formatter
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 发布工具
cd ../wechat-publisher
bun install
bun scripts/bootstrap-local.ts --project-root ..
```

### 3.2 写作阶段：自动保存与版本管理

**Hook 配置——会话结束时自动提交：**

```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "cd /path/to/articles && git add . && git commit -m 'auto: save' 2>/dev/null || true"
      }]
    }]
  }
}
```

**踩坑：**
- `Stop` 钩子不支持 matcher，所有会话结束都会触发
- `2>/dev/null || true` 防止「没有变更」时报错
- 需要条件判断时，把逻辑放在脚本里（见 [`conditional-hook.sh`](https://github.com/Aias00/agent-skills/blob/main/content/claude-code-automation-workflow-advanced/code-examples/conditional-hook.sh)）

### 3.3 审阅阶段：质量检查流水线

```bash
# 在 Claude Code 中直接调用
> 用 technical-article-review 审阅 articles/workspaces/my-article/my-article.md

# 或运行禁用词检查脚本
python3 ../technical-article-review/scripts/check_banned_scaffolding.py --input article.md
```

**踩坑：**
- `technical-article-review` 默认会直接修改文章，说「只审不改」或 `review-only` 可只看报告
- 禁用词检查会自动排除代码块和引用块

### 3.4 格式化阶段：一键生成 HTML

```bash
wechat-article-formatter/.venv/bin/python \
  wechat-article-formatter/scripts/markdown_to_html.py \
  --input article.md \
  --theme mist-blue \
  --preview
```

**可用主题：** `mist-blue`（默认）、`ai-tech`、`tech-blue`、`forest-green`、`sunset`、`slate`、`midnight`、`warm-orange`

### 3.5 发布阶段：封面生成与 API 推送

```bash
# 生成封面
python3 ../wechat-publisher/scripts/generate-cover-image.py \
  --markdown article.md \
  --out imgs/cover.png \
  --bootstrap-pillow

# 发布
cd ../wechat-publisher
bun scripts/wechat-publish.ts article.md --dry-run  # 预览
bun scripts/wechat-publish.ts article.md            # 正式发布
```

### 3.6 完整流水线脚本

用一个 Makefile 把所有步骤串起来：

```makefile
ARTICLE ?= articles/workspaces/my-article/my-article.md

review:
	python3 ../technical-article-review/scripts/check_banned_scaffolding.py --input $(ARTICLE)

format:
	../wechat-article-formatter/.venv/bin/python \
		../wechat-article-formatter/scripts/markdown_to_html.py \
		--input $(ARTICLE) --theme mist-blue

cover:
	python3 ../wechat-publisher/scripts/generate-cover-image.py \
		--markdown $(ARTICLE) --out $(dir $(ARTICLE))imgs/cover.png

publish: review format cover
	cd ../wechat-publisher && bun scripts/wechat-publish.ts ../content/$(ARTICLE)
```

> 📦 **完整 Makefile：** [`Makefile`](https://github.com/Aias00/agent-skills/blob/main/content/claude-code-automation-workflow-advanced/code-examples/Makefile)

**使用方式：**

```bash
make all ARTICLE=articles/workspaces/my-article/my-article.md
make publish ARTICLE=articles/workspaces/my-article/my-article.md
```

---

## 四、进阶模式

### 4.1 并行执行多个任务

同时生成微信、头条、博客三个平台的 HTML：

```bash
#!/bin/bash
# 并行执行
format-article "$ARTICLE" --theme mist-blue --output wechat.html &
format-article "$ARTICLE" --theme tech-blue --output toutiao.html &
format-article "$ARTICLE" --theme forest --output blog.html &
wait
```

> 📦 **完整脚本：** [`parallel-format.sh`](https://github.com/Aias00/agent-skills/blob/main/content/claude-code-automation-workflow-advanced/code-examples/parallel-format.sh)

### 4.2 错误恢复与重试

```typescript
const result = await withRetry(
  () => publishToWechat(article),
  { maxRetries: 3, baseDelayMs: 1000, name: '发布到微信' }
);
```

> 📦 **完整实现：** [`retry.ts`](https://github.com/Aias00/agent-skills/blob/main/content/claude-code-automation-workflow-advanced/code-examples/retry.ts)

**踩坑：**
- 重试次数 3 次足够
- 指数退避（每次延迟翻倍）比固定延迟更友好
- 确保操作是幂等的

### 4.3 条件分支

`Stop` 钩子不支持 matcher，条件判断放在脚本内部：

```bash
#!/bin/bash
if [[ "$CLAUDE_PROJECT_DIR" == *"articles/workspaces"* ]]; then
  # 执行文章相关操作
  make review
fi
```

> 📦 **完整脚本：** [`conditional-hook.sh`](https://github.com/Aias00/agent-skills/blob/main/content/claude-code-automation-workflow-advanced/code-examples/conditional-hook.sh)

### 4.4 状态管理

用 frontmatter 记录文章状态：

```yaml
---
title: 我的文章
status: draft      # draft → reviewing → ready → published
type: tech
created: 2024-01-15
---
```

> 📦 **状态更新脚本：** [`update-status.sh`](https://github.com/Aias00/agent-skills/blob/main/content/claude-code-automation-workflow-advanced/code-examples/update-status.sh)

### 4.5 监控与日志

```typescript
log({
  level: 'info',
  stage: 'format',
  message: '格式化完成',
  duration: 1500,
});
```

> 📦 **完整实现：** [`logger.ts`](https://github.com/Aias00/agent-skills/blob/main/content/claude-code-automation-workflow-advanced/code-examples/logger.ts)

---

## 五、踩坑经验与最佳实践

### 5.1 配置调试技巧

| 问题 | 排查方法 |
|------|----------|
| Hook 不触发 | `cat ~/.claude/settings.json \| python3 -m json.tool` 验证 JSON |
| MCP 连不上 | `npx @modelcontextprotocol/server-filesystem /path` 独立启动测试 |
| Skill 无响应 | 确认文件位置：`ls ~/.claude/skills/my-skill/SKILL.md` |

### 5.2 常见错误排查

| 错误现象 | 可能原因 | 解决方案 |
|----------|----------|----------|
| Hook 不执行 | JSON 格式错误 | `python3 -m json.tool` 验证 |
| MCP 超时 | 进程未启动 | 重启 Claude Code |
| Skill 无响应 | 触发词不匹配 | 检查 SKILL.md 中的 triggers |
| 脚本权限错误 | 缺少执行权限 | `chmod +x script.sh` |
| API 调用失败 | 权限不足 | 运行 `check-permissions.ts` |

### 5.3 安全注意事项

```json
// 不好：硬编码 API Key
"env": { "API_KEY": "sk-xxxxx" }

// 好：使用环境变量
"env": { "API_KEY": "${MY_API_KEY}" }
```

### 5.4 渐进式自动化建议

**建议顺序：**
1. 先自动化最频繁、最机械的步骤（格式化、封面生成）
2. 再自动化需要人工复核的步骤（审阅、检查）
3. 最后自动化跨阶段编排（完整流水线）

**何时停止自动化：**
- 边际收益递减：调试时间 > 节省时间
- 灵活性下降：每次调整都要改配置
- 维护成本过高：配置比实际工作还复杂

---

## 总结

Claude Code 的自动化工作流，核心是理解三驾马车的边界：

- **Hooks**：轻量级事件触发，适合「在某个时机自动执行脚本」
- **MCP**：外部能力扩展，适合「让 Claude 访问数据或工具」
- **Skills**：任务封装复用，适合「复杂多步骤流程」

组合使用，就能搭建出真正省心的自动化流水线。

**所有代码示例都在 GitHub 仓库：** [code-examples/](https://github.com/Aias00/agent-skills/tree/main/content/claude-code-automation-workflow-advanced/code-examples)

照着抄作业，再根据自己的需求调整，就能跑起来。
