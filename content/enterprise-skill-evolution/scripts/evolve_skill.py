#!/usr/bin/env python3
"""
evolve_skill.py - 迭代更新 Skill 文件

用法：
    python evolve_skill.py --skill review-checklist --add-check "性能影响评估"
    python evolve_skill.py --skill debug-workflow --from-feedback session-xxx.jsonl
"""

import argparse
import json
from pathlib import Path
from datetime import datetime
import re

SKILLS_DIR = Path.home() / ".claude" / "skills"

def read_skill(skill_name):
    """读取 Skill 文件"""
    skill_file = SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_file.exists():
        raise FileNotFoundError(f"Skill not found: {skill_name}")
    return skill_file.read_text(encoding='utf-8')

def write_skill(skill_name, content):
    """写入 Skill 文件"""
    skill_file = SKILLS_DIR / skill_name / "SKILL.md"
    skill_file.write_text(content, encoding='utf-8')

def add_check_item(skill_name, section, item, reason=""):
    """添加检查项"""
    content = read_skill(skill_name)

    # 找到对应章节
    section_pattern = rf'(## {section}.*?)(\n## |\Z)'
    match = re.search(section_pattern, content, re.DOTALL)

    if match:
        section_content = match.group(1)
        # 添加检查项
        new_item = f"\n- [ ] {item}"
        updated_section = section_content.rstrip() + new_item + "\n"
        content = content.replace(section_content, updated_section)

        # 更新 Evolution Log
        log_entry = f"""
### v1.x.0 ({datetime.now().strftime("%Y-%m-%d")})
- 新增：{section} - {item}
- 触发：{reason or '手动添加'}
"""

        if "## Evolution Log" in content:
            content = content.replace("## Evolution Log", "## Evolution Log" + log_entry)
        else:
            content += "\n## Evolution Log\n" + log_entry

        write_skill(skill_name, content)
        print(f"✅ 已添加检查项: {item}")
    else:
        print(f"❌ 未找到章节: {section}")

def validate_skill(skill_name):
    """验证 Skill 格式"""
    content = read_skill(skill_name)

    issues = []

    # 检查 YAML frontmatter
    if not content.startswith("---"):
        issues.append("缺少 YAML frontmatter")

    # 检查必要字段
    required_fields = ["name", "description"]
    for field in required_fields:
        if f"{field}:" not in content[:500]:
            issues.append(f"缺少必要字段: {field}")

    # 检查章节
    required_sections = ["## Overview", "## Workflow", "## Checklist"]
    for section in required_sections:
        if section not in content:
            issues.append(f"缺少必要章节: {section}")

    # 检查 Evolution Log
    if "## Evolution Log" not in content:
        issues.append("缺少 Evolution Log 章节")

    return issues

def main():
    parser = argparse.ArgumentParser(description="迭代更新 Skill")
    parser.add_argument("--skill", required=True, help="Skill 名称")
    parser.add_argument("--add-check", help="添加检查项")
    parser.add_argument("--section", default="Checklist", help="目标章节")
    parser.add_argument("--reason", help="更新原因")
    parser.add_argument("--validate", action="store_true", help="验证 Skill 格式")
    args = parser.parse_args()

    if args.validate:
        issues = validate_skill(args.skill)
        if issues:
            print(f"❌ 验证失败:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"✅ 验证通过: {args.skill}")

    elif args.add_check:
        add_check_item(args.skill, args.section, args.add_check, args.reason)

    else:
        print("请指定操作: --add-check 或 --validate")

if __name__ == "__main__":
    main()
