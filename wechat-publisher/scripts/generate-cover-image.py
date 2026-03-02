#!/usr/bin/env python3
"""Generate a WeChat article cover image from title/summary or markdown.

Design goals (v2):
- Keep covers visually consistent across topics.
- Use a WeChat-friendly wide ratio by default (900x383).
- Keep title/summary/badge inside a safe area to avoid clipping in previews.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

BOOTSTRAP_ENV = "BAOYU_COVER_NO_BOOTSTRAP"


def parse_frontmatter(markdown_text: str) -> tuple[dict[str, str], str]:
    if not markdown_text.startswith("---"):
        return {}, markdown_text

    lines = markdown_text.splitlines()
    if len(lines) < 3:
        return {}, markdown_text

    fm: dict[str, str] = {}
    end_idx = -1
    for i in range(1, len(lines)):
        line = lines[i].strip()
        if line == "---":
            end_idx = i
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            fm[key] = value

    if end_idx == -1:
        return {}, markdown_text
    body = "\n".join(lines[end_idx + 1 :])
    return fm, body


def first_paragraph(markdown_body: str) -> str:
    blocks = [b.strip() for b in markdown_body.split("\n\n") if b.strip()]
    for block in blocks:
        if block.startswith("#"):
            continue
        if block.startswith("!"):
            continue
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", block)
        text = re.sub(r"[`*_>#-]", "", text).strip()
        text = re.sub(r"\s+", " ", text)
        if text:
            return text
    return ""


def wrap_text(draw, text: str, font, max_width: int, max_lines: int) -> list[str]:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return []

    lines: list[str] = []
    current = ""
    truncated = False
    idx = 0

    while idx < len(text):
        ch = text[idx]
        candidate = current + ch
        box = draw.textbbox((0, 0), candidate, font=font)
        width = box[2] - box[0]

        if width <= max_width or not current:
            current = candidate
            idx += 1
            continue

        if current.strip():
            lines.append(current.rstrip())
        current = ch.lstrip()
        idx += 1

        if len(lines) >= max_lines:
            truncated = True
            current = ""
            break

    if current and len(lines) < max_lines:
        lines.append(current.rstrip())
    if idx < len(text):
        truncated = True

    if truncated and lines:
        last = lines[-1].rstrip()
        while last:
            ell_line = f"{last}…"
            b = draw.textbbox((0, 0), ell_line, font=font)
            if (b[2] - b[0]) <= max_width:
                lines[-1] = ell_line
                break
            last = last[:-1]
        else:
            lines[-1] = "…"

    return [line for line in lines[:max_lines] if line]


def parse_size(size: str) -> tuple[int, int]:
    normalized = (size or "").strip().lower()
    if "x" not in normalized:
        raise ValueError("Invalid --size format. Use WIDTHxHEIGHT, e.g. 900x383")
    w_raw, h_raw = normalized.split("x", 1)
    w = int(w_raw)
    h = int(h_raw)
    if w < 400 or h < 220:
        raise ValueError("Image size too small; use at least 400x220")
    return w, h


def resolve_font_path() -> str | None:
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return path
    return None


def load_font(image_font_module, font_path: str | None, size: int):
    if font_path:
        try:
            return image_font_module.truetype(font_path, size)
        except Exception:
            pass
    return image_font_module.load_default()


def line_height(draw, font) -> int:
    box = draw.textbbox((0, 0), "Ag中", font=font)
    return max(1, box[3] - box[1])


def fit_text_block(
    draw,
    text: str,
    font_path: str | None,
    max_width: int,
    max_height: int,
    max_lines: int,
    max_size: int,
    min_size: int,
    gap_ratio: float,
    image_font_module,
):
    if max_width <= 0 or max_height <= 0:
        raise ValueError("Invalid layout area for text rendering")

    best = None
    for size in range(max_size, min_size - 1, -2):
        font = load_font(image_font_module, font_path, size)
        lines = wrap_text(draw, text, font, max_width, max_lines)
        if not lines:
            continue
        lh = line_height(draw, font)
        gap = int(lh * gap_ratio)
        block_height = lh * len(lines) + gap * max(0, len(lines) - 1)
        if block_height <= max_height:
            return font, lines, lh, gap
        best = (font, lines, lh, gap)

    if best:
        return best

    fallback = load_font(image_font_module, font_path, min_size)
    lines = wrap_text(draw, text, fallback, max_width, max_lines)
    lh = line_height(draw, fallback)
    gap = int(lh * gap_ratio)
    return fallback, lines, lh, gap


def draw_gradient(draw, w: int, h: int) -> None:
    start = (9, 23, 62)
    end = (32, 74, 145)
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(start[0] + (end[0] - start[0]) * t)
        g = int(start[1] + (end[1] - start[1]) * t)
        b = int(start[2] + (end[2] - start[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def ensure_pillow(allow_bootstrap: bool) -> None:
    try:
        import PIL  # noqa: F401
        return
    except Exception:
        pass

    if not allow_bootstrap or os.environ.get(BOOTSTRAP_ENV) == "1":
        raise RuntimeError(
            "Pillow is required. Install manually or run with --bootstrap-pillow."
        )

    cache_venv = Path.home() / ".cache" / "wechat-publisher" / "cover-venv"
    py = cache_venv / "bin" / "python3"

    cache_venv.parent.mkdir(parents=True, exist_ok=True)
    if not py.exists():
        subprocess.check_call([sys.executable, "-m", "venv", str(cache_venv)])

    try:
        subprocess.check_call([str(py), "-c", "import PIL"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        subprocess.check_call([str(py), "-m", "pip", "install", "pillow"])

    env = os.environ.copy()
    env[BOOTSTRAP_ENV] = "1"
    os.execve(str(py), [str(py), __file__, *sys.argv[1:]], env)


def render_cover(title: str, summary: str, out_path: Path, size: str, badge: str) -> None:
    from PIL import Image, ImageDraw, ImageFont

    w, h = parse_size(size)

    img = Image.new("RGB", (w, h), (9, 23, 62))
    draw = ImageDraw.Draw(img)
    draw_gradient(draw, w, h)

    # Ambient color circles keep the same visual identity across posts.
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    circles = [
        (int(w * 0.82), int(h * 0.18), int(min(w, h) * 0.34), (67, 129, 255, 90)),
        (int(w * 0.22), int(h * 0.90), int(min(w, h) * 0.33), (24, 168, 185, 78)),
        (int(w * 0.57), int(h * 0.47), int(min(w, h) * 0.35), (129, 89, 255, 64)),
    ]
    for cx, cy, radius, color in circles:
        od.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=color)
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Soft frame for consistent card-like styling.
    frame_inset = max(8, int(h * 0.035))
    draw.rounded_rectangle(
        (frame_inset, frame_inset, w - frame_inset, h - frame_inset),
        radius=max(14, int(h * 0.08)),
        outline=(75, 132, 216),
        width=max(2, int(h * 0.006)),
        fill=None,
    )

    safe_left = int(w * 0.075)
    safe_right = int(w * 0.065)
    safe_top = int(h * 0.16)
    safe_bottom = int(h * 0.09)
    content_width = w - safe_left - safe_right

    badge_h = max(36, int(h * 0.135))
    badge_y = h - safe_bottom - badge_h
    text_bottom_limit = badge_y - int(h * 0.06)

    font_path = resolve_font_path()

    compact_title = re.sub(r"\s+", "", title)
    title_len = len(compact_title)
    title_max_size = max(34, int(h * 0.125))
    if title_len > 24:
        title_max_size = max(31, int(h * 0.112))
    if title_len > 34:
        title_max_size = max(28, int(h * 0.102))

    title_font, title_lines, title_lh, title_gap = fit_text_block(
        draw=draw,
        text=title,
        font_path=font_path,
        max_width=content_width,
        max_height=max(60, int(h * 0.40)),
        max_lines=2,
        max_size=title_max_size,
        min_size=max(26, int(h * 0.09)),
        gap_ratio=0.22,
        image_font_module=ImageFont,
    )
    if not title_lines:
        title_lines = ["AI Agent"]

    y = safe_top
    for i, line in enumerate(title_lines):
        draw.text((safe_left, y), line, font=title_font, fill=(245, 250, 255))
        y += title_lh
        if i < len(title_lines) - 1:
            y += title_gap

    summary_space = max(0, text_bottom_limit - y - int(h * 0.06))
    summary_font, summary_lines, summary_lh, summary_gap = fit_text_block(
        draw=draw,
        text=summary,
        font_path=font_path,
        max_width=max(1, int(content_width * 0.96)),
        max_height=max(34, summary_space),
        max_lines=2,
        max_size=max(22, int(h * 0.078)),
        min_size=max(16, int(h * 0.048)),
        gap_ratio=0.3,
        image_font_module=ImageFont,
    )
    if summary_lines and summary_space > 10:
        y += int(h * 0.05)
        for i, line in enumerate(summary_lines):
            draw.text((safe_left, y), line, font=summary_font, fill=(204, 225, 250))
            y += summary_lh
            if i < len(summary_lines) - 1:
                y += summary_gap

    # Badge in safe area, width adapts to text length.
    badge = (badge or "AI Agent / Architecture").strip()
    badge_font = load_font(ImageFont, font_path, max(16, int(badge_h * 0.43)))
    badge_box = draw.textbbox((0, 0), badge, font=badge_font)
    badge_text_w = max(1, badge_box[2] - badge_box[0])
    badge_text_h = max(1, badge_box[3] - badge_box[1])

    badge_x = safe_left
    badge_w = max(int(w * 0.30), min(int(w * 0.62), badge_text_w + int(w * 0.07)))
    draw.rounded_rectangle(
        (badge_x, badge_y, badge_x + badge_w, badge_y + badge_h),
        radius=max(12, int(badge_h / 2.2)),
        outline=(144, 203, 255),
        width=2,
        fill=(14, 40, 95),
    )
    draw.text(
        (
            badge_x + (badge_w - badge_text_w) // 2,
            badge_y + (badge_h - badge_text_h) // 2 - 1,
        ),
        badge,
        font=badge_font,
        fill=(225, 241, 255),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate WeChat cover image for article publishing")
    parser.add_argument("--markdown", help="Markdown file path; title/summary auto-extracted")
    parser.add_argument("--title", help="Cover title text")
    parser.add_argument("--summary", default="", help="Cover subtitle text")
    parser.add_argument("--badge", default="Observe • Plan • Act • Reflect", help="Bottom badge text")
    parser.add_argument(
        "--size",
        default="900x383",
        help="Image size, default 900x383 (WeChat-friendly wide ratio)",
    )
    parser.add_argument("--out", help="Output png path; default: <markdown_dir>/imgs/cover.png")
    parser.add_argument("--bootstrap-pillow", action="store_true", help="Auto-create local venv and install Pillow if missing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    md_path = Path(args.markdown).expanduser().resolve() if args.markdown else None
    if md_path and not md_path.exists():
        print(f"[ERROR] markdown not found: {md_path}", file=sys.stderr)
        return 1

    title = (args.title or "").strip()
    summary = (args.summary or "").strip()

    if md_path:
        content = md_path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(content)
        if not title:
            title = (fm.get("title") or "").strip()
        if not summary:
            summary = (fm.get("summary") or fm.get("digest") or "").strip()
        if not summary:
            summary = first_paragraph(body)

    if not title:
        print("[ERROR] Missing title. Provide --title or --markdown with frontmatter title.", file=sys.stderr)
        return 1

    if not summary:
        summary = "从概念、闭环到工程架构，构建可执行、可治理的 Agent 系统。"

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
    elif md_path:
        out_path = md_path.parent / "imgs" / "cover.png"
    else:
        out_path = Path.cwd() / "imgs" / "cover.png"

    ensure_pillow(allow_bootstrap=args.bootstrap_pillow)
    render_cover(title=title, summary=summary, out_path=out_path, size=args.size, badge=args.badge)

    print("[OK] cover generated")
    print(f"[OUT] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
