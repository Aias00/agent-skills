#!/usr/bin/env python3
"""
analyze_team_style_v2.py - 深度分析团队代码风格和协作模式

改进：
1. 分析提交内容的语义模式
2. 分析文件变更关联性
3. 分析代码风格规范
4. 生成可执行的团队 Skill 内容

用法：
    python analyze_team_style_v2.py --repo /path/to/repo --since "3 months ago"
    python analyze_team_style_v2.py --repo . --output team-style.json --report
"""

import subprocess
import argparse
import json
import re
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Optional

def run_git_command(cmd: str, cwd: str = ".") -> str:
    """执行 Git 命令"""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        shell=True
    )
    return result.stdout.strip()

def analyze_commit_messages(since: str = "3 months ago") -> Dict:
    """深度分析提交消息模式"""
    cmd = f'git log --since="{since}" --pretty=format:"%s%n%b%n---COMMIT_END---"'
    output = run_git_command(cmd)
    commits = output.split("---COMMIT_END---")

    # 提交前缀统计
    prefixes = Counter()
    # 提交类型分布
    commit_types = Counter()
    # 提交范围统计
    scopes = Counter()
    # 关键词统计
    keywords = Counter()
    # 提交消息长度统计
    message_lengths = []
    # 是否有 Breaking Change
    breaking_changes = 0
    # 是否有 Issue 引用
    issue_refs = 0

    keyword_patterns = [
        (r'\bfix\b', 'fix'),
        (r'\badd\b', 'add'),
        (r'\bupdate\b', 'update'),
        (r'\bremove\b', 'remove'),
        (r'\bdelete\b', 'delete'),
        (r'\brefactor\b', 'refactor'),
        (r'\bimprove\b', 'improve'),
        (r'\boptimize\b', 'optimize'),
        (r'\btest\b', 'test'),
        (r'\bdoc\b', 'doc'),
        (r'\b修复\b', 'fix_cn'),
        (r'\b新增\b', 'add_cn'),
        (r'\b更新\b', 'update_cn'),
        (r'\b删除\b', 'delete_cn'),
        (r'\b优化\b', 'optimize_cn'),
    ]

    for commit in commits:
        commit = commit.strip()
        if not commit:
            continue

        lines = commit.split('\n')
        subject = lines[0] if lines else ""

        # 解析提交前缀 (type(scope): description)
        match = re.match(r'^(\w+)(\([^)]+\))?:', subject)
        if match:
            prefix = match.group(1)
            scope = match.group(2)
            prefixes[prefix] += 1
            commit_types[prefix] += 1
            if scope:
                scopes[scope] += 1

        # 统计关键词
        subject_lower = subject.lower()
        for pattern, keyword in keyword_patterns:
            if re.search(pattern, subject_lower):
                keywords[keyword] += 1

        # 统计消息长度
        message_lengths.append(len(subject))

        # 检查 Breaking Change
        if '!' in subject or 'BREAKING CHANGE' in commit:
            breaking_changes += 1

        # 检查 Issue 引用
        if re.search(r'#\d+', commit):
            issue_refs += 1

    return {
        "total_commits": len([c for c in commits if c.strip()]),
        "prefix_patterns": dict(prefixes.most_common(10)),
        "commit_types": dict(commit_types.most_common(10)),
        "scopes": dict(scopes.most_common(10)),
        "keyword_frequency": dict(keywords.most_common(10)),
        "avg_message_length": sum(message_lengths) / len(message_lengths) if message_lengths else 0,
        "breaking_changes": breaking_changes,
        "issue_refs": issue_refs,
        "conventional_commits_ratio": sum(prefixes.values()) / len(commits) if commits else 0,
    }

