# Claude Code 自动化工作流实战 - 代码示例

这篇文章配套的完整代码示例：[Claude Code 自动化工作流实战：构建内容生产流水线](../claude-code-automation-workflow-advanced.md)

## 文件说明

### Hooks 配置

| 文件 | 说明 |
|------|------|
| `hooks-stop-auto-save.json` | Stop 钩子配置：会话结束时自动 Git 提交 |
| `hooks-pretooluse-file-log.json` | PreToolUse 钩子配置：文件修改时记录日志 |
| `conditional-hook.sh` | 条件触发脚本：在脚本内部判断目录类型 |

### MCP 配置

| 文件 | 说明 |
|------|------|
| `mcp-servers.json` | MCP server 配置示例：filesystem、brave-search 等 |

### Skills 文件

| 文件 | 说明 |
|------|------|
| `article-init-SKILL.md` | 创建新文章的 Skill |
| `article-process-SKILL.md` | 根据文章类型执行不同流程的 Skill |

### 自动化脚本

| 文件 | 说明 |
|------|------|
| `Makefile` | 完整流水线：审阅 → 格式化 → 封面 → 发布 |
| `parallel-format.sh` | 并行生成多平台 HTML |
| `retry.ts` | 带指数退避的重试封装 |
| `update-status.sh` | 更新文章 frontmatter 状态 |
| `logger.ts` | 结构化日志工具 |

## 快速使用

### 1. 复制配置文件

```bash
# Hooks 配置
cp code-examples/hooks-stop-auto-save.json ~/.claude/settings.json

# 或追加到现有配置
# 手动合并 JSON

# MCP 配置
cp code-examples/mcp-servers.json ~/.claude/settings.json
# 或手动合并
```

### 2. 安装 Skill

```bash
# 创建 skills 目录
mkdir -p ~/.claude/skills/article-init
mkdir -p ~/.claude/skills/article-process

# 复制 SKILL.md
cp code-examples/article-init-SKILL.md ~/.claude/skills/article-init/SKILL.md
cp code-examples/article-process-SKILL.md ~/.claude/skills/article-process/SKILL.md
```

### 3. 使用流水线脚本

```bash
# 复制 Makefile 到你的文章目录
cp code-examples/Makefile /path/to/your/articles/

# 运行
cd /path/to/your/articles/
make all ARTICLE=workspaces/my-article/my-article.md
```

## 依赖

这些脚本依赖 `agent-skills` 仓库中的其他工具：

- `technical-article-review` - 文章审阅
- `wechat-article-formatter` - Markdown 转 HTML
- `wechat-publisher` - 发布到微信公众号

详见 [主仓库](../../)。
