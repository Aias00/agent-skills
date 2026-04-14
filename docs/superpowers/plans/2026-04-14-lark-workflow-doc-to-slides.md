# Lark Workflow Doc To Slides Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repo-local `lark-workflow-doc-to-slides` skill that resolves a source document from URL/token/name, generates a reviewable outline, renders deterministic slide XML, and publishes a new or append-only Feishu Slides deck through existing `lark-cli` commands.

**Architecture:** The feature is split into two layers: a router-style skill package that defines workflow policy and a single Python script with subcommands (`resolve-source`, `fetch`, `validate-outline`, `render`, `publish`) that performs deterministic I/O and publish work. The AI owns source interpretation and outline authoring, while the script owns lark-cli invocation, pagination, validation, XML rendering, and result persistence.

**Tech Stack:** Markdown skill files, Python 3 standard library (`argparse`, `json`, `pathlib`, `subprocess`, `tempfile`, `unittest`, `urllib.parse`, `xml.sax.saxutils`), existing `lark-cli` commands from `lark-doc` and `lark-slides`.

---

## File Map

### New skill package

- Create: `lark-workflow-doc-to-slides/SKILL.md`
  Responsibility: router entrypoint, trigger wording, hard gates, required reading, and workflow branching.

- Create: `lark-workflow-doc-to-slides/references/workflow-new-slides.md`
  Responsibility: “new deck” execution path and its operator rules.

- Create: `lark-workflow-doc-to-slides/references/workflow-append-slides.md`
  Responsibility: “append to existing deck” execution path, including additive-only constraints.

- Create: `lark-workflow-doc-to-slides/references/content-modes.md`
  Responsibility: `faithful` vs `report` mode guidance and selection rules.

- Create: `lark-workflow-doc-to-slides/references/slide-authoring-rules.md`
  Responsibility: slide density, layout choice, duplicate-cover avoidance, and new-vs-append XML authoring constraints.

- Create: `lark-workflow-doc-to-slides/templates/outline.json`
  Responsibility: canonical intermediate outline schema example that both the AI and script validate against.

- Create: `lark-workflow-doc-to-slides/scripts/doc_to_slides.py`
  Responsibility: CLI entrypoint plus reusable helpers for source resolution, fetch pagination, outline validation, XML rendering, and publish orchestration.

### Tests

- Create: `tests/lark_workflow_doc_to_slides/test_doc_to_slides.py`
  Responsibility: unit tests and integration-style dry-run tests for the Python script.

- Create: `tests/lark_workflow_doc_to_slides/fixtures/search-zero.json`
  Responsibility: name-resolution fixture for zero-match behavior.

- Create: `tests/lark_workflow_doc_to_slides/fixtures/search-single.json`
  Responsibility: name-resolution fixture for single-match auto-continue behavior.

- Create: `tests/lark_workflow_doc_to_slides/fixtures/search-multiple.json`
  Responsibility: name-resolution fixture for ambiguous candidate handling.

- Create: `tests/lark_workflow_doc_to_slides/fixtures/fetch-page-1.json`
  Responsibility: first paginated docs fetch result.

- Create: `tests/lark_workflow_doc_to_slides/fixtures/fetch-page-2.json`
  Responsibility: second paginated docs fetch result.

- Create: `tests/lark_workflow_doc_to_slides/fixtures/outline-valid-report.json`
  Responsibility: valid report-mode outline for render tests.

- Create: `tests/lark_workflow_doc_to_slides/fixtures/outline-invalid-layout.json`
  Responsibility: invalid layout fixture for validation failures.

- Create: `tests/lark_workflow_doc_to_slides/fixtures/presentation-create.json`
  Responsibility: mocked `slides +create` success response.

- Create: `tests/lark_workflow_doc_to_slides/fixtures/slide-create.json`
  Responsibility: mocked `xml_presentation.slide.create` success response.

- Create: `tests/lark_workflow_doc_to_slides/fixtures/wiki-node-slides.json`
  Responsibility: mocked wiki-node resolution response for append-mode target resolution.

### Repo docs

- Modify: `README.md`
  Responsibility: list the new skill in the repo-local skill library and describe its purpose in one short bullet.

## Implementation Strategy

Implementation should proceed in four layers:

1. Script interface and source resolution.
2. Full-document fetch and outline validation.
3. Deterministic XML rendering.
4. Publish orchestration plus skill documentation.

Keep the Python script as one file to match the approved design, but structure it with small pure functions that tests can call directly.

Before implementation starts, freeze these interface contracts and keep them aligned across script, template, tests, and skill docs:

- `resolve-source` is a first-class stage and persists `resolved-source.json`
- outline uses an explicit boolean such as `section_divider` for append-mode divider slides; no magic string markers
- publish writes a normalized `publish-result.json` shape with top-level fields:
  - `target_mode`
  - `xml_presentation_id`
  - `url`
  - `slide_ids`
  - `slides_added`
  - `run_dir`