def analyze_branch_patterns() -> Dict:
    """深度分析分支命名模式"""
    cmd = "git branch -a --format='%(refname:short)'"
    output = run_git_command(cmd)
    branches = [b.strip() for b in output.split('\n') if b.strip()]

    patterns = Counter()
    branch_types = Counter()
    has_issue_number = 0

    for branch in branches:
        # 提取分支类型
        type_match = re.match(r'(feature|feat|bugfix|fix|hotfix|release|chore|docs|test|main|master|develop|dev)', branch, re.IGNORECASE)
        if type_match:
            branch_types[type_match.group(1).lower()] += 1

        # 检查命名模式
        if re.match(r'^(feature|feat)/', branch, re.IGNORECASE):
            patterns["feature/*"] += 1
        elif re.match(r'^(bugfix|fix)/', branch, re.IGNORECASE):
            patterns["bugfix/*"] += 1
        elif re.match(r'^hotfix/', branch, re.IGNORECASE):
            patterns["hotfix/*"] += 1
        elif re.match(r'^release/', branch, re.IGNORECASE):
            patterns["release/*"] += 1
        elif re.match(r'^chore/', branch, re.IGNORECASE):
            patterns["chore/*"] += 1
        elif branch in ['main', 'master']:
            patterns["main-branch"] += 1
        elif branch in ['develop', 'dev']:
            patterns["develop-branch"] += 1
        else:
            patterns["other"] += 1

        # 检查 Issue 编号
        if re.search(r'#?\d+', branch):
            has_issue_number += 1

    return {
        "total_branches": len(branches),
        "branch_types": dict(branch_types.most_common(10)),
        "patterns": dict(patterns.most_common(10)),
        "issue_number_ratio": has_issue_number / len(branches) if branches else 0,
    }

def analyze_file_changes(since: str = "3 months ago", top: int = 20) -> Dict:
    """深度分析文件变更模式"""
    cmd = f'git log --since="{since}" --name-status --pretty=format:"COMMIT_START"'
    output = run_git_command(cmd)

    # 解析文件变更
    file_changes = Counter()
    file_additions = Counter()
    file_deletions = Counter()
    file_types = Counter()
    directories = Counter()

    # 文件关联分析（经常一起修改的文件）
    commit_files = []
    current_files = []

    for line in output.split('\n'):
        line = line.strip()
        if line == 'COMMIT_START':
            if current_files:
                commit_files.append(current_files)
            current_files = []
        elif line:
            parts = line.split('\t')
            if len(parts) >= 2:
                status = parts[0]
                file_path = parts[1]

                file_changes[file_path] += 1
                current_files.append(file_path)

                # 文件类型
                ext = Path(file_path).suffix
                if ext:
                    file_types[ext] += 1

                # 目录
                dir_name = str(Path(file_path).parent)
                if dir_name and dir_name != ".":
                    directories[dir_name] += 1

                # 增删统计
                if status == 'A':
                    file_additions[file_path] += 1
                elif status == 'D':
                    file_deletions[file_path] += 1

    if current_files:
        commit_files.append(current_files)

    # 计算文件关联
    file_pairs = Counter()
    for files in commit_files:
        if len(files) > 1:
            for i, f1 in enumerate(files):
                for f2 in files[i+1:]:
                    pair = tuple(sorted([f1, f2]))
                    file_pairs[pair] += 1

    return {
        "file_types": dict(file_types.most_common(15)),
        "hot_files": dict(file_changes.most_common(top)),
        "hot_directories": dict(directories.most_common(15)),
        "frequently_added": dict(file_additions.most_common(10)),
        "frequently_deleted": dict(file_deletions.most_common(10)),
        "file_pairs": {f"{p[0]} <-> {p[1]}": c for p, c in file_pairs.most_common(10)},
    }

