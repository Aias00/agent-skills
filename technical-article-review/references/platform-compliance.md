# Platform Compliance Notes (CN Tech Content)

Use this file for submission-risk reduction.  
These are practical editing checks, not legal advice or platform policy guarantees.

## Common Rejection Triggers

1. Filler-heavy content with weak technical relevance
2. Abstract claims without implementation details
3. Title/body mismatch
4. Clickbait framing with low technical signal
5. Unsupported statistics or references
6. Excessive promotion and weak original insight

## Anti-Rejection Minimum

Before submission, ensure the article has:

1. Clear technical topic scope
2. At least one concrete mechanism explanation
3. At least one executable or inspectable artifact:
   - command/API example
   - code/config snippet
   - architecture flow
   - measured result
4. Explicit limitations or tradeoffs
5. Source attribution for external claims

## Submission Rescue Pattern

When an article is rejected for "灌水/技术无关":

1. Remove slogan paragraphs without technical payload.
2. Replace broad claims with mechanism + example.
3. Add one "how to reproduce" subsection.
4. Add one "failure case / boundary condition" subsection.
5. Re-check title to match technical depth and scope.

## Output Check Prompt

Use this short internal checklist before finalizing:

```text
- Is every major claim technically explainable?
- Can at least one key point be reproduced?
- Is there enough concrete detail to help practitioners act?
- Does the article teach something non-trivial?
```