- every layout accepted by validation must be renderable, or it must be removed from the allowed enum and template/docs

Recommended top-level functions inside `doc_to_slides.py`:

```python
def parse_args(argv: list[str]) -> argparse.Namespace: ...
def ensure_run_dir(path_arg: str | None) -> Path: ...
def resolve_source(args: argparse.Namespace, run_dir: Path) -> dict: ...
def fetch_source(resolved: dict, run_dir: Path) -> dict: ...
def validate_outline(outline: dict) -> None: ...
def render_outline(outline: dict, run_dir: Path) -> dict: ...
def publish_slides(outline: dict, slides: list[str], run_dir: Path, target_slides_url: str | None) -> dict: ...
def main(argv: list[str] | None = None) -> int: ...
```

Subprocess access to `lark-cli` should go through one wrapper:

```python
def run_lark_cli(args: list[str]) -> dict:
    proc = subprocess.run(args, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"lark-cli failed: {' '.join(args)}")
    return json.loads(proc.stdout)
```

That single wrapper gives tests one seam to stub.

## Tasks

### Task 1: Scaffold the script and test harness

**Files:**
- Create: `lark-workflow-doc-to-slides/scripts/doc_to_slides.py`
- Create: `tests/lark_workflow_doc_to_slides/test_doc_to_slides.py`
- Create: `tests/lark_workflow_doc_to_slides/fixtures/outline-valid-report.json`
- Create: `tests/lark_workflow_doc_to_slides/fixtures/outline-invalid-layout.json`

- [ ] **Step 1: Write the failing script-entry and argument tests**

```python
import importlib.util
import json
import pathlib
import sys
import unittest

SCRIPT_PATH = pathlib.Path("lark-workflow-doc-to-slides/scripts/doc_to_slides.py")

def load_module():
    spec = importlib.util.spec_from_file_location("doc_to_slides", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["doc_to_slides"] = module
    spec.loader.exec_module(module)
    return module


class CliSkeletonTests(unittest.TestCase):
    def test_module_exposes_main(self):
        module = load_module()
        self.assertTrue(callable(module.main))

    def test_resolve_source_requires_exactly_one_source_flag(self):
        module = load_module()
        with self.assertRaises(SystemExit) as cm:
            module.main(["resolve-source", "--run-dir", "/tmp/run"])
        self.assertEqual(cm.exception.code, 2)

    def test_validate_outline_rejects_invalid_layout_fixture(self):
        module = load_module()
        outline = json.loads(pathlib.Path(
            "tests/lark_workflow_doc_to_slides/fixtures/outline-invalid-layout.json"
        ).read_text())
        with self.assertRaises(ValueError):
            module.validate_outline(outline)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python3 -m unittest discover tests/lark_workflow_doc_to_slides -v
```

Expected:

- import failure because `doc_to_slides.py` does not exist yet, or
- missing `main` / `validate_outline` symbols

- [ ] **Step 3: Write the minimal script skeleton**

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

