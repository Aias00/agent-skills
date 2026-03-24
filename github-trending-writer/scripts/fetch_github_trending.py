#!/usr/bin/env python3
"""
Fetch GitHub Trending repositories, read repo pages via url-reader,
and save review-friendly local packages.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

GITHUB_BASE = "https://github.com"
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
URL_READER_PATH = REPO_ROOT / "url-reader" / "scripts" / "url_reader.py"
DEFAULT_LIMIT = 4
BAD_CONTENT_PATTERNS = [
    "Page not found",
    "Not Found",
    "There isn’t anything here",
]


def load_url_reader() -> Any:
    if not URL_READER_PATH.exists():
        raise FileNotFoundError(f"url-reader script not found: {URL_READER_PATH}")
    spec = importlib.util.spec_from_file_location("github_trending_url_reader", URL_READER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load url-reader module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def default_output_dir() -> Path:
    date_part = datetime.now().strftime("%Y-%m-%d")
    return Path.cwd() / "tmp" / "github-trending-review" / date_part / "curated"


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text[:60] or "github-trending-item"


def parse_number(text: str | None) -> int:
    if not text:
        return 0
    cleaned = text.replace(",", "").strip().lower()
    multiplier = 1
    if cleaned.endswith("k"):
        multiplier = 1000
        cleaned = cleaned[:-1]
    elif cleaned.endswith("m"):
        multiplier = 1_000_000
        cleaned = cleaned[:-1]
    try:
        return int(float(cleaned) * multiplier)
    except Exception:
        return 0


def fetch_trending(language: str | None, since: str) -> list[dict[str, Any]]:
    path = "/trending"
    if language:
        path += f"/{language}"
    response = requests.get(
        f"{GITHUB_BASE}{path}",
        params={"since": since},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    items: list[dict[str, Any]] = []
    for index, article in enumerate(soup.select("article.Box-row"), start=1):
        repo_link = article.select_one("h2 a")
        if not repo_link:
            continue
        href = repo_link.get("href", "").strip()
        if not href or href.count("/") < 2:
            continue
        repo_path = href.strip("/")
        repo_url = f"{GITHUB_BASE}/{repo_path}"
        title = " / ".join(part.strip() for part in repo_path.split("/")[:2])
        description = article.select_one("p")
        language_tag = article.select_one('[itemprop="programmingLanguage"]')
        stat_links = article.select('a.Link--muted')
        total_stars = parse_number(stat_links[0].get_text(" ", strip=True) if len(stat_links) > 0 else "")
        forks = parse_number(stat_links[1].get_text(" ", strip=True) if len(stat_links) > 1 else "")

        today_stars = 0
        today_stars_label = ""
        today_span = article.select_one("span.d-inline-block.float-sm-right")
        if today_span:
            today_stars_label = today_span.get_text(" ", strip=True)
            today_stars = parse_number(today_stars_label.split()[0])

        items.append(
            {
                "index": index,
                "title": title,
                "repo_path": repo_path,
                "source_url": repo_url,
                "description": description.get_text(" ", strip=True) if description else "",
                "language": language_tag.get_text(" ", strip=True) if language_tag else "",
                "total_stars": total_stars,
                "forks": forks,
                "today_stars": today_stars,
                "today_stars_label": today_stars_label,
                "since": since,
                "trending_language": language or "",
            }
        )
    return items


def looks_bad_content(content: str) -> bool:
    stripped = content.strip()
    if not stripped:
        return True
    return any(pattern in content for pattern in BAD_CONTENT_PATTERNS)


def strip_reader_wrapper(content: str) -> str:
    marker = "\nMarkdown Content:\n"
    index = content.find(marker)
    if index != -1:
        return content[index + len(marker) :].lstrip()
    return content


def save_candidate_package(base_dir: Path, item: dict[str, Any], read_result: dict[str, Any], url_reader: Any) -> dict[str, Any]:
    folder = base_dir / f"{item['index']:02d}-{slugify(item['repo_path'])}"
    folder.mkdir(parents=True, exist_ok=True)

    raw_content = read_result.get("content", "")
    cleaned_content = strip_reader_wrapper(raw_content)
    images = url_reader.extract_images_from_content(cleaned_content)[:9]
    image_map: dict[str, str] = {}
    for idx, img_url in enumerate(images, 1):
        local_name = url_reader.download_image(img_url, folder, idx)
        if local_name:
            image_map[img_url] = local_name

    localized_content = cleaned_content
    for original, local_name in image_map.items():
        localized_content = localized_content.replace(original, local_name)

    meta = {
        **item,
        "strategy": read_result.get("strategy", "unknown"),
        "platform": (read_result.get("platform") or {}).get("name", "未知"),
        "images": len(image_map),
    }

    def yaml_quote(value: Any) -> str:
        if isinstance(value, str):
            return json.dumps(value, ensure_ascii=False)
        if value is None:
            return "null"
        return str(value)

    frontmatter_lines = [
        "---",
        f"title: {yaml_quote(meta['title'])}",
        f"repo_path: {yaml_quote(meta['repo_path'])}",
        f"source_url: {yaml_quote(meta['source_url'])}",
        f"description: {yaml_quote(meta['description'])}",
        f"language: {yaml_quote(meta['language'])}",
        f"total_stars: {meta['total_stars']}",
        f"forks: {meta['forks']}",
        f"today_stars: {meta['today_stars']}",
        f"since: {yaml_quote(meta['since'])}",
        f"trending_language: {yaml_quote(meta['trending_language'])}",
        f"strategy: {yaml_quote(meta['strategy'])}",
        f"platform: {yaml_quote(meta['platform'])}",
        f"images: {meta['images']}",
        "---",
        "",
    ]

    preface = [
        f"# {meta['title']}",
        "",
        f"**仓库链接**：{meta['source_url']}",
        "",
        f"**Trending 周期**：{meta['since']}",
        "",
        f"**语言**：{meta['language'] or '未知'}",
        "",
        f"**总 Stars**：{meta['total_stars']}",
        "",
        f"**新增 Stars**：{meta['today_stars_label'] or meta['today_stars']}",
        "",
        f"**Forks**：{meta['forks']}",
        "",
    ]
    if meta["description"]:
        preface += [f"**简介**：{meta['description']}", "",]
    preface += [f"**读取策略**：{meta['strategy']}", "", "---", "",]

    (folder / "content.md").write_text("\n".join(frontmatter_lines + preface) + localized_content, encoding="utf-8")
    (folder / "raw.md").write_text(raw_content, encoding="utf-8")
    (folder / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        **meta,
        "dir": str(folder),
        "content_md": str(folder / "content.md"),
    }


def write_index(output_dir: Path, manifest: list[dict[str, Any]], language: str | None, since: str) -> None:
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# GitHub Trending 候选清单", "", f"**周期**：{since}", ""]
    if language:
        lines += [f"**语言**：{language}", ""]
    for item in manifest:
        lines.append(f"## {item['index']}. {item['title']}")
        if item.get("description"):
            lines.append(f"- 简介：{item['description']}")
        lines.append(f"- 仓库：{item['source_url']}")
        lines.append(f"- 语言：{item['language'] or '未知'}")
        lines.append(f"- 总 Stars：{item['total_stars']}")
        lines.append(f"- 新增：{item['today_stars_label'] or item['today_stars']}")
        lines.append(f"- 本地目录：{item['dir']}")
        lines.append(f"- 读取策略：{item['strategy']}")
        lines.append("")
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch GitHub Trending repositories and save them locally.")
    parser.add_argument("--language", help="Programming language filter, e.g. python, typescript, rust.")
    parser.add_argument("--since", choices=["daily", "weekly", "monthly"], default="daily", help="Trending period.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="How many good candidates to save.")
    parser.add_argument("--output-dir", default=str(default_output_dir()), help="Where to store candidate packages.")
    parser.add_argument("--list-only", action="store_true", help="Only print filtered candidates without saving content.")
    args = parser.parse_args()

    candidates = fetch_trending(args.language, args.since)[: args.limit]

    if args.list_only:
        print(json.dumps(candidates, ensure_ascii=False, indent=2))
        return

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    url_reader = load_url_reader()
    manifest: list[dict[str, Any]] = []
    for item in candidates:
        result = url_reader.read_url(item["source_url"], verbose=False)
        if not result.get("success"):
            continue
        content = result.get("content", "")
        if not content or looks_bad_content(content):
            continue
        manifest.append(save_candidate_package(output_dir, item, result, url_reader))

    write_index(output_dir, manifest, args.language, args.since)
    payload = {"output_dir": str(output_dir), "count": len(manifest), "items": manifest}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if manifest:
        print("\n候选编号：")
        for item in manifest:
            print(f"{item['index']}. {item['title']}")


if __name__ == "__main__":
    main()
