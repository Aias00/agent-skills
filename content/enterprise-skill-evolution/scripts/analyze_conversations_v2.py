#!/usr/bin/env python3
"""
analyze_conversations_v2.py - 深度分析会话日志，提取有价值的 Skill 模式

改进：
1. 使用 LLM 进行语义分析
2. 提取完整的工作流模式
3. 识别修正模式（用户反复纠正 AI）
4. 识别重复模式（用户重复相同指令）
5. 生成可执行的 Skill 内容

用法：
    python analyze_conversations_v2.py --project /path/to/project --output deep-analysis.json
    python analyze_conversations_v2.py --all --min-count 3 --output deep-analysis.json
    python analyze_conversations_v2.py --deep --use-llm --output semantic-analysis.json
"""

import json
import argparse
import os
import re
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
from typing import Optional
import subprocess
import sys

CLAUDE_DIR = Path.home() / ".claude"

# 意图分类模板（更细粒度）
INTENT_PATTERNS = {
    # 开发类
    "code_review": {
        "keywords": ["检查", "review", "审查", "看下这段代码", "有没有问题", "review一下", "代码审查"],
        "sub_intents": ["security_check", "performance_check", "style_check", "logic_check"]
    },
    "debug": {
        "keywords": ["报错", "错误", "bug", "为什么", "不工作", "调试", "失败", "异常", "exception", "error"],
        "sub_intents": ["runtime_error", "logic_error", "config_error", "dependency_error"]
    },
    "refactor": {
        "keywords": ["重构", "优化", "改进", "简化", "重写", "cleanup", "清理"],
        "sub_intents": ["performance_optimize", "code_simplify", "structure_improve", "remove_duplicate"]
    },
    "test": {
        "keywords": ["测试", "test", "单元测试", "覆盖率", "测试用例", "junit", "mock"],
        "sub_intents": ["unit_test", "integration_test", "e2e_test", "test_fix"]
    },
    "implement": {
        "keywords": ["实现", "开发", "添加", "新增", "create", "implement", "add feature"],
        "sub_intents": ["new_feature", "api_endpoint", "ui_component", "data_processing"]
    },

    # 文档类
    "document": {
        "keywords": ["文档", "注释", "readme", "说明", "文档化", "doc"],
        "sub_intents": ["code_comment", "api_doc", "readme_update", "architecture_doc"]
    },

    # 运维类
    "deploy": {
        "keywords": ["部署", "deploy", "发布", "上线", "ci/cd", "pipeline"],
        "sub_intents": ["env_setup", "config_deploy", "rollback", "monitoring"]
    },

    # API 类
    "api": {
        "keywords": ["api", "接口", "endpoint", "请求", "rest", "graphql", "http"],
        "sub_intents": ["api_design", "api_debug", "api_document", "api_security"]
    },

    # 安全类
    "security": {
        "keywords": ["安全", "漏洞", "注入", "xss", "sql", "权限", "auth", "加密"],
        "sub_intents": ["vulnerability_scan", "permission_check", "data_encryption", "auth_flow"]
    },

    # 架构类
    "architecture": {
        "keywords": ["架构", "设计", "方案", "技术选型", "design", "architecture"],
        "sub_intents": ["system_design", "module_split", "tech_choice", "migration_plan"]
    },

    # 知识类
    "explain": {
        "keywords": ["解释", "说明", "什么是", "怎么理解", "为什么", "explain"],
        "sub_intents": ["concept_explain", "code_explain", "best_practice", "comparison"]
    }
}

# 修正模式检测（用户纠正 AI 的模式）
CORRECTION_PATTERNS = {
    "style_correction": [
        r"不[，,。]应该",
        r"不要这样",
        r"换成",
        r"改成",
        r"用.*而不是",
        r"我想要.*不是"
    ],
    "logic_correction": [
        r"理解错了",
        r"不是这个意思",
        r"重新理解",
        r"我想说的是",
        r"我的意思是"
    ],
    "scope_correction": [
        r"只需要",
        r"不用改",
        r"保持原样",
        r"只改",
        r"范围太大了"
    ],
    "quality_correction": [
        r"太复杂了",
        r"简化一点",
        r"可以更简洁",
        r"性能.*问题",
        r"可读性"
    ]
}

