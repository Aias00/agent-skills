---
name: code-review
description: |
  统一代码评审 skill，三种模式：PR 评审（pr：deep 深审 + follow-up 评论回复）、全仓库缺陷发现（repo-audit）、Java 安全深度审计（security-audit）。
  触发：pr deep=「review this code」「code review」「before merge」「深度 review #PR」「审 PR 有什么问题」；pr follow-up=「待处理」「review 修了吗」「英文回复」「处理这个 PR 的 review」「#PR」；repo-audit=「分析项目问题」「全仓库扫描」「audit the repo」「find issues」「建 issue」「不要重复」；security-audit=「安全审计」「审安全」「check security」「audit for vulnerabilities」「审 Controller」「单接口安全」。
  安全类只写本地 Markdown 不写缺陷系统；非安全建 issue 前先列清单确认。Critical/High 与全部安全 finding 必过统一核验门（可移植：独立 general-purpose subagent 隔上下文复核；OMX 运行时优先用 code-reviewer+architect 双 lane）。
---

# Code Review Skill（统一）

本 skill 整合三种评审能力到一个 SOP，由模式路由分发：

| 模式 | 作用域 | 产物 | 核心机制 |
|---|---|---|---|
| **pr**（deep / follow-up） | 一个 PR/diff + 邻近代码 | APPROVE/REQUEST CHANGES/COMMENT 裁决；评论/英文回复/受托修复 | 独立双 lane + 确定性合并门；live PR 状态 + 线程分类 + 生成物溯源 + DCO |
| **repo-audit** | 整个仓库存量 | GitHub issue（非安全）+ 本地 md（安全） | 并行 fan-out + 去重基线 + 分梯队 + 确认门 + 核验门 |
| **security-audit** | Java 仓库/diff/Controller/单接口，仅安全 | 仅本地 Markdown | 数据流追踪 + 对抗式独立核验门 + 变体搜索 |

模式可组合：repo-audit 的 Critical/High 与 security-audit 的全部 finding 都走**统一核验门**（见第五节）。

---

## 〇、模式路由

按用户措辞选模式与子模式：

- **pr / deep**：「review this code」「code review」「before merge」「质量评估」「深度 review 这个 PR」「深度 review #<PR>」「审 PR 有什么问题」「像 reviewer 一样看这个 PR」
- **pr / follow-up**：「查一下我的 PR 有没有待处理」「处理这个 PR 的 review」「这些 review 修了吗」「根据 reviewer 情况处理」「给我英文回复」「#<PR>」
- **repo-audit**：「分析项目问题」「找 bug」「全仓库扫描」「扫描项目」「audit the repo」「find issues in this project」「帮我把这些问题建 issue」「不要重复创建已有的 issue」
- **security-audit**：「安全审计」「审安全」「check security」「audit this repo for vulnerabilities」「审 Controller 安全」「单接口安全审计」「检查分支/PR 的安全差异」

组合与约束：
- 「安全审计 + 建 issue」→ security-audit 产本地报告，**不**建公开 issue（安全类永不公开）。
- 「repo-audit + 把 Critical 安全复核」→ repo-audit 后对安全类再走核验门。
- 措辞模糊（如"分析项目安全问题"既可 repo-audit 也可 security-audit）→ 先确认范围与引用版本（分支/SHA/PR 号），**不要假设**。

---

## 一、公共纪律（三模式共用）

### 1. 证据模型
每条结论必须绑可复现证据，禁止凭记忆或旧对话状态：
- 代码：`path:line` + 当前实际行为
- 提交：包含修复的 commit SHA（pr 模式）
- 测试：确切命令 + pass/fail（pr 模式）
- GitHub：PR `headRefOid`、review 线程状态、DCO/CLA/check 状态（pr 模式）
- 仓库：`owner/repo` + 引用版本（分支/标签/SHA/PR）+ 文件路径 + 行号（三模式）

证据不足时输出 `inconclusive` 或 `not_covered`。**不得把"大概修了"写成"已修"**，**不得把"疑似漏洞"写成"confirmed"**。

### 2. 严重度 / 置信度 / 覆盖状态分离
禁止用单一加减分混合这三个概念。每个 finding 分别记录：
- **severity**：Critical / High / Medium / Low
- **confidence**：high（代码路径与影响已验证）/ medium（强暗示但无运行时复现）/ low（降为 open question，不作为 finding）
- **coverage**（security-audit 必填，repo-audit 推荐）：`confirmed` / `inconclusive` / `not_covered`

### 3. 验证前不下结论（反捷径）
- 不因"有权限注解"判定安全；验证注解实现、全局链、AOP、过滤器、主体/资源/租户绑定。
- 不因"没有方法注解"判定严重；查全局安全链、父类、接口、过滤器、网关。
- 不因"扫描器报错"判定漏洞成立；证明可达性、控制、影响。
- 不因"reviewer 说修了"判定已修；读代码确认。
- 不停在 Controller；追到授权决策或敏感操作，找不到标覆盖不足。
- 不因"剩余接口看起来相同"批量推断安全；逐接口记覆盖证据。

