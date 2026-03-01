---
name: chrome-extension-social-promo
description: Generate social media promotion content for a Chrome extension release. Use when the user asks for post drafts, campaign copy, launch announcements, or cross-platform social content (X/LinkedIn/Reddit/Telegram/Weibo/Xiaohongshu) based on extension manifest and release artifacts.
---

# Chrome Extension Social Promo

## Overview

Use this skill to generate ready-to-post promotion copy for Chrome extensions across multiple social platforms.
It reads extension metadata and release docs, then outputs channel-specific drafts with CTA, hashtags, and bilingual variants.

## When To Use

Trigger this skill for requests such as:
- "帮我写推广文案"
- "生成社交平台发帖内容"
- "做一套插件发布宣发文案"
- "write launch posts for my extension"
- "create X/LinkedIn/Reddit copy for this plugin"

Typical inputs:
- Extension root with `manifest.json`
- Optional publish artifacts:
  - `release/cws-listing.zh-en.md`
  - `release/permission-audit.md`
  - store URL and landing URL

## Core Command

Run from anywhere:

```bash
python3 scripts/generate_social_promo.py \
  --root /abs/path/to/extension \
  --store-url https://chromewebstore.google.com/detail/<item-id> \
  --website-url https://example.com \
  --lang bilingual
```

## Output

Default output file:
- `release/social-promo.md`

Generated sections include:
1. Campaign brief (name/version/value prop)
2. Message pillars and proof points
3. Platform-ready posts
   - X
   - LinkedIn
   - Reddit
   - Telegram
   - Weibo
   - Xiaohongshu
4. Reusable hashtag set
5. Publishing checklist

## Workflow

1. Parse `manifest.json` for product identity.
2. Parse `release/cws-listing.zh-en.md` when available for richer feature bullets.
3. Build short and long message variants per channel.
4. Enforce platform-aware style:
   - short/concise for X
   - structured/professional for LinkedIn
   - title + body for Reddit
5. Save to `release/social-promo.md` for direct copy/paste.

## Guardrails

- Do not claim unsupported outcomes ("best", "No.1", unverifiable metrics).
- Do not claim privacy/security guarantees beyond actual implementation.
- Keep product scope aligned with declared extension purpose.
- If store URL is missing, keep CTA as placeholder and mark clearly.

## Script

- `scripts/generate_social_promo.py`: deterministic social-content generator.

## References

- Platform guidance and copy structure: [references/social-platform-specs.md](references/social-platform-specs.md)