def analyze_code_style(repo_path: str = ".") -> Dict:
    """分析代码风格（从现有代码中提取）"""
    style = {
        "indentation": {},
        "naming_conventions": {},
        "comment_style": {},
        "test_patterns": {},
    }

    # 检测缩进风格
    for ext in ['.py', '.ts', '.js', '.java']:
        files = list(Path(repo_path).rglob(f'*{ext}'))[:10]
        for f in files:
            try:
                content = f.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')

                # 检测缩进
                for line in lines:
                    if line.startswith('    '):
                        style["indentation"]["4-spaces"] = style["indentation"].get("4-spaces", 0) + 1
                    elif line.startswith('\t'):
                        style["indentation"]["tabs"] = style["indentation"].get("tabs", 0) + 1
                    elif line.startswith('  '):
                        style["indentation"]["2-spaces"] = style["indentation"].get("2-spaces", 0) + 1

                # 检测命名约定
                if ext == '.py':
                    # Python: snake_case for functions/variables
                    if re.search(r'def [a-z][a-z0-9_]*\(', content):
                        style["naming_conventions"]["snake_case_functions"] = style["naming_conventions"].get("snake_case_functions", 0) + 1
                    if re.search(r'class [A-Z][a-zA-Z0-9]*', content):
                        style["naming_conventions"]["PascalCase_classes"] = style["naming_conventions"].get("PascalCase_classes", 0) + 1

                elif ext in ['.ts', '.js']:
                    # TypeScript/JavaScript: camelCase for functions
                    if re.search(r'function [a-z][a-zA-Z0-9]*\(', content):
                        style["naming_conventions"]["camelCase_functions"] = style["naming_conventions"].get("camelCase_functions", 0) + 1
                    if re.search(r'class [A-Z][a-zA-Z0-9]*', content):
                        style["naming_conventions"]["PascalCase_classes"] = style["naming_conventions"].get("PascalCase_classes", 0) + 1

                # 检测注释风格
                if re.search(r'#.*', content):
                    style["comment_style"]["hash_comments"] = style["comment_style"].get("hash_comments", 0) + 1
                if re.search(r'//.*', content):
                    style["comment_style"]["double_slash_comments"] = style["comment_style"].get("double_slash_comments", 0) + 1
                if re.search(r'/\*.*\*/', content, re.DOTALL):
                    style["comment_style"]["block_comments"] = style["comment_style"].get("block_comments", 0) + 1

                # 检测测试模式
                if 'test' in str(f).lower():
                    if re.search(r'def test_', content):
                        style["test_patterns"]["pytest"] = style["test_patterns"].get("pytest", 0) + 1
                    if re.search(r'describe\(', content):
                        style["test_patterns"]["jest"] = style["test_patterns"].get("jest", 0) + 1
                    if re.search(r'@Test', content):
                        style["test_patterns"]["junit"] = style["test_patterns"].get("junit", 0) + 1

            except Exception:
                continue

    return style

