# Rewrite Playbook

Use these patterns for "review + rewrite" tasks.

## Recommended Article Skeleton

```markdown
# <Title aligned with scope>

## Problem
What practical problem is being solved?

## Constraints and Tradeoffs
What assumptions, limits, and competing options exist?

## Approach
Architecture, algorithm, or design choices.

## Implementation
Key commands, code snippets, configs, and integration steps.

## Validation
How results were verified (tests, metrics, comparisons).

## Failure Cases and Boundaries
Where this approach can fail and what to do.

## Conclusion
When to use this approach and next actions.
```

## Rewrite Tactics

1. Convert slogan sentences into mechanism statements.
2. Convert abstract claims into example + condition.
3. Add "because/therefore" links to close reasoning gaps.
4. Replace generic advice with operator-level actions.
5. Keep paragraphs compact but information-dense.

## Chinese Tone Preferences

Use these defaults when the user is asking for Chinese article polish, especially for WeChat/public-account style posts:

1. Prefer natural spoken-written Chinese over report-summary tone.
2. Prefer `能看出` / `主要看` / `这次观察范围` over `更适合` / `不太适合` / `用于回答`.
3. Prefer direct lead-ins such as `先看一个最直观的变化` over analytical lines like `最先跳出来的是`.
4. Prefer `更容易看明白` / `更容易看懂` over `不容易看偏`.
5. Replace section openers like `这一项要单独看` with more natural explanation, for example `这部分得单独说`.
6. If the article is based on a research paper or report, absorb the evidence into the prose; do not let the article sound like a translated abstract.
7. Keep the register relaxed but not sloppy: one point per paragraph, short transitions, fewer meta-comments about the article itself.

## Quick Replacements

```text
Avoid: 这篇研究更适合回答……
Prefer: 这篇研究主要反映…… / 这次能看出的，是……

Avoid: 最先跳出来的是输入字符数。
Prefer: 先看一个最直观的变化：输入字符数。

Avoid: 这三点先记住，后面的数据就不容易看偏。
Prefer: 这三点先记住，后面的数据就更容易看明白。

Avoid: 这一项要单独看。
Prefer: 这部分得单独说。 / 这块要单独看。
```

## Before/After Pattern

```text
Before: "This architecture is more advanced and improves efficiency."
After:  "This architecture removes cross-service polling by using event-driven dispatch, reducing average latency from 420ms to 170ms in our staging test."
```

## Submission Rescue Paragraph Template

```markdown
## Why This Works in Practice
核心机制是 <mechanism>。在 <environment> 下，我们通过 <operation> 验证了它的效果。  
局限是 <limitation>，当出现 <failure condition> 时，建议切换到 <fallback>.
```
