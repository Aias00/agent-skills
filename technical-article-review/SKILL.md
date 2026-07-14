---
name: technical-article-review
description: Review and polish technical articles for publish readiness. Use when users ask to 审阅/润色/改稿/提审 technical content, fix rejection reasons like 灌水内容 or 技术无关, validate technical accuracy and evidence quality, optimize structure and readability, or produce a publish-ready revision from Markdown drafts and long-form technical posts.
---

# Technical Article Review

## Language

Match the user's language.

## What This Skill Delivers

Produce one of the following based on user intent:

- `Review-only`: findings + prioritized fixes, no full rewrite.
- `Review + rewrite`: full revised article + change rationale.
- `Submission rescue`: targeted rewrite to address rejection reasons.

Default behavior:
- If the user asks to review an article and does not explicitly limit the task to `Review-only`, treat the review as the first phase of a direct revision workflow.

## Workflow

```text
Technical Article Review Flow:
- [ ] Step 1: Determine mode and target platform
- [ ] Step 2: Run rejection-risk screening
- [ ] Step 3: Audit technical correctness and evidence
- [ ] Step 4: Audit structure and teaching clarity
- [ ] Step 5: Polish language without diluting technical density
- [ ] Step 6: Apply revisions when rewrite is requested or clearly implied
- [ ] Step 7: Run banned-pattern final sweep on the rewritten draft
- [ ] Step 8: Produce final deliverable (report or rewritten draft)
```

### Step 1: Determine mode and platform

Collect or infer:

- article objective: tutorial / case study / opinion / release note
- target reader: beginner / practitioner / expert
- target platform: WeChat / Toutiao / Tencent Dev Community / generic blog
- required output: review report or full rewrite

If information is missing, make conservative assumptions and continue.

### Step 2: Rejection-risk screening

Immediately flag high-risk patterns:

- non-technical filler dominates the article
- broad claims without mechanism or examples
- large sections with motivational or slogan-like text only
- title and body mismatch
- copied-style paragraphs with no original insight

For submission rescue tasks, load:
[references/platform-compliance.md](references/platform-compliance.md)

### Step 3: Technical correctness and evidence audit

Always audit technical claims before style polish.  
Load:
[references/review-rubric.md](references/review-rubric.md)

Rules:

- Do not fabricate facts, benchmarks, APIs, versions, or policy details.
- Mark unverified statements as `Needs evidence`.
- Prefer primary sources when available: official docs, standards, code, papers.
- Separate fact vs inference explicitly.
- Keep critical findings ordered by severity.

### Step 4: Structure and teaching clarity audit

Check whether the article follows a teachable path:

1. Problem and context
2. Constraints and tradeoffs
3. Approach and architecture
4. Implementation details
5. Validation (tests, metrics, failure cases)
6. Conclusion and actionable next steps

If sequence is broken, propose a minimal reordering plan first.

### Step 5: Language polish

Polish without lowering technical content density:

- remove vague buzzwords and empty intensifiers
- shorten overlong sentences
- keep code terms, config keys, and command names precise
- prefer concrete verbs and measurable statements
- preserve the author's technical intent and voice
- flatten meta-analysis phrasing that makes the draft sound AI-written

If full rewrite is requested, load:
[references/rewrite-playbook.md](references/rewrite-playbook.md)

During language polish, explicitly check for these patterns and rewrite them into flatter Chinese:

- `不是……而是……` contrast sentences used to force a conclusion
- `如果只把它当成……` / `如果只看……` / `如果想……` style lead-ins that sound like analysis scaffolding
- headings or leads such as `拆开看` / `先看目录就能发现` / `下面按 X 个层面讲`
- over-explanatory pivots such as `更准确一点说` / `也就是说` when the sentence can be stated directly
- evaluation-heavy titles like `最值得看` / `真正聪明的地方` / `更像一个观察窗口`
- soft evaluation phrases such as `更实操` / `最容易上手` / `更稳` / `更省事` / `更适合` when they can be replaced by direct description
- analysis-heavy transitions such as `这一步很关键` / `这一步主要...` / `先抓一个最实用的区分`
- vague opener lines like `这类项目放在一起看` / `最先要分清的一件事是`
- avoid stiff translated compounds when simpler Chinese exists; for example prefer `编程 Agent` over `AI 编码代理` when context is already clear
- avoid meta-source narration in derived articles such as `原文里说` / `作者提到` / `这篇文章讲的是`; absorb the source content into the article instead of constantly pointing back to the source
- when the article is based on one source and the main takeaway is clear, prefer front-loading the core conclusions near the beginning instead of saving all takeaways for the end
- when the user asks to preserve the original article, keep the original section order and sentence logic as much as possible; prefer swapping tables / ASCII diagrams for images over rewriting the body
- flatten awkward semi-literal translations such as `自动化成了一个完全不同的工作` / `从真实经验里长出来` / `把任务做通的`; rewrite them into natural Chinese
- avoid forcing causal claims that are not established in the source, for example linking `模型本身够强` to `skill 是否好用` without evidence
- avoid headline-style commentary such as `最醒目的地方` / `真正讲清楚的是` / `最值得带走的一句话` / `这篇文章最后留下来的东西`
- avoid contrasty framing around examples like `不只是让 agent 看代码，还要...`; prefer direct phrasing of what the system can do
- replace vague motion metaphors such as `漂掉` with concrete engineering language like `变形` / `走样` / `失去边界`
- replace weak translated summaries like `吞吐量没有掉，反而继续往上走` with precise engineering phrasing such as `整体交付吞吐量没有下降，还继续提高了`
- avoid `把...压住` / `压什么问题` as a default explanatory verb for article prose or figure captions; prefer concrete verbs like `处理` / `减少` / `收进规则里`
- avoid vague architecture phrases such as `做薄` / `保持轻`; describe what the layer actually does, for example `CLI 负责入口`
- avoid empty trend/opening lines such as `最近看到一个仓库：` / `这两天 ... 讨论得很多` when they do not add concrete context
- avoid stitched transition sentences like `如果只看表面...` / `这篇文章往下展开的是...`; state the point directly
- when referring to a public figure or company, add the minimum useful identity context once if it helps general readers (for example a well-known role or current position), but do not let that identity dominate the article
- for Chinese tech commentary and WeChat-style prose, prefer `能看出` / `主要看` / `这次观察范围` over report-like phrasing such as `更适合` / `不太适合` / `用于回答`
- avoid abstract transition lines such as `最先跳出来的是...` / `这一项要单独看` / `这三点先记住，后面的数据就不容易看偏`; rewrite them into natural spoken-written Chinese
- when polishing article leads and section openers, bias toward `先看一个最直观的变化...` / `先把边界摆出来...` / `这件事更值得注意...` style phrasing instead of summary-report tone
- if the user is clearly pushing the draft toward “更像人写的公众号口吻”, preserve the facts and structure but relax the register: shorter clauses, fewer meta-judgments, fewer “研究摘要体” sentences, and more natural explanatory transitions

