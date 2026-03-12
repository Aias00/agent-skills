#!/usr/bin/env python3
"""
Repo-local source fetchers for ai-hotspot-collector.

This module replaces the old dependency on ~/.codex source skills with
self-contained fetchers that save a consistent candidate layout:

<source-output>/
  manifest.json
  01-<slug>/
    content.md
    meta.json
    raw.html
    img_01.jpg
"""

from __future__ import annotations

import json
import mimetypes
import re
from datetime import datetime
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

import requests

USER_AGENT = "Mozilla/5.0 (compatible; ai-hotspot-collector/1.0)"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
AI_KEYWORDS = {
    "ai",
    "artificial intelligence",
    "agent",
    "agents",
    "openai",
    "anthropic",
    "claude",
    "gemini",
    "gpt",
    "copilot",
    "llm",
    "llms",
    "multimodal",
    "reasoning",
    "inference",
    "chatgpt",
    "xai",
    "grok",
    "perplexity",
    "open source ai",
}

RSS_NAMESPACES = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "media": "http://search.yahoo.com/mrss/",
    "atom": "http://www.w3.org/2005/Atom",
}

SOURCE_LABELS = {
    "techcrunch": "TechCrunch",
    "the-verge": "The Verge",
    "hn": "Hacker News",
    "github-trending": "GitHub Trending",
    "engadget": "Engadget",
    "fast-company": "Fast Company",
}


def slugify(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fa5._-]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "item"


def html_to_text(value: str) -> str:
    text = unescape(value or "")
    text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", text, flags=re.S)
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</(p|div|li|section|article|h1|h2|h3)>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def contains_ai(text: str) -> bool:
    normalized = (text or "").lower()
    return any(keyword in normalized for keyword in AI_KEYWORDS)


def safe_get(url: str, timeout: int = 25) -> requests.Response:
    response = requests.get(
        url,
        timeout=timeout,
        headers={
            "user-agent": USER_AGENT,
            "accept": "application/json, text/html, application/xml, text/xml;q=0.9, */*;q=0.8",
        },
    )
    response.raise_for_status()
    return response


def fetch_text(url: str, timeout: int = 25) -> str:
    response = safe_get(url, timeout=timeout)
    response.encoding = response.encoding or "utf-8"
    return response.text


def fetch_json(url: str, timeout: int = 25) -> dict:
    return safe_get(url, timeout=timeout).json()


def extract_image_from_html(html: str, base_url: str = "") -> str:
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<img[^>]+src=["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.I)
        if match:
            return urljoin(base_url, match.group(1).strip())
    return ""


def fetch_article_snapshot(url: str) -> dict:
    if not url:
        return {"preview": "", "image": "", "raw_html": ""}
    try:
        html = fetch_text(url, timeout=30)
    except Exception:
        return {"preview": "", "image": "", "raw_html": ""}

    preview = ""
    candidates = []
    meta_desc = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html, flags=re.I)
    if meta_desc:
        candidates.append(meta_desc.group(1))
    og_desc = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']', html, flags=re.I)
    if og_desc:
        candidates.append(og_desc.group(1))
    paragraphs = re.findall(r"<p\b[^>]*>(.*?)</p>", html, flags=re.I | re.S)
    for paragraph in paragraphs[:4]:
        candidates.append(paragraph)

    for candidate in candidates:
        text = html_to_text(candidate)
        if len(text) >= 60:
            preview = text[:600]
            break

    return {
        "preview": preview,
        "image": extract_image_from_html(html, base_url=url),
        "raw_html": html,
    }


