// code-review.workflow.js
// 三 Agent 流水线代码审查：分析 → 检测 → 修复建议 → 汇总
// 用法：claude -p "/workflow code-review.workflow.js"
//       或在 Claude Code 会话中 /workflow code-review.workflow.js

export const meta = {
  name: 'code-review',
  description: '三 Agent 流水线代码审查：分析 → 检测 → 修复建议',
  phases: [
    { title: 'Analyze', detail: 'Agent 1：结构化代码分析' },
    { title: 'Detect', detail: 'Agent 2：多维度问题检测（Bug/安全/性能）' },
    { title: 'Fix', detail: 'Agent 3：生成修复建议' },
    { title: 'Report', detail: '汇总输出 Review Report' }
  ]
}

// ============================================
// Phase 1：获取 PR 信息
// ============================================
phase('Analyze')

const prInfo = await agent(
  `获取当前分支相对于 main 的改动：
  1. 运行 git diff main...HEAD --stat 获取改动文件列表
  2. 运行 git diff main...HEAD 获取完整 diff
  3. 识别出所有被修改的关键文件（接口定义、核心逻辑、测试）
  4. 输出文件列表和每个文件的改动行数`
)

// ============================================
// Phase 2：Agent 1 - 结构化代码分析
// ============================================
const ANALYSIS_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    changedFiles: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          path: { type: 'string' },
          changeType: { type: 'string' },
          purpose: { type: 'string' },
          riskLevel: { type: 'string' },
          callers: { type: 'array', items: { type: 'string' } },
          dependencies: { type: 'array', items: { type: 'string' } }
        },
        required: ['path', 'changeType', 'purpose', 'riskLevel']
      }
    },
    affectedModules: { type: 'array', items: { type: 'string' } },
    crossCuttingConcerns: { type: 'array', items: { type: 'string' } }
  },
  required: ['summary', 'changedFiles', 'affectedModules']
}

const analysis = await agent(
  `## 任务
你是代码分析专家。基于以下 PR diff 和仓库上下文，生成结构化的改动摘要。

## PR 信息
${prInfo}

## 分析要求
对每个改动文件：
1. 识别改动类型（新增/修改/删除）
2. 说明业务目的（这段代码要解决什么问题）
3. 追溯调用链（grep 查找谁调用了这个函数/方法）
4. 追溯依赖链（这个文件 import 了什么）
5. 评估风险等级（high：改动了核心接口或数据库操作；medium：改动了业务逻辑；low：纯重构或测试）

## 注意事项
- 只描述事实，不评价好坏
- 如果你不确定某个改动的目的，标记为 "uncertain"
- 忽略纯格式变更（缩进、换行、注释）`,
  {
    phase: 'Analyze',
    schema: ANALYSIS_SCHEMA
  }
)

log(`Agent 1 完成：分析了 ${analysis.changedFiles.length} 个文件，识别出 ${analysis.affectedModules.length} 个受影响模块`)

// ============================================
// Phase 3：Agent 2 - 多维度并行检测
// ============================================
phase('Detect')

const ISSUE_SCHEMA = {
  type: 'object',
  properties: {
    dimension: { type: 'string' },
    issues: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          severity: { type: 'string' },
          file: { type: 'string' },
          line: { type: 'number' },
          description: { type: 'string' },
          trigger: { type: 'string' },
          impact: { type: 'string' }
        },
        required: ['id', 'severity', 'file', 'line', 'description']
      }
    }
  },
  required: ['dimension', 'issues']
}

const DETECTION_DIMENSIONS = [
  {
    key: 'bugs',
    prompt: `你是 Bug 猎手。基于以下代码分析，找出所有可能导致生产事故的逻辑错误。
重点关注：边界条件遗漏、并发安全、错误处理缺陷、逻辑缺陷。

代码分析摘要：${JSON.stringify(analysis, null, 2)}

对每个发现的 Bug：
- 标注严重程度（critical/high/medium/low）
- 精确到文件和行号
- 说明触发条件和最坏后果
- 不要提修复建议`
  },
  {
    key: 'security',
    prompt: `你是安全审计专家。基于以下代码分析，找出所有安全漏洞。
检测清单：注入攻击（SQL/命令）、认证授权绕过、敏感信息泄露、不安全的加密使用、输入验证缺失。

代码分析摘要：${JSON.stringify(analysis, null, 2)}

对每个安全漏洞：
- 标注严重程度和 CWE 编号（如适用）
- 精确到文件和行号
- 说明攻击向量和影响范围`
  },
  {
    key: 'performance',
    prompt: `你是性能分析专家。基于以下代码分析，找出所有性能隐患。
检测清单：N+1 查询、不必要的内存分配、阻塞 I/O、缺少缓存、大对象拷贝。

代码分析摘要：${JSON.stringify(analysis, null, 2)}

对每个性能问题：
- 标注影响程度
- 说明在什么数据量/并发量下会成为瓶颈`
  }
]