### 4. 对外动作姿态
- 默认只读。不修改文件、不发评论、不建 issue、不推送，除非用户明确要求。
- 安全类**永不**写入缺陷系统/公开 issue，只产本地 Markdown（即使用户说"建 issue"，安全类仍走本地披露路径，并提示用户走厂商安全披露）。
- 非安全类建 issue 前**必须先列清单确认**（标题/标签/file:line/影响/修复/与已有 issue 区分），确认后再 `gh issue create`。
- 推送/评论仅在用户明确要求或上下文清楚要求时进行；`--force-with-lease` 仅在 rebase/squash 改写历史后。

### 5. 并行 fan-out（repo-audit / security-audit）
仓库级审计用并行 subagent 分方向（如 admin / gateway-core / protocol-plugins / client-register-sync / security / perf-governance），每路给同一去重基线与"只读实际源码、file:line 核实、禁推测"约束。fan-out 后人工合并去重 + 跨方向同缺陷合并。

**可移植调用样板**（不依赖 OMX）：
```bash
# 1. 去重基线
gh issue list --state all --limit 1000 --json number,title,state > /tmp/existing_issues.tsv
# 2. 分方向 spawn 独立 subagent（每路新上下文，给基线 + 约束）
#    Agent 工具示例：
#      Agent(subagent_type='general-purpose',
#            prompt="审查 <module>，对照 /tmp/existing_issues.tsv 去重。
#                   只报基线未覆盖的新缺陷。读实际源码，file:line 核实，禁推测。
#                   输出 id/title(英文,issue-ready)/severity/files/description(根因+触发)/
#                         impact/suggested_fix/confidence/related_existing(# 或 none+为何非重复)")
# 3. 核验方：对 Critical/High 再 spawn 独立 subagent，只给"主张+file:line"
#    （不含发现方推理/修复建议）——见第五节
```

### 6. 安全 vs 可建 issue 的硬规则（分流判定）
- 缺 `@RequiresPermissions`/`@Valid` 且**主张核心是"某主体能否对某资源做某动作"**（鉴权/越权）→ **安全文件**，不建 issue。
- 主张核心是**数据正确性/部分失败/事务/资源泄漏/NPE**（即使有安全影响）→ 可建 issue。
- 模糊时**默认安全/本地**（宁保守不公开）。
- 逻辑 bug 即使有安全影响（如跨 namespace 的 SQL WHERE 漏字段）按 issue 处理；但鉴权缺失类按安全处理，以与既有分流一致。

### 7. 图驱动评审心智模型（借鉴 code-review-graph，零依赖）
评审不止读 diff 与邻近行——按"变更在依赖图里的位置与半径"思考。以下启发式均可纯推理执行（`rg` + 读码 + 推理）；装了 code-review-graph（见八）则用其 MCP 工具精确化。无图工具时全部退化为 `rg` + 读码（近似，可能漏节点）——**不假装有图**。

1. **影响半径优先**：改一个符号前，先列它的所有 caller/consumer（`rg` 函数名/字段/import），审半径而非仅 diff 行。半径越大→blast radius→severity 上调。（图工具：`get_impact_radius_tool`）
2. **按流而非按文件审**：追一条请求/数据流：入口→链→sink。security-audit 的 Source→守卫→Sink 即此法。（图工具：`get_affected_flows_tool`/`get_flow_tool`）
3. **所有权边界**：判定变更是否跨 community（跨团队/跨模块）。跨边界=脆弱，architect lane 重点看。（图工具：`list_communities_tool`）
4. **hub 节点 = 爆炸半径**：改动触及高 fan-in（被很多处依赖）文件→一处坏全仓坏，severity 上调。（图工具：`get_hub_nodes_tool`）
5. **bridge 节点 = 脆弱耦合**：跨 community 桥接节点→改它易破坏多模块，标 maintainability finding。（图工具：`get_bridge_nodes_tool`）
6. **knowledge gap = 覆盖洞**：改动落在孤立/无调用/无测试节点→覆盖洞，要求补路径测试或显式标 `not_covered`。（图工具：`get_knowledge_gaps_tool`）
7. **语义变体搜索**：确认 bug 后搜"同形态"变体——syntactic 用 `rg` + 人工"同模式是否会重现在兄弟代码"；有 embeddings 则语义搜。security-audit 变体搜索加此视角。（图工具：`semantic_search_nodes_tool`）
8. **复杂度热点优先**：优先审最大/最连通的改动函数（高复杂度=高缺陷概率）。（图工具：`find_large_functions_tool`）

### 8. 确定性 × Agent 混合分工（借鉴 open-code-review）
该不出错的步骤用**工程逻辑**保证，不让 LLM 猜；LLM 只做动态判断 + 取上下文。每步标注属于哪侧：
- **确定性（工程，禁 LLM 猜）**：文件选择（`git diff --stat`/聚焦，不漏不滥）、规则匹配（按文件特征模板匹配，非语言引导）、评论定位（行号锚定，独立校准）、生成物溯源（submodule/commit 比对）。
- **Agent（LLM）**：行为判断、跨文件上下文取用、数据流推理、变体搜索、严重度裁定。
原则：能用 `git`/`grep`/rule-template 确定的，不让 LLM 自由发挥——这是 precision 高 + token 低的根因。

