#!/usr/bin/env python3
"""
create_skill_v2.py - 创建高质量的 Claude Code Skill 文件

改进：
1. 根据意图类型生成定制化内容
2. 包含完整的工作流程和检查清单
3. 添加示例和反例
4. 包含常见陷阱和解决方案
5. 自动生成 Evolution Log

用法：
    python create_skill_v2.py --name review-checklist --description "代码审查清单"
    python create_skill_v2.py --from-analysis deep-analysis.json --top 3
    python create_skill_v2.py --intent code_review --output-dir ./skills
"""

import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

SKILLS_DIR = Path.home() / ".claude" / "skills"


# 高质量的 Skill 模板
def get_skill_template(intent_name: str) -> Dict:
    """根据意图类型返回 Skill 模板"""

    templates = {
        "code_review": {
            "workflow": """### 1. 静态检查阶段
- 代码风格检查（命名、格式、注释）
- 潜在问题扫描（未使用变量、死代码）
- 安全漏洞扫描（SQL 注入、XSS）
- 依赖检查（版本冲突、已知漏洞）

### 2. 逻辑审查阶段
- 边界条件处理（空值、越界、异常输入）
- 异常处理完整性
- 并发安全性（线程安全、竞态条件）
- 资源管理（内存泄漏、文件句柄）

### 3. 性能评估阶段
- 算法复杂度评估
- 数据库查询优化
- 缓存策略检查
- 潜在性能瓶颈识别

### 4. 测试覆盖阶段
- 单元测试覆盖核心逻辑
- 边界测试覆盖异常输入
- 集成测试覆盖关键路径
- 测试可读性和可维护性""",
            "checklist": """### 代码质量
- [ ] 命名清晰，符合团队规范
- [ ] 无重复代码，DRY 原则
- [ ] 函数职责单一，不超过 50 行
- [ ] 无魔法数字，常量有命名
- [ ] 注释清晰，复杂逻辑有说明

### 功能正确性
- [ ] 边界条件已处理
- [ ] 异常情况已覆盖
- [ ] 无明显的逻辑错误
- [ ] 无安全隐患

### 性能考量
- [ ] 无 O(n²) 以上复杂度
- [ ] 数据库查询已优化
- [ ] 无内存泄漏风险
- [ ] 大数据量场景已考虑

### 测试覆盖
- [ ] 单元测试覆盖核心逻辑
- [ ] 边界测试覆盖异常输入
- [ ] 集成测试覆盖关键路径
- [ ] 测试覆盖率达标""",
            "examples": """### 好的示例

**检查边界条件：**
```python
def get_user(user_id: str) -> Optional[User]:
    if not user_id:
        return None
    return db.query(User).filter_by(id=user_id).first()
```

**有意义的错误信息：**
```python
raise ValueError(f"Invalid user_id: {user_id}, expected UUID format")
```""",
            "anti_patterns": """### 常见陷阱

1. **过度信任输入**
   - 问题：假设用户输入总是有效的
   - 解决：始终验证和清理输入

2. **忽略错误处理**
   - 问题：try-catch 捕获但不处理
   - 解决：至少记录日志，或向上传播

3. **过度优化**
   - 问题：过早优化，牺牲可读性
   - 解决：先写清晰代码，必要时再优化"""
        },
        "debug": {
            "workflow": """### 1. 问题复现阶段
- 记录完整的错误信息
- 确认稳定的复现步骤
- 收集环境信息

### 2. 问题定位阶段
- 分析错误栈追踪
- 使用二分法缩小范围
- 检查最近变更

### 3. 根因分析阶段
- 区分表面原因和根本原因
- 检查相关代码逻辑
- 验证假设

### 4. 修复验证阶段
- 实现最小化修复
- 添加回归测试
- 验证修复不影响其他功能""",
            "checklist": """### 问题复现
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
- [ ] 副作用已检查""",
            "examples": """### 调试流程示例

**问题：用户登录失败**

1. 复现阶段
   - 错误信息：AuthenticationException
   - 复现步骤：使用过期 token 登录
   - 环境：生产环境，v2.3.1

2. 定位阶段
   - 错误栈指向 AuthService.validateToken()
   - 检查 token 验证逻辑

3. 根因分析
   - 根本原因：时区处理不一致

4. 修复验证
   - 修改时区处理逻辑
   - 添加 token 过期测试用例""",
            "anti_patterns": """### 调试陷阱

1. **只修复表面症状**
   - 问题：修复了错误信息，没修复根因
   - 解决：问 5 次 Why

2. **跳过复现阶段**
   - 问题：假设问题原因，盲目修改
   - 解决：先确认能稳定复现

3. **忽略环境差异**
   - 问题：本地正常，线上失败
   - 解决：记录完整环境信息"""
        },
        "refactor": {
            "workflow": """### 1. 准备阶段
- 确保所有测试通过
- 识别重构范围和目标
- 评估风险和影响

### 2. 执行阶段
- 小步重构，每次只改一点
- 每步后运行测试
- 保持代码可工作状态

### 3. 验证阶段
- 运行完整测试套件
- 确认功能不变
- 性能对比测试

### 4. 清理阶段
- 删除冗余代码
- 更新文档和注释
- 提交清晰的变更说明""",
            "checklist": """### 重构前
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
- [ ] 文档已更新""",
            "examples": """### 重构示例

**重构前：**
```python
def calculate_total(items):
    total = 0
    for item in items:
        if item['type'] == 'book':
            total += item['price'] * 0.9
        elif item['type'] == 'electronics':
            total += item['price'] * 1.05
        else:
            total += item['price']
    return total
```

**重构后：**
```python
def calculate_total(items):
    return sum(calculate_item_price(item) for item in items)

def calculate_item_price(item):
    discount_map = {'book': 0.9, 'electronics': 1.05}
    multiplier = discount_map.get(item['type'], 1.0)
    return item['price'] * multiplier
```""",
            "anti_patterns": """### 重构陷阱

1. **大爆炸重构**
   - 问题：一次改太多，难以定位问题
   - 解决：小步重构

2. **边重构边加功能**
   - 问题：混在一起，难以追踪
   - 解决：重构归重构，功能归功能

3. **没有测试保护**
   - 问题：重构后不知道是否破坏功能
   - 解决：先写测试，再重构"""
        },
        "test": {
            "workflow": """### 1. 测试设计阶段
- 分析测试范围和重点
- 设计测试用例
- 确定测试策略

### 2. 测试实现阶段
- 编写测试代码
- Mock 外部依赖
- 准备测试数据

### 3. 测试执行阶段
- 运行测试
- 分析失败原因
- 修复问题

### 4. 测试维护阶段
- 更新过时测试
- 补充遗漏场景
- 清理冗余测试""",
            "checklist": """### 测试设计
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
- [ ] 测试清晰，意图明确""",
            "examples": """### 好的测试示例

```python
def test_calculate_total_with_discount():
    # Arrange
    items = [
        {'type': 'book', 'price': 100},
        {'type': 'electronics', 'price': 200},
    ]

    # Act
    total = calculate_total(items)

    # Assert
    assert total == 300
```

### 测试命名规范
- test_<method>_<scenario>_<expected>
- test_calculate_total_with_book_discount_returns_discounted_price""",
            "anti_patterns": """### 测试陷阱

1. **测试实现细节**
   - 问题：测试内部实现，而非行为
   - 解决：测试公开接口和预期行为

2. **过度 Mock**
   - 问题：Mock 太多，测试变得脆弱
   - 解决：只 Mock 外部依赖

3. **测试间依赖**
   - 问题：测试必须按特定顺序执行
   - 解决：每个测试独立"""
        },
        "implement": {
            "workflow": """### 1. 需求理解阶段
- 确认需求细节
- 识别技术约束
- 设计初步方案

### 2. 设计阶段
- 模块划分
- 接口设计
- 数据结构设计

### 3. 实现阶段
- 编写核心逻辑
- 处理边界情况
- 添加错误处理

### 4. 验证阶段
- 单元测试通过
- 集成测试通过
- 功能验收通过""",
            "checklist": """### 需求确认
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
- [ ] 功能验收通过""",
            "examples": """### 实现示例

**需求：实现用户登录功能**

1. 需求确认
   - 输入：用户名、密码
   - 输出：token 或错误
   - 验收标准：正确登录、错误处理

2. 设计
   - 验证输入
   - 查询用户
   - 验证密码
   - 生成 token

3. 实现
   - 核心逻辑
   - 边界处理
   - 错误处理""",
            "anti_patterns": """### 实现陷阱

1. **过度设计**
   - 问题：设计复杂，难以实现
   - 解决：YAGNI 原则

2. **忽略边界情况**
   - 问题：正常情况工作，边界情况失败
   - 解决：列出所有边界情况

3. **先实现后测试**
   - 问题：测试成为负担，覆盖率低
   - 解决：TDD"""
        },
        "api": {
            "workflow": """### 1. 设计阶段
- 定义 API 接口
- 设计请求/响应格式
- 设计错误处理

### 2. 实现阶段
- 实现路由处理
- 实现业务逻辑
- 实现数据验证

### 3. 文档阶段
- 编写 API 文档
- 添加使用示例
- 说明错误码

### 4. 测试阶段
- 单元测试
- 集成测试
- 性能测试""",
            "checklist": """### 设计
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
- [ ] API 文档完整
- [ ] 使用示例清晰
- [ ] 错误码说明完整""",
            "examples": """### RESTful API 设计

**资源路径：**
```
GET    /api/v1/users          # 获取用户列表
GET    /api/v1/users/{id}     # 获取单个用户
POST   /api/v1/users          # 创建用户
PUT    /api/v1/users/{id}     # 更新用户
DELETE /api/v1/users/{id}     # 删除用户
```

**响应格式：**
```json
{
  "code": 0,
  "message": "success",
  "data": {"id": 1, "name": "John"}
}
```""",
            "anti_patterns": """### API 设计陷阱

1. **动词化路径**
   - 问题：/api/getUser
   - 解决：使用 RESTful 风格

2. **不一致的错误格式**
   - 问题：不同接口返回不同格式
   - 解决：统一错误码和格式

3. **忽略版本控制**
   - 问题：API 变更导致客户端崩溃
   - 解决：路径中包含版本号"""
        }
    }

    return templates.get(intent_name, get_default_template())


