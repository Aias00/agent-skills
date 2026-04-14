# Lark Workflow Doc To Slides Design

Status: approved in chat, pending written-spec review

## Summary

Add a new repo-local skill, `lark-workflow-doc-to-slides`, that turns a Feishu/Lark document or Wiki page into a reviewable slide outline and, after explicit user confirmation, publishes the outline as a new Slides presentation or appends it to an existing Slides deck.

The first version is intentionally execution-capable rather than prompt-only:

- the skill routes and enforces workflow rules
- a Python script performs fetch, outline validation, XML rendering, and publishing
- outline approval is a hard gate before any slide creation

Defaults agreed in chat:

- target mode supports both `new` and `append`
- content mode supports both `faithful` and `report`
- default content mode is `report`
- default workflow is `outline first, generate second`
- append mode only adds slides and never rewrites existing slides

## Problem

The current Lark skill set already supports:

- reading document content via `lark-doc`
- creating and appending Slides via `lark-slides`

What is missing is the orchestration layer between them:

- fetch document content
- restructure it into slide-sized units
- show a human-reviewable intermediate outline
- convert the approved outline into valid slide XML
- publish either to a new deck or by appending to an existing deck

Without this workflow skill, the user must manually bridge a document-shaped artifact and a presentation-shaped artifact. That gap is exactly what this skill should close.

## Goals

- Accept a Feishu/Lark source document as input via URL, token, or document name.
- Generate a structured slide outline before any deck mutation.
- Support two authoring modes:
  - `faithful`: preserve original structure, compress for slides
  - `report`: reorganize into presentation logic, default
- Support two publishing targets:
  - create a new Slides deck
  - append new slides to an existing Slides deck
- Persist all intermediate artifacts to a run directory for auditability and restartability.
- Use existing `lark-cli` capabilities only; do not depend on a non-existent `slides +create-from-outline`.
- Avoid new Python dependencies in the first version.

## Non-goals

- No in-place editing, deletion, or reordering of existing slides.
- No automatic synchronization from future document edits back into Slides.
- No visual theme engine or multiple brand skins in v1.
- No automatic chart extraction from tables or spreadsheets in v1.
- No fully autonomous 30+ slide deck generation without human outline review.
- No direct HTML/PDF export layer; the workflow stops at Feishu Slides creation/update.

## User-facing behavior

### Trigger shape

The skill should be discoverable for prompts such as:

- "把这篇文档转成 PPT"
- "把这个 Wiki 做成飞书幻灯片"
- "帮我把周报文档变成汇报幻灯片"
- "根据文档名称生成 PPT"
- "把《项目周报》做成 Slides"
- "把这篇文档追加到现有 Slides"
- "doc to slides"
- "document to slides"
- "turn this doc into slides"
- "append slides from a document"

Prompts may refer to the source by URL, token, or document name.
When the source is given by name and multiple candidates match, the workflow must stop and ask the user to choose.

### Input contract

Primary source input is required, but it does not have to be a URL.

Supported source forms:

- `doc_url`
- `doc_name`
- `doc_token`

Optional:

- `target_slides_url`
- `content_mode` (`faithful` or `report`)
- `title`
- `max_slides`

Resolved defaults:

- `target_mode = new` when `target_slides_url` is absent
- `target_mode = append` when `target_slides_url` is present
- `content_mode = report` when omitted

### Hard gate

The workflow must always stop at the outline preview and wait for user confirmation before rendering slide XML or mutating any Slides presentation.

This is a workflow invariant, not a recommendation.

### Source resolution rules

The workflow should normalize all accepted source inputs into one concrete document target before fetch:

- `doc_url`: use directly
- `doc_token`: resolve directly through `lark-doc` supported token handling
- `doc_name`: search first, then require the user to choose one concrete result when ambiguity exists

For `doc_name`, automatic guessing is explicitly disallowed in v1. The resolution rule should be:

- `0` candidates: fail and ask the user to provide a better document identifier
- `1` clear candidate: continue automatically
- `>1` plausible candidates: stop and ask the user to choose before any fetch or outline generation continues

## Skill structure

The new skill should use a lightweight router layout:

```text
lark-workflow-doc-to-slides/
├── SKILL.md
├── references/
│   ├── workflow-new-slides.md
│   ├── workflow-append-slides.md
│   ├── content-modes.md
│   └── slide-authoring-rules.md
├── templates/
│   └── outline.json
└── scripts/
    └── doc_to_slides.py
```