**precision-over-recall 立场**：宁漏不滥——宁少报真问题，不刷假阳性。每条 finding 须"security/engineer 敢在 PR 公开提"。Recall 刻意可低，precision 优先。

---

## 二、模式：pr

PR 级评审，三个子模式：**deep**（pre-merge 深审，默认）、**follow-up**（处理已有 reviewer 评论/回复）、**scan**（无 diff 整文件/整目录审计，用于陌生代码库或无意义 diff 的目录）。

### 2.1 deep（深审，默认）

把 PR 当"对真实系统的拟议变更"评审，不止复述 diff。

**核心机制**：双独立 lane + 确定性合并门。
- `code-reviewer` lane：规范合规/安全/质量/性能/可维护性 finding。
- `architect` lane：devil's-advocate 设计/权衡视角。
- 两 lane 在干净上下文并行，互不见对方推理。**任一 lane 不可用/失败 → 报 `independent review unavailable` 并阻断批准，禁止作者 lane 兜底**（"do not self-review as a fallback"）。
- 在非 OMX 环境，两 lane 用两个独立 `general-purpose` subagent 实现（见第五节可移植机制）。

**严重度**：CRITICAL（安全/必须修）/ HIGH（bug/应修）/ MEDIUM / LOW。
**架构状态**：CLEAR / WATCH（非阻塞但须出现在最终综合）/ BLOCK（阻塞合并）。
**确定性合并门**：
- architect=BLOCK → REQUEST CHANGES
- else code-reviewer=REQUEST CHANGES → REQUEST CHANGES
- else architect=WATCH → COMMENT
- else follow code-reviewer lane

**两阶段 plan→main**：plan 阶段先产审查计划（审哪些文件、匹配哪些规则、预期风险）+ 确定性文件选择（见一.8）；main 阶段执行审 + 取上下文。两阶段工具集分离（plan 用只读/检索工具，main 用判断工具），避免一上来乱翻。

**评审要点**（不止语法）：现有用户/升级/回滚/多版本/陈旧配置/nil/重试/并发/缓存/部分失败；API/schema 变更查 source-of-truth/生成副本/校验/默认/枚举兼容；K8s 查幂等/ownerRef/patch/status；插件/数据面查生命周期/流式/body 缓冲/fail-open vs fail-closed/路由匹配/header 大小写/内存上限；Helm 查 chart 副本/CRD 顺序/升级路径。
**测试即契约**：要会因回归失败的测试，而非只测 helper；生成/schema-only PR 查生成溯源而非强求单测。
**验证可疑发现后再报**：读码/定向测试/最小命令复现；推测不作为 finding，列为 open question。
**排序**：blocker / should_fix / nit（仅当用户要穷尽）。

**Deep Review 完整 SOP（内联）**

#### Evidence Model
每条 PR 状态主张须绑可复现证据，不凭记忆或旧对话状态。维护此 evidence packet：
```yaml
pr: { repo, number, baseRefName, headRefName, headRefOid }
local: { branch, head, dirty_state: clean|tracked_changes|untracked_only|mixed }
review_thread: { url, path, line, latest_reviewer_comment, latest_author_reply? }
verdict: { status: fixed|needs_code_change|reply_only|outdated|waiting_reviewer|resolved|ci_only|blocked, evidence: [], reply? }
```
Evidence 条目类型与"大概修了≠fixed"规则见一.1；本节补充 PR 专属的 evidence packet 与 verdict 状态枚举。

#### Deep Review Workflow
1. **理解意图**：读 PR title/body/linked issue/commits/changed files；先一句话说预期行为再找 bug；识别所有权域（API/schema、controller/reconcile、数据面插件、Helm/打包、文档、测试、CI、submodule）。
2. **建本地评审面**：取 PR head+base（优先 worktree）；`git diff --stat <base>...HEAD` + 聚焦 diff；读周边代码/调用方/测试/生成物/发布安装路径；`rg` 找新字段/配置键/helper/metrics/生成物的所有消费方。**图驱动**：先算影响半径与 caller/consumer（见一.7 启发式 1/4）。
3. **审行为不审语法**：见上"评审要点"。
4. **测试即契约**：见上。
5. **验证可疑发现后再报**：见上。
6. **按合并风险排序**：见上 blocker/should_fix/nit。

#### Deep Review Finding Taxonomy（有意找这些类）
- **Correctness**：错分支、漏 nil/empty/default、顺序错、比较错、陈旧缓存、race、未处理错误、fail-open/fail-closed 错。
- **Compatibility**：API 字段重命名/删除、enum/默认变更、旧控制面/数据面不匹配、升级/回滚破坏、多版本行为。
- **Generated artifacts**：生成文件被改而 source 未更、chart/hgctl CRD 副本漂移、submodule 指针不匹配、声称生成器可用实则不可用。
- **Coverage gaps**：测试只测 helper 不测 caller、缺负路径、无升级/安装验证、用户可见工作流无 e2e。**图驱动**：孤立/无调用/无测试节点即 knowledge gap（见一.7 启发式 6）。
- **Security/robustness**：token/secret 泄漏、auth 绕过、不安全默认、请求走私/头混淆、无界 body/内存/时间。
- **Operations**：CI 不覆盖该路径、chart value 默认意外、安装顺序、metrics 基数、噪声日志、故障诊断。
- **Maintainability**：重复所有权、新抽象无收益、偏离 repo 约定、无说明的硬编码 path/tag。**图驱动**：跨 community 桥接节点（bridge）与高 fan-in hub 见一.7 启发式 3/5。