def generate_team_skill_content(commit_analysis: Dict, branch_analysis: Dict,
                                file_analysis: Dict, code_style: Dict) -> Dict:
    """生成团队 Skill 内容"""

    # 确定提交约定
    commit_prefixes = commit_analysis.get("prefix_patterns", {})
    commit_convention = "conventional" if commit_analysis.get("conventional_commits_ratio", 0) > 0.5 else "free-form"

    # 生成提交约定说明
    if commit_convention == "conventional":
        commit_guide = f"""### 提交消息格式

团队使用 Conventional Commits 规范（覆盖率: {commit_analysis.get('conventional_commits_ratio', 0):.0%}）

**常用类型**:
"""
        for prefix, count in commit_prefixes.items():
            commit_guide += f"- `{prefix}`: {count} 次\n"
    else:
        commit_guide = """### 提交消息格式

团队使用自由格式的提交消息，建议逐步采用 Conventional Commits 规范。

**建议格式**: `type(scope): description`

**常用类型**:
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建/工具相关
"""

    # 生成分支命名约定
    branch_patterns = branch_analysis.get("patterns", {})
    branch_guide = """### 分支命名规范

**分支类型**:
"""
    for pattern, count in branch_patterns.items():
        branch_guide += f"- `{pattern}`: {count} 个分支\n"

    # 生成热门文件警告
    hot_files = file_analysis.get("hot_files", {})
    if hot_files:
        hot_files_guide = """### 热门文件（变更频繁）

修改以下文件时请特别注意依赖关系:
"""
        for file, count in list(hot_files.items())[:5]:
            hot_files_guide += f"- `{file}`: {count} 次变更\n"
    else:
        hot_files_guide = ""

    # 生成文件关联
    file_pairs = file_analysis.get("file_pairs", {})
    if file_pairs:
        file_pairs_guide = """### 经常一起修改的文件

以下文件经常在同一次提交中修改:
"""
        for pair, count in list(file_pairs.items())[:5]:
            file_pairs_guide += f"- {pair}: {count} 次\n"
    else:
        file_pairs_guide = ""

    # 生成代码风格约定
    indentation = code_style.get("indentation", {})
    if indentation:
        most_common_indent = max(indentation.items(), key=lambda x: x[1])[0] if indentation else "未知"
        indent_guide = f"\n- **缩进**: {most_common_indent}"
    else:
        indent_guide = ""

    naming = code_style.get("naming_conventions", {})
    naming_guide = ""
    if naming:
        naming_guide = "\n- **命名约定**:\n"
        for conv, count in naming.items():
            naming_guide += f"  - {conv}\n"

    test_patterns = code_style.get("test_patterns", {})
    test_guide = ""
    if test_patterns:
        most_common_test = max(test_patterns.items(), key=lambda x: x[1])[0] if test_patterns else ""
        if most_common_test:
            test_guide = f"\n- **测试框架**: {most_common_test}"

    workflow = f"""### 开发流程

1. **创建分支**
   - 功能开发: `feature/xxx` 或 `feat/xxx`
   - Bug 修复: `bugfix/xxx` 或 `fix/xxx`
   - 紧急修复: `hotfix/xxx`

2. **编写代码**
   - 遵循项目代码风格{indent_guide}{naming_guide}{test_guide}

3. **提交代码**
{commit_guide}

4. **创建 PR**
   - 标题格式: `type(scope): description`
   - 描述包含: 变更内容、测试方案、影响范围

5. **Code Review**
   - 检查代码风格
   - 检查测试覆盖
   - 检查文档更新

6. **合并代码**
   - 确保所有 CI 检查通过
   - 确保所有 Review 通过
   - 使用 Squash Merge 保持提交历史整洁
"""

    checklist = f"""### 提交前检查

**代码质量**
- [ ] 代码风格符合团队规范
- [ ] 无重复代码
- [ ] 函数职责单一
- [ ] 注释清晰

**测试覆盖**
- [ ] 新增代码有测试覆盖
- [ ] 所有测试通过
- [ ] 边界情况已测试

**文档同步**
- [ ] API 文档已更新（如有必要）
- [ ] README 已更新（如有必要）
- [ ] CHANGELOG 已更新（如有必要）

**提交规范**
- [ ] 提交消息格式正确
- [ ] 关联了相关 Issue
- [ ] 提交粒度适当（一个提交解决一个问题）
"""

    # 添加热门文件检查项
    if hot_files:
        checklist += """
**热门文件变更检查**
"""
        for file in list(hot_files.keys())[:5]:
            checklist += f"- [ ] 检查 `{file}` 的依赖关系\n"

    return {
        "workflow": workflow,
        "checklist": checklist,
        "commit_conventions": commit_prefixes,
        "branch_conventions": branch_patterns,
        "hot_files": list(hot_files.keys())[:10],
        "file_pairs": file_pairs,
        "code_style": {
            "indentation": indentation,
            "naming_conventions": naming,
            "test_patterns": test_patterns,
        },
    }

