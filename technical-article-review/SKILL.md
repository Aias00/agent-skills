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
- [ ] Step 7: Produce final deliverable (report or rewritten draft)
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

If full rewrite is requested, load:
[references/rewrite-playbook.md](references/rewrite-playbook.md)

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

### Step 7: Final deliverable

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
```

## Hard Rules

- Never invent citations or numbers.
- Never hide uncertainty; annotate assumptions.
- Never trade correctness for rhetorical smoothness.
- Prefer concise edits that are easy for authors to accept.
- If a claim is time-sensitive and cannot be verified locally, say so explicitly.

## References

- [references/review-rubric.md](references/review-rubric.md): scoring and severity framework
- [references/platform-compliance.md](references/platform-compliance.md): anti-rejection checks for CN content platforms
- [references/rewrite-playbook.md](references/rewrite-playbook.md): concrete rewrite patterns and section templates
