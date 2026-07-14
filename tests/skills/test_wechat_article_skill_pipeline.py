from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
FORMATTER = ROOT / "wechat-article-formatter" / "scripts" / "markdown_to_html.py"
FORMATTER_PYTHON = ROOT / "wechat-article-formatter" / ".venv" / "bin" / "python"
PUBLISHER_DIR = ROOT / "wechat-publisher"
PUBLISHER = PUBLISHER_DIR / "scripts" / "wechat-publish.ts"


ARTICLE = """---
title: Skill Pipeline Title
summary: Skill pipeline summary
author: 测试作者
coverImage: imgs/cover.png
---
# Skill Pipeline Title

**副标题：** 这是一段应该保留的副标题正文。

正文保留，元数据不应该进入公众号正文。
"""


def formatter_python() -> str:
    if FORMATTER_PYTHON.exists():
        return str(FORMATTER_PYTHON)
    fallback = shutil.which("python3")
    if not fallback:
        raise unittest.SkipTest("python3 is required for formatter tests")
    return fallback


class WechatArticleSkillPipelineTests(unittest.TestCase):
    def test_formatter_strips_frontmatter_h1_and_subtitle_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            markdown_path = tmp_path / "article.md"
            html_path = tmp_path / "article.html"
            markdown_path.write_text(ARTICLE, encoding="utf-8")

            result = subprocess.run(
                [
                    formatter_python(),
                    str(FORMATTER),
                    "--input",
                    str(markdown_path),
                    "--output",
                    str(html_path),
                    "--theme",
                    "ai-tech",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            html = html_path.read_text(encoding="utf-8")
            self.assertNotIn("coverImage", html)
            self.assertNotIn("summary:", html)
            self.assertNotIn("<h1", html.lower())
            self.assertNotIn("副标题：", html)
            self.assertIn("这是一段应该保留的副标题正文", html)
            self.assertIn("正文保留", html)

    def test_publish_dry_run_uses_preferred_formatter_and_markdown_title(self):
        if not shutil.which("bun"):
            raise unittest.SkipTest("bun is required for publisher dry-run tests")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            markdown_path = tmp_path / "article.md"
            markdown_path.write_text(ARTICLE, encoding="utf-8")

            result = subprocess.run(
                [
                    "bun",
                    str(PUBLISHER),
                    str(markdown_path),
                    "--method",
                    "api",
                    "--theme",
                    "ai-tech",
                    "--dry-run",
                ],
                cwd=PUBLISHER_DIR,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["method"], "api")
            self.assertTrue(payload["source"].endswith(".wechat-publisher.html"))
            self.assertIn("--title", payload["command"])
            self.assertIn("Skill Pipeline Title", payload["command"])

            generated_html = pathlib.Path(payload["source"]).read_text(encoding="utf-8")
            self.assertNotIn("coverImage", generated_html)
            self.assertIn("正文保留", generated_html)


if __name__ == "__main__":
    unittest.main()
