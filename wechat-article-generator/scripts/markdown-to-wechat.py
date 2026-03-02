#!/usr/bin/env python3
"""
Convert Markdown to WeChat-friendly HTML (<p> + inline style).
"""

import argparse
import html
import json
import re
import sys
from pathlib import Path

FRONTMATTER_DELIM = "---"
INLINE_TOKEN_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)|`([^`]+)`|\*\*([^*]+)\*\*")
ORDERED_LIST_RE = re.compile(r"^(\d+)\.\s+(.+)$")
HORIZONTAL_RULE_RE = re.compile(r"^[-*_]{3,}$")


def parse_frontmatter(content: str):
    if not content.startswith(FRONTMATTER_DELIM + "\n") and content != FRONTMATTER_DELIM:
        return {}, content

    lines = content.splitlines()
    frontmatter = {}
    end_idx = None

    for i in range(1, len(lines)):
        line = lines[i]
        if line.strip() == FRONTMATTER_DELIM:
            end_idx = i
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            frontmatter[key] = value

    if end_idx is None:
        # Invalid frontmatter, fallback to original content.
        return {}, content

    body = "\n".join(lines[end_idx + 1 :])
    return frontmatter, body


def sanitize_url(url: str) -> str:
    value = (url or "").strip()
    if re.match(r"^(https?://|mailto:)", value, flags=re.IGNORECASE):
        return html.escape(value, quote=True)
    return "#"


def escape_text(text: str) -> str:
    return html.escape(text or "", quote=True)


def format_inline(text: str) -> str:
    text = text or ""
    parts = []
    last = 0

    for match in INLINE_TOKEN_RE.finditer(text):
        if match.start() > last:
            parts.append(escape_text(text[last : match.start()]))

        link_label, link_url, inline_code, strong_text = match.groups()
        if link_label is not None:
            label = escape_text(link_label)
            url = sanitize_url(link_url)
            parts.append(
                f'<a href="{url}" style="color: #576b95; text-decoration: none;">{label}</a>'
            )
        elif inline_code is not None:
            code_text = escape_text(inline_code)
            parts.append(
                '<code style="font-family: Consolas, Monaco, monospace; font-size: 14px; '
                'background: #f6f8fa; padding: 2px 6px; border-radius: 3px; color: #d63384;">'
                f"{code_text}</code>"
            )
        elif strong_text is not None:
            strong = escape_text(strong_text)
            parts.append(f'<strong style="font-weight: bold; color: #000;">{strong}</strong>')

        last = match.end()

    if last < len(text):
        parts.append(escape_text(text[last:]))

    return "".join(parts)


def convert_markdown_to_wechat_html(body: str) -> str:
    html_lines = []
    lines = body.splitlines()
    i = 0

    while i < len(lines):
        raw = lines[i]
        line = raw.strip()

        if not line:
            i += 1
            continue

        if line.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i].rstrip("\n"))
                i += 1

            for code_line in code_lines:
                escaped = escape_text(code_line)
                html_lines.append(
                    '<p style="font-family: Consolas, Monaco, monospace; font-size: 14px; '
                    'line-height: 1.6; margin: 2px 0; padding: 4px 12px; background-color: #f6f8fa; '
                    f'border-left: 3px solid #d1d5da; color: #24292e; white-space: pre;">{escaped}</p>'
                )
            html_lines.append('<p style="margin: 10px 0;">&nbsp;</p>')

            if i < len(lines) and lines[i].strip().startswith("```"):
                i += 1
            continue

        if line.startswith("# "):
            text = format_inline(line[2:])
            html_lines.append(
                f'<p style="font-size: 20px; font-weight: bold; color: #000; margin: 20px 0 10px; line-height: 1.4;">{text}</p>'
            )
            i += 1
            continue

        if line.startswith("## "):
            text = format_inline(line[3:])
            html_lines.append(
                f'<p style="font-size: 16px; font-weight: bold; color: #000; margin: 18px 0 8px; padding-left: 10px; border-left: 4px solid #07c160;">{text}</p>'
            )
            i += 1
            continue

        if line.startswith("### "):
            text = format_inline(line[4:])
            html_lines.append(
                f'<p style="font-size: 15px; font-weight: bold; color: #333; margin: 15px 0 6px;">{text}</p>'
            )
            i += 1
            continue

        if line.startswith("#### "):
            text = format_inline(line[5:])
            html_lines.append(
                f'<p style="font-size: 14px; font-weight: bold; color: #555; margin: 12px 0 5px;">{text}</p>'
            )
            i += 1
            continue

        if HORIZONTAL_RULE_RE.match(line):
            html_lines.append('<p style="border-top: 1px solid #e1e4e8; margin: 20px 0;">&nbsp;</p>')
            i += 1
            continue

        ordered_match = ORDERED_LIST_RE.match(line)
        if ordered_match:
            items = []
            while i < len(lines):
                current = lines[i].strip()
                match = ORDERED_LIST_RE.match(current)
                if not match:
                    break
                items.append(match.group(2))
                i += 1

            for idx, item in enumerate(items, start=1):
                text = format_inline(item)
                html_lines.append(
                    f'<p style="font-size: 16px; line-height: 1.8; margin: 6px 0; padding-left: 25px; color: #333;"><span style="font-weight: bold;">{idx}.</span> {text}</p>'
                )
            continue

        if line.startswith("- ") or line.startswith("* "):
            items = []
            while i < len(lines):
                current = lines[i].strip()
                if not (current.startswith("- ") or current.startswith("* ")):
                    break
                items.append(current[2:])
                i += 1

            for item in items:
                text = format_inline(item)
                html_lines.append(
                    f'<p style="font-size: 16px; line-height: 1.8; margin: 6px 0; padding-left: 25px; color: #333;">• {text}</p>'
                )
            continue

        if line.startswith("|") and line.endswith("|"):
            table_lines = []
            while i < len(lines):
                current = lines[i].strip()
                if not (current.startswith("|") and current.endswith("|")):
                    break
                table_lines.append(current)
                i += 1

            if len(table_lines) > 1:
                for row_idx, row in enumerate(table_lines):
                    cells = [c.strip() for c in row.split("|")[1:-1]]
                    if cells and all(re.match(r"^[:\-\s]*$", cell) for cell in cells):
                        continue
                    cell_text = "  |  ".join(format_inline(c) for c in cells)
                    if row_idx == 0:
                        html_lines.append(
                            f'<p style="font-size: 14px; font-weight: bold; background: #f6f8fa; padding: 8px 12px; margin: 4px 0;">{cell_text}</p>'
                        )
                    else:
                        html_lines.append(
                            f'<p style="font-size: 14px; padding: 8px 12px; margin: 4px 0; border-bottom: 1px solid #e1e4e8;">{cell_text}</p>'
                        )
                html_lines.append('<p style="margin: 10px 0;">&nbsp;</p>')
            continue

        paragraph = format_inline(line)
        html_lines.append(
            f'<p style="font-size: 16px; line-height: 1.8; margin: 0 0 10px; color: #333;">{paragraph}</p>'
        )
        i += 1

    return "\n".join(html_lines)