#### Deep Review Comment Style
可执行、基于证据。形如：
```text
<具体问题>。在 <条件>，<当前代码行为> 导致 <坏结果>。这很重要因为 <运行时/用户影响>。能否 <具体修复或测试>？
```
范例：
```text
This generated CRD copy is updated, but the source schema is not. The file header says it is generated from the Istio APIs, so the next generation pass will drop these fields. Please update the source submodule/generated artifact or add a PR note explaining why this copy is intentionally hand-maintained.
```
```text
This test exercises the helper directly, but the regression would happen through Reconcile. Could we add a Reconcile-level test so the wiring and no-op behavior are covered together?
```
避免：只复述 diff / 个人口味 / 不说测什么回归就要测试。

#### Review Quality Rubric
高质量评论至少做其一：挑战架构/所有权边界而非只样式；识别真实运行时条件下会坏的行为；要测真实生产路径而非只 helper；减少重复或无谓抽象；保护未来可维护性（如固定 hash 输入/字段覆盖）；建议平台原生行为（如让 K8s 拥有 rollout）。
低质量/低优先：纯样式无行为影响；已被当前代码反驳；基于过期 diff；更适合 reply-only 权衡讨论。用户问"这 review 好不好/严不严/可不可行"时用此 rubric。

#### Reviewer Discipline
- 以 findings 开头，非变更摘要。
- 只报有 file/line 证据、测试、生成物、文档行为支撑的问题。
- 宁少而高信号，勿多而弱。
- 尽量给确切 file/line。
- 区分已证 finding 与 open question。
- 重要 positive/neutral 上下文放 findings 之后（若有用）。
- 无问题就直说，并说明剩余验证/测试缺口。
- **未经用户明确要求，不 approve / request changes / 发评论、不改文件**。
- 置信度可见：high=代码路径与影响已验证；medium=强暗示但无运行时复现；low=作 open question 而非 finding。

#### No-Action and Zero-Result Handling
无显然 blocker 时仍要讲清"无待处理"指哪种：
- 全部线程 resolved；
- 未决但最新作者回复在等 reviewer；
- 未决但 outdated，当前代码已不含该问题；
- 无 review 待办但 CI/DCO/CLA pending 或 failing；
- 需 review 但无具体可行动 reviewer 评论。
精确措辞例：
```text
没有新的代码待处理。剩余状态是 reviewDecision=REVIEW_REQUIRED，有 2 条 unresolved threads 都是已回复/过期，等 reviewer resolve；CI 仍 pending。
```
GitHub 返回空线程/空文件时，报检索范围与来源，勿把"无"当"通过"。

#### Implementation Rules（处理 review feedback 时）
- 改动严格限定在 review 评论范围。
- 主仓有无关本地改动/脏 submodule 时用隔离 worktree。
- 优先删除或用既有 helper，而非新 wrapper。
- review 要 wiring 覆盖时加走真实 caller 路径的测试。
- rollout/hashing/caching/reconcile/K8s 行为，测"该变时变"与"已当前时不变"两类。
- review 回复简短技术化。
- DCO 仓库用 signed-off commit。
- 仅用户要求或上下文清楚要求时 push；正常 push 用 fast-forward，rebase/squash/改写历史后才 `--force-with-lease`。
- push 后从 GitHub 刷新 PR head 与 checks 再报状态。
- 评论冲突时优先更近 reviewer 评论；reviewer 提设计替代时评估是否简化所有权与运行时；只在有具体代码/测试证据时 push back。

### 2.2 follow-up（处理评论/回复）

**取 live 状态**（必做）：
```bash
gh pr view <number> -R <owner>/<repo> \
  --json number,title,url,baseRefName,headRefName,headRefOid,mergeStateStatus,reviewDecision,statusCheckRollup,body,commits,files
gh pr list -R <owner>/<repo> --author <login> --state open --limit 100 \
  --json number,title,url,headRefName,headRefOid,mergeStateStatus,reviewDecision,statusCheckRollup
gh api graphql -f owner=<owner> -f repo=<repo> -F number=<number> -f query='
query($owner:String!, $repo:String!, $number:Int!) {
  repository(owner:$owner, name:$repo) { pullRequest(number:$number) {
    reviewThreads(first:100) { nodes { isResolved isOutdated path line originalLine
      comments(first:30) { nodes { databaseId author { login } body outdated createdAt url } } } } } } }'
```

**Head 一致性门**（下"已修复"结论前必过）：
```bash
git rev-parse HEAD
gh pr view <number> -R <owner>/<repo> --json headRefOid,headRefName
```
本地 `HEAD` == PR `headRefOid` 才能说"GitHub 已反映修复"。不一致先 fetch/checkout/rebase（脏仓库用 worktree）。`mergeStateStatus: BLOCKED` 拆成 pending checks / required review / branch protection 分别报。