# 工作流模式检测（连续的指令序列）
WORKFLOW_PATTERNS = {
    "tdd_workflow": [
        ("write_test", "实现.*测试"),
        ("write_code", "实现.*代码"),
        ("refactor", "重构")
    ],
    "debug_workflow": [
        ("check_error", "错误|报错|异常"),
        ("analyze_cause", "原因|为什么|分析"),
        ("fix_issue", "修复|解决")
    ],
    "code_review_workflow": [
        ("check_style", "风格|规范"),
        ("check_logic", "逻辑|正确性"),
        ("check_security", "安全|漏洞"),
        ("suggest_improve", "建议|改进")
    ],
    "feature_dev_workflow": [
        ("design", "设计|方案"),
        ("implement", "实现|开发"),
        ("test", "测试"),
        ("document", "文档")
    ]
}


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
                "messages": messages,
                "path": str(session_file)
            })
    return sessions


def extract_conversation_flows(sessions):
    """从会话中提取对话流（用户 -> AI -> 用户 -> ...）"""
    flows = []
    for session in sessions:
        flow = {
            "session_file": session["file"],
            "exchanges": []
        }
        current_exchange = None

        for msg in session["messages"]:
            msg_type = msg.get("type", "")

            if msg_type == "user":
                if current_exchange:
                    flow["exchanges"].append(current_exchange)
                current_exchange = {
                    "user": msg.get("content", ""),
                    "assistant": "",
                    "tools": []
                }
            elif msg_type == "assistant" and current_exchange:
                current_exchange["assistant"] = msg.get("content", "")
            elif msg_type == "tool_use" and current_exchange:
                current_exchange["tools"].append({
                    "name": msg.get("name", ""),
                    "input": msg.get("input", {})
                })

        if current_exchange:
            flow["exchanges"].append(current_exchange)

        if flow["exchanges"]:
            flows.append(flow)

    return flows


def detect_correction_patterns(flows):
    """检测修正模式（用户反复纠正 AI）"""
    corrections = defaultdict(list)

    for flow in flows:
        for i, exchange in enumerate(flow["exchanges"]):
            user_msg = exchange["user"]
            if not isinstance(user_msg, str):
                continue

            for correction_type, patterns in CORRECTION_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, user_msg, re.IGNORECASE):
                        # 找到前一个 exchange 作为上下文
                        prev_exchange = flow["exchanges"][i-1] if i > 0 else None
                        corrections[correction_type].append({
                            "correction": user_msg[:200],
                            "prev_context": prev_exchange["user"][:200] if prev_exchange else None,
                            "session": flow["session_file"]
                        })
                        break

    return dict(corrections)


def detect_repetition_patterns(flows, min_repeat=2):
    """检测重复模式（用户重复相似指令）"""
    # 按语义相似性分组（简化版：按关键词）
    repetition_groups = defaultdict(list)

    for flow in flows:
        for exchange in flow["exchanges"]:
            user_msg = exchange["user"]
            if not isinstance(user_msg, str) or len(user_msg) < 20:
                continue

            # 提取关键动词+名词组合
            key_patterns = extract_key_pattern(user_msg)
            if key_patterns:
                for pattern in key_patterns:
                    repetition_groups[pattern].append({
                        "message": user_msg[:200],
                        "session": flow["session_file"]
                    })

    # 过滤出高频重复
    repetitions = {
        k: v for k, v in repetition_groups.items()
        if len(v) >= min_repeat
    }

    return repetitions