def derive_summary(body: str, fallback_title: str) -> str:
    blocks = [block.strip() for block in body.split("\n\n") if block.strip()]
    for block in blocks:
        if block.startswith("#"):
            continue
        text = re.sub(r"<[^>]+>", "", block).strip()
        text = re.sub(r"[`*#-]", "", text).strip()
        text = re.sub(r"\s+", " ", text)
        if text:
            return text[:120]
    return (fallback_title or "")[:120]


def build_output_html(title: str, content_html: str) -> str:
    safe_title = escape_text(title or "无标题")
    return (
        "<!DOCTYPE html>\n"
        "<html>\n"
        "<head>\n"
        '    <meta charset="UTF-8">\n'
        f"    <title>{safe_title}</title>\n"
        "</head>\n"
        "<body>\n"
        f"{content_html}\n"
        "</body>\n"
        "</html>"
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Convert Markdown to WeChat-friendly HTML")
    parser.add_argument("markdown_file", help="Input markdown file path")
    parser.add_argument("--out", help="Output HTML path (default: <input>-wechat.html)")
    parser.add_argument("--title", help="Override title")
    parser.add_argument("--author", help="Override author")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    md_path = Path(args.markdown_file).expanduser().resolve()
    if not md_path.exists():
        print(f"[ERROR] markdown file not found: {md_path}", file=sys.stderr)
        return 1

    content = md_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)

    rendered_html = convert_markdown_to_wechat_html(body)
    title = args.title or frontmatter.get("title") or md_path.stem
    author = args.author or frontmatter.get("author") or "AI 助手"

    out_path = Path(args.out).expanduser().resolve() if args.out else md_path.with_name(f"{md_path.stem}-wechat.html")
    out_path.write_text(build_output_html(title, rendered_html), encoding="utf-8")

    metadata = {
        "htmlPath": str(out_path),
        "title": title,
        "author": author,
        "summary": derive_summary(body, title),
        "contentImages": [],
    }

    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    print(f"\n[OK] generated: {out_path}")
    print("[INFO] WeChat mode: <p> + inline style")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