**线程分类法**：`needs_code_change` / `needs_reply_only` / `already_answered` / `outdated` / `bot_or_noise` / `ci_only` / `metadata_only` / `generated_file_provenance`。以最新评论作者 + `isOutdated` 为信号但**不单独依赖**，必须对照当前 diff 与 commits 验证后才说"已处理"。

**verdict**：`fixed` / `needs_code_change` / `reply_only` / `outdated` / `waiting_reviewer` / `resolved` / `ci_only` / `blocked`。每条 actionable 记：`question / change / evidence(file:line, commit, test cmd) / reply(英文)`。

**生成物溯源**（高频高信号 blocker）：
1. 判定是否声明生成/复制自生成/chart 副本：`head -40 <file>` + `rg -n "DO NOT EDIT|Generated by|go generate|make gen|protoc-gen|buf generate"`。
2. 追 source-of-truth（proto/CRD 生成器/submodule/upstream artifact）。
3. 查 source commit 是否已在：`git submodule status`、`git -C <sub> show --stat <commit>`、`gh pr view <upstream> -R <owner>/<repo> --json state,commits,files`。
4. 优先重新生成/从 upstream 生成物同步，而非手改生成输出。
5. 生成器本地不可用明说；可用与 upstream 生成物对比验证，但**不得声称"重跑了生成"除非命令真跑过**。
6. CRD/schema-only：`git diff --check`、`kubectl apply --dry-run=client --validate=false -f <crd>`、`diff -u <(src snippet) <(pr snippet)`。

**DCO 卫生**：DCO 仓库新 commit 用 `git commit -s`；rebase/merge main 后查 `Signed-off-by` 是否丢失；修复用 `git rebase --signoff <base>` 或 amend/cherry-pick `-s` + `--force-with-lease` push；push 后 `gh pr checks <number>` 验证。汇总时 DCO 与 CI 分开报。

**评论/回复风格**：
- reviewer 评论 shape 与范例见二.1 Deep Review Comment Style。
- 英文回复简短技术化：`Done. <what changed>.` / `Added a test for <case>.` / `Kept this path because <tradeoff>.`；避免 "Great point!"、避免把未跑命令写成已跑、避免 CI 仍 pending 时说绿。
- 中文总结放详细映射，英文回复块只放可粘贴短句。

**输出形**：
- 「查待处理」：open PR 列表 + 每条 Review/CI/Next。
- 「处理这个 PR」：改动文件+push head、验证命令 pass/fail、当前 PR 状态(reviewDecision/mergeStateStatus/DCO/CLA/checks)、逐条英文回复草稿。
- 「修了吗」：逐条 current code evidence。

**默认只读**：不修文件、不发评论除非用户明说；脏仓库用 worktree 或 fetched refs；证据够了就停，不凑低价值 nit。

### 2.3 scan（整文件/整目录审计）
无 diff 或审计陌生代码库时用。不走 diff，按文件/目录整审：读全文件 → 按规则匹配（见一.8 确定性）→ agent 行为判断 + 跨文件取上下文 → findings（`file:line` + 根因 + 修复）。适用：接手陌生仓、目录级安全审、无 PR 的存量审计。与 deep 的区别：deep 审"变更"，scan 审"存量整文件"。

---

## 三、模式：repo-audit（全仓库缺陷发现）

**目标**：整仓存量代码中发现**新**缺陷（正确性/性能/可扩展性/测试与工程治理/安全），去重已有 issue，分梯队确认后建 issue（安全类写本地）。

**流水线**：
1. **初始化**：确认 `owner/repo` + 引用版本（默认当前分支）；建任务清单。
2. **去重基线**：`gh issue list --state all --limit 1000 --json number,title,state` 存参考文件；各路 agent 拿此基线 + 已产出的本地审计文件，**只报基线未覆盖的新问题**。
3. **并行 fan-out**：按**相关文件束**而非纯模块分派独立 subagent（调用样板见一.5）——controller+service+mapper / DTO+VO+i18n 对 等相关文件捆一束，每束隔离上下文 = 分治 + 稳定 + 可并发（借鉴 open-code-review）。每路输出结构化 finding：`id / 标题(英文,issue-ready) / severity / files(file:line) / description(根因+触发) / impact / suggested_fix / confidence / related_existing(# 或 none + 为何非重复)`。
4. **合并去重**：跨方向同缺陷合并（保留描述更准的一条，其余标注=另一条）；与已建 issue 重复的整条剔除；安全类（见一.6 硬规则）分流到本地安全文件，不建 issue。
5. **核验门**：Critical/High finding 走第五节统一核验门（独立 subagent 复核，五要素）。
6. **分梯队**：Critical / High / Medium（可再分 Medium-High / Medium / Low-Medium）/ Low。给每梯队推荐创建范围。
7. **确认门**：候选整理成清单文件（`id/标题/labels/file/一句话`）+ 摘要表呈现，**等用户确认创建范围与标签**后再建。
8. **批量创建**：脚本 `gh issue create --title ... --body-file ... --label ...`；正文统一含 Description/Location(file:line)/Impact/Suggested fix/Related existing/指向审计清单。**仅用已知存在的 label**（建前先 `gh label list`），未知 label 留空 area 而非瞎填（避免 `could not add label` 失败）。后台运行 + 失败续跑 + 重试修正。
9. **族 tracking**：同根因族群建/并入 tracking issue 并交叉链接，而非每条独立修。
10. **安全类产物**：写入本地 `docs/security-audit-{repo}-{ref}-{date}.md`（路径与第六节一致）；Critical（RCE/鉴权绕过/SSRF）提示走厂商安全披露（如 security@apache.org），不建公开 issue。