def extract_key_pattern(text):
    """提取文本的关键模式"""
    patterns = []

    # 动词 + 名词模式
    verb_noun_patterns = [
        r'(检查|review|审查|分析|优化|重构|测试|实现|开发|部署|调试)\s*([^\s，。！？]{2,10})',
        r'(check|review|analyze|optimize|refactor|test|implement|develop|deploy|debug)\s+(\w+)'
    ]

    for pattern in verb_noun_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                patterns.append(f"{match[0]}_{match[1]}")

    return patterns[:3]  # 最多返回 3 个模式


def analyze_intent_distribution(flows):
    """分析意图分布"""
    intent_counts = defaultdict(int)
    intent_examples = defaultdict(list)

    for flow in flows:
        for exchange in flow["exchanges"]:
            user_msg = exchange["user"]
            if not isinstance(user_msg, str):
                continue

            for intent_name, intent_config in INTENT_PATTERNS.items():
                keywords = intent_config["keywords"]
                if any(kw in user_msg.lower() for kw in keywords):
                    intent_counts[intent_name] += 1
                    if len(intent_examples[intent_name]) < 5:
                        intent_examples[intent_name].append(user_msg[:150])
                    break

    return dict(intent_counts), dict(intent_examples)


def analyze_tool_usage(flows):
    """分析工具使用模式"""
    tool_counts = Counter()
    tool_sequences = Counter()  # 工具序列

    prev_tools = []
    for flow in flows:
        for exchange in flow["exchanges"]:
            tools = exchange.get("tools", [])
            for tool in tools:
                tool_name = tool.get("name", "unknown")
                tool_counts[tool_name] += 1

                # 记录工具序列
                if prev_tools:
                    seq = " -> ".join(prev_tools[-2:] + [tool_name])
                    tool_sequences[seq] += 1

                prev_tools.append(tool_name)

    return dict(tool_counts.most_common(20)), dict(tool_sequences.most_common(10))


def detect_workflow_patterns(flows):
    """检测工作流模式（连续的意图序列）"""
    detected_workflows = defaultdict(list)

    for flow in flows:
        # 提取意图序列
        intent_sequence = []
        for exchange in flow["exchanges"]:
            user_msg = exchange["user"]
            if not isinstance(user_msg, str):
                continue

            detected_intent = None
            for intent_name, intent_config in INTENT_PATTERNS.items():
                if any(kw in user_msg.lower() for kw in intent_config["keywords"]):
                    detected_intent = intent_name
                    break

            intent_sequence.append(detected_intent)

        # 匹配工作流模式
        for workflow_name, workflow_steps in WORKFLOW_PATTERNS.items():
            if len(intent_sequence) < len(workflow_steps):
                continue

            # 滑动窗口匹配
            for i in range(len(intent_sequence) - len(workflow_steps) + 1):
                window = intent_sequence[i:i+len(workflow_steps)]
                match_score = sum(1 for a, b in zip(window, [s[0] for s in workflow_steps]) if a == b)
                if match_score >= len(workflow_steps) * 0.7:  # 70% 匹配
                    detected_workflows[workflow_name].append({
                        "session": flow["session_file"],
                        "matched_steps": match_score,
                        "total_steps": len(workflow_steps),
                        "intents": window
                    })

    return dict(detected_workflows)