VALID_LAYOUTS = {
    "title-only",
    "title-body",
    "two-column",
    "bullets",
    "comparison",
    "timeline",
    "metrics",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    rs = sub.add_parser("resolve-source")
    rs.add_argument("--doc-url")
    rs.add_argument("--doc-token")
    rs.add_argument("--doc-name")
    rs.add_argument("--run-dir", required=True)

    fetch = sub.add_parser("fetch")
    fetch.add_argument("--resolved-source", required=True)
    fetch.add_argument("--run-dir", required=True)

    validate = sub.add_parser("validate-outline")
    validate.add_argument("--outline", required=True)

    render = sub.add_parser("render")
    render.add_argument("--outline", required=True)
    render.add_argument("--run-dir", required=True)

    publish = sub.add_parser("publish")
    publish.add_argument("--outline", required=True)
    publish.add_argument("--slides-json", required=True)
    publish.add_argument("--run-dir", required=True)
    publish.add_argument("--target-slides-url")

    return parser.parse_args(argv)


def validate_outline(outline: dict) -> None:
    for slide in outline.get("slides", []):
        layout = slide.get("layout")
        if layout not in VALID_LAYOUTS:
            raise ValueError(f"invalid layout: {layout}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "resolve-source":
        sources = [v for v in [args.doc_url, args.doc_token, args.doc_name] if v]
        if len(sources) != 1:
            raise SystemExit(2)
        return 0
    if args.command == "validate-outline":
        outline = json.loads(Path(args.outline).read_text())
        validate_outline(outline)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify the skeleton passes**

Run:

```bash
python3 -m unittest discover tests/lark_workflow_doc_to_slides -v
```

Expected:

- basic CLI and validation tests PASS

- [ ] **Step 5: Commit**

```bash
git add lark-workflow-doc-to-slides/scripts/doc_to_slides.py tests/lark_workflow_doc_to_slides
git commit -m "feat: scaffold doc-to-slides script and test harness"
```

### Task 2: Implement source resolution for URL, token, and document name

**Files:**
- Modify: `lark-workflow-doc-to-slides/scripts/doc_to_slides.py`
- Modify: `tests/lark_workflow_doc_to_slides/test_doc_to_slides.py`
- Create: `tests/lark_workflow_doc_to_slides/fixtures/search-zero.json`
- Create: `tests/lark_workflow_doc_to_slides/fixtures/search-single.json`
- Create: `tests/lark_workflow_doc_to_slides/fixtures/search-multiple.json`

- [ ] **Step 1: Write failing source-resolution tests**

```python
from unittest import mock


class ResolveSourceTests(unittest.TestCase):
    @mock.patch("doc_to_slides.run_lark_cli")
    def test_doc_url_passes_through(self, run_lark_cli):
        module = load_module()
        run_dir = pathlib.Path("/tmp/run")
        args = module.parse_args(["resolve-source", "--doc-url", "https://x/docx/abc", "--run-dir", str(run_dir)])
        resolved = module.resolve_source(args, run_dir)
        self.assertEqual(resolved["resolved_kind"], "doc_url")
        self.assertEqual(resolved["resolved_value"], "https://x/docx/abc")
        run_lark_cli.assert_not_called()

    @mock.patch("doc_to_slides.run_lark_cli")
    def test_doc_name_zero_match_fails(self, run_lark_cli):
        module = load_module()
        run_lark_cli.return_value = json.loads(pathlib.Path(
            "tests/lark_workflow_doc_to_slides/fixtures/search-zero.json"
        ).read_text())
        args = module.parse_args(["resolve-source", "--doc-name", "不存在的文档", "--run-dir", "/tmp/run"])
        with self.assertRaises(RuntimeError):
            module.resolve_source(args, pathlib.Path("/tmp/run"))

    @mock.patch("doc_to_slides.run_lark_cli")
    def test_doc_name_single_match_continues(self, run_lark_cli):
        module = load_module()
        run_lark_cli.return_value = json.loads(pathlib.Path(
            "tests/lark_workflow_doc_to_slides/fixtures/search-single.json"
        ).read_text())
        args = module.parse_args(["resolve-source", "--doc-name", "项目周报", "--run-dir", "/tmp/run"])
        resolved = module.resolve_source(args, pathlib.Path("/tmp/run"))
        self.assertFalse(resolved["needs_user_choice"])

    @mock.patch("doc_to_slides.run_lark_cli")
    def test_doc_name_multiple_matches_stop_for_choice(self, run_lark_cli):
        module = load_module()
        run_lark_cli.return_value = json.loads(pathlib.Path(
            "tests/lark_workflow_doc_to_slides/fixtures/search-multiple.json"
        ).read_text())
        args = module.parse_args(["resolve-source", "--doc-name", "项目周报", "--run-dir", "/tmp/run"])
        resolved = module.resolve_source(args, pathlib.Path("/tmp/run"))
        self.assertTrue(resolved["needs_user_choice"])
        self.assertGreater(len(resolved["search_candidates"]), 1)
```

- [ ] **Step 2: Run the source-resolution tests and verify they fail**

Run:

```bash
python3 -m unittest discover tests/lark_workflow_doc_to_slides -v
```

Expected:

- failures for missing `resolve_source`
- failures for unresolved fixture handling

- [ ] **Step 3: Implement `resolve_source()` and persistence**

```python
FETCHABLE_ENTITY_TYPES = {"DOC", "DOCX"}
RESOLVABLE_ENTITY_TYPES = {"WIKI"}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def extract_search_candidates(search_result: dict) -> list[dict]:
    data = search_result.get("data", {})
    results = data.get("results") or data.get("res_units") or []
    candidates = []
    for item in results:
        result_meta = item.get("result_meta") or {}
        entity_type = item.get("entity_type") or result_meta.get("doc_types")
        url = result_meta.get("url")
        if not url:
            continue
        if isinstance(entity_type, list):
            candidate_type = entity_type[0] if entity_type else ""
        else:
            candidate_type = entity_type or ""
        if candidate_type in FETCHABLE_ENTITY_TYPES:
            resolved_kind = "doc_url"
        elif candidate_type in RESOLVABLE_ENTITY_TYPES:
            resolved_kind = "wiki_url"
        else:
            continue
        candidates.append({
            "title": item.get("title") or item.get("title_highlighted") or "",
            "resolved_kind": resolved_kind,
            "resolved_value": url,
            "entity_type": candidate_type,
        })
    return candidates


def resolve_source(args: argparse.Namespace, run_dir: Path) -> dict:
    if args.doc_url:
        resolved = {
            "input_kind": "doc_url",
            "resolved_kind": "doc_url",
            "resolved_value": args.doc_url,
            "title": "",
            "search_candidates": [],
            "needs_user_choice": False,
        }
    elif args.doc_token:
        resolved = {
            "input_kind": "doc_token",
            "resolved_kind": "doc_token",
            "resolved_value": args.doc_token,
            "title": "",
            "search_candidates": [],
            "needs_user_choice": False,
        }
    else:
        search_result = run_lark_cli([
            "lark-cli", "docs", "+search", "--as", "user",
            "--format", "json", "--query", args.doc_name,
        ])
        candidates = extract_search_candidates(search_result)
        if len(candidates) == 0:
            raise RuntimeError(f"no document found for name: {args.doc_name}")
        if len(candidates) == 1:
            resolved = {
                "input_kind": "doc_name",
                **candidates[0],
                "search_candidates": candidates,
                "needs_user_choice": False,
            }
        else:
            resolved = {
                "input_kind": "doc_name",
                "resolved_kind": "",
                "resolved_value": "",
                "title": "",
                "search_candidates": candidates,
                "needs_user_choice": True,
            }
    write_json(run_dir / "resolved-source.json", resolved)
    return resolved
```

- [ ] **Step 4: Run tests to verify source resolution passes**

Run:

```bash
python3 -m unittest discover tests/lark_workflow_doc_to_slides -v
```

Expected:

- zero-match, single-match, and multi-match cases PASS

- [ ] **Step 5: Commit**

```bash
git add lark-workflow-doc-to-slides/scripts/doc_to_slides.py tests/lark_workflow_doc_to_slides
git commit -m "feat: add deterministic source resolution for doc-to-slides"
```

### Task 3: Implement full-document fetch with pagination

**Files:**
- Modify: `lark-workflow-doc-to-slides/scripts/doc_to_slides.py`
- Modify: `tests/lark_workflow_doc_to_slides/test_doc_to_slides.py`
- Create: `tests/lark_workflow_doc_to_slides/fixtures/fetch-page-1.json`
- Create: `tests/lark_workflow_doc_to_slides/fixtures/fetch-page-2.json`

- [ ] **Step 1: Write failing fetch-pagination tests**

```python
class FetchTests(unittest.TestCase):
    @mock.patch("doc_to_slides.run_lark_cli")
    def test_fetch_aggregates_all_pages_until_has_more_is_false(self, run_lark_cli):
        module = load_module()
        run_lark_cli.side_effect = [
            json.loads(pathlib.Path("tests/lark_workflow_doc_to_slides/fixtures/fetch-page-1.json").read_text()),
            json.loads(pathlib.Path("tests/lark_workflow_doc_to_slides/fixtures/fetch-page-2.json").read_text()),
        ]
        resolved = {"resolved_kind": "doc_url", "resolved_value": "https://example/docx/abc"}
        result = module.fetch_source(resolved, pathlib.Path("/tmp/run"))
        self.assertIn("第一段", result["markdown"])
        self.assertIn("第二段", result["markdown"])
        self.assertEqual(run_lark_cli.call_count, 2)
```

- [ ] **Step 2: Run the tests to verify fetch pagination fails**

Run:

```bash
python3 -m unittest discover tests/lark_workflow_doc_to_slides -v
```

Expected:

- missing `fetch_source`
- or only-first-page assertions failing

- [ ] **Step 3: Implement paginated fetch**

```python
def fetch_source(resolved: dict, run_dir: Path) -> dict:
    offset = 0
    limit = 200
    pages = []
    markdown_parts = []
    title = resolved.get("title") or ""
    fetch_target = resolved["resolved_value"]

    if resolved.get("resolved_kind") == "wiki_url":
        wiki_token = fetch_target.rstrip("/").split("/")[-1]
        node_result = run_lark_cli([
            "lark-cli", "wiki", "spaces", "get_node", "--as", "user",
            "--params", json.dumps({"token": wiki_token}),
            "--format", "json",
        ])
        node = node_result["node"]
        if node.get("obj_type") != "docx":
            raise RuntimeError(f"wiki source resolves to unsupported obj_type: {node.get('obj_type')}")
        fetch_target = node["obj_token"]

    while True:
        fetch_args = [
            "lark-cli", "docs", "+fetch", "--as", "user",
            "--format", "json", "--doc", fetch_target,
            "--offset", str(offset), "--limit", str(limit),
        ]
        page = run_lark_cli(fetch_args)
        pages.append(page)
        if page.get("title") and not title:
            title = page["title"]
        markdown = page.get("markdown", "")
        if markdown:
            markdown_parts.append(markdown.rstrip())

        has_more = bool(page.get("has_more"))
        if not has_more:
            break
        offset += limit

    result = {
        "title": title,
        "markdown": "\n\n".join(part for part in markdown_parts if part),
        "pages": len(pages),
        "raw_pages": pages,
    }
    write_json(run_dir / "source.json", result)
    (run_dir / "source.md").write_text(result["markdown"] + ("\n" if result["markdown"] else ""))
    return result
```

- [ ] **Step 4: Run the tests to verify full-document fetch passes**

Run:

```bash
python3 -m unittest discover tests/lark_workflow_doc_to_slides -v
```

Expected:

- paginated fetch test PASS
- `source.json` and `source.md` contain both pages

- [ ] **Step 5: Commit**

```bash
git add lark-workflow-doc-to-slides/scripts/doc_to_slides.py tests/lark_workflow_doc_to_slides
git commit -m "feat: fetch full documents with pagination for doc-to-slides"
```

### Task 4: Implement outline validation against the approved contract

**Files:**
- Modify: `lark-workflow-doc-to-slides/scripts/doc_to_slides.py`
- Modify: `tests/lark_workflow_doc_to_slides/test_doc_to_slides.py`
- Create: `lark-workflow-doc-to-slides/templates/outline.json`

- [ ] **Step 1: Write failing validation tests for required fields and append-mode constraints**

```python
class OutlineValidationTests(unittest.TestCase):
    def test_valid_report_outline_passes(self):
        module = load_module()
        outline = json.loads(pathlib.Path(
            "tests/lark_workflow_doc_to_slides/fixtures/outline-valid-report.json"
        ).read_text())
        module.validate_outline(outline)

    def test_append_mode_rejects_cover_slide_without_explicit_section_intent(self):
        module = load_module()
        outline = {
            "presentation": {
                "title": "x",
                "source": {"input_kind": "doc_url", "resolved_kind": "doc_url", "resolved_value": "u"},
                "target_mode": "append",
                "content_mode": "report",
            },
            "slides": [
                {"no": 1, "role": "cover", "section_divider": False, "title": "封面", "layout": "title-only", "key_points": []}
            ],
        }
        with self.assertRaises(ValueError):
            module.validate_outline(outline)
```

- [ ] **Step 2: Run tests and verify validation is still too permissive**

Run:

```bash
python3 -m unittest discover tests/lark_workflow_doc_to_slides -v
```

Expected:

- append-mode / missing-field tests fail

- [ ] **Step 3: Implement schema and policy checks**

```python
def validate_outline(outline: dict) -> None:
    pres = outline.get("presentation") or {}
    source = pres.get("source") or {}
    slides = outline.get("slides")

    required_presentation = ["title", "target_mode", "content_mode"]
    for field in required_presentation:
        if not pres.get(field):
            raise ValueError(f"missing presentation.{field}")

    for field in ["input_kind", "resolved_kind", "resolved_value"]:
        if not source.get(field):
            raise ValueError(f"missing presentation.source.{field}")

    if not isinstance(slides, list) or not slides:
        raise ValueError("slides must be a non-empty list")

    for idx, slide in enumerate(slides, start=1):
        for field in ["no", "role", "title", "layout", "key_points"]:
            if field not in slide:
                raise ValueError(f"slide {idx} missing {field}")
        if slide["layout"] not in VALID_LAYOUTS:
            raise ValueError(f"slide {idx} invalid layout: {slide['layout']}")
        if not isinstance(slide["key_points"], list):
            raise ValueError(f"slide {idx} key_points must be a list")
        if len(slide["key_points"]) > 5:
            raise ValueError(f"slide {idx} exceeds 5 key points")

    if pres["target_mode"] == "append":
        first_role = slides[0].get("role")
        if first_role == "cover" and not bool(slides[0].get("section_divider")):
            raise ValueError("append mode cannot inject a generic cover slide")
```

- [ ] **Step 4: Write the template file and verify tests pass**

Template snippet:

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
      "key_points": ["要点 1", "要点 2"],
      "source_sections": ["原文章节标题"],
      "visual_hint": "可选：指标卡 / 对比 / 时间线",
      "notes": "可选补充"
    }
  ]
}
```

Run:

```bash
python3 -m unittest discover tests/lark_workflow_doc_to_slides -v
python3 - <<'PY'
import json, pathlib
json.loads(pathlib.Path("lark-workflow-doc-to-slides/templates/outline.json").read_text())
print("outline template ok")
PY
```

Expected:

- validation tests PASS
- template JSON parses successfully

- [ ] **Step 5: Commit**

```bash
git add lark-workflow-doc-to-slides/scripts/doc_to_slides.py lark-workflow-doc-to-slides/templates/outline.json tests/lark_workflow_doc_to_slides
git commit -m "feat: validate doc-to-slides outlines against the approved contract"
```

### Task 5: Implement deterministic slide XML rendering

**Files:**
- Modify: `lark-workflow-doc-to-slides/scripts/doc_to_slides.py`
- Modify: `tests/lark_workflow_doc_to_slides/test_doc_to_slides.py`

- [ ] **Step 1: Write failing snapshot-style rendering tests**

```python
class RenderTests(unittest.TestCase):
    def test_render_report_outline_produces_cover_and_content_xml(self):
        module = load_module()
        outline = json.loads(pathlib.Path(
            "tests/lark_workflow_doc_to_slides/fixtures/outline-valid-report.json"
        ).read_text())
        rendered = module.render_outline(outline, pathlib.Path("/tmp/run"))
        self.assertEqual(len(rendered["slides"]), 2)
        self.assertIn("<slide", rendered["slides"][0])
        self.assertIn("项目周报", rendered["slides"][0])
        self.assertIn("背景", rendered["slides"][1])