def generate_team_skill_markdown(skill_content: Dict, analysis_time: str) -> str:
    """生成团队 Skill Markdown 文件"""

    template = f'''---
name: team-style
description: 团队代码风格和协作规范
triggers: ["team", "团队", "规范", "convention"]
version: 1.0.0
created: {analysis_time[:10]}
---

# Team Style

## Overview

团队代码风格和协作规范，帮助新成员快速融入团队，保持代码一致性。

{skill_content["workflow"]}

## Checklist

{skill_content["checklist"]}

## Hot Files

以下文件变更频繁，修改时请特别注意依赖关系：

'''
    for file in skill_content["hot_files"][:10]:
        template += f"- `{file}`\n"

    if skill_content.get("file_pairs"):
        template += """
## File Associations

以下文件经常在同一次提交中修改，修改其中之一时请考虑另一文件：

"""
        for pair, count in list(skill_content["file_pairs"].items())[:10]:
            template += f"- {pair}: {count} 次\n"

    template += f"""
## Code Style Summary

- **Indentation**: {max(skill_content["code_style"].get("indentation", {}).items(), key=lambda x: x[1])[0] if skill_content["code_style"].get("indentation") else "Not detected"}
- **Naming Conventions**: {', '.join(skill_content["code_style"].get("naming_conventions", {}).keys()) or "Not detected"}
- **Test Framework**: {max(skill_content["code_style"].get("test_patterns", {}).items(), key=lambda x: x[1])[0] if skill_content["code_style"].get("test_patterns") else "Not detected"}

## Evolution Log

### v1.0.0 ({analysis_time[:10]})
- 初始版本
- 触发：从团队 Git 历史自动生成
- 内容：提交约定、分支规范、热门文件、代码风格

---

> 此 Skill 由 `analyze_team_style_v2.py` 自动生成，建议根据团队实际情况调整。
"""
    return template

def generate_report(result: Dict, output_file: str):
    """生成可读的分析报告"""

    report = f"""# 团队风格分析报告

**分析时间**: {result['analysis_time']}
**分析范围**: {result['time_range']}

---

## 一、提交分析

### 提交概览

| 指标 | 数值 |
|------|------|
| 总提交数 | {result['commit_analysis']['total_commits']} |
| 平均消息长度 | {result['commit_analysis']['avg_message_length']:.1f} 字符 |
| Conventional Commits 覆盖率 | {result['commit_analysis']['conventional_commits_ratio']:.0%} |
| Breaking Changes | {result['commit_analysis']['breaking_changes']} |
| Issue 引用 | {result['commit_analysis']['issue_refs']} |

### 提交类型分布

| 类型 | 次数 |
|------|------|
"""
    for prefix, count in result['commit_analysis']['prefix_patterns'].items():
        report += f"| {prefix} | {count} |\n"

    report += """
### 关键词统计

| 关键词 | 次数 |
|--------|------|
"""
    for keyword, count in result['commit_analysis']['keyword_frequency'].items():
        report += f"| {keyword} | {count} |\n"

    report += f"""
---

## 二、分支分析

### 分支概览

| 指标 | 数值 |
|------|------|
| 总分支数 | {result['branch_analysis']['total_branches']} |
| Issue 编号引用率 | {result['branch_analysis']['issue_number_ratio']:.0%} |

### 分支模式

| 模式 | 数量 |
|------|------|
"""
    for pattern, count in result['branch_analysis']['patterns'].items():
        report += f"| {pattern} | {count} |\n"

    report += """
---

## 三、文件分析

### 文件类型分布

| 类型 | 数量 |
|------|------|
"""
    for ext, count in result['file_analysis']['file_types'].items():
        report += f"| {ext} | {count} |\n"

    report += """
### 热门文件（变更频繁）

| 文件 | 变更次数 |
|------|----------|
"""
    for file, count in result['file_analysis']['hot_files'].items():
        report += f"| `{file}` | {count} |\n"

    report += """
### 经常一起修改的文件

| 文件对 | 次数 |
|--------|------|
"""
    for pair, count in result['file_analysis']['file_pairs'].items():
        report += f"| {pair} | {count} |\n"

    report += """
---

## 四、代码风格

### 缩进风格

| 风格 | 检测次数 |
|------|----------|
"""
    for style, count in result['code_style']['indentation'].items():
        report += f"| {style} | {count} |\n"

    report += """
### 命名约定

| 约定 | 检测次数 |
|------|----------|
"""
    for conv, count in result['code_style']['naming_conventions'].items():
        report += f"| {conv} | {count} |\n"

    report += """
### 测试框架

| 框架 | 检测次数 |
|------|----------|
"""
    for pattern, count in result['code_style']['test_patterns'].items():
        report += f"| {pattern} | {count} |\n"

    report += f"""
---

## 五、建议

### 提交规范建议

"""
    if result['commit_analysis']['conventional_commits_ratio'] < 0.5:
        report += "- 建议团队采用 Conventional Commits 规范，提高提交消息的可读性\n"
    if result['commit_analysis']['avg_message_length'] < 30:
        report += "- 建议增加提交消息的详细程度，描述变更的原因和影响\n"
    if result['commit_analysis']['issue_refs'] < result['commit_analysis']['total_commits'] * 0.3:
        report += "- 建议在提交消息中关联 Issue，便于追溯\n"

    report += """
### 分支规范建议

"""
    if result['branch_analysis']['issue_number_ratio'] < 0.3:
        report += "- 建议在分支名中包含 Issue 编号，便于追踪\n"

    report += """
### 代码风格建议

"""
    if not result['code_style']['indentation']:
        report += "- 建议添加 .editorconfig 文件统一缩进风格\n"
    if not result['code_style']['test_patterns']:
        report += "- 建议添加测试并统一测试框架\n"

    report += """
---

> 此报告由 `analyze_team_style_v2.py --report` 自动生成
"""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    return output_file