def generate_skill_content_v2(intent_name, examples, corrections, repetitions):
    """生成更有价值的 Skill 内容"""

    # 根据意图类型生成结构化内容
    skill_templates = {
        "code_review": {
            "workflow": """## 工作流程

1. **静态检查阶段**
   - 代码风格检查（命名、格式、注释）
   - 潜在问题扫描（未使用变量、死代码）
   - 安全漏洞扫描（SQL 注入、XSS）

2. **逻辑审查阶段**
   - 边界条件处理
   - 异常处理完整性
   - 并发安全性

3. **性能评估阶段**
   - 算法复杂度评估
   - 资源使用分析
   - 潜在性能瓶颈

4. **测试覆盖阶段**
   - 单元测试覆盖核心逻辑
   - 边界测试覆盖异常输入
   - 集成测试覆盖关键路径""",
            "checklist_template": """## 审查清单

### 代码质量
- [ ] 命名清晰，符合团队规范
- [ ] 无重复代码，DRY 原则
- [ ] 函数职责单一，不超过 50 行
- [ ] 无魔法数字，常量有命名
- [ ] 注释清晰，复杂逻辑有说明

### 功能正确性
- [ ] 边界条件已处理（空值、越界、异常输入）
- [ ] 异常情况已覆盖
- [ ] 无明显的逻辑错误
- [ ] 无安全隐患（SQL 注入、XSS、敏感数据泄露）

### 性能考量
- [ ] 无 O(n²) 以上复杂度（除非必要并说明）
- [ ] 数据库查询已优化
- [ ] 无内存泄漏风险
- [ ] 大数据量场景已考虑

### 测试覆盖
- [ ] 单元测试覆盖核心逻辑
- [ ] 边界测试覆盖异常输入
- [ ] 集成测试覆盖关键路径
- [ ] 测试覆盖率达标"""
        },
        "debug": {
            "workflow": """## 调试工作流

1. **问题复现阶段**
   - 记录完整的错误信息
   - 确认复现步骤
   - 收集环境信息（版本、配置）

2. **问题定位阶段**
   - 分析错误栈追踪
   - 使用二分法缩小范围
   - 检查最近变更（git diff/blame）

3. **根因分析阶段**
   - 区分表面原因和根本原因
   - 检查相关代码逻辑
   - 验证假设

4. **修复验证阶段**
   - 实现最小化修复
   - 添加回归测试
   - 验证修复不影响其他功能""",
            "checklist_template": """## 调试清单

### 问题复现
- [ ] 完整错误信息已记录
- [ ] 复现步骤已确认
- [ ] 环境信息已收集

### 问题定位
- [ ] 错误栈已分析
- [ ] 相关代码已检查
- [ ] 最近变更已审查

### 根因分析
- [ ] 表面原因已区分
- [ ] 根本原因已确定
- [ ] 假设已验证

### 修复验证
- [ ] 最小化修复已实现
- [ ] 回归测试已添加
- [ ] 副作用已检查"""
        },
        "refactor": {
            "workflow": """## 重构工作流

1. **准备阶段**
   - 确保测试全部通过
   - 识别重构范围和目标
   - 评估风险和影响

2. **执行阶段**
   - 小步重构，每次只改一点
   - 每步后运行测试
   - 保持代码可工作状态

3. **验证阶段**
   - 运行完整测试套件
   - 确认功能不变
   - 性能对比测试

4. **清理阶段**
   - 删除冗余代码
   - 更新文档和注释
   - 提交清晰的变更说明""",
            "checklist_template": """## 重构清单

### 重构前
- [ ] 所有测试通过
- [ ] 重构目标明确
- [ ] 风险已评估

### 重构中
- [ ] 小步前进
- [ ] 每步测试通过
- [ ] 代码始终可工作

### 重构后
- [ ] 功能不变
- [ ] 性能无退化
- [ ] 文档已更新

### 常见重构手法
- 提取方法/函数
- 内联方法/函数
- 提取变量
- 重命名
- 移动代码"""
        },
        "test": {
            "workflow": """## 测试工作流

1. **测试设计阶段**
   - 分析测试范围和重点
   - 设计测试用例（正常、边界、异常）
   - 确定测试策略（单元/集成/E2E）

2. **测试实现阶段**
   - 编写测试代码
   - Mock 外部依赖
   - 准备测试数据

3. **测试执行阶段**
   - 运行测试
   - 分析失败原因
   - 修复问题

4. **测试维护阶段**
   - 更新过时测试
   - 补充遗漏场景
   - 清理冗余测试""",
            "checklist_template": """## 测试清单

### 测试设计
- [ ] 测试范围已确定
- [ ] 测试用例已设计
- [ ] 测试策略已选择

### 测试实现
- [ ] 正常场景已覆盖
- [ ] 边界场景已覆盖
- [ ] 异常场景已覆盖
- [ ] 外部依赖已 Mock

### 测试质量
- [ ] 测试独立，无依赖顺序
- [ ] 测试快速，无外部等待
- [ ] 测试稳定，无随机失败
- [ ] 测试清晰，意图明确"""
        },
        "implement": {
            "workflow": """## 实现工作流

1. **需求理解阶段**
   - 确认需求细节
   - 识别技术约束
   - 设计初步方案

2. **设计阶段**
   - 模块划分
   - 接口设计
   - 数据结构设计

3. **实现阶段**
   - 编写核心逻辑
   - 处理边界情况
   - 添加错误处理

4. **验证阶段**
   - 单元测试
   - 集成测试
   - 功能验收""",
            "checklist_template": """## 实现清单

### 需求确认
- [ ] 需求细节已确认
- [ ] 技术约束已识别
- [ ] 验收标准已明确

### 设计
- [ ] 模块划分合理
- [ ] 接口设计清晰
- [ ] 数据结构合理

### 实现
- [ ] 核心逻辑正确
- [ ] 边界情况处理
- [ ] 错误处理完整

### 验证
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 功能验收通过"""
        },
        "api": {
            "workflow": """## API 开发工作流

1. **设计阶段**
   - 定义 API 接口（路径、方法、参数）
   - 设计请求/响应格式
   - 设计错误处理

2. **实现阶段**
   - 实现路由处理
   - 实现业务逻辑
   - 实现数据验证

3. **文档阶段**
   - 编写 API 文档
   - 添加使用示例
   - 说明错误码

4. **测试阶段**
   - 单元测试
   - 集成测试
   - 性能测试""",
            "checklist_template": """## API 开发清单

### 设计
- [ ] 路径设计符合 RESTful
- [ ] HTTP 方法语义正确
- [ ] 参数验证规则完整

### 实现
- [ ] 输入验证完整
- [ ] 错误处理完整
- [ ] 日志记录完整

### 安全
- [ ] 认证机制正确
- [ ] 权限检查完整
- [ ] 敏感数据保护

### 文档
- [ ] 接口文档完整
- [ ] 使用示例清晰
- [ ] 错误码说明完整"""
        }
    }

    template = skill_templates.get(intent_name, {
        "workflow": "1. 步骤一\n2. 步骤二\n3. 步骤三",
        "checklist_template": "- [ ] 检查项一\n- [ ] 检查项二\n- [ ] 检查项三"
    })

    # 添加从修正模式中提取的额外检查项
    additional_checks = []
    for correction_type, items in corrections.items():
        if items:
            check_item = f"- [ ] 注意避免：{correction_type.replace('_', ' ')}"
            additional_checks.append(check_item)

    # 添加从重复模式中提取的常见操作
    common_operations = []
    for pattern, items in repetitions.items():
        if len(items) >= 3:
            operation = f"- [ ] 常见操作：{pattern.replace('_', ' ')}"
            common_operations.append(operation)

    # 构建最终内容
    content = {
        "workflow": template["workflow"],
        "checklist": template["checklist_template"],
        "additional_checks": additional_checks[:5],
        "common_operations": common_operations[:5],
        "examples": examples[:5]
    }

    return content


