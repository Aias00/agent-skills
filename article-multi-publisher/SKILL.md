---
name: article-multi-publisher
description: Publish the same article package directly to one or more of WeChat Official Account (微信公众号), Xiaohongshu (小红书), and Toutiao (头条号). Use when the user wants a unified workflow for 多平台发文, 同步发布到公众号/小红书/头条, or wants one article package dispatched to these Chinese content platforms.
---

# Article Multi Publisher

Use this skill when one reviewed article or one article package needs to go to any combination of:

- 微信公众号
- 小红书
- 头条号

## Unified Entry

From the repository root:

```bash
python3 article-multi-publisher/scripts/publish.py <source> [options]
```

`<source>` can be:

- an article package directory
- a single `.md` file
- a single `.html` file

## Repo-local Dependencies

This repo-local version resolves platform publishers from the repository itself:

- WeChat → [wechat-publisher](../wechat-publisher/SKILL.md)
- Xiaohongshu → `post-to-xhs/`
- Toutiao → `toutiao-publisher/`

If you only publish to WeChat, Xiaohongshu and Toutiao runtime dependencies do not need to be healthy in the current run.

## Source Resolution

If `<source>` is a directory, the script resolves platform variants automatically:

- `wechat`: pass directory or final HTML straight to [wechat-publisher](../wechat-publisher/SKILL.md)
- `xhs`: `article-xhs.md` → `xhs.md` → `article-toutiao.md` → `article.md`
- `toutiao`: `article-toutiao.md` → `article.md` → `article.html`

Cover/image fallback:

- `images/01-cover.*`
- `images/cover.*`
- `images/cover-wide.*`
- `imgs/cover.*`
- first image under `images/` or `imgs/`

## Defaults

Optional config files:

- project: `.baoyu-skills/article-multi-publisher/EXTEND.md`
- user: `$HOME/.baoyu-skills/article-multi-publisher/EXTEND.md`

Supported keys:

- `default_platforms`
- `default_xhs_mode`
- `default_xhs_template`
- `default_xhs_account`
- `default_wechat_author`

## Usage

Publish to all configured platforms:

```bash
python3 article-multi-publisher/scripts/publish.py ./article-package
```

Publish to WeChat + Toutiao only:

```bash
python3 article-multi-publisher/scripts/publish.py ./article-package --platforms wechat,toutiao
```

Force Xiaohongshu long-article mode:

```bash
python3 article-multi-publisher/scripts/publish.py ./article-package \
  --platforms xhs \
  --xhs-mode long-article \
  --xhs-template "杂志风"
```

Resolve commands without publishing:

```bash
python3 article-multi-publisher/scripts/publish.py ./article-package --dry-run
```

## Platform Strategy

- `wechat`: delegates article publishing to [wechat-publisher](../wechat-publisher/SKILL.md)
- `xhs`: uses repo-local `post-to-xhs`; defaults to image-text unless long-article template is configured
- `toutiao`: uses repo-local `toutiao-publisher` direct API flow

Current boundary:

- This wrapper resolves source files, titles, covers, and per-platform variants.
- Platform-specific metadata quirks should be fixed in the underlying platform skill, not duplicated here.

## Notes

- If WeChat needs a default author, keep `wechat-publisher/EXTEND.md` as the source of truth.
- Existing logins and credentials are reused from the underlying platform skills; this wrapper does not create new sessions by itself.
- If you distribute this repo to another machine, verify the platform-specific runtimes in `post-to-xhs/`, `toutiao-publisher/`, and `wechat-publisher/` before expecting end-to-end publishing to succeed.