def parse_feed_items(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    tag = root.tag.lower()
    if tag.endswith("rss"):
        channel = root.find("channel")
        items = channel.findall("item") if channel is not None else []
        parsed = []
        for item in items:
            title = item.findtext("title", default="")
            link = item.findtext("link", default="")
            description = item.findtext("description", default="")
            content = item.findtext(f"{{{RSS_NAMESPACES['content']}}}encoded", default="")
            author = item.findtext(f"{{{RSS_NAMESPACES['dc']}}}creator", default="") or item.findtext("author", default="")
            published = item.findtext("pubDate", default="")
            media = item.find(f"{{{RSS_NAMESPACES['media']}}}content")
            image = media.get("url", "") if media is not None else ""
            if not image:
                enclosure = item.find("enclosure")
                image = enclosure.get("url", "") if enclosure is not None else ""
            if not image:
                image = extract_image_from_html(description or content, base_url=link)
            parsed.append(
                {
                    "title": html_to_text(title),
                    "url": link.strip(),
                    "description": html_to_text(content or description),
                    "author": html_to_text(author),
                    "published_time": html_to_text(published),
                    "image_url": image,
                }
            )
        return parsed

    if tag.endswith("feed"):
        parsed = []
        entries = root.findall(f"{{{RSS_NAMESPACES['atom']}}}entry")
        for entry in entries:
            title = entry.findtext(f"{{{RSS_NAMESPACES['atom']}}}title", default="")
            summary = entry.findtext(f"{{{RSS_NAMESPACES['atom']}}}summary", default="")
            content = entry.findtext(f"{{{RSS_NAMESPACES['atom']}}}content", default="")
            author_node = entry.find(f"{{{RSS_NAMESPACES['atom']}}}author")
            author = ""
            if author_node is not None:
                author = author_node.findtext(f"{{{RSS_NAMESPACES['atom']}}}name", default="")
            published = entry.findtext(f"{{{RSS_NAMESPACES['atom']}}}published", default="") or entry.findtext(
                f"{{{RSS_NAMESPACES['atom']}}}updated", default=""
            )
            link = ""
            for link_node in entry.findall(f"{{{RSS_NAMESPACES['atom']}}}link"):
                href = link_node.get("href", "").strip()
                rel = link_node.get("rel", "alternate")
                if href and rel == "alternate":
                    link = href
                    break
                if href and not link:
                    link = href
            image = extract_image_from_html(content or summary, base_url=link)
            parsed.append(
                {
                    "title": html_to_text(title),
                    "url": link,
                    "description": html_to_text(content or summary),
                    "author": html_to_text(author),
                    "published_time": html_to_text(published),
                    "image_url": image,
                }
            )
        return parsed

    return []


def fetch_hn_items(limit: int) -> list[dict]:
    data = fetch_json("https://hn.algolia.com/api/v1/search?tags=front_page")
    items = []
    for hit in data.get("hits", []):
        title = html_to_text(hit.get("title") or "")
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
        summary = html_to_text(hit.get("story_text") or hit.get("comment_text") or "")
        if not contains_ai(" ".join([title, url, summary])):
            continue
        snapshot = fetch_article_snapshot(url) if hit.get("url") else {"preview": "", "image": "", "raw_html": ""}
        items.append(
            {
                "title": title,
                "url": url,
                "description": summary or snapshot["preview"],
                "author": html_to_text(hit.get("author") or ""),
                "published_time": html_to_text(hit.get("created_at") or ""),
                "image_url": snapshot["image"],
                "raw_html": snapshot["raw_html"],
            }
        )
        if len(items) >= limit:
            break
    return items


def fetch_rss_source(source: str, url: str, limit: int, item_filter) -> list[dict]:
    items = []
    for item in parse_feed_items(fetch_text(url)):
        if not item_filter(item):
            continue
        if not item.get("description"):
            snapshot = fetch_article_snapshot(item["url"])
            item["description"] = snapshot["preview"]
            item["raw_html"] = snapshot["raw_html"]
            if not item.get("image_url"):
                item["image_url"] = snapshot["image"]
        items.append(item)
        if len(items) >= limit:
            break
    return items


def fetch_github_trending(limit: int) -> list[dict]:
    html = fetch_text("https://github.com/trending")
    articles = re.findall(r"<article\b[^>]*class=\"Box-row\"[\s\S]*?</article>", html, flags=re.I)
    items = []
    for article in articles:
        repo_match = re.search(r'<h2\b[^>]*>[\s\S]*?<a\b[^>]*href=\"([^\"]+)\"', article, flags=re.I)
        if not repo_match:
            continue
        repo_path = repo_match.group(1).strip()
        repo_url = urljoin("https://github.com", repo_path)
        repo_name = html_to_text(repo_path.strip("/"))
        desc_match = re.search(r'<p\b[^>]*>([\s\S]*?)</p>', article, flags=re.I)
        description = html_to_text(desc_match.group(1)) if desc_match else ""
        if not contains_ai(" ".join([repo_name, description])):
            continue
        items.append(
            {
                "title": repo_name,
                "url": repo_url,
                "description": description or "GitHub Trending AI-related repository.",
                "author": "",
                "published_time": datetime.utcnow().strftime("%Y-%m-%d"),
                "image_url": "",
                "raw_html": article,
            }
        )
        if len(items) >= limit:
            break
    return items


def source_candidates(source: str, limit: int) -> list[dict]:
    if source == "hn":
        return fetch_hn_items(limit)
    if source == "engadget":
        return fetch_rss_source(
            source,
            "https://www.engadget.com/rss.xml",
            limit,
            lambda item: "/ai/" in item.get("url", "") or contains_ai(" ".join([item["title"], item["description"]])),
        )
    if source == "fast-company":
        return fetch_rss_source(
            source,
            "https://www.fastcompany.com/section/artificial-intelligence/rss",
            limit,
            lambda item: contains_ai(" ".join([item["title"], item["description"]])),
        )
    if source == "the-verge":
        return fetch_rss_source(
            source,
            "https://www.theverge.com/rss/index.xml",
            limit,
            lambda item: "/ai" in item.get("url", "") or contains_ai(" ".join([item["title"], item["description"]])),
        )
    if source == "techcrunch":
        return fetch_rss_source(
            source,
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            limit,
            lambda item: contains_ai(" ".join([item["title"], item["description"]])),
        )
    if source == "github-trending":
        return fetch_github_trending(limit)
    raise ValueError(f"Unsupported source: {source}")


def image_extension_from_url(url: str, content_type: str = "") -> str:
    parsed = urlparse(url)
    ext = Path(parsed.path).suffix.lower()
    if ext in IMAGE_EXTS:
        return ext
    guessed = mimetypes.guess_extension((content_type or "").split(";")[0].strip()) or ".jpg"
    return guessed if guessed in IMAGE_EXTS else ".jpg"


def download_image(url: str, target_dir: Path, index: int = 1) -> str:
    if not url:
        return ""
    try:
        response = requests.get(url, timeout=30, headers={"user-agent": USER_AGENT}, stream=True)
        response.raise_for_status()
        ext = image_extension_from_url(url, response.headers.get("content-type", ""))
        file_name = f"img_{index:02d}{ext}"
        target_path = target_dir / file_name
        with target_path.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=16384):
                if chunk:
                    fh.write(chunk)
        return file_name
    except Exception:
        return ""


