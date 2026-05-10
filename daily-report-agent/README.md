# AI 驱动的团队日报生成器

一个基于 Claude AI 的自动化日报工具，能够从 GitHub 提交记录自动生成结构化团队日报，并推送到飞书/钉钉群。

## 功能特点

- **智能整理**：使用 Claude AI 自动归纳整理提交记录
- **多平台支持**：支持推送到飞书、钉钉
- **灵活部署**：支持本地运行、GitHub Actions、云函数等多种方式
- **自动触发**：支持定时自动执行

## 快速开始

### 1. 安装依赖

```bash
pip install anthropic requests
```

### 2. 配置环境变量

```bash
# 必需
export GITHUB_TOKEN="your_github_token"        # GitHub Personal Access Token
export GITHUB_REPO="owner/repo"                # GitHub 仓库地址
export ANTHROPIC_API_KEY="your_api_key"        # Claude API Key

# 推送目标（至少设置一个）
export FEISHU_WEBHOOK="your_webhook_url"       # 飞书机器人 Webhook
export DINGTALK_WEBHOOK="your_webhook_url"     # 钉钉机器人 Webhook（可选）
```

### 3. 运行

```bash
# 生成昨天的日报
python daily_report_agent.py

# 生成指定日期的日报
python daily_report_agent.py --date 2024-01-15

# 干跑模式（只生成，不推送）
python daily_report_agent.py --dry-run
```

## 获取配置

### GitHub Token

1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 勾选 `repo` 权限
4. 复制保存

### Claude API Key

1. 访问 https://console.anthropic.com
2. 创建 API Key
3. 新用户有 $5 免费额度

### 飞书 Webhook

1. 打开飞书群 → 设置 → 群机器人 → 添加机器人
2. 选择"自定义机器人"
3. 复制 Webhook 地址

### 钉钉 Webhook

1. 打开钉钉群 → 设置 → 智能群助手 → 添加机器人
2. 选择"自定义"
3. 安全设置选择"自定义关键词"，添加"日报"
4. 复制 Webhook 地址

## GitHub Actions 部署

### 1. 添加 Secrets

进入你的 GitHub 仓库 → Settings → Secrets and variables → Actions，添加：

- `ANTHROPIC_API_KEY`：Claude API 密钥
- `FEISHU_WEBHOOK`：飞书机器人 Webhook（可选）
- `DINGTALK_WEBHOOK`：钉钉机器人 Webhook（可选）

> `GITHUB_TOKEN` 无需手动添加，GitHub Actions 自动提供

### 2. 启用 Workflow

将 `.github/workflows/daily-report.yml` 文件提交到仓库，Workflow 会自动：

- 每天 9:00（北京时间）自动执行
- 支持在 Actions 页面手动触发

### 3. 手动触发

进入 Actions → Daily Team Report → Run workflow，可指定日期运行。

## 成本估算

以 10 人团队为例：

| 项目 | 成本 |
|-----|------|
| Claude API | ~¥0.02/次 |
| GitHub Actions | 免费 |
| 飞书/钉钉 | 免费 |
| **月成本** | **<¥1** |

## 自定义

### 修改 Prompt

编辑 `daily_report_agent.py` 中的 `prompt` 变量，自定义日报格式：

```python
prompt = f"""请将以下 Git 提交记录整理成团队日报。

要求：
1. 按成员分组
2. 归纳每人的工作内容
3. 突出重要变更
4. 在末尾添加统计信息
5. 输出 Markdown 格式

提交记录：
{raw_report}
"""
```

### 支持其他平台

参考 `push_to_feishu` 和 `push_to_dingtalk` 函数，添加其他平台的推送逻辑。

## 本地验证

### 快速测试（无需 API Key）

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Mac/Linux
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 创建测试脚本
python3 << 'EOF'
from datetime import datetime, timedelta

# Mock 数据
MOCK_COMMITS = [
    {"sha": "abc1234", "commit": {"author": {"name": "张三"}, "message": "feat: 添加用户认证模块"}},
    {"sha": "def5678", "commit": {"author": {"name": "张三"}, "message": "fix: 修复登录样式"}},
    {"sha": "ghi9012", "commit": {"author": {"name": "李四"}, "message": "feat: 数据导出功能"}},
]

# 按作者分组
by_author = {}
for c in MOCK_COMMITS:
    author = c["commit"]["author"]["name"]
    message = c["commit"]["message"].split("\n")[0]
    sha = c["sha"][:7]
    if author not in by_author:
        by_author[author] = []
    by_author[author].append({"sha": sha, "message": message})

# 生成日报
print("## 📅 团队日报\n")
for author, commits in by_author.items():
    print(f"### 👤 {author}")
    for c in commits:
        print(f"- [{c['sha']}] {c['message']}")
    print()
print(f"**📊 统计**: {len(by_author)} 人提交")
EOF
```

### 完整测试（需要 API Key）

```bash
# 设置环境变量
export GITHUB_TOKEN="ghp_xxx"
export GITHUB_REPO="owner/repo"
export ANTHROPIC_API_KEY="sk-xxx"
export FEISHU_WEBHOOK="https://open.feishu.cn/xxx"  # 可选

# 干跑模式（只生成，不推送）
python daily_report_agent.py --dry-run

# 完整运行
python daily_report_agent.py

# 指定日期
python daily_report_agent.py --date 2024-01-15
```

## 常见问题

**Q: GitHub Actions 定时不准时怎么办？**

A: GitHub Actions 的 cron 可能有延迟。如果对时间敏感，建议：
- 使用云函数（阿里云函数计算、腾讯云 SCF）
- 或自建服务器 Cron

**Q: 如何支持私有仓库？**

A: GitHub Token 需要添加 `repo` 权限。

**Q: 如何支持 GitLab / Gitee？**

A: 修改 `fetch_github_commits` 函数的 API 地址：

```python
# GitLab
url = f"https://gitlab.com/api/v4/projects/{project_id}/repository/commits"

# Gitee
url = f"https://gitee.com/api/v5/repos/{owner}/{repo}/commits"
```

**Q: 运行时提示 `ModuleNotFoundError: No module named 'anthropic'`？**

A: 确保已安装依赖：
```bash
pip install -r requirements.txt
```

**Q: 飞书推送失败怎么办？**

A: 检查：
1. Webhook 地址是否正确
2. 机器人是否被移出群
3. 消息内容是否超过飞书限制（Markdown 最大 10000 字符）

**Q: 如何调试 GitHub Actions？**

A: 在 Workflow 中添加调试步骤：
```yaml
- name: Debug
  run: |
    echo "GITHUB_REPO: $GITHUB_REPO"
    echo "Commits found: $(ls -la)"
```

## 项目结构

```
daily-report-agent/
├── daily_report_agent.py      # 主程序
├── requirements.txt           # Python 依赖
├── README.md                  # 使用文档
└── .github/workflows/
    └── daily-report.yml       # GitHub Actions 配置
```

## License

MIT