def get_default_template() -> Dict:
    """返回默认模板"""
    return {
        "workflow": """### 1. 准备阶段
- 确认任务目标
- 收集必要信息
- 制定执行计划

### 2. 执行阶段
- 按步骤执行
- 记录关键决策
- 处理异常情况

### 3. 验证阶段
- 检查执行结果
- 验证目标达成
- 记录问题和改进

### 4. 收尾阶段
- 整理文档
- 归档资源
- 总结经验""",
        "checklist": """### 准备
- [ ] 任务目标明确
- [ ] 必要信息完整
- [ ] 执行计划合理

### 执行
- [ ] 按计划执行
- [ ] 异常情况处理
- [ ] 关键决策记录

### 验证
- [ ] 结果符合预期
- [ ] 目标已达成
- [ ] 问题已记录

### 收尾
- [ ] 文档完整
- [ ] 资源归档
- [ ] 经验总结""",
        "examples": """### 示例

根据具体任务补充示例...""",
        "anti_patterns": """### 常见陷阱

1. **目标不明确**
   - 解决：开始前确认具体目标

2. **信息不完整**
   - 解决：提前收集必要信息

3. **缺少验证**
   - 解决：执行后验证结果"""
    }


def get_skill_meta(intent_name: str) -> Dict:
    """获取 Skill 元信息"""
    meta_map = {
        "code_review": {"name": "review-checklist", "description": "代码审查清单，涵盖代码质量、功能正确性、性能和安全", "triggers": ["review", "审查", "检查代码"]},
        "debug": {"name": "debug-workflow", "description": "调试工作流，从问题复现到修复验证的完整流程", "triggers": ["debug", "调试", "报错", "错误"]},
        "refactor": {"name": "refactor-guide", "description": "重构指南，安全重构的完整流程和检查项", "triggers": ["refactor", "重构", "优化"]},
        "test": {"name": "test-workflow", "description": "测试工作流，从测试设计到测试维护的完整流程", "triggers": ["test", "测试", "单元测试"]},
        "implement": {"name": "implementation-guide", "description": "功能实现指南，从需求理解到功能验收的完整流程", "triggers": ["implement", "实现", "开发"]},
        "api": {"name": "api-standard", "description": "API 开发规范，涵盖设计、实现、安全和文档", "triggers": ["api", "接口", "endpoint"]},
        "document": {"name": "documentation-guide", "description": "文档编写指南，代码注释、API 文档和 README", "triggers": ["document", "文档", "注释"]},
        "deploy": {"name": "deploy-workflow", "description": "部署工作流，环境配置、发布流程和回滚策略", "triggers": ["deploy", "部署", "发布"]},
        "security": {"name": "security-checklist", "description": "安全检查清单，常见漏洞扫描和防护措施", "triggers": ["security", "安全", "漏洞"]},
    }
    return meta_map.get(intent_name, {"name": f"{intent_name}-workflow", "description": f"{intent_name} 相关工作流", "triggers": [intent_name]})


