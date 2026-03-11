import re
import html as html_lib


def _escape_and_format_inline(text):
    """Escape HTML and keep minimal Markdown inline formatting."""
    placeholders = {}

    def stash(fragment):
        key = f"__MD_PLACEHOLDER_{len(placeholders)}__"
        placeholders[key] = fragment
        return key

    text = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: stash(
            f'<img alt="{html_lib.escape(m.group(1), quote=True)}" src="{html_lib.escape(m.group(2), quote=True)}" />'
        ),
        text,
    )
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: stash(
            f'<a href="{html_lib.escape(m.group(2), quote=True)}">{html_lib.escape(m.group(1), quote=True)}</a>'
        ),
        text,
    )

    safe_text = html_lib.escape(text, quote=True)
    safe_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", safe_text)
    safe_text = re.sub(r"`([^`]+)`", r"<code>\1</code>", safe_text)
    safe_text = re.sub(r"(?<!\*)\*(?!\*)(.*?)\*(?<!\*)", r"<i>\1</i>", safe_text)

    for key, fragment in placeholders.items():
        safe_text = safe_text.replace(key, fragment)
    return safe_text


def raw_text_to_html(text):
    """Convert plain text to safe HTML paragraphs."""
    blocks = []
    for paragraph in text.split("\n\n"):
        p = paragraph.strip("\n")
        if not p.strip():
            continue
        blocks.append(f"<p>{html_lib.escape(p, quote=True).replace('\n', '<br>')}</p>")
    return "\n".join(blocks)


def convert(text):
    """
    Simple Markdown to HTML converter for Toutiao.
    Handles headers, code blocks, lists, and basic formatting.
    """
    lines = text.split("\n")
    html = []
    in_code_block = False
    in_list = False
    list_tag = "ul"

    for line in lines:
        stripped = line.strip()

        # Code blocks
        if stripped.startswith("```"):
            if in_code_block:
                html.append("</code></pre>")
                in_code_block = False
            else:
                html.append("<pre><code>")
                in_code_block = True
            continue

        if in_code_block:
            # Escape code content
            safe_line = html_lib.escape(line)
            html.append(
                f"{safe_line}<br>"
            )  # Use br for newlines in code for some editors
            continue

        # List handling logic (exit list if empty line or header)
        if in_list and (not stripped or stripped.startswith("#")):
            html.append(f"</{list_tag}>")
            in_list = False
            list_tag = "ul"

        # Headers
        if line.startswith("#"):
            # Close list if open
            if in_list:
                html.append(f"</{list_tag}>")
                in_list = False
                list_tag = "ul"

            level = len(line.split()[0])
            # Max h6
            if level > 6:
                level = 6
            content = _escape_and_format_inline(line[level:].strip())
            html.append(f"<h{level}>{content}</h{level}>")
            continue

        if re.fullmatch(r"[-*_]{3,}", stripped):
            if in_list:
                html.append(f"</{list_tag}>")
                in_list = False
                list_tag = "ul"
            html.append("<hr />")
            continue

        if stripped.startswith("> "):
            if in_list:
                html.append(f"</{list_tag}>")
                in_list = False
                list_tag = "ul"
            content = _escape_and_format_inline(stripped[2:].strip())
            html.append(f"<blockquote><p>{content}</p></blockquote>")
            continue

        # Lists ( * or - or 1.)
        # Simplified: treat all as ul for now or simple lists
        ordered_match = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        is_list_item = stripped.startswith("* ") or stripped.startswith("- ") or bool(ordered_match)

        if is_list_item:
            current_tag = "ol" if ordered_match else "ul"
            if not in_list:
                html.append(f"<{current_tag}>")
                in_list = True
                list_tag = current_tag
            elif list_tag != current_tag:
                html.append(f"</{list_tag}>")
                html.append(f"<{current_tag}>")
                list_tag = current_tag
            content = _escape_and_format_inline(ordered_match.group(2) if ordered_match else stripped[2:])
            html.append(f"<li>{content}</li>")
            continue

        # Paragraphs
        if stripped:
            # If we're not in a list or code block, it's a paragraph
            if not in_list:
                line_content = _escape_and_format_inline(stripped)
                html.append(f"<p>{line_content}</p>")
            else:
                # Continuation of list? Or close it?
                # For simplicity, if we hit non-list text line, close list
                html.append(f"</{list_tag}>")
                in_list = False
                list_tag = "ul"
                line_content = _escape_and_format_inline(stripped)
                html.append(f"<p>{line_content}</p>")

    if in_list:
        html.append(f"</{list_tag}>")

    return "\n".join(html)


if __name__ == "__main__":
    # Test
    sample = """# Title
    
    Introduction **bold**.
    
    * Item 1
    * Item 2
    
    ```python
    print("Code")
    ```
    """
    print(convert(sample))