```

- [ ] **Step 2: Run tests and verify render support is missing**

Run:

```bash
python3 -m unittest discover tests/lark_workflow_doc_to_slides -v
```

Expected:

- missing `render_outline`
- no `slides.json`

- [ ] **Step 3: Implement XML render helpers**

```python
from xml.sax.saxutils import escape


def render_title_body_slide(title: str, points: list[str]) -> str:
    bullet_xml = "".join(f"<ul><li><p>{escape(point)}</p></li></ul>" for point in points)
    return (
        '<slide xmlns="http://www.larkoffice.com/sml/2.0">'
        '<style><fill><fillColor color="rgb(248,250,252)"/></fill></style>'
        '<data>'
        f'<shape type="text" topLeftX="80" topLeftY="72" width="800" height="80"><content textType="title"><p>{escape(title)}</p></content></shape>'
        f'<shape type="text" topLeftX="80" topLeftY="170" width="800" height="280"><content textType="body">{bullet_xml}</content></shape>'
        '</data>'
        '</slide>'
    )


def render_outline(outline: dict, run_dir: Path) -> dict:
    rendered = []
    for slide in outline["slides"]:
        role = slide["role"]
        layout = slide["layout"]
        if role == "cover":
            rendered.append(render_title_body_slide(slide["title"], slide.get("key_points", [])))
        elif layout == "title-only":
            rendered.append(render_title_only_slide(slide["title"]))
        elif layout in {"title-body", "bullets"}:
            rendered.append(render_title_body_slide(slide["title"], slide["key_points"]))
        elif layout == "two-column":
            rendered.append(render_two_column_slide(slide))
        elif layout == "comparison":
            rendered.append(render_comparison_slide(slide))
        elif layout == "timeline":
            rendered.append(render_timeline_slide(slide))
        elif layout == "metrics":
            rendered.append(render_metrics_slide(slide))
        else:
            raise ValueError(f"unsupported render layout: {layout}")

    result = {"slides": rendered, "count": len(rendered)}
    write_json(run_dir / "render-summary.json", {"count": len(rendered)})
    (run_dir / "slides.json").write_text(json.dumps(rendered, ensure_ascii=False, indent=2) + "\n")
    return result
