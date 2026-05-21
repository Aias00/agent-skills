#!/usr/bin/env python3
"""
analyze_conversations.py - 从 Claude Code 会话日志中提取高频模式

用法：
    python analyze_conversations.py --project /path/to/project --output patterns.json
    python analyze_conversations.py --all --min-count 3 --output patterns.json
"""

import json
import argparse
from pathlib import Path
from collections import Counter
from datetime import datetime
import re

CLAUDE_DIR = Path.home() / ".claude"

def load_history(limit=None):
    """加载全局会话历史"""
    history_file = CLAUDE_DIR / "history.jsonl"
    records = []
    if not history_file.exists():
        print(f"历史文件不存在: {history_file}")
        return records
    with open(history_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            try:
                records.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
    return records

def load_project_sessions(project_path):
    """加载指定项目的会话"""
    project_dir = CLAUDE_DIR / "projects" / project_path.replace("/", "-").lstrip("-")
    sessions = []
    if not project_dir.exists():
        print(f"项目目录不存在: {project_dir}")
        return sessions
    for session_file in project_dir.glob("*.jsonl"):
        with open(session_file, 'r', encoding='utf-8') as f:
            messages = []
            for line in f:
                try:
                    messages.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
            sessions.append({
                "file": session_file.name,
                "messages": messages
            })
    return sessions

def extract_user_prompts(records):
    """提取用户提示词"""
    prompts = []
    for record in records:
        display = record.get("display", "").strip()
        if display and len(display) > 10:  # 过滤太短的输入
            prompts.append(display)
    return prompts

def cluster_by_intent(prompts, min_count=3):
    """按意图聚类提示词"""
    # 关键词模式匹配
    patterns = {
        "code_review": ["检查", "review", "审查", "看下这段代码", "有没有问题"],
        "debug": ["报错", "错误", "bug", "为什么", "不工作", "调试"],
        "refactor": ["重构", "优化", "改进", "简化", "重写"],
        "test": ["测试", "test", "单元测试", "覆盖率"],
        "document": ["文档", "注释", "readme", "说明"],
        "deploy": ["部署", "deploy", "发布", "上线"],
        "api": ["api", "接口", "endpoint", "请求"],
        "security": ["安全", "漏洞", "注入", "xss", "sql"],
    }

    clusters = {key: [] for key in patterns}
    clusters["other"] = []

    for prompt in prompts:
        matched = False
        prompt_lower = prompt.lower()
        for category, keywords in patterns.items():
            if any(kw in prompt_lower for kw in keywords):
                clusters[category].append(prompt)
                matched = True
                break
        if not matched:
            clusters["other"].append(prompt)

    # 过滤低频聚类
    return {k: v for k, v in clusters.items() if len(v) >= min_count}

def extract_patterns(prompts):
    """提取高频模式"""
    # 1. 高频短语
    phrases = []
    for prompt in prompts:
        # 提取中文短语（2-10字）
        cn_phrases = re.findall(r'[一-龥]{2,10}', prompt)
        phrases.extend(cn_phrases)
        # 提取英文单词组合
        en_phrases = re.findall(r'\b[a-z]{3,}(?:\s+[a-z]{3,}){0,3}\b', prompt.lower())
        phrases.extend(en_phrases)

    phrase_counter = Counter(phrases)

    # 2. 高频完整提示词
    prompt_counter = Counter(prompts)

    return {
        "top_phrases": phrase_counter.most_common(20),
        "top_prompts": prompt_counter.most_common(10),
        "total_prompts": len(prompts),
        "unique_prompts": len(set(prompts))
    }

def generate_skill_proposal(cluster_name, prompts, count):
    """根据聚类生成 Skill 提案"""
    skill_templates = {
        "code_review": {
            "name": "review-checklist",
            "description": "代码审查清单",
            "triggers": ["review", "审查", "检查代码"]
        },
        "debug": {
            "name": "debug-workflow",
            "description": "调试工作流",
            "triggers": ["debug", "调试", "报错"]
        },
        "refactor": {
            "name": "refactor-guide",
            "description": "重构指南",
            "triggers": ["refactor", "重构", "优化"]
        },
        "test": {
            "name": "test-workflow",
            "description": "测试工作流",
            "triggers": ["test", "测试"]
        },
        "api": {
            "name": "api-standard",
            "description": "API 开发规范",
            "triggers": ["api", "接口"]
        }
    }

    template = skill_templates.get(cluster_name, {
        "name": f"{cluster_name}-workflow",
        "description": f"{cluster_name} 相关工作流",
        "triggers": [cluster_name]
    })

    return {
        "suggested_skill": template,
        "sample_prompts": prompts[:5],
        "occurrence_count": count,
        "confidence": min(count / 10, 1.0)  # 置信度
    }

def main():
    parser = argparse.ArgumentParser(description="分析 Claude Code 会话日志")
    parser.add_argument("--project", help="指定项目路径")
    parser.add_argument("--all", action="store_true", help="分析所有项目")
    parser.add_argument("--limit", type=int, default=1000, help="限制历史记录数量")
    parser.add_argument("--min-count", type=int, default=3, help="最小出现次数")
    parser.add_argument("--output", default="patterns.json", help="输出文件")
    args = parser.parse_args()

    print("📂 加载会话历史...")

    if args.project:
        sessions = load_project_sessions(args.project)
        prompts = []
        for session in sessions:
            for msg in session["messages"]:
                if msg.get("type") == "user":
                    content = msg.get("content", "")
                    if isinstance(content, str) and len(content) > 10:
                        prompts.append(content)
    else:
        records = load_history(args.limit)
        prompts = extract_user_prompts(records)

    print(f"📊 分析 {len(prompts)} 条提示词...")

    if not prompts:
        print("❌ 没有找到提示词数据")
        return

    # 聚类
    clusters = cluster_by_intent(prompts, args.min_count)

    # 提取模式
    patterns = extract_patterns(prompts)

    # 生成 Skill 提案
    proposals = []
    for cluster_name, cluster_prompts in clusters.items():
        if len(cluster_prompts) >= args.min_count:
            proposal = generate_skill_proposal(cluster_name, cluster_prompts, len(cluster_prompts))
            proposals.append(proposal)

    # 按置信度排序
    proposals.sort(key=lambda x: x["confidence"], reverse=True)

    result = {
        "analysis_time": datetime.now().isoformat(),
        "total_prompts": len(prompts),
        "unique_prompts": patterns["unique_prompts"],
        "clusters": {k: len(v) for k, v in clusters.items()},
        "top_phrases": patterns["top_phrases"],
        "skill_proposals": proposals
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 分析完成！结果保存到 {args.output}")
    print(f"\n📈 发现 {len(proposals)} 个 Skill 提案：")
    for p in proposals[:5]:
        print(f"  - {p['suggested_skill']['name']}: {p['suggested_skill']['description']} (置信度: {p['confidence']:.0%})")

if __name__ == "__main__":
    main()