def generate_skill_markdown(name: str, description: str, triggers: List[str],
                           workflow: str, checklist: str, examples: str,
                           anti_patterns: str, sample_prompts: List[str],
                           source: str = "手动创建") -> str:
    """生成完整的 Skill Markdown 文件"""

    now = datetime.now().strftime("%Y-%m-%d")

    template = f'''---
name: {name}
description: {description}
triggers: {json.dumps(triggers, ensure_ascii=False)}
version: 1.0.0
created: {now}
---

# {name.replace("-", " ").title()}

## Overview

{description}

## Workflow

{workflow}

## Checklist

{checklist}

## Examples

{examples}

## Common Pitfalls

{anti_patterns}

## Sample Prompts

用户可能这样触发这个 Skill：

'''
    for i, prompt in enumerate(sample_prompts[:5], 1):
        template += f'{i}. "{prompt[:100]}..."\n'

    template += f'''
## Evolution Log

### v1.0.0 ({now})
- 初始版本
- 触发：从会话日志中自动生成
- 来源：{source}
- 内容：基础工作流程和检查清单

---

> 此 Skill 由 analyze_conversations_v2.py 自动生成，建议根据实际使用情况迭代优化。
'''
    return template


def create_skill_from_intent(intent_name: str, sample_prompts: List[str],
                             output_dir: Path, source: str = "自动分析") -> Path:
    """根据意图类型创建 Skill"""

    template = get_skill_template(intent_name)
    meta = get_skill_meta(intent_name)

    name = meta["name"]
    description = meta["description"]
    triggers = meta["triggers"]

    # 生成 Markdown
    content = generate_skill_markdown(
        name=name,
        description=description,
        triggers=triggers,
        workflow=template["workflow"],
        checklist=template["checklist"],
        examples=template["examples"],
        anti_patterns=template["anti_patterns"],
        sample_prompts=sample_prompts,
        source=source
    )

    # 写入文件
    skill_dir = output_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content, encoding='utf-8')

    print(f"✅ Skill 已创建: {skill_file}")
    return skill_file


