# daily_report_agent.py
"""
AI Agent 示例：每日自动生成团队日报并推送到飞书

功能：
1. 从 GitHub 获取团队提交记录
2. 使用 Claude AI 整理成结构化日报
3. 推送到飞书/钉钉群

使用方法：
    # 设置环境变量
    export GITHUB_TOKEN="your_github_token"
    export GITHUB_REPO="owner/repo"  # 或直接修改下方 GITHUB_REPO
    export FEISHU_WEBHOOK="your_webhook_url"
    export ANTHROPIC_API_KEY="your_api_key"

    # 运行
    python daily_report_agent.py

依赖：
    pip install anthropic requests
"""

import os
import requests
from datetime import datetime, timedelta
from anthropic import Anthropic

# ========== 配置 ==========
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "your-org/your-repo")  # 格式: owner/repo
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")
DINGTALK_WEBHOOK = os.getenv("DINGTALK_WEBHOOK")  # 可选
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# AI 模型配置
CLAUDE_MODEL = "claude-sonnet-4-6-20250514"
MAX_COMMITS = 50  # 每次处理的最大提交数


# ========== 1. 数据收集 Agent ==========
def fetch_github_commits(since_date: str) -> list[dict]:
    """
    收集指定日期后的 GitHub 提交记录

    Args:
        since_date: ISO 格式日期字符串，如 "2024-01-01T00:00:00Z"

    Returns:
        提交记录列表
    """
    if not GITHUB_TOKEN:
        raise ValueError("请设置 GITHUB_TOKEN 环境变量")

    url = f"https://api.github.com/repos/{GITHUB_REPO}/commits"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    params = {
        "since": since_date,
        "per_page": MAX_COMMITS
    }

    print(f"   正在获取 {GITHUB_REPO} 的提交记录...")

    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()

    commits = response.json()
    print(f"   获取到 {len(commits)} 条提交")

    return commits


# ========== 2. AI 整理 Agent ==========
def summarize_commits(commits: list[dict]) -> str:
    """
    使用 Claude AI 整理提交记录，生成日报

    Args:
        commits: GitHub 提交记录列表

    Returns:
        Markdown 格式的日报内容
    """
    if not commits:
        return "今日无提交记录"

    if not CLAUDE_API_KEY:
        raise ValueError("请设置 ANTHROPIC_API_KEY 环境变量")

    # 提取关键信息
    commit_texts = []
    for c in commits[:MAX_COMMITS]:
        try:
            author = c["commit"]["author"]["name"]
            message = c["commit"]["message"].split("\n")[0].strip()
            sha = c["sha"][:7]

            # 跳过合并提交
            if message.startswith("Merge "):
                continue

            commit_texts.append(f"- [{sha}] {author}: {message}")
        except (KeyError, IndexError):
            continue

    if not commit_texts:
        return "今日无有效提交记录"

    raw_report = "\n".join(commit_texts)

    # 调用 Claude 生成结构化日报
    client = Anthropic(api_key=CLAUDE_API_KEY)

    prompt = f"""请将以下 Git 提交记录整理成团队日报。

要求：
1. 按成员分组
2. 归纳每人的工作内容（不要简单罗列，要总结归纳）
3. 突出重要变更（新功能、Bug修复、重构、文档更新等）
4. 在末尾添加统计信息
5. 输出 Markdown 格式，适合在飞书/钉钉中展示

提交记录：
{raw_report}
"""

    print("   正在调用 Claude AI 整理日报...")

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text


# ========== 3. 推送 Agent ==========
def push_to_feishu(report: str, date: str) -> bool:
    """
    推送到飞书群机器人

    Args:
        report: 日报内容
        date: 日期字符串

    Returns:
        是否推送成功
    """
    if not FEISHU_WEBHOOK:
        print("   ⚠️ 未设置 FEISHU_WEBHOOK，跳过飞书推送")
        return False

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"📅 团队日报 - {date}"},
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": report
                },
                {
                    "tag": "note",
                    "elements": [
                        {"tag": "plain_text", "content": "🤖 由 AI Agent 自动生成"}
                    ]
                }
            ]
        }
    }

    print("   正在推送到飞书...")

    response = requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)
    response.raise_for_status()

    result = response.json()
    if result.get("StatusCode") == 0:
        print(f"   ✅ 日报已推送到飞书")
        return True
    else:
        print(f"   ❌ 飞书推送失败: {result}")
        return False


def push_to_dingtalk(report: str, date: str) -> bool:
    """
    推送到钉钉群机器人

    Args:
        report: 日报内容
        date: 日期字符串

    Returns:
        是否推送成功
    """
    if not DINGTALK_WEBHOOK:
        print("   ⚠️ 未设置 DINGTALK_WEBHOOK，跳过钉钉推送")
        return False

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": f"团队日报 - {date}",
            "text": f"## 📅 团队日报 - {date}\n\n{report}\n\n---\n🤖 由 AI Agent 自动生成"
        }
    }

    print("   正在推送到钉钉...")

    response = requests.post(DINGTALK_WEBHOOK, json=payload, timeout=10)
    response.raise_for_status()

    result = response.json()
    if result.get("errcode") == 0:
        print(f"   ✅ 日报已推送到钉钉")
        return True
    else:
        print(f"   ❌ 钉钉推送失败: {result}")
        return False


# ========== 4. 主调度逻辑 ==========
def run_daily_report(target_date: str = None):
    """
    主函数：收集 -> 整理 -> 推送

    Args:
        target_date: 目标日期，格式 "YYYY-MM-DD"，默认昨天
    """
    # 计算日期
    if target_date:
        date = target_date
    else:
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print("=" * 50)
    print(f"🔄 开始生成 {date} 的日报...")
    print("=" * 50)

    try:
        # Step 1: 收集
        print("\n📥 Step 1: 收集提交记录...")
        commits = fetch_github_commits(f"{date}T00:00:00Z")

        # Step 2: AI 整理
        print("\n🤖 Step 2: AI 整理日报...")
        report = summarize_commits(commits)

        # Step 3: 推送
        print("\n📤 Step 3: 推送通知...")
        feishu_ok = push_to_feishu(report, date)
        dingtalk_ok = push_to_dingtalk(report, date)

        # 输出预览
        print("\n" + "=" * 50)
        print("📝 日报内容预览:")
        print("=" * 50)
        print(report)
        print("=" * 50)

        if feishu_ok or dingtalk_ok:
            print("\n✨ 日报生成并推送完成！")
        else:
            print("\n⚠️ 日报已生成，但未推送到任何平台")
            print("   请设置 FEISHU_WEBHOOK 或 DINGTALK_WEBHOOK 环境变量")

        return report

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI 驱动的团队日报生成器")
    parser.add_argument(
        "--date",
        help="目标日期，格式 YYYY-MM-DD，默认昨天",
        default=None
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只生成日报，不推送"
    )

    args = parser.parse_args()

    if args.dry_run:
        # 干跑模式：只输出，不推送
        date = args.date or (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        print(f"🔍 干跑模式：生成 {date} 的日报（不推送）\n")

        commits = fetch_github_commits(f"{date}T00:00:00Z")
        report = summarize_commits(commits)

        print("\n" + "=" * 50)
        print(report)
        print("=" * 50)
    else:
        run_daily_report(args.date)