**去重要点**：三层去重——①已有 issue ②已产出本地审计文件 ③跨方向 fan-out 重复。每条 finding 的 `related_existing` 必须注明与基线的区分，否则视为重复剔除。

---

## 四、模式：security-audit（Java 安全深度审计）

**目标**：以仓库为事实源做可追溯 Java 安全审计；产物**仅本地 Markdown**，不写缺陷系统。

**流水线**：
1. **初始化**：记 `owner/repo` + 引用版本（分支/标签/SHA/PR）+ 审计模式（仓库/diff/Controller/单接口）+ 范围/排除/输出目录。缺关键输入先从当前仓库/git 配置/GitHub 上下文解析，解析不了再问。
2. **取码与接口**：优先会话 GitHub 连接器/MCP，不可用降级只读 `gh` + 本地检索。接口发现**可选**用 ONEAPI，不可用时从代码解析 Spring MVC/WebFlux/JAX-RS/Servlet 入口；**不得按路径名或 API 文档注解直接排除接口**。diff 模式读 GitHub compare/PR diff。
3. **建安全上下文**（每入口）：角色（调用者/服务身份/admin/普通用户/租户/匿名）、资源（类型/标识/所属主体/允许操作）、守卫（SecurityFilterChain/方法安全/过滤器/拦截器/AOP/自定义权限注解/网关约束）、数据流（请求参数→认证主体→授权决策→敏感操作）、敏感操作（DB/文件/网络/消息/缓存/脚本/反序列化）。按"入口→身份来源→授权守卫→数据转换→敏感操作"追踪，不强制固定分层。
4. **发现并研判**：先证明**攻击者可达性与输入控制**，再判**授权绕过或危险数据流**，最后评**真实影响**。每 finding 记：精确主张/根因、攻击者/前置条件/输入向量/影响、Source/验证点/授权守卫/转换步骤/Sink、支持证据/反驳证据/覆盖限制/修复建议、CWE/OWASP、severity 与 confidence **分别**。**按流追踪**（入口→守卫→sink）见一.7 启发式 2。
5. **独立核验门**（见第五节，本模式核心）：复杂或高危 finding 在隔离上下文重新取证；不得把原始推理与修复建议传给核验方。
6. **同根因变体搜索**：确认后从精确模式起搜全仓，**每次只泛化一个变量/方法名/调用形态**并复核新匹配；误报率高即停。简单语法用 `rg`/Semgrep，跨函数流用 CodeQL/YASA（若可用）；扫描器结果只算候选证据。**加语义视角**：搜"同形态"是否重现在兄弟代码（见一.7 启发式 7）。
7. **本地报告**：`docs/security-audit-{repo}-{ref}-{date}.md`（路径与第六节一致）；含范围/工具/覆盖率/Finding/已确认安全项/未覆盖项/风险汇总/修复优先级。

**工具说明（重要）**：ONEAPI / CodeQL / YASA / Semgrep / `api_diff_extractor.py` / `verification-verdict.schema.json` / `validate_verdict.py` 等**均未随本 skill 打包**，位于 `/Users/aias/Work/github/hzb-security-check`；缺则跳过，降级为 `rg`/`grep` + LLM 读码 + 独立 subagent 核验。扫描器结果只算候选证据，不得等价为漏洞。

**输入向量与 sink 清单**：
- 注入：MyBatis `${}`(用户输入)/SpEL(`StandardEvaluationContext` 而非 `SimpleEvaluationContext`)/模板/路径/CRLF/log4j layout 含用户输入；SSRF（swagger/AI baseUrl/MCP tool URL/monitor scrape/alert webhook）。
- 反序列化：Jackson/Gson 多态 typing/Kryo/Hessian/YAML 配置/Base64 信任。
- 路径穿越：上传/下载/导入导出/ext-lib/日志文件路径/config zip。
- 加密：key 管理/IV 复用/`Random` vs `SecureRandom`/timing oracle/key 轮换/MQTT 等密码哈希。
- 密钥泄漏：错误信息/日志/响应/配置默认/actuator 端点暴露。
- DoS：无界集合/regex(ReDoS)/XML-JSON 解析无限制/请求走私/头大小限制/slowloris/multipart/SSE。
- 鉴权：每个 mutating controller 方法查 `@RequiresPermissions`；service 层 namespace 成员校验；JWT claims 信任；Shiro 过滤器链/anon 名单；CSRF；密码重置/修改流；data permission 绕过。

