# code-review

Unified code-review skill (single `SKILL.md`, zero dependencies). Three modes + a unified adversarial verification gate. Absorbs methodology from `github-pr-review`, `hzb-security-check`, `code-review-graph`, `claude-code-security-review`, `reverse-skill`, and `open-code-review`.

## Modes
- **pr** (`deep` / `follow-up` / `scan`) — PR diff review, comment follow-up & reply, whole-file audit.
- **repo-audit** — whole-repo defect discovery → dedup against existing issues → tiered confirm → create GitHub issues (security stays local).
- **security-audit** — Java security deep audit → local Markdown only, with adversarial independent verification gate (5 elements).

## Cross-cutting
- **Unified verification gate**: isolated independent verifier (only claim + file:line, no original reasoning), 5 elements for `confirmed`, fix-feasibility excluded from truth.
- **Graph-driven mental model** (impact radius / flows / communities / hub / bridge / knowledge-gap / semantic variants / complexity hotspots) — works with `rg`, accelerated by `code-review-graph` MCP.
- **Deterministic × Agent hybrid split** — file selection / rule matching / comment positioning are engineering-guaranteed, not LLM-guessed.
- **precision-over-recall** — prefer fewer true findings over noise.
- **Layered FP suppression** — hard-exclude → confidence cutoff → independent adversarial gate → positioning + reflection.

## Install
Single file — copy `SKILL.md` into your skill dir:
- Codex: `~/.codex/skills/code-review/SKILL.md`
- Claude Code: `~/.claude/skills/code-review/SKILL.md`

## Outward policy
Security findings never go to the issue tracker (local Markdown + vendor disclosure for Critical); non-security issues are created only after a tiered confirmation list. Default read-only; no comments/commits unless explicitly asked.