### File responsibilities

#### `SKILL.md`

Acts as the router and policy surface:

- routes by `new` vs `append`
- routes by `faithful` vs `report`
- enforces outline approval gate
- requires reading:
  - `../lark-shared/SKILL.md`
  - `../lark-doc/SKILL.md`
  - `../lark-slides/SKILL.md`
- points detailed procedures to `references/`
- invokes the script entrypoints under `scripts/`

#### `references/workflow-new-slides.md`

Explains:

- fetch source doc
- produce and review outline
- render slide XML
- create a new deck
- choose between `slides +create --slides` and `slides +create` then `xml_presentation.slide.create`

#### `references/workflow-append-slides.md`

Explains:

- how `target_slides_url` is resolved
- append-only behavior
- duplicate-cover avoidance
- safe publication rules for adding pages to an existing deck

#### `references/content-modes.md`

Defines:

- when `faithful` should be used
- when `report` should be used
- what transformation latitude is allowed in each mode

#### `references/slide-authoring-rules.md`

Defines:

- page density
- max bullet counts
- title length expectations
- layout selection rules
- when to split content across pages
- when new decks can use batch create and when they must switch to incremental add

#### `templates/outline.json`

Provides the canonical intermediate schema shape used by both the AI and the validation script.

#### `scripts/doc_to_slides.py`

Provides executable workflow helpers with real I/O and publish behavior.

## Architecture

### High-level flow

```text
source input
→ resolve source
→ fetch source doc
→ generate outline
→ user confirms outline
→ validate outline
→ render slide XML
→ publish
→ return slides url + ids + run artifact paths
```

### Execution split

AI is responsible for:

- understanding the source content
- deciding on outline structure
- choosing `faithful` or `report`
- presenting outline preview to the user
- deciding when the outline is approved

Script is responsible for:

- calling `lark-cli`
- saving run artifacts
- validating intermediate JSON
- rendering deterministic slide XML from approved outline
- creating or appending Slides
- returning machine-readable publish results

This keeps semantic judgment and deterministic execution separated.

## Outline protocol

The intermediate outline should be JSON, not YAML, to avoid adding a YAML parser dependency.

Recommended template shape:

```json
{
  "presentation": {
    "title": "string",
    "subtitle": "string",
    "source": {
      "input_kind": "doc_name",
      "resolved_kind": "doc_url",
      "resolved_value": "string",
      "title": "string"
    },
    "target_mode": "new",
    "content_mode": "report",
    "audience": "string",
    "total_slides": 6
  },
  "slides": [
    {
      "no": 1,
      "role": "cover",
      "section_divider": false,
      "title": "页面标题",
      "objective": "这一页要让观众理解什么",
      "layout": "title-body",
      "key_points": [
        "要点 1",
        "要点 2"
      ],
      "source_sections": [
        "原文章节标题"
      ],
      "visual_hint": "可选：指标卡 / 对比 / 时间线",
      "notes": "可选补充"
    }
  ]
}
```

### Required fields

At minimum:

- `presentation.title`
- `presentation.source`
- `presentation.source.input_kind`
- `presentation.source.resolved_kind`
- `presentation.source.resolved_value`
- `presentation.target_mode`
- `presentation.content_mode`
- `slides[]`
- per slide:
  - `no`
  - `role`
  - `title`
  - `layout`
  - `key_points`

### Layout enum

The first version should support a bounded set:

- `title-only`
- `title-body`
- `two-column`
- `bullets`
- `comparison`
- `timeline`
- `metrics`

Unknown layouts should fail validation before render.

## Content modes

### `faithful`

Use when the source should remain structurally recognizable:

- technical design docs
- architecture notes
- API walkthroughs
- implementation proposals where section order matters

Rules:

- preserve chapter order unless there is an obvious slide split
- compress prose into bullets, do not reframe arguments into a management summary
- preserve limits, assumptions, and caveats from the source

### `report`

Default mode.

Use when the deck should read like a presentation instead of a compressed document:

- weekly reports
- project updates
- stakeholder briefings
- technical material that needs a meeting-friendly structure

Suggested shape:

- cover
- background / goal
- problem / current state
- proposal / approach
- key execution details
- value / outcomes
- risks / decisions
- next steps

Rules:

- content can be reorganized across source sections
- not every source section needs a slide
- appendix-like detail may be dropped or folded into notes

