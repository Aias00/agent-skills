---
name: chrome-extension-publish
description: Publish or update Chrome extensions on Chrome Web Store end-to-end. Use when preparing a first release, submitting an update, writing CWS form responses (permissions/remote code/data use/privacy), minimizing manifest permissions, packaging upload ZIPs, or addressing CWS review feedback/rejections.
---

# Chrome Extension Publish

Use this skill to ship Chrome extensions with minimal review risk and fast iteration.

## Workflow

1. Confirm release intent.
- Confirm whether this is first publish or update.
- Confirm target version and primary change summary.

2. Audit `manifest.json` for least privilege.
- Keep only actually used permissions.
- Remove unused host permissions and broad match patterns.
- Verify permission usage by searching code:
```bash
rg -n "chrome\\.(storage|alarms|notifications|tabs|scripting|identity)|fetch\\(" -S .
```

3. Build upload ZIP from source files only.
- Include: `manifest.json`, runtime code, icons, needed assets.
- Exclude: `.git`, screenshots, local notes, test artifacts.
- Before packaging, ensure release artifacts are git-ignored to avoid noisy commits.
- Treat `release/` as generated output only. Do not keep canonical docs only in `release/` if that folder is ignored.
- Keep the source-of-truth privacy policy in a tracked path (for example `docs/privacy-policy.md` or `privacy-policy.md`), and optionally copy/export a release copy when needed.
- Add/update `.gitignore` with:
```bash
release/
__pycache__/
*.py[cod]
```
- Prefer deterministic packaging command:
```bash
python3 - <<'PY'
import os, zipfile
root='.'
out='release/chrome-webstore.zip'
os.makedirs('release', exist_ok=True)
include_dirs=['background','popup','utils','icons','data']
files=['manifest.json']
for d in include_dirs:
    if not os.path.isdir(d): continue
    for b, _, ns in os.walk(d):
        for n in ns:
            if n == '.DS_Store': continue
            files.append(os.path.join(b,n))
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for f in files:
        z.write(f)
print(out)
PY
```

4. Prepare store listing graphic assets (required before submit).
- Follow current CWS image specs:
  - Store icon: `128x128` (PNG).
  - Screenshots: at least 1, up to 5, use `1280x800` (preferred) or `640x400`.
  - Small promo tile: `440x280`.
  - Marquee promo tile: `1400x560` (optional).
- Generate assets from one or more source images:
```bash
python3 scripts/generate_store_assets.py \
  --inputs /abs/path/source-1.png /abs/path/source-2.jpg \
  --icon-source /abs/path/icon.png \
  --root release/store-assets \
  --include-marquee
```
- The generator auto-picks an icon source from icon/logo-like names or near-square images.
- If multiple provided images are all screenshot-like, set `--icon-source` explicitly to avoid screenshot-derived icons.
- Use the naming convention in `references/cws-publish-templates.md`.
- Validate asset dimensions/count:
```bash
python3 scripts/validate_store_assets.py --root release/store-assets
```

5. Prepare store listing content.
- Write short summary and detailed description focused on user value.
- Always draft a Single Purpose statement for CWS (concise, concrete, feature-linked).
- State non-advisory nature for finance-related extensions.
- Produce paired Chinese and English versions for all listing text blocks (short summary, long description, single purpose, permissions rationale, remote code answer, data use disclosure, reviewer notes), unless user explicitly requests single-language output.
- If user asks for text, load `references/cws-publish-templates.md`.

6. Fill sensitive CWS forms correctly.
- Permissions rationale: explain each permission with concrete feature linkage.
- Remote code: answer "No" unless extension executes remote JS/Wasm/eval/new Function.
- Data use: if no personal data collection, select none and keep policy consistent.
- Privacy policy: provide public URL and ensure wording matches actual behavior.
- Privacy policy file location: default to a git-tracked file (for example `docs/privacy-policy.md`), not `release/privacy-policy.md` when `release/` is ignored.
- Privacy policy maintenance on every release/update:
  - Run a policy drift check against current code and manifest changes.
  - If behavior changed (permissions, host permissions, external endpoints, data storage keys, data flow, user-visible features), update policy text and `Last updated` date.
  - Keep CWS Data Use answers and privacy policy wording strictly consistent.
  - If no behavior changed, explicitly record "policy update not required" with reason.

7. Submit and track.
- Upload ZIP.
- Add review notes describing test path and why permissions are required.
- Keep a changelog entry for each submitted version.

## Decision Rules

### Remote Code
Answer "No remote code" when all executable JS/Wasm is packaged in extension files and network requests are data-only (JSON/HTML/text).

### Data Disclosure
Do not declare user data collection when extension only fetches public market data and stores cache locally without account identifiers.

### Privacy Policy Update Trigger
Update the privacy policy when any of the following changes:
- `manifest.json` permissions or host permissions.
- New or removed external data endpoints.
- New local storage keys/categories or changed retention/usage.
- New user data categories, analytics, auth/account linkage, or data sharing behavior.
- New feature flows that change what data is processed.
If none of the above changed, keep existing policy text but still refresh the release note with an explicit "no policy change" decision.

### Permission Rationale Quality Bar
For every permission:
- Mention exact feature.
- Mention scope and limits.
- Mention no personal data transfer when applicable.

### Single Purpose Quality Bar
- Must describe one core purpose in one short paragraph.
- Must map major features back to that same single purpose.
- Must explicitly state no unrelated functionality.

### Language Completeness
- Default output is bilingual (`ZH` + `EN`) for all CWS text content.
- Chinese and English versions must be semantically aligned, with no policy or feature mismatch.

## Rejection Triage

When CWS rejects:
1. Extract the exact rejection category and quote.
2. Map it to manifest fields and code paths.
3. Propose smallest fix first (remove permission, tighten host, correct image asset size, adjust wording).
4. Resubmit with explicit reviewer note on what changed.

## Output Contract

When assisting a publish task, return:
1. Release readiness checklist (pass/fail).
2. Required manifest changes (if any).
3. Graphic asset checklist (required/optional, size, status).
4. Privacy policy decision for this release (`update required` / `not required`) with concrete reason.
5. Ready-to-paste bilingual (`ZH`/`EN`) CWS text blocks (short summary, long description, single purpose, permissions, remote code, data use, review notes) and canonical privacy-policy file path.
6. Final packaging command and ZIP path.

## Templates

### Single Purpose (ZH) Template
该扩展的单一用途是帮助用户管理和维护浏览器书签。它会扫描书签链接状态、识别无效或重复书签，并提供按域名整理、重试检测与删除无效项等能力。以上功能均服务于“书签清理与组织”这一唯一目的，不包含与书签管理无关的功能。

### Single Purpose (EN) Template
The extension has a single purpose: helping users maintain and organize browser bookmarks. It checks bookmark link health, identifies invalid or duplicate bookmarks, and provides domain-based organization, retry checks, and invalid-bookmark removal. All features support this single bookmark-management purpose and do not provide unrelated functionality.
