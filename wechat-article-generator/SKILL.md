---
name: wechat-article-generator
description: Legacy compatibility skill for generating older WeChat article package outputs such as tar.gz bundles and inline-style HTML. Use only when maintaining an existing legacy package workflow or reproducing historical deliverables.
---

# WeChat Article Generator (Legacy)

This skill is kept for backward compatibility only.

## Do Not Use For New Work

For new article workflows, use:

```text
technical-article-review
→ technical-article-preflight
→ wechat-article-formatter
→ wechat-publisher
```

## When It Is Still Acceptable

Use this legacy skill only when you explicitly need to reproduce the older package shape:

- `article.md`
- `article-wechat.html`
- `images/`
- `README.txt`
- `{slug}.tar.gz`

## Why It Is Legacy

- It uses the older inline-style HTML conversion path.
- It bypasses the newer review-first pipeline by default.
- It is not the preferred formatter for current WeChat publishing work.

## Safe Boundary

If a user asks for “生成旧发布包”“兼容之前的 tar.gz 交付结构”“复刻老的 article-wechat.html 输出”，this skill is still appropriate.

Otherwise, prefer the repo-local modern workflow above.
