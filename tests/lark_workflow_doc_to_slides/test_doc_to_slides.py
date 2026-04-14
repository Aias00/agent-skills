from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "lark-workflow-doc-to-slides" / "scripts" / "doc_to_slides.py"
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
        outline = json.loads((FIXTURES_DIR / "outline-invalid-layout.json").read_text(encoding="utf-8"))
        with self.assertRaises(ValueError):
            module.validate_outline(outline)


if __name__ == "__main__":
    unittest.main()
