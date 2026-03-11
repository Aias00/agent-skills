import re
import html as html_lib


def _strip_frontmatter(text):
    """Remove YAML frontmatter when present at document head."""
    if not text:
        return text
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return normalized
    end = normalized.find("\n---\n", 4)
    if end == -1:
        return normalized
    return normalized[end + 5 :]


def _escape_and_format_inline(text):
    """Escape HTML and keep minimal Markdown inline formatting."""
    safe_text = html_lib.escape(text, quote=True)
    safe_text = re.sub(r"\[(.*?)\]\((https?://[^\s)]+)\)", r'<a href="\2">\1</a>', safe_text)
    safe_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", safe_text)
    safe_text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", safe_text)
    return safe_text


def _parse_image_markdown(line):
    match = re.fullmatch(r"!\[(.*?)\]\((.*?)\)", line.strip())
    if not match:
        return None
    alt, src = match.groups()
    return alt.strip(), src.strip()


def raw_text_to_html(text):
    """Convert plain text to safe HTML paragraphs."""
    text = _strip_frontmatter(text)
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
    text = _strip_frontmatter(text)
    lines = text.split("\n")
    html = []
    in_code_block = False
    in_list = False

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
            html.append("</ul>")
            in_list = False

        # Headers
        if line.startswith("#"):
            # Close list if open
            if in_list:
                html.append("</ul>")
                in_list = False

            level = len(line.split()[0])
            # Max h6
            if level > 6:
                level = 6
            content = _escape_and_format_inline(line[level:].strip())
            html.append(f"<h{level}>{content}</h{level}>")
            continue

        if stripped == "---":
            html.append("<hr>")
            continue

        if stripped.startswith("> "):
            content = _escape_and_format_inline(stripped[2:].strip())
            html.append(f"<blockquote><p>{content}</p></blockquote>")
            continue

        image = _parse_image_markdown(stripped)
        if image:
            alt, src = image
            if re.match(r"^https?://", src, re.IGNORECASE):
                safe_src = html_lib.escape(src, quote=True)
                safe_alt = html_lib.escape(alt or "image", quote=True)
                html.append(f'<p><img src="{safe_src}" alt="{safe_alt}"></p>')
            # Skip local image references. Tencent editor does not automatically upload
            # local markdown images during HTML insertion, and showing raw markdown looks worse.
            continue

        # Lists ( * or - or 1.)
        # Simplified: treat all as ul for now or simple lists
        is_list_item = stripped.startswith("* ") or stripped.startswith("- ")

        if is_list_item:
            if not in_list:
                html.append("<ul>")
                in_list = True
            content = _escape_and_format_inline(stripped[2:])
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
                html.append("</ul>")
                in_list = False
                line_content = _escape_and_format_inline(stripped)
                html.append(f"<p>{line_content}</p>")

    if in_list:
        html.append("</ul>")

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