def create_skill_from_analysis(analysis_file: str, top: int, output_dir: Path) -> List[Path]:
    """从分析结果创建 Skill"""
    with open(analysis_file, 'r', encoding='utf-8') as f:
        analysis = json.load(f)

    created = []
    for proposal in analysis.get("skill_proposals", [])[:top]:
        skill = proposal["suggested_skill"]

        # 确定意图类型
        intent_name = skill["name"].replace("-workflow", "").replace("-checklist", "").replace("-guide", "").replace("-standard", "")
        intent_name = intent_name.replace("-", "_")

        # 获取模板
        template = get_skill_template(intent_name)

        # 使用分析结果中的内容（如果有）
        workflow = skill.get("workflow", template["workflow"])
        checklist = skill.get("checklist", template["checklist"])

        # 生成 Markdown
        content = generate_skill_markdown(
            name=skill["name"],
            description=skill["description"],
            triggers=skill.get("triggers", []),
            workflow=workflow,
            checklist=checklist,
            examples=template["examples"],
            anti_patterns=template["anti_patterns"],
            sample_prompts=proposal.get("sample_prompts", []),
            source=f"自动分析: {analysis_file}"
        )

        # 写入文件
        skill_dir = output_dir / skill["name"]
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(content, encoding='utf-8')

        created.append(skill_file)
        print(f"✅ Skill 已创建: {skill_file}")

    return created


def main():
    parser = argparse.ArgumentParser(description="创建高质量的 Claude Code Skill")
    parser.add_argument("--name", help="Skill 名称")
    parser.add_argument("--description", help="Skill 描述")
    parser.add_argument("--triggers", nargs="+", help="触发关键词")
    parser.add_argument("--intent", help="意图类型（code_review, debug, refactor, test, implement, api）")
    parser.add_argument("--from-analysis", help="从分析结果创建")
    parser.add_argument("--top", type=int, default=3, help="创建前 N 个 Skill")
    parser.add_argument("--output-dir", default=None, help="输出目录（默认 ~/.claude/skills）")
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else SKILLS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.from_analysis:
        print(f"📂 从 {args.from_analysis} 创建 Skill...")
        created = create_skill_from_analysis(args.from_analysis, args.top, output_dir)
        print(f"\n✅ 创建了 {len(created)} 个 Skill")
    elif args.intent:
        print(f"📂 从意图类型 {args.intent} 创建 Skill...")
        created = create_skill_from_intent(
            intent_name=args.intent,
            sample_prompts=[],
            output_dir=output_dir,
            source="手动指定意图"
        )
        print(f"\n✅ 创建了 Skill: {created}")
    elif args.name and args.description:
        # 手动创建，使用默认模板
        template = get_default_template()
        content = generate_skill_markdown(
            name=args.name,
            description=args.description,
            triggers=args.triggers or [args.name],
            workflow=template["workflow"],
            checklist=template["checklist"],
            examples=template["examples"],
            anti_patterns=template["anti_patterns"],
            sample_prompts=[],
            source="手动创建"
        )

        skill_dir = output_dir / args.name
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(content, encoding='utf-8')
        print(f"✅ Skill 已创建: {skill_file}")
    else:
        print("请提供以下之一：")
        print("  --from-analysis <文件>  从分析结果创建")
        print("  --intent <意图类型>     从意图模板创建")
        print("  --name <名称> --description <描述>  手动创建")


if __name__ == "__main__":
    main()
