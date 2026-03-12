#!/usr/bin/env python3
"""
Bridge script for n8n to run the AI hotspot collection and publishing pipeline.

Commands:
  prepare  -> collect hotspots, build publish bundle variants, emit JSON
  publish  -> publish an existing bundle to multi-platform + Tencent, emit JSON
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(os.environ.get("HOTSPOT_WORKSPACE", Path(__file__).resolve().parent.parent))
COLLECTOR_RUN = REPO_ROOT / "ai-hotspot-collector" / "scripts" / "run.py"
WECHAT_PUBLISH = Path(os.environ.get("WECHAT_PUBLISH_SCRIPT", REPO_ROOT / "wechat-publisher" / "scripts" / "wechat-publish.ts"))
XHS_PIPELINE = Path(os.environ.get("XHS_PUBLISH_PIPELINE", REPO_ROOT / "post-to-xhs" / "scripts" / "publish_pipeline.py"))
TOUTIAO_PUBLISH = Path(os.environ.get("TOUTIAO_PUBLISH_SCRIPT", REPO_ROOT / "toutiao-publisher" / "scripts" / "api_publisher.py"))
TENCENT_PUBLISH = Path(os.environ.get("TENCENT_PUBLISH_SCRIPT", REPO_ROOT / "tencent-dev-community-publisher" / "scripts" / "publisher.py"))
BUN_BIN = os.environ.get("BUN_BIN", "bun")


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
    images_dir = package_dir / "images"
    if not images_dir.exists():
        return []
    return [
        path
        for path in sorted(images_dir.iterdir())
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    ]


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


def build_publish_bundle(package_dir: Path) -> dict:
    digest_path = package_dir / "00-今日AI热点速读.md"
    if not digest_path.exists():
        raise FileNotFoundError(f"Digest not found: {digest_path}")

    digest_text = read_text(digest_path)
    title = extract_title(digest_text)
    cover = infer_cover(package_dir)
    sections = parse_digest_sections(digest_text)

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
        ]
        if args.keep_duplicates:
            cmd.append("--keep-duplicates")
        if args.fail_fast:
            cmd.append("--fail-fast")
        fetch_result = run_cmd(cmd)
        if not fetch_result["ok"]:
            print(json.dumps({"ok": False, "stage": "fetch", **fetch_result}, ensure_ascii=False, indent=2))
            return fetch_result["returncode"] or 1

    bundle = build_publish_bundle(package_dir)
    payload = {
        "ok": True,
        "stage": "prepare",
        "packageDir": str(package_dir),
        "fetchExecuted": not bool(args.existing_package_dir),
        "fetch": fetch_result,
        "bundle": bundle,
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
    prepare.add_argument("--sources", default="hn,engadget,fast-company", help="Comma-separated hotspot sources")
    prepare.add_argument("--limit-per-source", type=int, default=3)
    prepare.add_argument("--output-dir", help="Explicit output package dir")
    prepare.add_argument("--existing-package-dir", help="Skip fetch and rebuild metadata for an existing package dir")
    prepare.add_argument("--rewrite-mode", default="auto", choices=["auto", "off", "api"])
    prepare.add_argument("--rewrite-provider", default="gemini", choices=["auto", "openai", "gemini"])
    prepare.add_argument("--rewrite-model", default="gemini-3-pro-preview")
    prepare.add_argument("--date", help="Override package date (YYYY-MM-DD)")
    prepare.add_argument("--keep-duplicates", action="store_true")
    prepare.add_argument("--fail-fast", action="store_true")

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