```

- [ ] **Step 4: Run rendering tests and inspect fixture output**

Run:

```bash
python3 -m unittest discover tests/lark_workflow_doc_to_slides -v
python3 - <<'PY'
import json, pathlib
slides = json.loads(pathlib.Path("/tmp/run/slides.json").read_text())
print(len(slides))
print(slides[0][:120])
PY
```

Expected:

- render tests PASS
- slide XML strings are persisted and human-inspectable

- [ ] **Step 5: Commit**

```bash
git add lark-workflow-doc-to-slides/scripts/doc_to_slides.py tests/lark_workflow_doc_to_slides
git commit -m "feat: render deterministic slide xml from approved outlines"
```

### Task 6: Implement publish flow for new presentations

**Files:**
- Modify: `lark-workflow-doc-to-slides/scripts/doc_to_slides.py`
- Modify: `tests/lark_workflow_doc_to_slides/test_doc_to_slides.py`
- Create: `tests/lark_workflow_doc_to_slides/fixtures/presentation-create.json`
- Create: `tests/lark_workflow_doc_to_slides/fixtures/slide-create.json`

- [ ] **Step 1: Write failing publish tests for the incremental new-deck flow**

```python
class PublishNewDeckTests(unittest.TestCase):
    def test_publish_new_deck_uses_incremental_add_for_new_presentations(self):
        ...