def generate_detailed_skill_proposal(intent_name, intent_count, examples, corrections, repetitions, tool_usage):
    """生成详细的 Skill 提案"""

    skill_templates = {
        "code_review": {
            "name": "review-checklist",
            "description": "代码审查清单，涵盖代码质量、功能正确性、性能和安全",
            "triggers": ["review", "审查", "检查代码", "code review"]
        },
        "debug": {
            "name": "debug-workflow",
            "description": "调试工作流，从问题复现到修复验证的完整流程",
            "triggers": ["debug", "调试", "报错", "错误", "异常"]
        },
        "refactor": {
            "name": "refactor-guide",
            "description": "重构指南，安全重构的完整流程和检查项",
            "triggers": ["refactor", "重构", "优化", "改进"]
        },
        "test": {
            "name": "test-workflow",
            "description": "测试工作流，从测试设计到测试维护的完整流程",
            "triggers": ["test", "测试", "单元测试", "覆盖率"]
        },
        "implement": {
            "name": "implementation-guide",
            "description": "功能实现指南，从需求理解到功能验收的完整流程",
            "triggers": ["implement", "实现", "开发", "新增功能"]
        },
        "api": {
            "name": "api-standard",
            "description": "API 开发规范，涵盖设计、实现、安全和文档",
            "triggers": ["api", "接口", "endpoint", "rest"]
        },
        "document": {
            "name": "documentation-guide",
            "description": "文档编写指南，代码注释、API 文档和 README",
            "triggers": ["document", "文档", "注释", "readme"]
        },
        "deploy": {
            "name": "deploy-workflow",
            "description": "部署工作流，环境配置、发布流程和回滚策略",
            "triggers": ["deploy", "部署", "发布", "上线"]
        },
        "security": {
            "name": "security-checklist",
            "description": "安全检查清单，常见漏洞扫描和防护措施",
            "triggers": ["security", "安全", "漏洞", "权限"]
        },
        "architecture": {
            "name": "architecture-design",
            "description": "架构设计指南，系统设计和技术选型",
            "triggers": ["architecture", "架构", "设计", "方案"]
        },
        "explain": {
            "name": "knowledge-explain",
            "description": "知识解释模板，概念解释和最佳实践",
            "triggers": ["explain", "解释", "说明", "什么是"]
        }
    }

    template = skill_templates.get(intent_name, {
        "name": f"{intent_name}-workflow",
        "description": f"{intent_name} 相关工作流",
        "triggers": [intent_name]
    })

    # 生成详细内容
    content = generate_skill_content_v2(intent_name, examples, corrections, repetitions)

    # 计算置信度（基于多个因素）
    confidence_factors = {
        "frequency": min(intent_count / 10, 1.0),
        "has_corrections": 0.2 if corrections else 0,
        "has_repetitions": 0.1 if repetitions else 0,
        "has_examples": 0.1 if examples else 0
    }
    confidence = sum(confidence_factors.values())

    # 生成推荐理由
    reasons = []
    if intent_count >= 10:
        reasons.append(f"高频操作（{intent_count} 次）")
    if corrections:
        reasons.append(f"存在 {len(corrections)} 类修正模式（说明 Skill 可以避免重复纠正）")
    if repetitions:
        reasons.append(f"存在 {len(repetitions)} 类重复操作（说明 Skill 可以自动化）")

    return {
        "suggested_skill": {
            "name": template["name"],
            "description": template["description"],
            "triggers": template["triggers"],
            "workflow": content["workflow"],
            "checklist": content["checklist"],
            "additional_checks": content["additional_checks"],
            "common_operations": content["common_operations"]
        },
        "sample_prompts": examples,
        "occurrence_count": intent_count,
        "confidence": round(confidence, 2),
        "confidence_factors": confidence_factors,
        "recommendation_reasons": reasons,
        "corrections_found": list(corrections.keys()) if corrections else [],
        "repetitions_found": list(repetitions.keys()) if repetitions else []
    }


