# Technical Review Rubric

Use this rubric to score a technical article before release.

## Scoring Model (100 points)

1. Technical correctness (30)
2. Evidence quality (20)
3. Reproducibility (15)
4. Structure and pedagogy (15)
5. Practical depth (10)
6. Language clarity (5)
7. Platform compliance readiness (5)

## Severity Rules

- `Critical`: factual error, unsafe guidance, fabricated data/source, or publish-blocking issue.
- `Major`: weak evidence, missing validation, broken structure, low reproducibility.
- `Minor`: wording, concision, tone, formatting polish.

## Publish Threshold

- `Ready`: score >= 85 and no Critical.
- `Needs revision`: score 70-84 or any Major cluster.
- `Blocked`: score < 70 or any unresolved Critical.

## What Counts as Evidence

Preferred order:

1. Official docs/specs/standards
2. Source code and commit history
3. Reproducible benchmark or experiment log
4. Reputable technical media or secondary analysis

If no source can be verified, mark the statement:

```text
Needs evidence: <claim>
```

## Reproducibility Checks

A practical technical article should include at least 2 items:

- exact commands or API calls
- config snippets or parameters
- error handling / edge cases
- validation method (test, metric, comparison)
- version/environment constraints