**Critical 处置 + PMC 签收门**：RCE/鉴权绕过/SSRF 等确认的 Critical **不建公开 issue**，走厂商安全披露（如 `security@apache.org`），本地文件标注待披露。**Critical 经核验门 confirmed 后，必须 PMC/运维人工签收方可走厂商披露**——核验门结论是建议非裁决，人工是最后门。

---

## 五、统一核验门（三模式交叉点，整合的核心）

本门是三个能力里最该统一的部分——既有 OMX 双独立 lane（不得自审兜底）、hzb 的"隔离对抗核验 + 五要素"、repo-audit 的"Critical 抽查"合并为一条强制门。

### 适用范围
- security-audit 的全部 finding
- repo-audit 的 Critical / High finding（建 issue 前）
- pr 模式中"已修复/已处理"的结论

### 机制（可移植，B1 修复）
- **默认可移植**：核验方 = 独立 `general-purpose` subagent，**新上下文**，只给"主张 + file:line"，**不给**发现方的原始推理与修复建议（防确认偏误）。核验方自行读码取证。
- **OMX 增强（可选）**：当 OMX runtime 与 `code-reviewer`/`architect` agent 可用，优先用双 lane（两 lane 互不见推理，任一失败即 `unavailable` 阻断，禁止自审兜底）。这是同一原则在 PR 级的更强实现；不可用时降级为上一条。
- repo-audit/security-audit：发现方 subagent → 独立核验方 subagent（隔上下文，只给主张+file:line）。
- pr follow-up 子模式：单线程即可，但"已修"结论必须读码验证；deep 子模式天然有双 lane。

### 五要素（security-audit 与 repo-audit Critical/High 必过）
`confirmed` 必须同时证明：①攻击者可达性 ②攻击者输入控制 ③保护缺口 ④真实影响 ⑤环境可利用性。缺任一降为 `inconclusive`/`not_covered`。**修复可行性不参与真实性判定**——漏洞好不好修不影响它成不成立。

### 严重度修正
若"可达性"有前置条件（如"需先获得 admin 配置写权限"），severity 仍按潜在影响定，但 confidence/coverage 与披露路径要反映前置条件。例：SpEL 用 `StandardEvaluationContext` 是真缺陷，但"无需 admin 无条件可达"需复核是否存在反射请求输入的 mock 规则；若依赖反射型规则，标 Critical + confidence=medium + 注明前置。

### PR"已修"核验
核验方对照当前 diff 与 commit，确认代码确实改了且覆盖该路径；不因"有回复说修了"就标 `fixed`。

### 定位校准 + 内容反思（核验门之后、输出之前）
核验门验"真实性"，但不验"评论位置准不准"与"评论内容对不对"。两道独立校准（借鉴 open-code-review 外部定位 + 反思模块）：
- **定位校准**：每条 finding 的 `file:line` 须指向**真正触发缺陷的行**，非 diff 任意行/邻近行。复核对齐当前代码（非过期 diff），行号随 base/head 校准。
- **内容反思**：评论内容须 (a) 说清根因 + 触发条件 (b) 给可执行修复 (c) 不复述 diff、不个人口味、不说"加测试"而不说测什么回归。反思不过的 finding 降级或重写，不直接输出。

### 落地
见一.5 调用样板（fan-out）与第九节 OMX 双 lane `task()` 样板。

---

## 六、产物与对外策略（统一）

| 产物 | 触发 | 约束 |
|---|---|---|
| APPROVE/REQUEST CHANGES/COMMENT 裁决 | pr deep | 双独立 lane 证据齐；任一缺失=unavailable 阻断 |
| 本地 Markdown 报告 | security-audit 全部；repo-audit 安全类 | 路径统一 `docs/security-audit-{repo}-{ref}-{date}.md`；不写缺陷系统 |
| GitHub issue | repo-audit 非安全类 | **先列清单确认**再建；用已知 label；批量脚本+失败续跑 |
| reviewer 评论/英文回复 | pr follow-up | 仅用户明确要求时发；简短技术化 |
| 代码修复 | pr follow-up 受托 | 仅用户明确要求时改；worktree 隔离；scoped；DCO `-s` |
| tracking issue 交叉链接 | repo-audit 族群 | 同根因建/并入 tracking issue + 双向评论链接 |

**安全类永不公开**：即使用户说"把安全问题也建 issue"，security-audit 仍只写本地并提示走披露。硬约束。

**Critical 披露门**：Critical 经核验门 confirmed 后，**必须 PMC/运维人工签收**方可走厂商安全披露。核验门是建议非裁决。

---

## 七、停止条件

- pr deep：双 lane 证据齐、确定性门给出裁决、architect blocker 显眼标注。
- pr follow-up：每条 actionable 线程已映射到 fix 或 reply-only；验证已过或缺口显式；push 后 PR head/checks 已刷新（若 push 了）。
- repo-audit：finding 已分梯队、去重、确认范围已给用户、创建完成或用户拒绝；安全类已落本地。
- security-audit：所有审计对象有覆盖状态；所有 finding 有仓库引用/file:line/攻击场景；已确认 finding 过核验门；severity/confidence 分开；报告已存本地。
- 不等 CI 除非用户明确要求。

---

## 八、与既有 skill 的关系