def call_llm_for_analysis(prompts, api_key=None):
    """使用 LLM 进行深度语义分析（可选）"""
    if not api_key:
        return None

    try:
        import openai

        client = openai.OpenAI(api_key=api_key)

        prompt_text = "\n".join([f"{i+1}. {p[:100]}" for i, p in enumerate(prompts[:20])])

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一个分析助手，分析用户的提示词模式，提取可自动化的工作流。"},
                {"role": "user", "content": f"分析以下提示词，识别：1. 高频模式 2. 可自动化的工作流 3. 推荐创建的 Skill\n\n{prompt_text}"}
            ]
        )

        return response.choices[0].message.content
    except Exception as e:
        print(f"LLM 分析失败: {e}")
        return None


def generate_report(result: Dict, output_file: str):
    """生成可读的分析报告"""

    report = f"""# Skill 进化分析报告

**分析时间**: {result['analysis_time']}
**分析版本**: {result['analysis_version']}

---

## 一、总体概览

| 指标 | 数值 |
|------|------|
| 总提示词数 | {result['summary']['total_prompts']} |
| 唯一提示词数 | {result['summary']['unique_prompts']} |
| 发现的意图类型 | {len(result['summary']['intent_distribution'])} |
| Skill 提案数 | {len(result['skill_proposals'])} |

---

## 二、意图分布

| 意图类型 | 出现次数 | 占比 |
|----------|----------|------|
"""

    total = result['summary']['total_prompts']
    for intent, count in sorted(result['summary']['intent_distribution'].items(), key=lambda x: -x[1]):
        pct = count / total * 100 if total > 0 else 0
        report += f"| {intent} | {count} | {pct:.1f}% |\n"

    report += """
---

## 三、Skill 提案详情

"""

    for i, proposal in enumerate(result['skill_proposals'], 1):
        skill = proposal['suggested_skill']
        report += f"""### {i}. {skill['name']}

**描述**: {skill['description']}

**触发词**: {', '.join(skill['triggers'])}

**置信度**: {proposal['confidence']:.0%}

**出现次数**: {proposal['occurrence_count']}

**推荐理由**:
"""
        for reason in proposal.get('recommendation_reasons', []):
            report += f"- {reason}\n"

        report += """
**示例提示词**:
"""
        for j, prompt in enumerate(proposal.get('sample_prompts', [])[:3], 1):
            report += f"{j}. {prompt[:100]}...\n"

        report += "\n---\n\n"

    report += """## 四、行动建议

### 立即行动
1. 创建高频 Skill（出现次数 ≥ 10 的意图）
2. 重点优化置信度 ≥ 100% 的 Skill

### 短期优化
1. 根据用户实际反馈调整 Skill 内容
2. 添加更多示例和反例

### 长期维护
1. 定期重新分析会话日志（建议每月一次）
2. 根据 Skill 使用频率决定是否归档

---

> 此报告由 `analyze_conversations_v2.py --report` 自动生成
"""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    return output_file


