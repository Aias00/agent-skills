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
