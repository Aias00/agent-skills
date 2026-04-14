from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "lark-workflow-doc-to-slides" / "scripts" / "doc_to_slides.py"
TEMPLATE_PATH = ROOT / "lark-workflow-doc-to-slides" / "templates" / "outline.json"
FIXTURES_DIR = ROOT / "tests" / "lark_workflow_doc_to_slides" / "fixtures"


def load_module():
    sys.modules.pop("doc_to_slides", None)
    spec = importlib.util.spec_from_file_location("doc_to_slides", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"unable to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["doc_to_slides"] = module
    spec.loader.exec_module(module)
    return module


def read_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


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
        with self.assertRaises(ValueError):
            module.validate_outline(read_fixture("outline-invalid-layout.json"))


class ResolveSourceTests(unittest.TestCase):
    def test_doc_url_passes_through(self):
        module = load_module()
        with mock.patch.object(module, "run_lark_cli") as run_lark_cli:
            with tempfile.TemporaryDirectory() as temp_dir:
                run_dir = pathlib.Path(temp_dir)
                args = module.parse_args(
                    ["resolve-source", "--doc-url", "https://x/docx/abc", "--run-dir", str(run_dir)]
                )
                resolved = module.resolve_source(args, run_dir)
                self.assertEqual(resolved["resolved_kind"], "doc_url")
                self.assertEqual(resolved["resolved_value"], "https://x/docx/abc")
                run_lark_cli.assert_not_called()
                self.assertTrue((run_dir / "resolved-source.json").exists())

    def test_doc_name_zero_match_fails(self):
        module = load_module()
        with mock.patch.object(module, "run_lark_cli", return_value=read_fixture("search-zero.json")):
            with tempfile.TemporaryDirectory() as temp_dir:
                args = module.parse_args(["resolve-source", "--doc-name", "不存在的文档", "--run-dir", temp_dir])
                with self.assertRaises(RuntimeError):
                    module.resolve_source(args, pathlib.Path(temp_dir))

    def test_doc_name_single_doc_match_continues(self):
        module = load_module()
        with mock.patch.object(module, "run_lark_cli", return_value=read_fixture("search-single.json")):
            with tempfile.TemporaryDirectory() as temp_dir:
                args = module.parse_args(["resolve-source", "--doc-name", "项目周报", "--run-dir", temp_dir])
                resolved = module.resolve_source(args, pathlib.Path(temp_dir))
                self.assertFalse(resolved["needs_user_choice"])
                self.assertEqual(resolved["resolved_kind"], "doc_url")
                self.assertEqual(resolved["entity_type"], "DOCX")

    def test_doc_name_single_wiki_match_continues_but_marks_wiki_url(self):
        module = load_module()
        with mock.patch.object(module, "run_lark_cli", return_value=read_fixture("search-wiki-single.json")):
            with tempfile.TemporaryDirectory() as temp_dir:
                args = module.parse_args(["resolve-source", "--doc-name", "知识库周报", "--run-dir", temp_dir])
                resolved = module.resolve_source(args, pathlib.Path(temp_dir))
                self.assertFalse(resolved["needs_user_choice"])
                self.assertEqual(resolved["resolved_kind"], "wiki_url")
                self.assertEqual(resolved["entity_type"], "WIKI")

    def test_doc_name_multiple_matches_stop_for_choice(self):
        module = load_module()
        with mock.patch.object(module, "run_lark_cli", return_value=read_fixture("search-multiple.json")):
            with tempfile.TemporaryDirectory() as temp_dir:
                args = module.parse_args(["resolve-source", "--doc-name", "项目周报", "--run-dir", temp_dir])
                resolved = module.resolve_source(args, pathlib.Path(temp_dir))
                self.assertTrue(resolved["needs_user_choice"])
                self.assertEqual(len(resolved["search_candidates"]), 2)
                self.assertEqual(resolved["search_candidates"][1]["resolved_kind"], "wiki_url")

    def test_doc_name_highlight_markup_is_stripped(self):
        module = load_module()
        search_result = {
            "data": {
                "results": [
                    {
                        "title_highlighted": "<h>测试</h>方案",
                        "result_meta": {"url": "https://example.feishu.cn/docx/doccn123"},
                        "entity_type": "DOCX",
                    }
                ]
            }
        }
        candidates = module.extract_search_candidates(search_result)
        self.assertEqual(candidates[0]["title"], "测试方案")


class FetchTests(unittest.TestCase):
    def test_fetch_aggregates_all_pages_until_has_more_is_false(self):
        module = load_module()
        with mock.patch.object(module, "run_lark_cli") as run_lark_cli:
            run_lark_cli.side_effect = [read_fixture("fetch-page-1.json"), read_fixture("fetch-page-2.json")]
            resolved = {"resolved_kind": "doc_url", "resolved_value": "https://example/docx/abc"}
            with tempfile.TemporaryDirectory() as temp_dir:
                run_dir = pathlib.Path(temp_dir)
                result = module.fetch_source(resolved, run_dir)
                self.assertIn("第一段", result["markdown"])
                self.assertIn("第二段", result["markdown"])
                self.assertEqual(run_lark_cli.call_count, 2)
                self.assertEqual(result["pages"], 2)
                self.assertTrue((run_dir / "source.json").exists())
                self.assertTrue((run_dir / "source.md").exists())

    def test_fetch_resolves_wiki_source_before_docs_fetch(self):
        module = load_module()
        wiki_node = read_fixture("wiki-node-docx.json")
        page = {"title": "知识库周报", "markdown": "Wiki 正文", "has_more": False}
        with mock.patch.object(module, "run_lark_cli") as run_lark_cli:
            run_lark_cli.side_effect = [wiki_node, page]
            resolved = {"resolved_kind": "wiki_url", "resolved_value": "https://example.feishu.cn/wiki/wikicn_doc"}
            with tempfile.TemporaryDirectory() as temp_dir:
                result = module.fetch_source(resolved, pathlib.Path(temp_dir))
                self.assertEqual(result["resolved_fetch_target"], "doccn_resolved_123")
                self.assertEqual(result["wiki_node"]["obj_type"], "docx")
                wiki_call = run_lark_cli.call_args_list[0].args[0]
                fetch_call = run_lark_cli.call_args_list[1].args[0]
                self.assertEqual(wiki_call[2:4], ["spaces", "get_node"])
                self.assertIn("doccn_resolved_123", fetch_call)

    def test_fetch_handles_lark_cli_enveloped_json_shape(self):
        module = load_module()
        enveloped_page_1 = {
            "ok": True,
            "identity": "user",
            "data": {
                "title": "E2E 文档转幻灯片测试 20260414",
                "markdown": "# 第一段",
                "has_more": True,
                "next_offset": 200,
            },
        }
        enveloped_page_2 = {
            "ok": True,
            "identity": "user",
            "data": {
                "markdown": "## 第二段",
                "has_more": False,
            },
        }
        with mock.patch.object(module, "run_lark_cli") as run_lark_cli:
            run_lark_cli.side_effect = [enveloped_page_1, enveloped_page_2]
            resolved = {"resolved_kind": "doc_url", "resolved_value": "https://example/docx/abc"}
            with tempfile.TemporaryDirectory() as temp_dir:
                run_dir = pathlib.Path(temp_dir)
                result = module.fetch_source(resolved, run_dir)
                self.assertEqual(result["title"], "E2E 文档转幻灯片测试 20260414")
                self.assertIn("# 第一段", result["markdown"])
                self.assertIn("## 第二段", result["markdown"])
                self.assertEqual(result["pages"], 2)

    def test_fetch_fails_fast_for_unresolved_source_choice_state(self):
        module = load_module()
        unresolved = {
            "input_kind": "doc_name",
            "resolved_kind": "",
            "resolved_value": "",
            "title": "",
            "search_candidates": [
                {"title": "项目周报", "resolved_kind": "doc_url", "resolved_value": "https://example/docx/doccn123"}
            ],
            "needs_user_choice": True,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(RuntimeError):
                module.fetch_source(unresolved, pathlib.Path(temp_dir))


class OutlineValidationTests(unittest.TestCase):
    def test_valid_report_outline_passes(self):
        module = load_module()
        module.validate_outline(read_fixture("outline-valid-report.json"))

    def test_append_mode_rejects_cover_slide_without_section_divider(self):
        module = load_module()
        outline = {
            "presentation": {
                "title": "项目周报",
                "source": {
                    "input_kind": "doc_url",
                    "resolved_kind": "doc_url",
                    "resolved_value": "https://example/docx/abc",
                },
                "target_mode": "append",
                "content_mode": "report",
            },
            "slides": [
                {
                    "no": 1,
                    "role": "cover",
                    "section_divider": False,
                    "title": "封面",
                    "layout": "title-only",
                    "key_points": [],
                }
            ],
        }
        with self.assertRaises(ValueError):
            module.validate_outline(outline)

    def test_missing_section_divider_is_rejected(self):
        module = load_module()
        outline = read_fixture("outline-valid-report.json")
        outline["slides"][0].pop("section_divider")
        with self.assertRaises(ValueError):
            module.validate_outline(outline)


class TemplateTests(unittest.TestCase):
    def test_outline_template_parses_and_validates(self):
        module = load_module()
        outline = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
        module.validate_outline(outline)


class ValidateOutlineCliTests(unittest.TestCase):
    def test_validate_outline_cli_emits_structured_error_payload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outline_path = pathlib.Path(temp_dir) / "invalid-outline.json"
            outline = read_fixture("outline-valid-report.json")
            outline["slides"][0].pop("section_divider")
            outline_path.write_text(json.dumps(outline, ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), "validate-outline", "--outline", str(outline_path)],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(proc.returncode, 0)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["ok"], False)
            self.assertEqual(payload["command"], "validate-outline")
            self.assertIn("section_divider", payload["error"])


class RenderTests(unittest.TestCase):
    def test_render_report_outline_produces_cover_and_content_xml(self):
        module = load_module()
        outline = read_fixture("outline-valid-report.json")
        with tempfile.TemporaryDirectory() as temp_dir:
            rendered = module.render_outline(outline, pathlib.Path(temp_dir))
            self.assertEqual(len(rendered["slides"]), 2)
            self.assertIn("<slide", rendered["slides"][0])
            self.assertIn("项目周报", rendered["slides"][0])
            self.assertIn("背景", rendered["slides"][1])
            self.assertTrue((pathlib.Path(temp_dir) / "slides.json").exists())
            for slide_xml in rendered["slides"]:
                ET.fromstring(slide_xml)

    def test_render_supports_every_allowed_layout(self):
        module = load_module()
        outline = {
            "presentation": {
                "title": "布局覆盖",
                "source": {
                    "input_kind": "doc_url",
                    "resolved_kind": "doc_url",
                    "resolved_value": "https://example/docx/layouts",
                },
                "target_mode": "new",
                "content_mode": "report",
            },
            "slides": [
                {"no": 1, "role": "cover", "section_divider": False, "title": "封面", "layout": "title-only", "key_points": []},
                {"no": 2, "role": "content", "section_divider": False, "title": "正文", "layout": "title-body", "key_points": ["A", "B"]},
                {"no": 3, "role": "content", "section_divider": False, "title": "双栏", "layout": "two-column", "key_points": ["A", "B", "C", "D"]},
                {"no": 4, "role": "content", "section_divider": False, "title": "列表", "layout": "bullets", "key_points": ["A", "B", "C"]},
                {"no": 5, "role": "content", "section_divider": False, "title": "对比", "layout": "comparison", "key_points": ["优点", "缺点"], "source_sections": ["当前", "目标"]},
                {"no": 6, "role": "content", "section_divider": False, "title": "时间线", "layout": "timeline", "key_points": ["第 1 周", "第 2 周", "第 3 周"]},
                {"no": 7, "role": "content", "section_divider": False, "title": "指标", "layout": "metrics", "key_points": ["10%", "99.9%", "3 项"]},
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            rendered = module.render_outline(outline, pathlib.Path(temp_dir))
            self.assertEqual(rendered["count"], 7)
            self.assertTrue(all("<slide" in slide for slide in rendered["slides"]))
            for slide_xml in rendered["slides"]:
                ET.fromstring(slide_xml)
            self.assertIn("第 1 周", rendered["slides"][5])
            self.assertIn('type="text"', rendered["slides"][5])
            self.assertIn("10%", rendered["slides"][6])
            self.assertIn('type="text"', rendered["slides"][6])


class PublishNewDeckTests(unittest.TestCase):
    def test_publish_new_deck_uses_incremental_add_when_slide_count_is_small(self):
        module = load_module()
        outline = {
            "presentation": {
                "title": "项目周报",
                "target_mode": "new",
                "content_mode": "report",
                "source": {"input_kind": "doc_url", "resolved_kind": "doc_url", "resolved_value": "u"},
            },
            "slides": [
                {"no": 1, "role": "cover", "section_divider": False, "title": "项目周报", "layout": "title-only", "key_points": []},
                {"no": 2, "role": "content", "section_divider": False, "title": "更新", "layout": "bullets", "key_points": ["A"]},
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = pathlib.Path(temp_dir)
            slides = module.render_outline(outline, run_dir)["slides"]
            calls: list[list[str]] = []

            def fake_run(args: list[str]) -> dict:
                calls.append(args)
                if len(calls) == 1:
                    payload = read_fixture("presentation-create.json")
                    payload["data"].pop("slide_ids", None)
                    payload["data"].pop("slides_added", None)
                    return payload
                return {"slide_id": f"slide_{len(calls) - 1}", "revision_id": 100 + len(calls)}

            with mock.patch.object(module, "run_lark_cli", side_effect=fake_run):
                result = module.publish_slides(outline, slides, run_dir, None)
            self.assertEqual(result["xml_presentation_id"], "pres_abc123")
            self.assertEqual(result["target_mode"], "new")
            self.assertEqual(result["slides_added"], 2)
            self.assertEqual(calls[0][2], "+create")
            self.assertNotIn("--format", calls[0])
            self.assertEqual(calls[1][2:4], ["xml_presentation.slide", "create"])
            self.assertTrue((run_dir / "publish-result.json").exists())

    def test_publish_new_deck_uses_incremental_add_when_slide_count_is_large(self):
        module = load_module()
        outline = {"presentation": {"title": "项目周报", "target_mode": "new", "content_mode": "report", "source": {"input_kind": "doc_url", "resolved_kind": "doc_url", "resolved_value": "u"}}, "slides": [{"no": 1, "role": "cover", "section_divider": False, "title": "项目周报", "layout": "title-only", "key_points": []}]}
        slides = [f"<slide>{i}</slide>" for i in range(11)]

        calls: list[list[str]] = []

        def fake_run(args: list[str]) -> dict:
            calls.append(args)
            if len(calls) == 1:
                payload = read_fixture("presentation-create.json")
                payload["data"].pop("slide_ids", None)
                payload["data"].pop("slides_added", None)
                return payload
            return {"slide_id": f"slide_{len(calls) - 1}", "revision_id": 100 + len(calls)}

        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = pathlib.Path(temp_dir)
            module.write_json(
                run_dir / "render-summary.json",
                {
                    "count": len(slides),
                    "layouts": ["title-only"],
                    "outline_fingerprint": module.fingerprint_payload(outline),
                    "slides_fingerprint": module.fingerprint_payload(slides),
                },
            )
            with mock.patch.object(module, "run_lark_cli", side_effect=fake_run):
                result = module.publish_slides(outline, slides, run_dir, None)
            self.assertEqual(result["xml_presentation_id"], "pres_abc123")
            self.assertEqual(len(result["slide_ids"]), 11)
            self.assertEqual(calls[0][2], "+create")
            self.assertNotIn("--format", calls[0])
            self.assertEqual(calls[1][2:4], ["xml_presentation.slide", "create"])

    def test_publish_rejects_outline_and_render_mismatch(self):
        module = load_module()
        outline = {
            "presentation": {
                "title": "项目周报",
                "target_mode": "new",
                "content_mode": "report",
                "source": {"input_kind": "doc_url", "resolved_kind": "doc_url", "resolved_value": "u"},
            },
            "slides": [
                {"no": 1, "role": "cover", "section_divider": False, "title": "项目周报", "layout": "title-only", "key_points": []},
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = pathlib.Path(temp_dir)
            slides = module.render_outline(outline, run_dir)["slides"]
            outline["presentation"]["title"] = "已修改标题"
            with self.assertRaises(RuntimeError):
                module.publish_slides(outline, slides, run_dir, None)

    def test_publish_new_deck_persists_partial_success_when_slide_add_fails(self):
        module = load_module()
        outline = {
            "presentation": {
                "title": "项目周报",
                "target_mode": "new",
                "content_mode": "report",
                "source": {"input_kind": "doc_url", "resolved_kind": "doc_url", "resolved_value": "u"},
            },
            "slides": [
                {"no": 1, "role": "cover", "section_divider": False, "title": "项目周报", "layout": "title-only", "key_points": []},
                {"no": 2, "role": "content", "section_divider": False, "title": "更新", "layout": "bullets", "key_points": ["A"]},
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = pathlib.Path(temp_dir)
            slides = module.render_outline(outline, run_dir)["slides"]
            calls = 0

            def fake_run(args: list[str]) -> dict:
                nonlocal calls
                calls += 1
                if calls == 1:
                    payload = read_fixture("presentation-create.json")
                    payload["data"].pop("slide_ids", None)
                    payload["data"].pop("slides_added", None)
                    return payload
                if calls == 2:
                    return {"slide_id": "slide_1", "revision_id": 101}
                raise RuntimeError("slide 2 failed")

            with mock.patch.object(module, "run_lark_cli", side_effect=fake_run):
                with self.assertRaises(module.PublishError):
                    module.publish_slides(outline, slides, run_dir, None)

            partial = json.loads((run_dir / "publish-result.json").read_text(encoding="utf-8"))
            self.assertEqual(partial["xml_presentation_id"], "pres_abc123")
            self.assertEqual(partial["slide_ids"], ["slide_1"])
            self.assertEqual(partial["slides_added"], 1)


class PublishAppendTests(unittest.TestCase):
    def test_append_mode_resolves_wiki_target_before_creating_slides(self):
        module = load_module()
        outline = {"presentation": {"title": "项目周报", "target_mode": "append", "content_mode": "report", "source": {"input_kind": "doc_url", "resolved_kind": "doc_url", "resolved_value": "u"}}, "slides": [{"no": 1, "role": "content", "section_divider": False, "title": "更新", "layout": "bullets", "key_points": ["A"]}]}

        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = pathlib.Path(temp_dir)
            slides = module.render_outline(outline, run_dir)["slides"]
            with mock.patch.object(module, "run_lark_cli") as run_lark_cli:
                run_lark_cli.side_effect = [read_fixture("wiki-node-slides.json"), read_fixture("slide-create.json")]
                result = module.publish_slides(
                    outline,
                    slides,
                    run_dir,
                    "https://x/wiki/wikcn123",
                )
            self.assertEqual(result["xml_presentation_id"], "slides_token_123")
            self.assertEqual(result["slide_ids"], ["slide_example_id"])

    def test_append_mode_accepts_direct_slides_url(self):
        module = load_module()
        outline = {"presentation": {"title": "项目周报", "target_mode": "append", "content_mode": "report", "source": {"input_kind": "doc_url", "resolved_kind": "doc_url", "resolved_value": "u"}}, "slides": [{"no": 1, "role": "content", "section_divider": False, "title": "更新", "layout": "bullets", "key_points": ["A"]}]}

        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = pathlib.Path(temp_dir)
            slides = module.render_outline(outline, run_dir)["slides"]
            with mock.patch.object(module, "run_lark_cli", return_value=read_fixture("slide-create.json")):
                result = module.publish_slides(
                    outline,
                    slides,
                    run_dir,
                    "https://x/slides/slides_direct_456",
                )
            self.assertEqual(result["xml_presentation_id"], "slides_direct_456")
            self.assertEqual(result["target_mode"], "append")


if __name__ == "__main__":
    unittest.main()
