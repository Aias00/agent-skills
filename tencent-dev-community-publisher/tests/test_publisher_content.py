import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import publisher


class FakePage:
    def __init__(self, body_text):
        self.body_text = body_text

    def evaluate(self, _script):
        return self.body_text


class PublisherContentTests(unittest.TestCase):
    def test_required_tag_selects_exact_existing_option(self):
        page = Mock()
        selected = [False]
        page.evaluate.side_effect = lambda *_args: (
            ["腾讯云架构师技术同盟"] if selected[0] else []
        )
        tag_input = Mock()
        tag_input.count.return_value = 1
        tag_input.first = tag_input
        option = Mock()
        option.count.return_value = 1
        option.nth.return_value = option
        option.inner_text.return_value = "腾讯云架构师技术同盟"
        option.get_attribute.return_value = "18103"
        option.click.side_effect = lambda **_kwargs: selected.__setitem__(0, True)
        page.locator.side_effect = [tag_input, option]

        self.assertTrue(publisher.ensure_required_article_tag(page))
        tag_input.fill.assert_called_once_with("腾讯云架构师技术同盟")
        option.click.assert_called_once_with(force=True)

    def test_required_tag_does_not_accept_similarly_named_option(self):
        page = Mock()
        page.evaluate.return_value = []
        tag_input = Mock()
        tag_input.count.return_value = 1
        tag_input.first = tag_input
        option = Mock()
        option.count.return_value = 1
        option.nth.return_value = option
        option.inner_text.return_value = "腾讯云架构师技术同盟活动"
        page.locator.side_effect = [tag_input, option]

        with patch.object(publisher.time, "time", side_effect=[0, 6]):
            self.assertFalse(publisher.ensure_required_article_tag(page))
        option.click.assert_not_called()

    def test_required_tag_rejects_missing_platform_option(self):
        page = Mock()
        page.evaluate.return_value = []
        tag_input = Mock()
        tag_input.count.return_value = 1
        tag_input.first = tag_input
        options = Mock()
        options.count.return_value = 0
        page.locator.side_effect = [tag_input, options]

        with patch.object(publisher.time, "time", side_effect=[0, 6]):
            self.assertFalse(publisher.ensure_required_article_tag(page))

    def test_required_tag_already_selected_needs_no_input(self):
        page = Mock()
        page.evaluate.return_value = ["腾讯云架构师技术同盟"]

        self.assertTrue(publisher.ensure_required_article_tag(page))
        page.locator.assert_not_called()

    def test_word_count_prefers_body_limit_over_title_limit(self):
        page = FakePage("标题字数：29 / 80\n字数: 1638 / 50000")

        self.assertEqual(publisher._word_count_from_page(page), 1638)

    def test_matching_leading_h1_is_removed_from_body(self):
        markdown = "# Article title\n\nIntroduction\n\n## Section\n"

        self.assertEqual(
            publisher._strip_leading_markdown_title(markdown, "Article title"),
            "Introduction\n\n## Section\n",
        )

    def test_different_leading_h1_is_preserved(self):
        markdown = "# Context heading\n\nIntroduction\n"

        self.assertEqual(
            publisher._strip_leading_markdown_title(markdown, "Article title"),
            markdown,
        )

    def test_tencent_markdown_uses_supported_plain_text_fence(self):
        markdown = "```text\nplain\n```\n\n```python\nprint('ok')\n```\n"

        self.assertEqual(
            publisher._normalize_markdown_for_tencent(markdown),
            "```txt\nplain\n```\n\n```python\nprint('ok')\n```\n",
        )


if __name__ == "__main__":
    unittest.main()