## Slide authoring rules

These rules should be enforced in references and partly by validation:

- One slide should communicate one main idea.
- Default bullet count per slide: 3 to 5.
- A single bullet should ideally stay within two visual lines.
- If a slide exceeds the density budget, split it instead of shrinking the font.
- If two or more consecutive slides are pure text, at least one should be considered for `comparison`, `timeline`, or `metrics` layout.
- In append mode, do not generate a cover slide unless the outline explicitly marks it as a section divider via a boolean field such as `section_divider: true`.
- In append mode, avoid re-creating a generic "目录" or "封面" if the target deck clearly already has one.

## Script design

Single script, multiple subcommands:

```text
python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py resolve-source
python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py fetch
python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py validate-outline
python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py render
python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py publish
```

### `resolve-source`

Purpose:

- normalize `doc_url`, `doc_token`, or `doc_name` into one concrete source target before fetch
- make source ambiguity explicit before any outline generation or slide mutation

Inputs:

- exactly one of:
  - `--doc-url`
  - `--doc-token`
  - `--doc-name`
- `--run-dir`

Behavior:

- `doc_url`: persist as already resolved
- `doc_token`: persist as already resolved
- `doc_name`: search document-like sources first, restricted to source types that `lark-cli docs +fetch` can consume
- `doc_name` resolution must follow:
  - `0` candidates: fail
  - `1` clear candidate: continue
  - `>1` plausible candidates: stop and require user choice
- when `doc_name` returns multiple plausible candidates:
  - stop immediately
  - emit a shortlist of candidates for user choice
  - optional ranking may be included as advisory metadata, but never used for auto-selection

Outputs:

- `resolved-source.json`

Suggested fields:

- `input_kind`
- `resolved_kind`
- `resolved_value`
- `title`
- `search_candidates`
- `needs_user_choice`

### `fetch`

Purpose:

- call `lark-cli docs +fetch --as user --format json`
- persist the raw structured result
- persist extracted markdown

Inputs:

- `--resolved-source`
- `--run-dir`

Outputs:

- `source.json`
- `source.md`

Behavior notes:

- fetch must continue pagination until the full source document is retrieved
- if `docs +fetch` returns `has_more`, the script must continue with the appropriate `offset` / `limit` inputs until completion
- `source.md` must represent the full source document, not only the first fetched chunk

### `validate-outline`

Purpose:

- schema validation
- density checks
- mode/target consistency checks

Inputs:

- `--outline`

Checks:

- required fields exist
- `slides` non-empty
- valid `layout`
- `key_points` list length within bounds
- append mode does not implicitly inject duplicate cover behavior

Output:

- zero exit on valid outline
- machine-readable error report on failure

### `render`

Purpose:

- map approved outline JSON to a list of slide XML strings

Inputs:

- `--outline`
- `--run-dir`

Outputs:

- `slides.json`
- `render-summary.json`

Rules:

- choose XML scaffolds by `role` and `layout`
- produce valid slide XML compatible with existing `lark-slides` references
- keep rendering deterministic from the outline

### `publish`

Purpose:

- publish rendered slides to Feishu Slides

Inputs:

- `--outline`
- `--slides-json`
- optional `--target-slides-url`
- `--run-dir`

Behavior:

- new deck, `<= 10` slides:
  - use `lark-cli slides +create --as user --title ... --slides ...`
- new deck, `> 10` slides:
  - use `lark-cli slides +create --as user --title ...`
  - extract `xml_presentation_id`
  - loop `lark-cli slides xml_presentation.slide create --as user`
- append mode:
  - resolve the target presentation id
  - loop `xml_presentation.slide create`

Outputs:

- `publish-result.json`

Result fields should include:

- `target_mode`
- `xml_presentation_id`
- `url`
- `slide_ids`
- `slides_added`
- `run_dir`

## URL and target resolution

### Source document

The workflow assumes source resolution can end at a document target compatible with `lark-cli docs +fetch`.

Supported final source targets should include:

- docx urls
- wiki urls resolving to document content
- document tokens supported by `lark-doc`

When the original input is `doc_name`, the workflow must first search for candidate documents. The search stage must only return candidates that the later fetch stage can actually consume. Resolution behavior must be:

- `0` candidates: fail
- `1` clear candidate: continue
- `>1` plausible candidates: stop for user confirmation

### Target slides

If `target_slides_url` is provided:

- direct `/slides/` URLs should resolve directly to `xml_presentation_id`
- `/wiki/` URLs must follow the existing `lark-slides` guidance:
  - resolve the wiki node first
  - confirm `obj_type == slides`
  - use `obj_token` as the true presentation id

If resolution fails, publication must stop before any page mutation.

## Run artifacts

All workflow state should persist under:

```text
.lark-workflow-doc-to-slides/runs/<timestamp>-<slug>/
```

Planned contents:

```text
resolved-source.json
source.json
source.md
outline.json
slides.json
render-summary.json
publish-result.json
```

This is required for:

- reproducibility
- debugging
- partial recovery after failed publish
- user review of the intermediate outline

## Error handling

### Fetch failure

Possible causes:

- invalid source URL
- invalid source token
- document name search returned no usable match
- document name search returned multiple plausible matches and the user has not selected one
- wrong identity
- missing document permission

Handling:

- stop immediately
- surface the underlying `lark-cli` error
- if permission-related, route according to `lark-shared`
- if source ambiguity-related, return candidate items and require explicit user selection
- if fetch pagination is incomplete or interrupted, do not continue to outline generation

### Outline validation failure

Handling:

- stop before render
- identify the failing slide index and field
- do not attempt XML generation

### Render failure

Handling:

- stop before publish
- report the failing slide index and layout/field cause
- keep the run directory for inspection

### Publish partial failure

Handling:

- do not silently roll back
- preserve created presentation and already-added pages
- return partial success metadata:
  - created presentation id
  - number of successful slides before failure
  - failed slide index
- keep `slides.json` to allow resume

### Append target mismatch

Handling:

- stop if target URL cannot be resolved to a Slides presentation
- stop if target is a wiki node that is not `obj_type=slides`

## Testing strategy

Implementation planning should cover three test layers.

### 1. Unit tests for script logic

- source input normalization
- mutually exclusive source argument validation
- `doc_name` zero-match behavior
- `doc_name` single-match auto-continue behavior
- ambiguous `doc_name` candidate handling
- paginated fetch aggregation
- outline validation
- layout enum validation
- role-to-layout rendering selection
- target mode branching
- run directory naming and file persistence

### 2. Snapshot-style tests for XML rendering

- render a small outline fixture
- assert stable XML for:
  - cover slide
  - content slide
  - comparison slide
  - summary / closing slide

### 3. Integration-style dry-run tests

Where feasible:

- verify generated `lark-cli` command shapes
- verify new-vs-append branch behavior
- verify `> 10` slide switch from batch create to incremental append

The first implementation should prefer deterministic script tests over live network tests.

## Acceptance criteria

The design is considered satisfied when implementation can demonstrate:

- support for source inputs via `doc_url`, `doc_token`, and `doc_name`
- automatic continue behavior when `doc_name` resolves to exactly one clear candidate
- explicit stop-and-choose behavior when `doc_name` resolves to multiple plausible candidates
- full-document fetch behavior across paginated `docs +fetch` responses
- outline-first workflow, with an explicit user approval stop
- both `new` and `append` target modes
- both `faithful` and `report` content modes, defaulting to `report`
- successful publication path using only existing `lark-cli` slide commands
- persisted run artifacts under `.lark-workflow-doc-to-slides/runs/...`
- zero new non-stdlib Python dependencies

## Risks

- Slide XML can become brittle if too much free-form logic is delegated to the AI.
- Append mode can create awkward decks if duplicate-cover detection is too naive.
- Source documents can be far denser than presentation-appropriate content, pushing too much judgment into outline generation.
- Name-based source resolution introduces ambiguity and increases the risk of generating from the wrong document if the workflow guesses.

The design intentionally mitigates these by:

- making outline the only AI-authored intermediate contract
- moving XML rendering to a deterministic script
- making append mode additive only
- requiring explicit outline approval
- forbidding automatic selection when `doc_name` matches multiple candidates

## Open implementation notes

- The script should not depend on `jq`, `yq`, or external YAML tooling.
- The script should assume `lark-cli` is the only required external binary.
- The script should treat the outline as the single source of truth after user approval; render and publish must not mutate the outline semantics.
- The skill should clearly state that `slides +create-from-outline` does not exist and is intentionally emulated through the approved command chain.
- The script should provide a source-resolution stage for `doc_name`, and in ambiguous cases must emit ranked candidates rather than auto-selecting one.