```

- [ ] **Step 2: Run tests and verify publish flow is missing**

Run:

```bash
python3 -m unittest discover tests/lark_workflow_doc_to_slides -v
```

Expected:

- missing `publish_slides`

- [ ] **Step 3: Implement new-deck publish branching**

```python
def publish_new_deck(title: str, slides: list[str]) -> dict:
    create_result = run_lark_cli([
        "lark-cli", "slides", "+create", "--as", "user",
        "--title", title,
        "--format", "json",
    ])
    presentation_id = create_result["xml_presentation_id"]
    slide_ids = []
    for slide_xml in slides:
        payload = json.dumps({"slide": {"content": slide_xml}}, ensure_ascii=False)
        created = run_lark_cli([
            "lark-cli", "slides", "xml_presentation.slide", "create", "--as", "user",
            "--params", json.dumps({"xml_presentation_id": presentation_id}),
            "--data", payload,
            "--format", "json",
        ])
        slide_ids.append(created.get("slide_id"))
    return {
        "target_mode": "new",
        "xml_presentation_id": presentation_id,
        "slide_ids": slide_ids,
        "slides_added": len(slide_ids),
        "url": create_result.get("url"),
    }
```

- [ ] **Step 4: Run publish tests**

Run:

```bash
python3 -m unittest discover tests/lark_workflow_doc_to_slides -v
```

Expected:

- new-deck incremental publish tests PASS

- [ ] **Step 5: Commit**

```bash
git add lark-workflow-doc-to-slides/scripts/doc_to_slides.py tests/lark_workflow_doc_to_slides
git commit -m "feat: publish new slides decks from rendered outlines"
```

### Task 7: Implement append-mode target resolution and append-only publish

**Files:**
- Modify: `lark-workflow-doc-to-slides/scripts/doc_to_slides.py`
- Modify: `tests/lark_workflow_doc_to_slides/test_doc_to_slides.py`
- Create: `tests/lark_workflow_doc_to_slides/fixtures/wiki-node-slides.json`

- [ ] **Step 1: Write failing append-mode tests**

```python
class PublishAppendTests(unittest.TestCase):
    @mock.patch("doc_to_slides.run_lark_cli")
    def test_append_mode_resolves_wiki_target_before_creating_slides(self, run_lark_cli):
        module = load_module()
        run_lark_cli.side_effect = [
            json.loads(pathlib.Path("tests/lark_workflow_doc_to_slides/fixtures/wiki-node-slides.json").read_text()),
            json.loads(pathlib.Path("tests/lark_workflow_doc_to_slides/fixtures/slide-create.json").read_text()),
        ]
        outline = {"presentation": {"title": "项目周报", "target_mode": "append"}}
        result = module.publish_slides(outline, ["<slide>a</slide>"], pathlib.Path("/tmp/run"), "https://x/wiki/wikcn123")
        self.assertEqual(result["xml_presentation_id"], "slides_token_123")