def main():
    parser = argparse.ArgumentParser(description="深度分析团队代码风格")
    parser.add_argument("--repo", default=".", help="Git 仓库路径")
    parser.add_argument("--since", default="3 months ago", help="分析时间范围")
    parser.add_argument("--output", default="team-style.json", help="输出文件")
    parser.add_argument("--report", action="store_true", help="生成可读报告")
    parser.add_argument("--skill", action="store_true", help="生成团队 Skill")
    args = parser.parse_args()

    print(f"📊 分析 {args.repo} 的团队风格...")

    commit_analysis = analyze_commit_messages(args.since)
    branch_analysis = analyze_branch_patterns()
    file_analysis = analyze_file_changes(args.since)
    code_style = analyze_code_style(args.repo)

    skill_content = generate_team_skill_content(
        commit_analysis, branch_analysis, file_analysis, code_style
    )

    result = {
        "analysis_time": datetime.now().isoformat(),
        "time_range": args.since,
        "commit_analysis": commit_analysis,
        "branch_analysis": branch_analysis,
        "file_analysis": file_analysis,
        "code_style": code_style,
        "team_skill": skill_content,
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 分析完成！结果保存到 {args.output}")
    print(f"\n📈 团队风格摘要：")
    print(f"  - 提交数: {commit_analysis['total_commits']}")
    print(f"  - Conventional Commits: {commit_analysis['conventional_commits_ratio']:.0%}")
    print(f"  - 提交前缀: {list(commit_analysis['prefix_patterns'].keys())[:5]}")
    print(f"  - 分支模式: {list(branch_analysis['patterns'].keys())}")
    print(f"  - 热门文件: {len(file_analysis['hot_files'])} 个")
    print(f"  - 文件关联: {len(file_analysis['file_pairs'])} 对")

    if args.report:
        report_file = args.output.replace('.json', '-report.md')
        generate_report(result, report_file)
        print(f"\n📄 可读报告已生成: {report_file}")

    if args.skill:
        skill_file = args.output.replace('.json', '-skill.md')
        skill_md = generate_team_skill_markdown(skill_content, result['analysis_time'])
        with open(skill_file, 'w', encoding='utf-8') as f:
            f.write(skill_md)
        print(f"\n📝 团队 Skill 已生成: {skill_file}")

if __name__ == "__main__":
    main()
