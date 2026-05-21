#!/usr/bin/env python3
"""
create_skill.py - 创建 Claude Code Skill 文件

用法：
    python create_skill.py --name review-checklist --description "代码审查清单"
    python create_skill.py --from-analysis patterns.json --top 3
"""

import argparse
import json
from pathlib import Path
from datetime import datetime

SKILLS_DIR = Path.home() / ".claude" / "skills"

SKILL_TEMPLATE = '''---
name: {name}
description: {description}
triggers: {triggers}
---

# {title}

## Overview

{overview}

## Workflow

{workflow}

## Checklist

{checklist}

## Examples

{examples}

## Evolution Log

### v1.0.0 ({date})
- 初始版本
- 触发：从会话日志中自动生成
- 来源：{source}
'''

def create_skill(name, description, triggers=None, workflow=None, checklist=None, examples=None, source="手动创建"):
    """创建 Skill 文件"""
    skill_dir = SKILLS_DIR / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    skill_file = skill_dir / "SKILL.md"

    # 默认值
    if triggers is None:
        triggers = [name]
    if workflow is None:
        workflow = "1. 步骤一\n2. 步骤二\n3. 步骤三"
    if checklist is None:
        checklist = "- [ ] 检查项一\n- [ ] 检查项二\n- [ ] 检查项三"
    if examples is None:
        examples = "示例场景描述和预期输出"

    content = SKILL_TEMPLATE.format(
        name=name,
        description=description,
        triggers=json.dumps(triggers, ensure_ascii=False),
        title=name.replace("-", " ").title(),
        overview=description,
        workflow=workflow,
        checklist=checklist,
        examples=examples,
        date=datetime.now().strftime("%Y-%m-%d"),
        source=source
    )

    skill_file.write_text(content, encoding='utf-8')
    print(f"✅ Skill 已创建: {skill_file}")
    return skill_file

def from_analysis(analysis_file, top=3):
    """从分析结果创建 Skill"""
    with open(analysis_file, 'r', encoding='utf-8') as f:
        analysis = json.load(f)

    created = []
    for proposal in analysis.get("skill_proposals", [])[:top]:
        skill = proposal["suggested_skill"]
        skill_file = create_skill(
            name=skill["name"],
            description=skill["description"],
            triggers=skill.get("triggers", []),
            examples="\n".join(f"- {p}" for p in proposal.get("sample_prompts", [])),
            source=f"自动分析: {analysis_file}"
        )
        created.append(skill_file)

    return created

def main():
    parser = argparse.ArgumentParser(description="创建 Claude Code Skill")
    parser.add_argument("--name", help="Skill 名称")
    parser.add_argument("--description", help="Skill 描述")
    parser.add_argument("--triggers", nargs="+", help="触发关键词")
    parser.add_argument("--from-analysis", help="从分析结果创建")
    parser.add_argument("--top", type=int, default=3, help="创建前 N 个 Skill")
    args = parser.parse_args()

    SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    if args.from_analysis:
        print(f"📂 从 {args.from_analysis} 创建 Skill...")
        created = from_analysis(args.from_analysis, args.top)
        print(f"\n✅ 创建了 {len(created)} 个 Skill")
    elif args.name and args.description:
        create_skill(args.name, args.description, args.triggers)
    else:
        print("请提供 --name 和 --description，或使用 --from-analysis")

if __name__ == "__main__":
    main()
