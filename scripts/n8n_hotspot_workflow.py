#!/usr/bin/env python3
"""
Bridge script for n8n to run the AI hotspot collection and publishing pipeline.

Commands:
  prepare  -> collect hotspots, build publish bundle variants, emit JSON
  publish  -> publish an existing bundle to multi-platform + Tencent, emit JSON

工作流配置建议 (2026-03-13):
  =========================

  n8n 工作流需要两个节点串行执行:

  Node 1: Execute Command - Prepare
    Command: python3 scripts/n8n_hotspot_workflow.py prepare --date $(date +%Y-%m-%d)
    Output: packageDir

  Node 2: Execute Command - Publish
    Command: python3 scripts/n8n_hotspot_workflow.py publish \
      --package-dir {{Node 1.packageDir}} \
      --platforms wechat,xhs,toutiao

图片处理说明:
  ===========

  1. 图片格式转换:
     - WebP/PNG → JPEG (微信兼容)
     - 自动转换在 prepare_bundle() 中执行

  2. 图片数量:
     - 工作流自动收集所有图片 (最多 9 张)
     - 当图片不足时，小红书发布效果会受限
     - 建议: 确保每篇文章至少有 3-4 张不同图片

  3. 小红书发布模式:
     - 1-2 张图片 → image-text 模式
     - 3+ 张图片 → long-article 模式

  4. 图片重复问题:
     - 当抓取内容只有 1 张配图时，系统会复制为封面图
     - 导致小红书发布时图片重复
     - 解决方案: 预先确保有足够的不同图片

  5. 手动发布 vs 工作流:
     - ❌ 手动调用: python3 post-to-xhs/scripts/publish_pipeline.py
       - 需要手动传递图片
       - 容易遗漏或重复
     - ✅ 工作流发布: python3 scripts/n8n_hotspot_workflow.py publish
       - 自动收集所有图片
       - 无需手动干预
       - 避免图片遗漏
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from PIL import Image


REPO_ROOT = Path(os.environ.get("HOTSPOT_WORKSPACE", Path(__file__).resolve().parent.parent))
COLLECTOR_RUN = REPO_ROOT / "ai-hotspot-collector" / "scripts" / "run.py"
WECHAT_PUBLISH = Path(os.environ.get("WECHAT_PUBLISH_SCRIPT", REPO_ROOT / "wechat-publisher" / "scripts" / "wechat-publish.ts"))
XHS_PIPELINE = Path(os.environ.get("XHS_PUBLISH_PIPELINE", REPO_ROOT / "post-to-xhs" / "scripts" / "publish_pipeline.py"))
TOUTIAO_PUBLISH = Path(os.environ.get("TOUTIAO_PUBLISH_SCRIPT", REPO_ROOT / "toutiao-publisher" / "scripts" / "api_publisher.py"))
TENCENT_PUBLISH = Path(os.environ.get("TENCENT_PUBLISH_SCRIPT", REPO_ROOT / "tencent-dev-community-publisher" / "scripts" / "publisher.py"))
BUN_BIN = os.environ.get("BUN_BIN", "bun")

# 自动加载 shell 环境变量（包括 GEMINI_API_KEY）
# 这确保在 n8n 工作流中执行时也能正确获取环境变量
def load_shell_env():
    """自动加载 ~/.zshrc 或 ~/.bashrc 中的环境变量"""
    import subprocess

    home = Path.home()
    shell_config_candidates = [
        home / ".zshrc",
        home / ".bash_profile",
        home / ".bashrc",
        home / ".profile",
    ]

    for config_file in shell_config_candidates:
        if config_file.exists():
            try:
                # 使用对应的shell来加载配置
                shell = "zsh" if config_file.name == ".zshrc" else "bash"
                result = subprocess.run(
                    [shell, "-c", f"source {config_file} && env"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    # 解析并设置环境变量
                    for line in result.stdout.split('\n'):
                        if '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            os.environ[key] = value
                    print(f"[env] Loaded environment from {config_file.name}")
                    return
            except (subprocess.TimeoutExpired, Exception) as e:
                print(f"[env] Warning: Failed to load {config_file.name}: {e}")

load_shell_env()


def slugify_model(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[^a-z0-9._-]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "default"


def default_package_dir(model: str, date_str: str | None = None) -> Path:
    day = date_str or datetime.now().strftime("%Y-%m-%d")
    return REPO_ROOT / "content" / "ai-hotspot-digests" / day / slugify_model(model)


def run_cmd(cmd: list[str]) -> dict:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "ok": result.returncode == 0,
        "command": cmd,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def sanitize_platforms(raw: str | None) -> list[str]:
    allowed = {"wechat", "xhs", "toutiao"}
    platforms = []
    for item in (raw or "wechat,xhs,toutiao").split(","):
        value = item.strip().lower()
        if value and value in allowed and value not in platforms:
            platforms.append(value)
    return platforms


def resolve_xhs_mode(raw: str | None) -> str:
    value = (raw or "").strip().lower()
    if value in {"image-text", "long-article"}:
        return value
    return "image-text"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def extract_title(markdown_text: str) -> str:
    for line in markdown_text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "今日 AI 热点速读"


def normalize_links_for_publish(text: str) -> str:
    text = re.sub(r"\*原文：\[(.*?)\]\((.*?)\)\*", r"原文：\2", text)
    text = re.sub(r"原文：\[(.*?)\]\((.*?)\)", r"原文：\2", text)
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1：\2", text)
    text = text.replace("🔹 ", "")
    text = text.replace("**", "")
    text = text.replace("__", "")
    text = re.sub(r"^\> ?", "", text, flags=re.M)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def infer_cover(package_dir: Path) -> Path | None:
    preferred = [
        package_dir / "images" / "01-cover.png",
        package_dir / "images" / "01-cover.jpg",
        package_dir / "images" / "01-cover.jpeg",
        package_dir / "images" / "cover.png",
        package_dir / "images" / "cover.jpg",
        package_dir / "images" / "cover.jpeg",
        package_dir / "images" / "cover.webp",
    ]
    for path in preferred:
        if path.exists():
            return path
    images_dir = package_dir / "images"
    if images_dir.exists():
        for path in sorted(images_dir.iterdir()):
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                return path
    return None


def collect_body_images(package_dir: Path) -> list[Path]:
    """
    收集内容包中的所有图片。

    注意事项 (2026-03-13 经验):
    ============================
    1. 图片数量:
       - 尽量确保有 3-4 张不同图片
       - 如果只有 1 张图片，会导致小红书发布时图片重复
       - 系统会将唯一配图复制为封面图

    2. 图片重复问题:
       - 当抓取内容只有 1 张配图时
       - 系统会将该配图复制为封面图
       - MD5 值相同，小红书编辑页会显示重复

    3. 解决方案:
       - 从历史内容包选择更多不同图片
       - 确保每张图片 MD5 值不同
       - 补充图片直到至少 3-4 张

    4. 小红书发布影响:
       - 1-2 张图片 → image-text 模式
       - 3+ 张图片 → long-article 模式
       - 图片数量不足会影响用户体验

    Returns:
        排序后的图片路径列表
    """
    images_dir = package_dir / "images"
    if not images_dir.exists():
        return []

    images = [
        path
        for path in sorted(images_dir.iterdir())
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    ]

    # 提示图片数量
    if len(images) <= 2:
        print(f"[images] WARNING: Only {len(images)} image(s) found. "
              f"Xiaohongshu posts work best with 3+ images.")
    elif len(images) > 9:
        print(f"[images] INFO: Found {len(images)} images. "
              f"Only first 9 will be used for publishing.")

    return images


def convert_images_to_compatible_format(package_dir: Path) -> int:
    """
    将 images/ 目录中的图片转换为微信平台兼容的格式。

    转换规则：
    - WebP → JPEG (微信不支持 WebP)
    - PNG → JPEG (微信对 PNG 支持有限，建议转换为 JPEG)
    - JPEG → JPEG (保持不变)

    返回转换的图片数量。
    """
    images_dir = package_dir / "images"
    if not images_dir.exists():
        return 0

    converted_count = 0

    for path in sorted(images_dir.iterdir()):
        if not path.is_file():
            continue

        # 跳过已经是 JPEG 的图片
        if path.suffix.lower() == ".jpg" or path.suffix.lower() == ".jpeg":
            continue

        # 转换 WebP 和 PNG 为 JPEG
        if path.suffix.lower() in {".webp", ".png"}:
            try:
                # 打开图片
                img = Image.open(path)

                # 创建新的 JPEG 文件名
                target_path = path.with_suffix(".jpg")

                # 转换 RGB (如果是 RGBA 或其他模式)
                if img.mode in ("RGBA", "LA", "P"):
                    # 创建白色背景
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    if img.mode in ("RGBA", "LA"):
                        background.paste(img, mask=img.split()[-1])
                        img = background
                    else:
                        img = img.convert("RGB")
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # 保存为 JPEG (质量 85)
                img.save(target_path, "JPEG", quality=85)

                # 删除原始文件
                path.unlink()

                converted_count += 1
                print(f"[image-convert] Converted {path.name} → {target_path.name}")

            except Exception as e:
                print(f"[image-convert] Failed to convert {path.name}: {e}")

    return converted_count


def parse_digest_sections(markdown_text: str) -> list[dict]:
    lines = markdown_text.splitlines()
    sections: list[dict] = []
    current: dict | None = None
    for raw in lines:
        line = raw.rstrip()
        m = re.match(r"^##\s+(.*)", line)
        if m:
            heading = m.group(1).strip()
            if heading in {"今日概览", "收尾", "原文链接"}:
                current = None
                continue
            current = {"title": heading.replace("🔹 ", "").strip(), "lines": []}
            sections.append(current)
            continue
        if current is not None:
            current["lines"].append(line)
    parsed: list[dict] = []
    for section in sections:
        body_lines = []
        for line in section["lines"]:
            stripped = line.strip()
            if not stripped or stripped == "---" or stripped.startswith("!["):
                continue
            if stripped.startswith("**来源**"):
                continue
            if stripped.startswith("原文：") or stripped.startswith("*原文：") or stripped.startswith("*原文:"):
                continue
            body_lines.append(stripped)
        paragraph = ""
        if body_lines:
            paragraph = " ".join(body_lines[:3]).replace(" ---", "")
        parsed.append({"title": section["title"], "summary": paragraph})
    return parsed


def build_xhs_body(title: str, sections: list[dict]) -> str:
    lines = [f"# {re.sub(r'（.*?）', '', title).strip()}"]
    if sections:
        lines.append("")
        lines.append("今天这波 AI 热点，核心就这几件事：")
        lines.append("")
        for idx, section in enumerate(sections[:3], start=1):
            heading = re.sub(r"^\d+\.\s*", "", section["title"]).strip()
            summary = section["summary"]
            if len(summary) > 120:
                summary = summary[:118].rstrip() + "…"
            lines.append(f"{idx}. {heading}")
            if summary:
                lines.append(summary)
            lines.append("")
        lines.append("如果把今天这几条连起来看，行业主线还是很清楚：")
        lines.append("AI 正在更深地进入浏览器、办公和自动执行场景。")
        lines.append("")
        lines.append("#AI热点 #人工智能 #科技资讯 #AIAgent #大模型")
    return "\n".join(lines).strip() + "\n"


def summarize_article_item(item: dict) -> str:
    # 优先使用 LLM 生成的中文摘要
    ai_summary = item.get("ai_summary", "")
    if ai_summary and ai_summary != "与 AI 无关":
        text = ai_summary.strip()
        text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", text)
        text = re.sub(r"\s+", " ", text).strip(" -")
        return text[:200] if text else (item.get("title", "")[:120])
    
    # 降级：使用原始描述/预览
    text = (item.get("preview") or item.get("description") or item.get("title") or "").strip()
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip(" -")
    return text[:120] if text else (item.get("title", "")[:120])


def build_single_article_markdown(item: dict, image_name: str = "") -> str:
    lines = [
        f"# {item.get('title', '未命名热点')}",
        "",
        f"**来源**：{item.get('source_label', '')}",
        f"**原文链接**：{item.get('source_url', '')}",
    ]
    if item.get("author"):
        lines.append(f"**作者**：{item['author']}")
    if item.get("published_time"):
        lines.append(f"**发布时间**：{item['published_time']}")
    if item.get("related_sources") and len(item["related_sources"]) > 1:
        lines.append(f"**补充来源**：{', '.join(item['related_sources'])}")
    
    # 优先使用 LLM 生成的中文摘要
    summary = item.get("ai_summary", "")
    if not summary or summary == "与 AI 无关":
        summary = item.get("description") or item.get("preview") or "暂无摘要。"
    
    lines.extend(["", "## 摘要", "", summary, ""])
    if image_name:
        lines.extend([f"![Image](./{image_name})", ""])
    return "\n".join(lines).strip() + "\n"


def build_single_xhs_body(item: dict) -> str:
    title = re.sub(r"（.*?）", "", item.get("title", "")).strip() or "今日 AI 热点"
    summary = summarize_article_item(item)
    lines = [
        f"# {title}",
        "",
        summary or "这条热点值得关注，先看关键信息。",
        "",
        f"来源：{item.get('source_label', '')}",
    ]
    if item.get("source_url"):
        lines.append(f"原文：{item['source_url']}")
    lines.extend(["", "#AI热点 #人工智能 #科技资讯"])
    return "\n".join(lines).strip() + "\n"


def materialize_individual_articles(package_dir: Path) -> list[dict]:
    manifest_path = package_dir / "manifest.json"
    if not manifest_path.exists():
        return []

    try:
        manifest = json.loads(read_text(manifest_path))
    except json.JSONDecodeError:
        return []

    articles_dir = package_dir / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)
    article_items: list[dict] = []

    for item in manifest:
        global_index = int(item.get("global_index") or len(article_items) + 1)
        slug = slugify_model(item.get("title", ""))[:80]
        article_dir = articles_dir / f"{global_index:02d}-{slug}"
        article_dir.mkdir(parents=True, exist_ok=True)

        source_content = Path(item.get("content_md", "")).expanduser()
        source_dir = source_content.parent if source_content.exists() else Path(item.get("dir", "")).expanduser()

        image_name = ""
        if source_dir.exists():
            for candidate in sorted(source_dir.iterdir()):
                if candidate.is_file() and candidate.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
                    shutil.copy2(candidate, article_dir / candidate.name)
                    image_name = candidate.name
                    break

        article_text = build_single_article_markdown(item, image_name=image_name)
        preview_text = article_text
        toutiao_text = normalize_links_for_publish(article_text)
        tencent_text = normalize_links_for_publish(article_text)
        xhs_text = build_single_xhs_body(item)

        article_md = article_dir / "article.md"
        preview_md = article_dir / "article-preview.md"
        toutiao_md = article_dir / "article-toutiao.md"
        tencent_md = article_dir / "article-tencent.md"
        xhs_md = article_dir / "article-xhs.md"
        metadata_json = article_dir / "metadata.json"

        write_text(article_md, article_text)
        write_text(preview_md, preview_text)
        write_text(toutiao_md, toutiao_text)
        write_text(tencent_md, tencent_text)
        write_text(xhs_md, xhs_text)

        payload = {
            "eventId": item.get("event_id", ""),
            "globalIndex": global_index,
            "title": item.get("title", ""),
            "summary": summarize_article_item(item),
            "source": item.get("source", ""),
            "sourceLabel": item.get("source_label", ""),
            "sourceUrl": item.get("source_url", ""),
            "author": item.get("author", ""),
            "publishedTime": item.get("published_time", ""),
            "cover": str(article_dir / image_name) if image_name else "",
            "files": {
                "article": str(article_md),
                "preview": str(preview_md),
                "xhs": str(xhs_md),
                "toutiao": str(toutiao_md),
                "tencent": str(tencent_md),
            },
            "relatedSources": item.get("related_sources", []),
            "sourceContent": str(source_content) if source_content else "",
            "sourceDir": str(source_dir) if source_dir else "",
        }
        write_text(metadata_json, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        payload["metadata"] = str(metadata_json)
        article_items.append(payload)

    return article_items


def build_publish_bundle(package_dir: Path) -> dict:
    digest_path = package_dir / "00-今日AI热点速读.md"
    if not digest_path.exists():
        raise FileNotFoundError(f"Digest not found: {digest_path}")

    digest_text = read_text(digest_path)
    title = extract_title(digest_text)
    cover = infer_cover(package_dir)
    sections = parse_digest_sections(digest_text)
    articles = materialize_individual_articles(package_dir)

    article_md = package_dir / "article.md"
    preview_md = package_dir / "article-preview.md"
    xhs_md = package_dir / "article-xhs.md"
    toutiao_md = package_dir / "article-toutiao.md"
    tencent_md = package_dir / "article-tencent.md"
    metadata_json = package_dir / "bundle-metadata.json"

    article_text = digest_text.strip() + "\n"
    preview_text = article_text
    toutiao_text = normalize_links_for_publish(article_text)
    tencent_text = normalize_links_for_publish(article_text)
    xhs_text = build_xhs_body(title, sections)

    write_text(article_md, article_text)
    write_text(preview_md, preview_text)
    write_text(toutiao_md, toutiao_text)
    write_text(tencent_md, tencent_text)
    write_text(xhs_md, xhs_text)

    summary_text = ""
    for chunk in re.split(r"\n\s*\n", digest_text):
        cleaned = chunk.strip()
        if not cleaned or cleaned.startswith("#") or cleaned.startswith(">") or cleaned.startswith("!["):
            continue
        cleaned = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", cleaned)
        cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
        cleaned = re.sub(r"^#+\s*", "", cleaned, flags=re.M)
        cleaned = " ".join(cleaned.split()).strip("- ").strip()
        if cleaned:
            summary_text = cleaned[:120]
            break

    if not summary_text:
        summary_text = title[:120]

    payload = {
        "packageDir": str(package_dir),
        "digestPath": str(digest_path),
        "title": title,
        "summary": summary_text,
        "cover": str(cover) if cover else "",
        "files": {
            "article": str(article_md),
            "preview": str(preview_md),
            "xhs": str(xhs_md),
            "toutiao": str(toutiao_md),
            "tencent": str(tencent_md),
        },
        "images": [str(path) for path in collect_body_images(package_dir)],
        "sections": sections,
        "articles": articles,
    }
    write_text(metadata_json, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return payload


def prepare_bundle(args: argparse.Namespace) -> int:
    package_dir = Path(args.existing_package_dir).expanduser().resolve() if args.existing_package_dir else (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else default_package_dir(args.rewrite_model, args.date)
    )
    package_dir.mkdir(parents=True, exist_ok=True)

    fetch_result = None
    if not args.existing_package_dir:
        cmd = [
            "python3",
            str(COLLECTOR_RUN),
            "fetch",
            "--sources",
            args.sources,
            "--limit-per-source",
            str(args.limit_per_source),
            "--output-dir",
            str(package_dir),
            "--rewrite-mode",
            args.rewrite_mode,
            "--rewrite-provider",
            args.rewrite_provider,
            "--rewrite-model",
            args.rewrite_model,
            "--llm-provider",
            args.llm_provider,
            "--ai-relevance-threshold",
            str(args.ai_relevance_threshold),
            "--max-candidates",
            str(args.max_candidates),
        ]
        if args.keep_duplicates:
            cmd.append("--keep-duplicates")
        if args.fail_fast:
            cmd.append("--fail-fast")
        if args.disable_llm:
            cmd.append("--disable-llm")
        fetch_result = run_cmd(cmd)
        if not fetch_result["ok"]:
            print(json.dumps({"ok": False, "stage": "fetch", **fetch_result}, ensure_ascii=False, indent=2))
            return fetch_result["returncode"] or 1

    bundle = build_publish_bundle(package_dir)

    # 图片格式转换：WebP/PNG → JPEG（微信兼容）
    converted_count = convert_images_to_compatible_format(package_dir)
    if converted_count > 0:
        print(f"[image-convert] Converted {converted_count} image(s) to JPEG format for WeChat compatibility")

    payload = {
        "ok": True,
        "stage": "prepare",
        "packageDir": str(package_dir),
        "fetchExecuted": not bool(args.existing_package_dir),
        "fetch": fetch_result,
        "bundle": bundle,
        "imagesConverted": converted_count,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def publish_bundle(args: argparse.Namespace) -> int:
    package_dir = Path(args.package_dir).expanduser().resolve()
    if not package_dir.exists():
        print(json.dumps({"ok": False, "error": f"Package dir not found: {package_dir}"}, ensure_ascii=False, indent=2))
        return 1

    metadata_path = package_dir / "bundle-metadata.json"
    bundle = json.loads(read_text(metadata_path)) if metadata_path.exists() else build_publish_bundle(package_dir)
    title = args.title or bundle["title"]
    cover = args.cover or bundle.get("cover") or ""

    platform_results = {}
    for platform in sanitize_platforms(args.platforms):
        if platform == "wechat":
            cmd = [BUN_BIN, str(WECHAT_PUBLISH), str(package_dir)]
            if args.wechat_method:
                cmd += ["--method", args.wechat_method]
            if title:
                cmd += ["--title", title]
            if args.wechat_summary:
                cmd += ["--summary", args.wechat_summary]
            if args.wechat_author:
                cmd += ["--author", args.wechat_author]
            if cover:
                cmd += ["--cover", cover]
            if args.wechat_profile:
                cmd += ["--profile", args.wechat_profile]
            if args.dry_run:
                cmd.append("--dry-run")
            platform_results["wechat"] = run_cmd(cmd)
        elif platform == "xhs":
            if args.dry_run:
                platform_results["xhs"] = {
                    "ok": True,
                    "skipped": True,
                    "reason": "Xiaohongshu publish pipeline has no native dry-run mode. Skipped during dry-run validation.",
                }
            else:
                xhs_source = package_dir / "article-xhs.md"
                xhs_title = re.sub(r"（.*?）", "", title).strip()
                images = collect_body_images(package_dir)
                xhs_mode = resolve_xhs_mode(args.xhs_mode)
                cmd = [
                    "python3",
                    str(XHS_PIPELINE),
                    "--title",
                    xhs_title,
                    "--content-file",
                    str(xhs_source),
                    "--mode",
                    xhs_mode,
                    "--account",
                    args.xhs_account or "default",
                    "--auto-publish",
                ]
                if images:
                    cmd += ["--images", *[str(path) for path in images[:9]]]
                if args.headless_browser:
                    cmd.append("--headless")
                platform_results["xhs"] = run_cmd(cmd)
        elif platform == "toutiao":
            if args.dry_run:
                platform_results["toutiao"] = {
                    "ok": True,
                    "skipped": True,
                    "reason": "Toutiao API publish is skipped during dry-run validation.",
                }
            else:
                toutiao_source = package_dir / "article-toutiao.md"
                cmd = [
                    "python3",
                    str(TOUTIAO_PUBLISH),
                    "--title",
                    title,
                    "--content",
                    str(toutiao_source),
                ]
                if cover:
                    cmd += ["--cover", cover]
                platform_results["toutiao"] = run_cmd(cmd)

    tencent_result = None
    if args.with_tencent:
        if args.dry_run:
            tencent_result = {
                "ok": True,
                "skipped": True,
                "reason": "Tencent browser publishing is skipped during dry-run to avoid blocking n8n validation.",
            }
        else:
            tencent_content = package_dir / "article-tencent.md"
            tencent_cmd = [
                "python3",
                str(TENCENT_PUBLISH),
                "--title",
                title,
                "--content",
                str(tencent_content),
                "--headless" if args.tencent_headless else "--no-headless",
            ]
            if cover:
                tencent_cmd += ["--cover", cover]
            tencent_result = run_cmd(tencent_cmd)

    ok = all(result.get("ok") for result in platform_results.values()) and (tencent_result["ok"] if tencent_result else True)
    payload = {
        "ok": ok,
        "stage": "publish",
        "packageDir": str(package_dir),
        "title": title,
        "platforms": platform_results,
        "tencent": tencent_result,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="n8n bridge for AI hotspot collection and publishing")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Collect hotspots and build publish bundle")
    prepare.add_argument("--sources", default="techcrunch,the-verge,hn,twitter,github-trending", help="Comma-separated hotspot sources (default: AI-relevant sources)")
    prepare.add_argument("--limit-per-source", type=int, default=3)
    prepare.add_argument("--output-dir", help="Explicit output package dir")
    prepare.add_argument("--existing-package-dir", help="Skip fetch and rebuild metadata for an existing package dir")
    prepare.add_argument("--rewrite-mode", default="auto", choices=["auto", "off", "api"])
    prepare.add_argument("--rewrite-provider", default="gemini", choices=["auto", "openai", "gemini"])
    prepare.add_argument("--rewrite-model", default="gemini-3-pro-preview")
    prepare.add_argument("--date", help="Override package date (YYYY-MM-DD)")
    prepare.add_argument("--keep-duplicates", action="store_true")
    prepare.add_argument("--fail-fast", action="store_true")
    # LLM-related arguments for AI relevance filtering
    prepare.add_argument("--disable-llm", action="store_true", help="Disable LLM for AI relevance scoring and summary generation (default: enabled)")
    prepare.add_argument("--llm-provider", choices=["auto", "openai", "gemini"], default="gemini", help="LLM provider for AI scoring (default: gemini)")
    prepare.add_argument("--ai-relevance-threshold", type=float, default=4.0, help="Minimum AI relevance score (0-10) to include (default: 4.0)")
    prepare.add_argument("--max-candidates", type=int, default=20, help="Maximum candidates to process (default: 20)")

    publish = subparsers.add_parser("publish", help="Publish an existing bundle")
    publish.add_argument("--package-dir", required=True)
    publish.add_argument("--platforms", default="wechat,xhs,toutiao")
    publish.add_argument("--with-tencent", action="store_true")
    publish.add_argument("--title", help="Override title")
    publish.add_argument("--cover", help="Override cover image path")
    publish.add_argument("--wechat-author", help="Override WeChat author")
    publish.add_argument("--wechat-summary", help="Override WeChat summary")
    publish.add_argument("--wechat-profile", default=os.environ.get("WECHAT_BROWSER_PROFILE"), help="Override WeChat Chrome profile directory")
    publish.add_argument("--xhs-mode", choices=["auto", "image-text", "long-article"])
    publish.add_argument("--xhs-template")
    publish.add_argument("--xhs-account")
    publish.add_argument("--wechat-method", choices=["auto", "api", "browser"], default="auto")
    publish.add_argument("--headless-browser", action=argparse.BooleanOptionalAction, default=True)
    publish.add_argument("--tencent-headless", action=argparse.BooleanOptionalAction, default=True)
    publish.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    if args.command == "prepare":
        sys.exit(prepare_bundle(args))
    if args.command == "publish":
        sys.exit(publish_bundle(args))


if __name__ == "__main__":
    main()
