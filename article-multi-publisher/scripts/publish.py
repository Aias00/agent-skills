#!/usr/bin/env python3
"""
Unified article publisher for WeChat, Xiaohongshu, and Toutiao.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SKILL_DIR.parent
WECHAT_PUBLISH = Path(os.environ.get("WECHAT_PUBLISH_SCRIPT", REPO_ROOT / "wechat-publisher" / "scripts" / "wechat-publish.ts")).expanduser()
XHS_PIPELINE = Path(os.environ.get("XHS_PIPELINE_SCRIPT", REPO_ROOT / "post-to-xhs" / "scripts" / "publish_pipeline.py")).expanduser()
XHS_CDP = Path(os.environ.get("XHS_CDP_SCRIPT", REPO_ROOT / "post-to-xhs" / "scripts" / "cdp_publish.py")).expanduser()
TOUTIAO_RUNNER = Path(os.environ.get("TOUTIAO_RUNNER_SCRIPT", REPO_ROOT / "toutiao-publisher" / "scripts" / "run.py")).expanduser()
TOUTIAO_VENV_PY = Path(os.environ.get("TOUTIAO_PYTHON", REPO_ROOT / "toutiao-publisher" / ".venv" / "bin" / "python")).expanduser()

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
PROJECT_EXTEND = Path(".baoyu-skills/article-multi-publisher/EXTEND.md")
USER_EXTEND = Path.home() / ".baoyu-skills/article-multi-publisher/EXTEND.md"


def load_extend_settings():
    for path in (PROJECT_EXTEND, USER_EXTEND):
        if path.exists():
            data = {}
            for raw in path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                key, value = line.split(":", 1)
                data[key.strip().lower()] = value.strip()
            return path, data
    return None, {}


def parse_platforms(raw: str | None, default_value: str | None):
    source = raw or default_value or "wechat,xhs,toutiao"
    values = [item.strip().lower() for item in source.split(",") if item.strip()]
    ordered = []
    for item in values:
        if item not in ordered:
            ordered.append(item)
    return ordered


def remove_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        parts = text.split("\n---\n", 1)
        if len(parts) == 2:
            return parts[1]
    return text


def extract_markdown_title_and_body(path: Path):
    text = remove_frontmatter(path.read_text(encoding="utf-8"))
    lines = text.splitlines()
    title = None
    body_lines = []
    title_consumed = False
    for line in lines:
        if not title_consumed and line.startswith("# "):
            title = line[2:].strip()
            title_consumed = True
            continue
        body_lines.append(line)
    body = "\n".join(body_lines).strip()
    return title, body


def html_to_text(html: str) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", "", text, flags=re.I | re.S)
    text = re.sub(r"<img\b[^>]*>", "", text, flags=re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</(p|div|section|h1|h2|h3|li)>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract_html_title_and_body(path: Path):
    text = path.read_text(encoding="utf-8")
    title_match = re.search(r"<h1[^>]*>(.*?)</h1>", text, flags=re.I | re.S)
    if not title_match:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", text, flags=re.I | re.S)
    title = html_to_text(title_match.group(1)).strip() if title_match else None
    body_match = re.search(r"<body[^>]*>(.*)</body>", text, flags=re.I | re.S)
    body_html = body_match.group(1) if body_match else text
    return title, html_to_text(body_html)


def normalize_title_candidate(title: str | None) -> str | None:
    if not title:
        return None
    cleaned = " ".join(title.split()).strip()
    if not cleaned:
        return None

    generic_titles = {
        "微信公众号文章",
        "文章",
        "Article",
        "Wechat Article",
        "WeChat Article",
    }
    if cleaned in generic_titles:
        return None
    return cleaned


def resolve_title_fallback(path: Path):
    parent = path.parent
    candidates = [
        parent / "article.md",
        parent / "article-preview.md",
        parent / "article-xhs.md",
        parent / "xhs.md",
        parent / "article-toutiao.md",
        parent / "article-api.html",
        parent / "article-wechat.html",
        parent / "article.html",
    ]
    seen = set()
    for candidate in candidates:
        if candidate in seen or not candidate.exists() or candidate == path:
            continue
        seen.add(candidate)
        try:
            if candidate.suffix.lower() == ".md":
                title, _ = extract_markdown_title_and_body(candidate)
            elif candidate.suffix.lower() in {".html", ".htm"}:
                title, _ = extract_html_title_and_body(candidate)
            else:
                continue
        except Exception:
            continue

        normalized = normalize_title_candidate(title)
        if normalized:
            return normalized

    stem = path.stem.replace("-", " ").replace("_", " ").strip()
    return stem or None


def markdown_to_social_text(path: Path):
    _, body = extract_markdown_title_and_body(path)
    body = re.sub(r"^\[![^\]]+\](?:\s+\[![^\]]+\])*\s*$", "", body, flags=re.M)
    body = re.sub(r"^:::\s*\w*\s*$", "", body, flags=re.M)
    body = re.sub(r"^!\[[^\]]*\]\([^)]+\)\s*$", "", body, flags=re.M)
    body = re.sub(r"^#{1,6}\s*", "", body, flags=re.M)
    body = re.sub(r"^-\s+", "• ", body, flags=re.M)
    body = re.sub(r"^\d+\.\s+", lambda m: m.group(0), body, flags=re.M)
    body = re.sub(r"```[\s\S]*?```", "", body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def first_paragraph(text: str, max_len: int = 120):
    for chunk in re.split(r"\n\s*\n", text):
        cleaned = " ".join(chunk.split()).strip()
        if cleaned:
            return cleaned[:max_len]
    return ""


def choose_first_existing(base: Path, names: list[str]):
    for name in names:
        candidate = base / name
        if candidate.exists():
            return candidate
    return None


def collect_images(base: Path):
    images = []
    for dirname in ("images", "imgs"):
        folder = base / dirname
        if folder.exists():
            for path in sorted(folder.iterdir()):
                if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
                    images.append(path)
    return images


def infer_cover(base: Path):
    preferred = [
        "images/01-cover.png",
        "images/01-cover.jpg",
        "images/01-cover.jpeg",
        "images/cover.png",
        "images/cover.jpg",
        "images/cover-wide.png",
        "images/cover-wide.jpg",
        "imgs/cover.png",
        "imgs/cover.jpg",
        "cover.png",
        "cover.jpg",
    ]
    for rel in preferred:
        candidate = base / rel
        if candidate.exists():
            return candidate
    images = collect_images(base)
    return images[0] if images else None


def resolve_platform_source(source: Path, platform: str):
    if source.is_file():
        return source

    candidates = {
        "xhs": ["article-xhs.md", "xhs.md", "article-toutiao.md", "article.md", "article.html"],
        "toutiao": ["article-toutiao.md", "article.md", "article.html"],
    }
    if platform not in candidates:
        raise ValueError(f"Platform source resolution is not handled here: {platform}")
    resolved = choose_first_existing(source, candidates[platform])
    if not resolved:
        raise FileNotFoundError(f"No {platform} source found under {source}")
    return resolved


def resolve_title_and_content(path: Path):
    if path.suffix.lower() == ".md":
        title, _ = extract_markdown_title_and_body(path)
        body = markdown_to_social_text(path)
    elif path.suffix.lower() in {".html", ".htm"}:
        title, body = extract_html_title_and_body(path)
    else:
        body = path.read_text(encoding="utf-8").strip()
        title = None
    normalized = normalize_title_candidate(title)
    if not normalized:
        normalized = resolve_title_fallback(path)
    return normalized, body


def run_cmd(cmd: list[str], dry_run: bool = False):
    printable = " ".join(json.dumps(part) if " " in part else part for part in cmd)
    if dry_run:
        return {"ok": True, "cmd": printable, "stdout": "", "stderr": "", "returncode": 0}
    result = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "ok": result.returncode == 0,
        "cmd": printable,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def ensure_dependency(path: Path, label: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")
    return path


def publish_wechat(source_input: Path, title: str | None, summary: str | None, author: str | None, cover: Path | None, dry_run: bool):
    cmd = ["bun", str(ensure_dependency(WECHAT_PUBLISH, "wechat-publisher entry")), str(source_input)]
    if title:
        cmd += ["--title", title]
    if summary:
        cmd += ["--summary", summary]
    if author:
        cmd += ["--author", author]
    if cover:
        cmd += ["--cover", str(cover)]
    if dry_run:
        cmd.append("--dry-run")
    return run_cmd(cmd, dry_run=dry_run)


def publish_xhs(source_file: Path, title: str, content: str, base_dir: Path, mode: str, template: str | None, account: str | None, dry_run: bool):
    images = collect_images(base_dir)
    with tempfile.TemporaryDirectory(prefix="xhs-publish-") as temp_dir:
        title_file = Path(temp_dir) / "title.txt"
        content_file = Path(temp_dir) / "content.txt"
        title_file.write_text(title, encoding="utf-8")
        content_file.write_text(content, encoding="utf-8")

        if mode == "image-text":
            if not images:
                raise RuntimeError("Xiaohongshu image-text mode requires at least one image")
            cmd = [sys.executable, str(ensure_dependency(XHS_PIPELINE, "post-to-xhs image-text pipeline")), "--mode", "image-text", "--title-file", str(title_file), "--content-file", str(content_file), "--auto-publish", "--images", *[str(p) for p in images[:9]]]
            if account:
                cmd += ["--account", account]
            return run_cmd(cmd, dry_run=dry_run)

        long_cmd = [sys.executable, str(ensure_dependency(XHS_CDP, "post-to-xhs CDP publisher"))]
        if account:
            long_cmd += ["--account", account]
        long_cmd += ["long-article", "--title-file", str(title_file), "--content-file", str(content_file)]
        if images:
            long_cmd += ["--images", *[str(p) for p in images[:9]]]

        if dry_run:
            return {"ok": True, "cmd": "long-article workflow", "stdout": "", "stderr": "", "returncode": 0}

        step1 = run_cmd(long_cmd)
        if not step1["ok"]:
            return step1

        match = re.search(r"TEMPLATES:\s*(\[.*\])", step1["stdout"])
        templates = json.loads(match.group(1)) if match else []
        chosen = template or (templates[0] if templates else None)
        if not chosen:
            return {**step1, "ok": False, "stderr": "No Xiaohongshu template available"}

        select_cmd = [sys.executable, str(XHS_CDP)]
        if account:
            select_cmd += ["--account", account]
        select_cmd += ["select-template", "--name", chosen]
        step2 = run_cmd(select_cmd)
        if not step2["ok"]:
            return step2

        next_cmd = [sys.executable, str(XHS_CDP)]
        if account:
            next_cmd += ["--account", account]
        next_cmd += ["click-next-step", "--content-file", str(content_file)]
        step3 = run_cmd(next_cmd)
        if not step3["ok"]:
            return step3

        publish_cmd = [sys.executable, str(XHS_CDP)]
        if account:
            publish_cmd += ["--account", account]
        publish_cmd += ["click-publish"]
        step4 = run_cmd(publish_cmd)
        step4["stdout"] = "\n".join([step1["stdout"], step2["stdout"], step3["stdout"], step4["stdout"]]).strip()
        step4["chosen_template"] = chosen
        return step4


def publish_toutiao(source_file: Path, title: str, cover: Path | None, dry_run: bool):
    toutiao_python = ensure_dependency(TOUTIAO_VENV_PY, "toutiao-publisher Python runtime")
    toutiao_runner = ensure_dependency(TOUTIAO_RUNNER, "toutiao-publisher entry")
    cmd = [str(toutiao_python), str(toutiao_runner), "api_publisher.py", "--title", title, "--content", str(source_file)]
    if cover:
        cmd += ["--cover", str(cover)]
    if dry_run:
        cmd.append("--dry-run")
    return run_cmd(cmd, dry_run=dry_run)


def main():
    parser = argparse.ArgumentParser(description="Publish one article to WeChat, Xiaohongshu, and Toutiao")
    parser.add_argument("source", help="Article file or package directory")
    parser.add_argument("--platforms", help="Comma-separated platforms: wechat,xhs,toutiao")
    parser.add_argument("--title", help="Override title for all platforms")
    parser.add_argument("--wechat-author", help="Override WeChat author")
    parser.add_argument("--wechat-summary", help="Override WeChat summary")
    parser.add_argument("--wechat-cover", help="Override WeChat cover path")
    parser.add_argument("--xhs-mode", choices=["auto", "image-text", "long-article"], help="Xiaohongshu publish mode")
    parser.add_argument("--xhs-template", help="Xiaohongshu long-article template name")
    parser.add_argument("--xhs-account", help="Xiaohongshu account name")
    parser.add_argument("--toutiao-cover", help="Override Toutiao cover path")
    parser.add_argument("--dry-run", action="store_true", help="Resolve inputs and commands without publishing")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    if not source.exists():
        print(f"❌ Source not found: {source}")
        sys.exit(1)

    extend_path, extend = load_extend_settings()
    if extend_path:
        print(f"⚙️ Loaded preferences from: {extend_path}")

    platforms = parse_platforms(args.platforms, extend.get("default_platforms"))
    xhs_mode = args.xhs_mode or extend.get("default_xhs_mode", "auto")
    xhs_template = args.xhs_template or extend.get("default_xhs_template")
    xhs_account = args.xhs_account or extend.get("default_xhs_account")

    base_dir = source if source.is_dir() else source.parent
    auto_cover = infer_cover(base_dir)

    results = {}
    overall_ok = True

    for platform in platforms:
        try:
            if platform == "wechat":
                title = args.title or None
                summary = args.wechat_summary or None
                author = args.wechat_author or extend.get("default_wechat_author")
                cover = Path(args.wechat_cover).expanduser() if args.wechat_cover else auto_cover
                result = publish_wechat(source, title, summary, author, cover, args.dry_run)
            elif platform == "xhs":
                platform_source = resolve_platform_source(source, platform)
                detected_title, content = resolve_title_and_content(platform_source)
                title = args.title or detected_title
                if not title:
                    raise RuntimeError(f"Could not resolve title for {platform}")
                resolved_mode = xhs_mode
                if resolved_mode == "auto":
                    resolved_mode = "long-article" if xhs_template else "image-text"
                result = publish_xhs(platform_source, title, content, base_dir, resolved_mode, xhs_template, xhs_account, args.dry_run)
            elif platform == "toutiao":
                platform_source = resolve_platform_source(source, platform)
                detected_title, content = resolve_title_and_content(platform_source)
                title = args.title or detected_title
                if not title:
                    raise RuntimeError(f"Could not resolve title for {platform}")
                cover = Path(args.toutiao_cover).expanduser() if args.toutiao_cover else auto_cover
                result = publish_toutiao(platform_source, title, cover, args.dry_run)
            else:
                raise RuntimeError(f"Unsupported platform: {platform}")

            results[platform] = result
            overall_ok = overall_ok and result.get("ok", False)
        except Exception as exc:
            results[platform] = {"ok": False, "error": str(exc)}
            overall_ok = False

    print(json.dumps(results, ensure_ascii=False, indent=2))
    if not overall_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