def main():
    parser = argparse.ArgumentParser(description="深度分析 Claude Code 会话日志")
    parser.add_argument("--project", help="指定项目路径")
    parser.add_argument("--all", action="store_true", help="分析所有项目")
    parser.add_argument("--limit", type=int, default=1000, help="限制历史记录数量")
    parser.add_argument("--min-count", type=int, default=3, help="最小出现次数")
    parser.add_argument("--output", default="deep-analysis.json", help="输出文件")
    parser.add_argument("--use-llm", action="store_true", help="使用 LLM 进行深度分析")
    parser.add_argument("--deep", action="store_true", help="启用深度分析模式")
    parser.add_argument("--report", action="store_true", help="生成可读报告")
    args = parser.parse_args()

    print("📂 加载会话历史...")

    all_corrections = defaultdict(list)
    all_repetitions = defaultdict(list)

    if args.project:
        sessions = load_project_sessions(args.project)
        flows = extract_conversation_flows(sessions)
        prompts = []
        for flow in flows:
            for exchange in flow["exchanges"]:
                user_msg = exchange["user"]
                if isinstance(user_msg, str) and len(user_msg) > 10:
                    prompts.append(user_msg)

        # 深度分析
        if args.deep:
            all_corrections = detect_correction_patterns(flows)
            all_repetitions = detect_repetition_patterns(flows)
    else:
        records = load_history(args.limit)
        prompts = []
        for record in records:
            display = record.get("display", "").strip()
            if display and len(display) > 10:
                prompts.append(display)
        flows = []

    print(f"📊 分析 {len(prompts)} 条提示词...")

    if not prompts:
        print("❌ 没有找到提示词数据")
        return

    # 意图分析
    intent_counts, intent_examples = analyze_intent_distribution(flows if flows else [{"exchanges": [{"user": p, "assistant": "", "tools": []}]} for p in prompts])

    # 工具使用分析
    tool_counts, tool_sequences = analyze_tool_usage(flows) if flows else ({}, {})

    # 工作流模式检测
    workflow_patterns = detect_workflow_patterns(flows) if flows else {}

    # LLM 分析（可选）
    llm_analysis = None
    if args.use_llm:
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            print("🤖 使用 LLM 进行深度分析...")
            llm_analysis = call_llm_for_analysis(prompts, api_key)
        else:
            print("⚠️ 未设置 API Key，跳过 LLM 分析")

    # 生成 Skill 提案
    proposals = []
    for intent_name, count in sorted(intent_counts.items(), key=lambda x: -x[1]):
        if count >= args.min_count:
            # 获取该意图的修正和重复模式
            intent_corrections = {}
            intent_repetitions = {}

            # 简化：使用全局的修正和重复模式
            proposal = generate_detailed_skill_proposal(
                intent_name,
                count,
                intent_examples.get(intent_name, []),
                all_corrections,
                all_repetitions,
                tool_counts
            )
            proposals.append(proposal)

    # 按置信度排序
    proposals.sort(key=lambda x: x["confidence"], reverse=True)

    result = {
        "analysis_time": datetime.now().isoformat(),
        "analysis_version": "2.0",
        "summary": {
            "total_prompts": len(prompts),
            "unique_prompts": len(set(prompts)),
            "intent_distribution": intent_counts,
            "tool_usage": tool_counts,
            "tool_sequences": tool_sequences,
            "workflow_patterns": {k: len(v) for k, v in workflow_patterns.items()},
            "correction_patterns": {k: len(v) for k, v in all_corrections.items()},
            "repetition_patterns": {k: len(v) for k, v in all_repetitions.items()}
        },
        "correction_details": {k: v[:3] for k, v in all_corrections.items()},
        "repetition_details": {k: v[:3] for k, v in all_repetitions.items()},
        "workflow_details": {k: v[:2] for k, v in workflow_patterns.items()},
        "skill_proposals": proposals,
        "llm_analysis": llm_analysis
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 分析完成！结果保存到 {args.output}")
    print(f"\n📈 分析摘要：")
    print(f"  - 总提示词: {len(prompts)}")
    print(f"  - 意图分布: {dict(list(intent_counts.items())[:5])}")
    print(f"  - 修正模式: {len(all_corrections)} 类")
    print(f"  - 重复模式: {len(all_repetitions)} 类")
    print(f"  - 工作流模式: {len(workflow_patterns)} 类")
    print(f"\n🎯 发现 {len(proposals)} 个 Skill 提案：")
    for p in proposals[:5]:
        print(f"  - {p['suggested_skill']['name']}: {p['suggested_skill']['description']}")
        print(f"    置信度: {p['confidence']:.0%} | 次数: {p['occurrence_count']}")
        if p['recommendation_reasons']:
            print(f"    推荐理由: {', '.join(p['recommendation_reasons'])}")

    # 生成可读报告
    if args.report:
        report_file = args.output.replace('.json', '-report.md')
        generate_report(result, report_file)
        print(f"\n📄 可读报告已生成: {report_file}")


if __name__ == "__main__":
    main()