### Step 6: Apply Revisions

If the user asks to "按审阅意见调整", "改一下", "修成可发版", or otherwise clearly wants more than a review report, edit the source draft directly.

Also apply revisions by default after review unless the user explicitly asked for:
- `Review-only`
- `只审不改`
- `先给意见，先别动稿`
- another clear constraint that blocks direct edits

Preferred revision order:
- fix time-sensitive or weakly supported claims first
- add missing prerequisites, commands, or minimum workflow paths
- convert recommendation-heavy paragraphs into mechanism + applicability statements
- remove repeated commentary that adds no new technical information

When revising:
- preserve the article's voice, but prefer verifiable wording over punchy wording
- keep the delta focused on the findings; do not rewrite unrelated sections just for style
- if the article has a downstream HTML publish artifact, treat markdown as the source of truth and let a later step regenerate HTML
- prefer direct declarative phrasing over meta commentary about how the article is structured

### Step 7: Banned-Pattern Final Sweep

Before returning any rewritten Chinese draft, do a literal final sweep on the final text.

Preferred command:

```bash
python3 scripts/check_banned_scaffolding.py --input /abs/path/to/final-draft.md
```

If the draft only exists in-memory, write it to a temporary file first, then run the checker before delivery.

Minimum blocked patterns to scan for:

- `不是`
- `而是`
- `不只是`
- `如果只`
- `也就是说`
- `这一步很关键`

How to apply the sweep:

1. Search the final draft for the blocked strings.
2. Read every hit in context.
3. If the hit forms analysis scaffolding, contrast framing, or AI-sounding exposition in unquoted prose, rewrite it.
4. Repeat until no blocked pattern remains in unquoted prose, or the remaining hit is clearly a source quote that must stay verbatim.

Hard gate:

- If `不是……而是……` or `不只是……而是……` remains in non-quoted prose, the draft is not ready and must not be returned.
- If the user explicitly flags a pattern during the conversation, elevate that pattern to a hard ban for the rest of the task.

### Step 8: Final deliverable

If user asks for review:

- output `Critical` / `Major` / `Minor` findings
- include exact paragraph or section references
- provide corrected text snippets for top issues

If user asks for rewrite:

- produce publish-ready full draft
- include a short `Change Log` section with top improvements
- include a final `Pre-submission Checklist`

If the user first asked for review and then asked to revise:

- do not repeat the full review unless needed
- return the revised draft or confirm the source file was updated
- summarize only the changes that map to the original findings

## Output Templates

### A) Review Report Template

```markdown
## Verdict
- Publish readiness: Blocked / Needs revision / Ready
- Top blocker:

## Findings
1. [Critical] ...
2. [Major] ...
3. [Minor] ...

## Recommended Fix Order
1. ...
2. ...
3. ...

## Quick Wins
- ...
```

### B) Rewrite Response Template

```markdown
## Revised Draft
<full revised article>

## Change Log
1. ...
2. ...
3. ...

## Pre-submission Checklist
- [ ] Technical claims have evidence or explicit caveats
- [ ] Examples and commands are executable/traceable
- [ ] Title matches article scope
- [ ] No filler-only paragraphs
- [ ] No banned scaffolding patterns remain in unquoted prose
```

## Hard Rules

- Never invent citations or numbers.
- Never hide uncertainty; annotate assumptions.
- Never trade correctness for rhetorical smoothness.
- Prefer concise edits that are easy for authors to accept.
- If a claim is time-sensitive and cannot be verified locally, say so explicitly.
- Never return a rewritten Chinese draft while banned scaffolding patterns remain in unquoted prose.
- Treat the banned-pattern final sweep as a release gate, not a style suggestion.

## References

- [references/review-rubric.md](references/review-rubric.md): scoring and severity framework
- [references/platform-compliance.md](references/platform-compliance.md): anti-rejection checks for CN content platforms
- [references/rewrite-playbook.md](references/rewrite-playbook.md): concrete rewrite patterns and section templates