```

- [ ] **Step 2: Run append tests and verify failure**

Run:

```bash
python3 -m unittest discover tests/lark_workflow_doc_to_slides -v
```

Expected:

- missing target-resolution helpers

- [ ] **Step 3: Implement append-only target resolution**

```python
def resolve_target_slides_url(target_slides_url: str) -> str:
    if "/slides/" in target_slides_url:
        return target_slides_url.rstrip("/").split("/")[-1]
    if "/wiki/" in target_slides_url:
        wiki_token = target_slides_url.rstrip("/").split("/")[-1]
        node = run_lark_cli([
            "lark-cli", "wiki", "spaces", "get_node", "--as", "user",
            "--params", json.dumps({"token": wiki_token}),
            "--format", "json",
        ])
        obj = node["node"]
        if obj.get("obj_type") != "slides":
            raise RuntimeError("target wiki node is not a slides presentation")
        return obj["obj_token"]
    raise RuntimeError("unsupported target_slides_url")


def publish_append(target_slides_url: str, slides: list[str]) -> dict:
    presentation_id = resolve_target_slides_url(target_slides_url)
    slide_ids = []
    for slide_xml in slides:
        created = run_lark_cli([
            "lark-cli", "slides", "xml_presentation.slide", "create", "--as", "user",
            "--params", json.dumps({"xml_presentation_id": presentation_id}),
            "--data", json.dumps({"slide": {"content": slide_xml}}, ensure_ascii=False),
            "--format", "json",
        ])
        slide_ids.append(created.get("slide_id"))
    return {
        "target_mode": "append",
        "xml_presentation_id": presentation_id,
        "slide_ids": slide_ids,
        "slides_added": len(slide_ids),
        "url": target_slides_url,
    }
