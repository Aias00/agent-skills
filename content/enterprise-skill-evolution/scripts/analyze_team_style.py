#!/usr/bin/env python3
"""
analyze_team_style.py - 分析团队代码风格和协作模式

用法：
    python analyze_team_style.py --repo /path/to/repo --since "3 months ago"
    python analyze_team_style.py --repo . --output team-style.json
"""

import subprocess
import argparse
import json
import re
from pathlib import Path
from collections import Counter
from datetime import datetime

def run_git_command(cmd, cwd="."):
    """执行 Git 命令"""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        shell=True
    )
    return result.stdout.strip()

def analyze_commit_messages(since="3 months ago"):
    """分析提交消息模式"""
    cmd = f'git log --since="{since}" --pretty=format:"%s"'
    output = run_git_command(cmd)
    messages = output.split("\n") if output else []

    # 提取前缀模式（如 feat:, fix:, docs:）
    prefixes = Counter()
    for msg in messages:
        match = re.match(r'^(\w+)(\(|:)', msg)
        if match:
            prefixes[match.group(1)] += 1

    # 提取常见关键词
    keywords = Counter()
    keyword_patterns = [
        r'fix', r'add', r'update', r'remove', r'refactor',
        r'test', r'doc', r'优化', r'修复', r'新增', r'删除'
    ]
    for msg in messages:
        msg_lower = msg.lower()
        for pattern in keyword_patterns:
            if re.search(pattern, msg_lower):
                keywords[pattern] += 1

    return {
        "total_commits": len(messages),
        "prefix_patterns": dict(prefixes.most_common(10)),
        "keyword_frequency": dict(keywords.most_common(10))
    }

def analyze_branch_names():
    """分析分支命名模式"""
    cmd = "git branch -a --format='%(refname:short)'"
    output = run_git_command(cmd)
    branches = output.split("\n") if output else []

    patterns = Counter()
    for branch in branches:
        # 提取前缀（feature/, bugfix/, hotfix/）
        match = re.match(r'(feature|bugfix|hotfix|release|main|master|develop)', branch)
        if match:
            patterns[match.group(1)] += 1
        # 检查是否有 issue 编号
        if re.search(r'#?\d+', branch):
            patterns["with-issue-number"] += 1

    return dict(patterns)

def analyze_file_changes(since="3 months ago", top=20):
    """分析文件变更模式"""
    cmd = f'git log --since="{since}" --name-only --pretty=format:""'
    output = run_git_command(cmd)
    files = [f for f in output.split("\n") if f.strip()]

    # 文件类型分布
    extensions = Counter()
    for f in files:
        ext = Path(f).suffix
        if ext:
            extensions[ext] += 1

    # 热门文件
    file_freq = Counter(files)

    # 目录分布
    directories = Counter()
    for f in files:
        dir_name = str(Path(f).parent)
        if dir_name and dir_name != ".":
            directories[dir_name] += 1

    return {
        "file_types": dict(extensions.most_common(10)),
        "hot_files": dict(file_freq.most_common(top)),
        "hot_directories": dict(directories.most_common(10))
    }

def generate_team_skill(commit_analysis, branch_analysis, file_analysis):
    """生成团队风格 Skill"""
    skill = {
        "name": "team-style",
        "description": "团队代码风格和协作规范",
        "commit_conventions": commit_analysis.get("prefix_patterns", {}),
        "branch_conventions": branch_analysis,
        "hot_files": list(file_analysis.get("hot_files", {}).keys())[:10],
        "suggested_workflow": [
            "分支命名遵循: feature/xxx, bugfix/xxx, hotfix/xxx",
            "提交消息格式: type(scope): description",
            "变更前检查热门文件的依赖关系"
        ]
    }
    return skill

def main():
    parser = argparse.ArgumentParser(description="分析团队代码风格")
    parser.add_argument("--repo", default=".", help="Git 仓库路径")
    parser.add_argument("--since", default="3 months ago", help="分析时间范围")
    parser.add_argument("--output", default="team-style.json", help="输出文件")
    args = parser.parse_args()

    print(f"📊 分析 {args.repo} 的团队风格...")

    commit_analysis = analyze_commit_messages(args.since)
    branch_analysis = analyze_branch_names()
    file_analysis = analyze_file_changes(args.since)

    team_skill = generate_team_skill(commit_analysis, branch_analysis, file_analysis)

    result = {
        "analysis_time": datetime.now().isoformat(),
        "time_range": args.since,
        "commit_analysis": commit_analysis,
        "branch_analysis": branch_analysis,
        "file_analysis": file_analysis,
        "team_skill": team_skill
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 分析完成！结果保存到 {args.output}")
    print(f"\n📈 团队风格摘要：")
    print(f"  - 提交数: {commit_analysis['total_commits']}")
    print(f"  - 提交前缀: {list(commit_analysis['prefix_patterns'].keys())[:5]}")
    print(f"  - 分支模式: {list(branch_analysis.keys())}")

if __name__ == "__main__":
    main()