def build_content_markdown(item: dict, image_file: str = "") -> str:
    lines = [
        f"# {item['title']}",
        "",
        f"**来源**：{item['source_label']}",
        f"**原文链接**：{item['source_url']}",
    ]
    if item.get("author"):
        lines.append(f"**作者**：{item['author']}")
    if item.get("published_time"):
        lines.append(f"**发布时间**：{item['published_time']}")
    lines.extend(["", "## 摘要", "", item.get("description") or "暂无摘要。", ""])
    if image_file:
        lines.extend([f"![Image](./{image_file})", ""])
    return "\n".join(lines).strip() + "\n"


def save_source_candidates(source: str, limit: int, output_dir: Path) -> list[dict]:
    label = SOURCE_LABELS[source]
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates = source_candidates(source, limit)
    manifest = []
    for idx, candidate in enumerate(candidates, start=1):
        slug = slugify(candidate["title"])[:80]
        candidate_dir = output_dir / f"{idx:02d}-{slug}"
        candidate_dir.mkdir(parents=True, exist_ok=True)

        image_file = download_image(candidate.get("image_url", ""), candidate_dir) if candidate.get("image_url") else ""
        raw_html = candidate.get("raw_html") or ""
        if raw_html:
            (candidate_dir / "raw.html").write_text(raw_html, encoding="utf-8")

        item = {
            "index": idx,
            "source": source,
            "source_label": label,
            "title": candidate["title"],
            "source_url": candidate["url"],
            "author": candidate.get("author", ""),
            "published_time": candidate.get("published_time", ""),
            "description": candidate.get("description", ""),
            "dir": str(candidate_dir),
            "content_md": str(candidate_dir / "content.md"),
            "image": image_file,
        }

        (candidate_dir / "content.md").write_text(build_content_markdown(item, image_file=image_file), encoding="utf-8")
        (candidate_dir / "meta.json").write_text(json.dumps(item, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest.append(item)

    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest
