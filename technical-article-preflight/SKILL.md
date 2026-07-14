---
name: technical-article-preflight
description: 审阅并整理技术文章的发文前准备项，输出可执行的修订与发布前检查结论。用于技术文章在发布前的预检场景，例如用户说“发文前检查”“提审前过一遍”“技术文章预审”“公众号发布前看看这篇”“检查封面/配图/HTML 是否能发”，尤其适合面向微信公众号、头条号、腾讯开发者社区或通用技术博客的 Markdown/HTML 文章包。
---

# Technical Article Preflight

## Overview

在技术文章进入发布前，先做一次“预检”，避免把不稳定的稿件、裁切的配图、过时的数字、或已经失真的 HTML 直接推进发布。

这个 skill 的目标不是直接重写一切，而是把发文前准备收成一个固定流程：先审稿，再修图，再生成最终发布包，最后做本地验证。

对微信公众号链路，这个 skill 是 `technical-article-review`、`wechat-article-formatter`、`wechat-publisher` 之间的发布前总闸。只要任务包含“写完并发布”“发到公众号草稿箱”“生成可发包再发布”，就先用这里的检查结果决定能不能进入发布脚本。

补充规则：

- 对技术文章，`写完首稿` 不等于 `稿件就绪`
- 首稿完成后，应该先 review，再把 review 结果直接落回源稿
- 只有经过 review 的修订稿，才应该继续进入 HTML、配图和发布

## Workflow

```text
Preflight Progress:
- [ ] Step 1: Find the source of truth
- [ ] Step 2: Review technical publish readiness
- [ ] Step 3: Apply review findings to the source article
- [ ] Step 4: Re-check the revised source
- [ ] Step 5: Check cover and inline diagrams
- [ ] Step 6: Regenerate platform output
- [ ] Step 7: Verify final package locally
- [ ] Step 8: Declare ready or list blockers
```

## WeChat Standard Path

Use this sequence for WeChat article delivery:

1. Keep Markdown as the source of truth.
2. Run `technical-article-review` and apply blocking fixes to the Markdown.
3. Check cover and inline images before generating final output.
4. Regenerate WeChat HTML through `wechat-article-formatter`.
5. Run `wechat-publisher/scripts/wechat-publish.ts <article.md> --dry-run`.
6. Publish only after the dry run resolves title, summary, author, cover, theme, and source path correctly.

Do not treat a successful formatter run as publish readiness. Formatter output proves only that HTML can be generated; it does not prove the article is reviewed, images are publishable, or the final WeChat draft metadata is correct.

### Step 1: Find the Source of Truth

Determine which file should be edited first.

- If markdown and HTML both exist, treat markdown as the source of truth unless the user explicitly says the HTML is canonical.
- If the article has local images, identify:
  - final article markdown/html
  - cover image
  - all inline diagrams or screenshots

Hard rule:
- Do not patch stale HTML first if the markdown draft is still being revised.

### Step 2: Review Technical Publish Readiness

If the article is technical, invoke `technical-article-review` before formatting or publishing.

If the article was just drafted in the current turn, still review it before treating it as ready.

Check for:
- fact vs inference separation
- time-sensitive numbers that need a date or a caveat
- at least one concrete mechanism explanation
- at least one reproducible path, command, config, or runtime precondition
- explicit limits, failure cases, or environment assumptions

If the article reads like a good commentary but lacks reproducibility, revise the article source first.

### Step 3: Apply Review Findings to the Source Article

If Step 2 returns `Needs revision`, do not stop at the review report. Patch the source markdown directly before moving on.

Make high-signal fixes in the source markdown:

- replace unsupported exact numbers with dated approximate values unless they were freshly verified
- add a short “minimum prerequisites / how to run” section when the article discusses code, experiments, APIs, or benchmarks
- convert slogan paragraphs into mechanism + condition statements
- reduce speculative wording around implementation details
- tighten repetitive commentary in the second half of the article
- add one concrete “first run” or “minimum workflow” path when the article is recommendation-heavy

Hard rules:
- Never fabricate facts, metrics, or repository behavior.
- Never hide uncertainty; add a caveat instead.

### Step 4: Re-check the Revised Source

After revising the markdown, do one quick confirmation pass before touching HTML or images.

Confirm:
- the top review findings were actually addressed
- newly added commands, setup steps, or prerequisites are traceable to a source
- section flow still reads naturally after the insertions
- no stale HTML-only fixes were applied to derived files instead of the source article

If the review originally found evidence gaps, verify that the revised text now uses either primary-source facts or explicit caveats.

### Step 5: Check Cover and Inline Diagrams

Verify that the article package is visually publishable.

Confirm:
- a usable cover exists, typically `imgs/cover.png`
- every inline image referenced by the final markdown/html exists on disk
- diagrams keep text inside a safe inner area
- long labels are manually wrapped when needed

For SVG-based diagrams:
- preserve the original canvas ratio when exporting to PNG
- do not use export paths that silently create cropped square thumbnails
- prefer shorter lines for labels like `TIME_BUDGET`, `peak_vram_mb`, `evaluate_bpb`

Blocker rule:
- If a diagram is clipped, cropped, or text touches the card edge, do not publish yet.

### Step 6: Regenerate Platform Output

Once the article source is stable, regenerate the platform artifact instead of hand-editing an old export.

Typical integrations:
- WeChat: use `wechat-article-formatter`
- Final publish to WeChat: use `wechat-publisher`

If the target output is WeChat HTML:
- regenerate HTML from the revised markdown
- then re-apply any custom project theme if you intentionally override formatter defaults

### Step 7: Verify Final Package Locally

Do one local verification pass on the final package.

Check:
- title, summary, author, and cover metadata
- images load
- lists and numbering render correctly
- theme/colors did not fall back unexpectedly
- code blocks remain readable

For WeChat HTML bundles, prefer a quick local browser preview before API publishing.

### Step 8: Declare Ready or List Blockers

When done, report one of:

- `Ready`: article source, images, cover, and publish artifact are all usable
- `Needs revision`: article is fixable before publish, list the blocking items in order

Keep the output concise and actionable.

## Output Template

```markdown
## Preflight Verdict
- Status: Ready / Needs revision
- Source of truth:
- Target platform:

## Blockers
1. ...
2. ...

## Ready Checks
- [ ] Source article updated
- [ ] Images verified
- [ ] Cover verified
- [ ] Final HTML/output regenerated
- [ ] Local preview checked
```

## Integration Notes

Use these skills when relevant:

- `technical-article-review` for technical correctness and publish readiness
- `wechat-article-formatter` for Markdown → WeChat HTML conversion
- `wechat-publisher` once the package is confirmed ready
- `frontend-design` only when the user wants stronger visual redesign for cover or diagrams

Operational rules:
- If `technical-article-review` finds blocking issues and the user wants the article shipped, revise the source article in the same turn instead of leaving the process at a review report.
- Default behavior: once review is complete, apply the high-signal fixes directly unless the user explicitly asked for `review-only`, `只审不改`, or an equivalent constraint.
- For newly written technical articles, do not present the first draft as the final draft. Review first, revise second, then surface the revised source.

## Hard Rules

- Edit the source article before regenerating derived HTML.
- Do not skip preflight when the same task asks to write or revise a technical article and publish it.
- Treat clipped or distorted diagrams as publish blockers.
- Time-sensitive figures must include a date or an explicit caveat.
- Do not publish a package you have not previewed locally when local preview is feasible.
- For WeChat, do not publish until `wechat-publish.ts --dry-run` confirms the resolved source, title, and theme path.