```

- [ ] **Step 4: Run append-mode tests**

Run:

```bash
python3 -m unittest discover tests/lark_workflow_doc_to_slides -v
```

Expected:

- wiki-target and direct-slides-target append tests PASS

- [ ] **Step 5: Commit**

```bash
git add lark-workflow-doc-to-slides/scripts/doc_to_slides.py tests/lark_workflow_doc_to_slides
git commit -m "feat: support append-only publishing to existing slides decks"
```

### Task 8: Write the skill package and integrate it into the repo docs

**Files:**
- Create: `lark-workflow-doc-to-slides/SKILL.md`
- Create: `lark-workflow-doc-to-slides/references/workflow-new-slides.md`
- Create: `lark-workflow-doc-to-slides/references/workflow-append-slides.md`
- Create: `lark-workflow-doc-to-slides/references/content-modes.md`
- Create: `lark-workflow-doc-to-slides/references/slide-authoring-rules.md`
- Modify: `README.md`

- [ ] **Step 1: Write a failing smoke test that the template and script paths referenced by the skill exist and that the documented contract matches the implementation surface**

```python
class SkillPackageTests(unittest.TestCase):
    def test_skill_files_exist(self):
        for rel in [
            "lark-workflow-doc-to-slides/SKILL.md",
            "lark-workflow-doc-to-slides/references/workflow-new-slides.md",
            "lark-workflow-doc-to-slides/references/workflow-append-slides.md",
            "lark-workflow-doc-to-slides/references/content-modes.md",
            "lark-workflow-doc-to-slides/references/slide-authoring-rules.md",
            "lark-workflow-doc-to-slides/templates/outline.json",
            "lark-workflow-doc-to-slides/scripts/doc_to_slides.py",
        ]:
            self.assertTrue(pathlib.Path(rel).exists(), rel)

    def test_skill_declares_real_script_subcommands_and_outline_field(self):
        text = pathlib.Path("lark-workflow-doc-to-slides/SKILL.md").read_text()
        self.assertIn("resolve-source", text)
        self.assertIn("validate-outline", text)
        self.assertIn("render", text)
        self.assertIn("publish", text)
        self.assertIn("section_divider", text)
```

- [ ] **Step 2: Run tests and verify docs files are missing**

Run:

```bash
python3 -m unittest discover tests/lark_workflow_doc_to_slides -v
```

Expected:

- existence checks FAIL for missing skill-package files

- [ ] **Step 3: Write the skill docs**

`SKILL.md` outline:

```markdown
---
name: lark-workflow-doc-to-slides
version: 1.0.0
description: "文档转幻灯片工作流：读取飞书文档或 Wiki 内容，先生成可审阅的 slide outline，经用户确认后新建 Slides 或追加到已有 Slides。支持 URL、token、文档名称三种源输入，适用于把技术方案、周报、汇报文档整理成飞书演示文稿。"
metadata:
  requires:
    bins: ["lark-cli", "python3"]
---

# Lark Workflow Doc To Slides

**CRITICAL — 开始前 MUST 先读取 [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md)、[`../lark-doc/SKILL.md`](../lark-doc/SKILL.md)、[`../lark-slides/SKILL.md`](../lark-slides/SKILL.md)**。

## Workflow gate

- 必须先出 outline
- 用户未确认 outline 前，禁止创建或追加 Slides

## Routing

- 没有 `target_slides_url` → `references/workflow-new-slides.md`
- 有 `target_slides_url` → `references/workflow-append-slides.md`
- `content_mode` 未指定时，默认 `report`
```

README change:

- add `lark-workflow-doc-to-slides` to the repo skill list under repo-local workflows

- [ ] **Step 4: Run the tests and verify skill package wiring passes**

Run:

```bash
python3 -m unittest discover tests/lark_workflow_doc_to_slides -v
```

Expected:

- file-existence smoke tests PASS

- [ ] **Step 5: Commit**

```bash
git add lark-workflow-doc-to-slides README.md tests/lark_workflow_doc_to_slides
git commit -m "feat: add doc-to-slides skill package and operator docs"
```

### Task 9: Final verification pass

**Files:**
- Modify: `lark-workflow-doc-to-slides/scripts/doc_to_slides.py` as needed
- Modify: `tests/lark_workflow_doc_to_slides/test_doc_to_slides.py` as needed

- [ ] **Step 1: Run the full test suite for this feature**

Run:

```bash
python3 -m unittest discover tests/lark_workflow_doc_to_slides -v
```

Expected:

- all unit and dry-run tests PASS

- [ ] **Step 2: Run a manual dry-run for a single resolved source**

Run:

```bash
python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py resolve-source \
  --doc-url "https://example.feishu.cn/docx/example" \
  --run-dir /tmp/doc-to-slides-run
```

Expected:

- `resolved-source.json` written under `/tmp/doc-to-slides-run`

- [ ] **Step 3: Run a manual dry-run for outline validation**

Run:

```bash
python3 lark-workflow-doc-to-slides/scripts/doc_to_slides.py validate-outline \
  --outline lark-workflow-doc-to-slides/templates/outline.json
```

Expected:

- exit code `0`

- [ ] **Step 4: Review output files and clean any accidental contract drift**

Checklist:

- `resolve-source` persists `resolved-source.json`
- `fetch` writes full `source.md`
- `publish-result.json` includes `xml_presentation_id`, `url`, `slide_ids`, `slides_added`, `run_dir`
- `SKILL.md` trigger wording matches the approved source forms

- [ ] **Step 5: Commit**

```bash
git add lark-workflow-doc-to-slides README.md tests/lark_workflow_doc_to_slides
git commit -m "test: verify doc-to-slides workflow contract end to end"
```