const detectionResults = await pipeline(
  DETECTION_DIMENSIONS,
  d => agent(d.prompt, {
    label: `detect:${d.key}`,
    phase: 'Detect',
    schema: ISSUE_SCHEMA
  }),
  result => {
    const allIssues = result.flatMap(r => r?.issues || [])
    const seen = new Set()
    const deduped = allIssues.filter(i => {
      const key = `${i.file}:${i.line}`
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
    return { issues: deduped, totalRaw: allIssues.length, deduped: deduped.length }
  }
)

const allDetectedIssues = detectionResults.filter(Boolean)
const totalIssues = allDetectedIssues.reduce((sum, r) => sum + (r?.issues?.length || 0), 0)

log(`Agent 2 完成：三个维度共检测到 ${totalIssues} 个问题（去重后）`)

// ============================================
// Phase 4：Agent 3 - 修复建议（只处理 critical/high）
// ============================================
phase('Fix')

const FIX_SCHEMA = {
  type: 'object',
  properties: {
    issueRef: { type: 'string' },
    patch: { type: 'string' },
    explanation: { type: 'string' },
    riskOfFix: { type: 'string' },
    testSuggestion: { type: 'string' }
  },
  required: ['issueRef', 'patch', 'explanation', 'riskOfFix']
}

const criticalAndHigh = allDetectedIssues
  .flatMap(r => r?.issues || [])
  .filter(i => i.severity === 'critical' || i.severity === 'high')

const fixes = await pipeline(
  criticalAndHigh,
  issue => agent(
    `## 任务
你是代码修复专家。针对以下问题，生成精确的修复方案。

## 问题
- ID: ${issue.id}
- 严重程度: ${issue.severity}
- 文件: ${issue.file}
- 行号: ${issue.line}
- 问题描述: ${issue.description}
- 触发条件: ${issue.trigger}
- 影响: ${issue.impact}

## 上下文
${JSON.stringify(analysis, null, 2)}

## 修复要求
1. 最小改动原则
2. unified diff 格式
3. 评估修复本身的风险
4. 给出测试建议
5. 解释用中文`,
    {
      label: `fix:${issue.id}`,
      phase: 'Fix',
      schema: FIX_SCHEMA
    }
  )
)

const validFixes = fixes.filter(Boolean)
log(`Agent 3 完成：为 ${validFixes.length} 个高危问题生成了修复建议`)

// ============================================
// Phase 5：汇总 Report
// ============================================
phase('Report')

const report = await agent(
  `## 任务
基于前面的分析，生成最终的代码审查报告。

## 输入数据
- 代码分析：${JSON.stringify(analysis, null, 2)}
- 检测到的问题：${JSON.stringify(allDetectedIssues, null, 2)}
- 修复建议：${JSON.stringify(validFixes, null, 2)}

## 报告格式
用 Markdown 生成一份完整的 Review Report，包含：
1. 📋 **PR 概览**：改了什么、影响范围
2. 🔴 **严重问题**（critical/high）：每个问题附修复建议
3. 🟡 **一般问题**（medium）：列表汇总
4. 🟢 **低风险项**（low）：简略提及
5. 📊 **统计**：按严重程度分布、按模块分布
6. ✅ **合并建议**：是否建议合并（附条件）

## 风格要求
- 直接、简洁，不要客套话
- 代码块用 diff 格式
- 最重要的问题放最前面`,
  {
    phase: 'Report'
  }
)

log('Review Report 生成完毕 ✓')

return {
  analysis,
  issues: allDetectedIssues,
  fixes: validFixes,
  report
}
