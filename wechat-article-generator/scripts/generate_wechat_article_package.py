#!/usr/bin/env python3
"""Generate WeChat article artifacts (markdown, html, assets, tar.gz)."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
import unicodedata
from datetime import date
from pathlib import Path


def slugify(text: str) -> str:
    source = (text or "").strip()
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    tokens = re.findall(r"[a-zA-Z0-9]+", ascii_text.lower())
    slug = "-".join(tokens[:6]).strip("-")
    if len(slug) >= 6:
        return slug

    seed = source or "wechat-article"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:6]
    base = slug if slug else "wechat-article"
    return f"{base}-{digest}"


def unique_slug(root: Path, slug: str) -> str:
    candidate = slug
    idx = 2
    while (root / candidate).exists() or (root / f"{candidate}.tar.gz").exists():
        candidate = f"{slug}-{idx}"
        idx += 1
    return candidate


def ensure_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def render_template(template: str, mapping: dict) -> str:
    output = template
    for key, value in mapping.items():
        output = output.replace(f"{{{{{key}}}}}", value)
    return output


def generate_markdown(topic: str, title: str, author: str, publish_date: str) -> str:
    return f"""---
title: {title}
author: {author}
date: {publish_date}
---

# {title}

## 为什么这个主题值得关注

{topic} 正在快速演进，很多实践正在从“可选”变成“必备”。这篇文章聚焦可落地的方法，帮助你在真实工作场景中直接应用。

## 核心观点

1. 先建立统一目标，再选工具与流程。
2. 用小步快跑方式验证，不要一次性重构全部链路。
3. 保持可复盘：记录关键决策、指标和边界条件。

## 实操步骤

### 第一步：明确问题边界

- 当前流程痛点是什么
- 成功指标是什么
- 不做哪些事情

### 第二步：设计最小可行方案

- 只保留 1-2 个关键场景
- 先跑通闭环再扩展
- 用数据验证收益

### 第三步：持续优化

- 每周复盘一次效果
- 清理无效动作
- 固化高价值模板

## 常见误区

- 一开始就追求“大而全”
- 只关注工具，不关注执行流程
- 没有明确验收标准

## 结语

如果你希望把 {topic} 真正落到团队里，建议先从一个高频场景开始，跑通后再复制到其他场景。
"""


def copy_images(images_dir: Path, cover: Path | None, images: list[Path]):
    images_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    used_source_paths = set()

    if cover:
        ext = cover.suffix.lower() or ".png"
        cover_target = images_dir / f"cover{ext}"
        shutil.copy2(cover, cover_target)
        copied.append(str(cover_target))
        used_source_paths.add(str(cover.resolve()))

    idx = 1
    for image in images:
        resolved = str(image.resolve())
        if resolved in used_source_paths:
            continue
        ext = image.suffix.lower() or ".png"
        target = images_dir / f"image-{idx}{ext}"
        shutil.copy2(image, target)
        copied.append(str(target))
        idx += 1

    if not copied:
        (images_dir / "README.txt").write_text(
            "No images provided. Add cover/image files before publishing to WeChat.",
            encoding="utf-8",
        )

    return copied


def extract_json(stdout: str):
    match = re.search(r"\{[\s\S]*\}", stdout)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def run_converter(converter: Path, article_md: Path, article_html: Path):
    cmd = [
        sys.executable,
        str(converter),
        str(article_md),
        "--out",
        str(article_html),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise RuntimeError("markdown-to-wechat conversion failed")
    return extract_json(result.stdout)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate WeChat article package")
    parser.add_argument("topic", nargs="?", default="", help="Article topic")
    parser.add_argument("--topic", dest="topic_opt", default="", help="Article topic")
    parser.add_argument("--title", default="", help="Article title")
    parser.add_argument("--author", default="AI 助手", help="Author name")
    parser.add_argument("--date", dest="publish_date", default=str(date.today()), help="Publish date")
    parser.add_argument("--slug", default="", help="Output slug")
    parser.add_argument("--root", default="./wechat-articles", help="Output root directory")
    parser.add_argument("--md-in", default="", help="Existing markdown input")
    parser.add_argument("--cover", default="", help="Cover image path")
    parser.add_argument("--images", nargs="*", default=[], help="Additional image paths")
    parser.add_argument("--template", default="", help="README template path")
    parser.add_argument("--no-package", action="store_true", help="Skip tar.gz package creation")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing slug directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    topic = (args.topic_opt or args.topic or "").strip()
    md_in = Path(args.md_in).expanduser().resolve() if args.md_in else None

    if not topic and not md_in:
        print("[ERROR] Provide a topic or --md-in", file=sys.stderr)
        return 1

    if md_in and not md_in.exists():
        print(f"[ERROR] markdown input not found: {md_in}", file=sys.stderr)
        return 1

    root = Path(args.root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    base_slug = args.slug.strip() or slugify(topic or md_in.stem)
    slug = base_slug if args.overwrite else unique_slug(root, base_slug)
    article_dir = root / slug
    article_dir.mkdir(parents=True, exist_ok=True)

    title = args.title.strip() or (topic if topic else md_in.stem)

    article_md = article_dir / "article.md"
    if md_in:
        article_md.write_text(md_in.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        article_md.write_text(
            generate_markdown(topic=topic, title=title, author=args.author, publish_date=args.publish_date),
            encoding="utf-8",
        )

    converter = Path(__file__).resolve().parent / "markdown-to-wechat.py"
    article_html = article_dir / "article-wechat.html"
    converter_meta = run_converter(converter, article_md, article_html)

    cover_path = Path(args.cover).expanduser().resolve() if args.cover else None
    if cover_path and not cover_path.exists():
        print(f"[ERROR] cover image not found: {cover_path}", file=sys.stderr)
        return 1

    image_paths = []
    for image in args.images:
        img = Path(image).expanduser().resolve()
        if not img.exists():
            print(f"[WARN] image not found, skipped: {img}")
            continue
        image_paths.append(img)

    if not cover_path and image_paths:
        cover_path = image_paths[0]

    images_dir = article_dir / "images"
    copied_images = copy_images(images_dir, cover_path, image_paths)

    template_path = (
        Path(args.template).expanduser().resolve()
        if args.template
        else (Path(__file__).resolve().parent.parent / "README_TEMPLATE.txt")
    )
    readme_template = ensure_text(template_path)
    if not readme_template:
        readme_template = "Article: {{title}}\nDate: {{date}}\nTopic: {{topic}}\n"

    readme_content = render_template(
        readme_template,
        {
            "title": title,
            "date": args.publish_date,
            "topic": topic or md_in.stem,
            "slug": slug,
        },
    )
    readme_path = article_dir / "README.txt"
    readme_path.write_text(readme_content, encoding="utf-8")

    tar_path = None
    if not args.no_package:
        tar_path = root / f"{slug}.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(article_dir, arcname=article_dir.name)

    output = {
        "slug": slug,
        "articleDir": str(article_dir),
        "articleMarkdown": str(article_md),
        "articleHtml": str(article_html),
        "readme": str(readme_path),
        "images": copied_images,
        "package": str(tar_path) if tar_path else "",
        "converterMetadata": converter_meta,
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