本 skill 是**单文件**整合。
- pr deep 完整 SOP（Evidence Model / Deep Review Workflow / Finding Taxonomy / Comment Style / Quality Rubric / Reviewer Discipline / No-Action / Implementation Rules）已内联于二.1。
- security-audit 重机器（modules/risk-analyzer/rules、schemas/verification-verdict.schema.json、scripts/validate_verdict.py、CodeQL/YASA/ONEAPI 适配）位于 `/Users/aias/Work/github/hzb-security-check`；缺则降级。
- **可选运行时加速器**：[`code-review-graph`](https://github.com/tirth8205/code-review-graph)（pip 包 + MCP server）。装法：`pip install code-review-graph && code-review-graph install --platform codex`。装后其一.7 启发式可由 MCP 工具精确化（`get_impact_radius_tool`/`get_affected_flows_tool`/`list_communities_tool`/`get_hub_nodes_tool`/`get_bridge_nodes_tool`/`get_knowledge_gaps_tool`/`semantic_search_nodes_tool`/`find_large_functions_tool`）。**职责切分**：code-review-graph 只给上下文/影响分析；SOP、证据模型、核验门、verdict 仍遵循本 skill——不把它当裁决来源。未装/工具名漂移/headless 会话 MCP 缺失时，全部退化为 `rg`+读码（见一.7 降级规则）。注意：其 installer 会往 `~/.codex/skills/` 注入 skill 并改写平台 rules，装前确认不与本 skill 同名冲突。
- 本 SKILL.md 提供统一路由与最严的核验门，是三能力的入口与收口。

---

## 九、OMX 集成（仅 OMX 运行时生效）

> 本节内容仅在 OMX/Autopilot 运行时生效；普通 Codex 会话忽略本节，核验门用第五节的可移植机制（独立 general-purpose subagent）。

### 双 lane 调用样板
```
task(
  agent_type="code-reviewer",
  prompt="CODE REVIEW TASK
Review code changes for quality, security, and maintainability.
This is the code/spec/security lane. Do not absorb architectural ownership.
Scope: [git diff or specific files]
Review Checklist:
- Security vulnerabilities (OWASP Top 10)
- Code quality (complexity, duplication)
- Performance issues (N+1, inefficient algorithms)
- Best practices (naming, documentation, error handling)
- Maintainability (coupling, testability)
Output: Code review report with files reviewed count, issues by severity
(CRITICAL/HIGH/MEDIUM/LOW), specific file:line locations, fix recommendations,
approval recommendation (APPROVE / REQUEST CHANGES / COMMENT)"
)
task(
  agent_type="architect",
  prompt="ARCHITECTURE / DEVIL'S-ADVOCATE REVIEW TASK
Review the same code changes from the architecture/tradeoff perspective.
Scope: [git diff or specific files]
Focus: system boundaries and interfaces; hidden coupling or long-term
maintainability risks; tradeoff tension the main reviewer might miss;
strongest counterargument against approving as-is.
Output: Architectural Status: CLEAR / WATCH / BLOCK; file:line evidence;
concrete tradeoff or design recommendation."
)
Run both lanes in parallel, then synthesize with the deterministic merge
gating rules in 二.1.
```
Do not self-review as a fallback. If either lane missing/unavailable/skipped/failed → emit `unavailable-review` and block approval until independent lane evidence exists. Respect user's current model/effort; omit `model`/`reasoning_effort` overrides unless user asks.

### State/HUD Phase Contract
- **Standalone `$code-review` activation**: rely on hook-owned `skill-active-state.json` (`skill:"code-review"`,`phase:"planning"`); do not create ad-hoc `code-review-state.json`.
- **Inside active Autopilot**: keep `mode:"autopilot"` active, set supervised phase `current_phase:"code-review"` / skill-active `phase:"code-review"`; do not activate a peer workflow over Autopilot.
- **On clean review**: persist artifact/verdict under Autopilot `handoff_artifacts.code_review`, transition to `current_phase:"ultraqa"` only after durable independent review evidence exists.
- **On non-clean review**: persist artifact/verdict, set `current_phase:"rework"` (impl-only fixes) or `current_phase:"ralplan"` (requirements/planning change), keep findings as scoped handoff.
```sh
omx state write --input '{"mode":"autopilot","active":true,"current_phase":"code-review"}' --json
```

### External Model Consultation (optional)
code-reviewer agent MAY consult Codex for cross-validation: form own review first → consult → critically evaluate → never blindly adopt. Never block on optional external consultation tools being unavailable; does not waive required independent lanes. Consult for security-sensitive/complex/unfamiliar/high-stakes; skip for simple/well-understood/time-critical/small changes. Prefer native `code-reviewer` agent or CLI-backed `ask_codex`; optional MCP ask tools only if already enabled.

### 与其它 OMX skill 协同
- **Team**: `/team "review recent auth changes and report findings"` — coordinated review across specialized agents.
- **Ralph**: `/ralph code-review then fix all issues` — on explicit Ralph path, findings flow into automatic fix follow-up without another prompt. Plain `code-review` itself remains read-only.
- **Ultrawork**: `/ultrawork review all files in src/` — parallel review across files.
