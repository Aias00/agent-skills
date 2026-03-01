#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_CHANNELS = ["x", "linkedin", "reddit", "telegram", "weibo", "xiaohongshu"]
SUPPORTED_CHANNELS = set(DEFAULT_CHANNELS)
LANG_OPTIONS = {"zh", "en", "bilingual"}

CHANNEL_SPECS = {
    "x": {"display": "X", "limit": 280},
    "linkedin": {"display": "LinkedIn", "limit": 1200},
    "reddit": {"display": "Reddit", "limit": 2200},
    "telegram": {"display": "Telegram", "limit": 900},
    "weibo": {"display": "Weibo", "limit": 300},
    "xiaohongshu": {"display": "Xiaohongshu", "limit": 900},
}

PERMISSION_HINTS_EN = {
    "storage": "Save settings locally for fast repeated workflows",
    "downloads": "Export processed results with one click",
    "activeTab": "Work on the current tab after explicit user action",
    "scripting": "Inject tools on supported pages when needed",
    "tabs": "Read tab context to streamline actions",
}


@dataclass
class ListingInfo:
    short_zh: str
    short_en: str
    features_zh: list[str]
    features_en: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate platform-specific social promotion copy for a Chrome extension "
            "from manifest + release listing artifacts."
        )
    )
    parser.add_argument("--root", default=".", help="Extension root directory (default: current directory)")
    parser.add_argument("--manifest", default="manifest.json", help="Manifest path relative to --root")
    parser.add_argument(
        "--listing",
        default="release/cws-listing.zh-en.md",
        help="Bilingual listing draft path relative to --root (optional)",
    )
    parser.add_argument(
        "--out",
        default="release/social-promo.md",
        help="Output markdown path relative to --root (default: release/social-promo.md)",
    )
    parser.add_argument(
        "--lang",
        choices=sorted(LANG_OPTIONS),
        default="bilingual",
        help="Output language mode (default: bilingual)",
    )
    parser.add_argument(
        "--channels",
        nargs="*",
        default=DEFAULT_CHANNELS,
        help="Target channels (default: x linkedin reddit telegram weibo xiaohongshu)",
    )
    parser.add_argument(
        "--campaign",
        choices=["launch", "update", "feature"],
        default="launch",
        help="Campaign type (default: launch)",
    )
    parser.add_argument(
        "--tone",
        choices=["practical", "builder", "casual"],
        default="practical",
        help="Copy tone style (default: practical)",
    )
    parser.add_argument("--store-url", default="", help="Chrome Web Store URL")
    parser.add_argument("--website-url", default="", help="Landing page or repo URL")
    parser.add_argument("--hashtags", nargs="*", default=[], help="Extra hashtags")
    parser.add_argument("--max-features", type=int, default=4, help="Max feature bullets per language (default: 4)")
    parser.add_argument("--variants", type=int, default=2, help="Variants per channel/language (default: 2)")
    return parser.parse_args()


def clamp(text: str, limit: int) -> str:
    token = text.strip()
    if len(token) <= limit:
        return token
    trimmed = token[: max(0, limit - 1)].rstrip()
    return f"{trimmed}..."


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def contains_cjk(text: str) -> bool:
    for ch in text or "":
        code = ord(ch)
        if 0x3400 <= code <= 0x4DBF:
            return True
        if 0x4E00 <= code <= 0x9FFF:
            return True
        if 0xF900 <= code <= 0xFAFF:
            return True
    return False


def read_manifest(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid manifest JSON: {exc}") from exc


def extract_section(text: str, section_heading: str, marker: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    section_start = -1
    for idx, line in enumerate(lines):
        if line.strip().lower().startswith(f"## {section_heading.lower()}"):
            section_start = idx
            break
    if section_start < 0:
        return ""

    section_end = len(lines)
    for idx in range(section_start + 1, len(lines)):
        if lines[idx].strip().startswith("## "):
            section_end = idx
            break

    chunk = lines[section_start + 1 : section_end]
    marker_start = -1
    for idx, line in enumerate(chunk):
        if line.strip() == marker:
            marker_start = idx
            break
    if marker_start < 0:
        return ""

    marker_end = len(chunk)
    for idx in range(marker_start + 1, len(chunk)):
        if chunk[idx].strip().startswith("### "):
            marker_end = idx
            break
    return "\n".join(chunk[marker_start + 1 : marker_end]).strip()


def extract_feature_lines(block: str) -> list[str]:
    features: list[str] = []
    for raw in block.splitlines():
        line = raw.strip()
        if not line:
            continue
        match = re.match(r"^\d+\.\s+(.*)$", line)
        if match:
            features.append(clean_text(match.group(1)))
    return features


def parse_listing(path: Path) -> ListingInfo:
    if not path.is_file():
        return ListingInfo("", "", [], [])

    text = path.read_text(encoding="utf-8", errors="ignore")
    short_zh = clean_text(extract_section(text, "1) Store Short Summary", "### ZH"))
    short_en = clean_text(extract_section(text, "1) Store Short Summary", "### EN"))

    long_zh = extract_section(text, "2) Listing Description (Long)", "### ZH")
    long_en = extract_section(text, "2) Listing Description (Long)", "### EN")
    features_zh = extract_feature_lines(long_zh)
    features_en = extract_feature_lines(long_en)
    return ListingInfo(short_zh, short_en, features_zh, features_en)


def split_desc_features(description: str) -> list[str]:
    tokens = re.split(r"[;；。.!?]\s*", description)
    return [clean_text(token) for token in tokens if clean_text(token)]


def normalize_hashtags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        token = tag.strip()
        if not token:
            continue
        if not token.startswith("#"):
            token = f"#{token}"
        key = token.lower()
        if key in seen:
            continue
        normalized.append(token)
        seen.add(key)
    return normalized


def pick_features(preferred: list[str], fallback: list[str], max_items: int) -> list[str]:
    base = preferred if preferred else fallback
    return base[: max(1, max_items)]


def english_fallback_features(manifest: dict, max_items: int) -> list[str]:
    features: list[str] = ["Practical in-browser workflow focused on one core task"]
    permissions = manifest.get("permissions", [])
    if isinstance(permissions, list):
        for perm in permissions:
            if not isinstance(perm, str):
                continue
            hint = PERMISSION_HINTS_EN.get(perm)
            if hint and hint not in features:
                features.append(hint)
    return features[: max(1, max_items)]


def default_hashtags(name: str, lang: str) -> list[str]:
    compact = re.sub(r"[^a-zA-Z0-9]+", "", name)
    if lang == "zh":
        return ["#Chrome插件", "#效率工具", f"#{compact}" if compact else "#浏览器工具"]
    return ["#ChromeExtension", "#Productivity", f"#{compact}" if compact else "#BrowserTool"]


def campaign_label(campaign: str, lang: str) -> str:
    mapping = {
        "launch": {"zh": "新发布", "en": "New launch"},
        "update": {"zh": "版本更新", "en": "Version update"},
        "feature": {"zh": "功能更新", "en": "Feature spotlight"},
    }
    return mapping[campaign][lang]


def cta_text(store_url: str, website_url: str, lang: str) -> str:
    if store_url:
        return ("立即安装: " if lang == "zh" else "Install now: ") + store_url
    if website_url:
        return ("了解更多: " if lang == "zh" else "Learn more: ") + website_url
    return "安装链接: <填入商店链接>" if lang == "zh" else "Install link: <add store url>"


def tone_suffix(tone: str, lang: str) -> str:
    if tone == "builder":
        return "适合开发者和重度用户。" if lang == "zh" else "Built for developers and power users."
    if tone == "casual":
        return "上手快，日常用起来很顺手。" if lang == "zh" else "Quick to use and easy for daily workflows."
    return "强调实用和可执行价值。" if lang == "zh" else "Focused on practical, actionable value."


def join_features_line(features: list[str], lang: str) -> str:
    if not features:
        return ""
    if lang == "zh":
        return "亮点: " + " / ".join(features)
    return "Highlights: " + " / ".join(features)


def build_variant(name: str, description: str, features: list[str], campaign: str, tone: str, lang: str, idx: int, links: str) -> str:
    label = campaign_label(campaign, lang)
    opening = (
        f"{label}: {name}。{description}"
        if lang == "zh"
        else f"{label}: {name}. {description}"
    )
    feature_line = join_features_line(features, lang)
    closer = tone_suffix(tone, lang)

    if idx % 2 == 0:
        parts = [opening, feature_line, closer, links]
    else:
        alt_opening = (
            f"{name} {label}，解决重复操作和效率问题。"
            if lang == "zh"
            else f"{name} {label} that reduces repetitive work and improves speed."
        )
        parts = [alt_opening, feature_line, closer, links]
    return "\n".join([part for part in parts if part.strip()])


def render_channel(
    channel: str,
    name: str,
    desc_zh: str,
    desc_en: str,
    features_zh: list[str],
    features_en: list[str],
    args: argparse.Namespace,
    hashtags_zh: list[str],
    hashtags_en: list[str],
) -> str:
    spec = CHANNEL_SPECS[channel]
    limit = spec["limit"]
    title = spec["display"]
    lines = [f"## {title}", ""]

    language_order = ["zh", "en"] if args.lang == "bilingual" else [args.lang]
    for lang in language_order:
        lines.append("### ZH" if lang == "zh" else "### EN")
        for idx in range(args.variants):
            content = build_variant(
                name=name,
                description=desc_zh if lang == "zh" else desc_en,
                features=features_zh if lang == "zh" else features_en,
                campaign=args.campaign,
                tone=args.tone,
                lang=lang,
                idx=idx,
                links=cta_text(args.store_url, args.website_url, lang),
            )

            lang_tags = hashtags_zh if lang == "zh" else hashtags_en

            if channel in {"x", "weibo"}:
                tag_text = " ".join(lang_tags[:2]) if lang_tags else ""
            elif channel == "xiaohongshu":
                tag_text = " ".join(lang_tags[:4]) if lang_tags else ""
            else:
                tag_text = " ".join(lang_tags[:5]) if lang_tags else ""

            merged = f"{content}\n{tag_text}".strip()
            if channel in {"x", "weibo"}:
                merged = clean_text(merged)
            if channel == "reddit":
                heading = (
                    f"Title: {clamp(f'{name} {campaign_label(args.campaign, lang)}', 120)}"
                    if lang == "en"
                    else f"Title: {clamp(f'{name} {campaign_label(args.campaign, lang)}', 80)}"
                )
                body = clamp(merged, limit)
                lines.append(f"Variant {idx + 1}")
                lines.append(heading)
                lines.append("Body:")
                lines.append(body)
            else:
                lines.append(f"Variant {idx + 1}")
                lines.append(clamp(merged, limit))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_output(
    args: argparse.Namespace,
    manifest: dict,
    listing: ListingInfo,
    channels: list[str],
    hashtags_zh: list[str],
    hashtags_en: list[str],
) -> str:
    name = clean_text(str(manifest.get("name", "Chrome Extension"))) or "Chrome Extension"
    version = clean_text(str(manifest.get("version", "")))
    raw_desc = clean_text(str(manifest.get("description", "")))

    fallback_features = split_desc_features(raw_desc)
    features_zh = pick_features(listing.features_zh, fallback_features, args.max_features)

    clean_features_en = [item for item in listing.features_en if item and not contains_cjk(item)]
    if clean_features_en:
        features_en = pick_features(clean_features_en, [], args.max_features)
    else:
        features_en = english_fallback_features(manifest, args.max_features)

    desc_zh = listing.short_zh or raw_desc or "高效完成核心任务的浏览器工具。"

    if listing.short_en and not contains_cjk(listing.short_en):
        desc_en = listing.short_en
    else:
        desc_en = f"{name} helps users complete the core task directly in the browser."

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    lines: list[str] = [
        "# Social Promotion Kit",
        "",
        f"Generated at: `{generated_at}`",
        "",
        "## Campaign Brief",
        "",
        f"- Product: `{name}`",
        f"- Version: `{version}`" if version else "- Version: `<unset>`",
        f"- Campaign: `{args.campaign}`",
        f"- Tone: `{args.tone}`",
        f"- Store URL: `{args.store_url}`" if args.store_url else "- Store URL: `<add-link>`",
        f"- Website URL: `{args.website_url}`" if args.website_url else "- Website URL: `<optional>`",
        "",
        "## Message Pillars",
        "",
    ]

    if args.lang in {"zh", "bilingual"}:
        lines.extend(["### ZH", *(f"- {item}" for item in features_zh), ""])
    if args.lang in {"en", "bilingual"}:
        lines.extend(["### EN", *(f"- {item}" for item in features_en), ""])

    lines.extend(["## Hashtags", ""])
    if args.lang in {"zh", "bilingual"}:
        lines.append(f"- ZH: {' '.join(hashtags_zh) if hashtags_zh else '<add-zh-hashtags>'}")
    if args.lang in {"en", "bilingual"}:
        lines.append(f"- EN: {' '.join(hashtags_en) if hashtags_en else '<add-en-hashtags>'}")
    lines.append("")

    for channel in channels:
        lines.append(
            render_channel(
                channel,
                name,
                desc_zh,
                desc_en,
                features_zh,
                features_en,
                args,
                hashtags_zh,
                hashtags_en,
            )
        )

    lines.extend(
        [
            "## Publishing Checklist",
            "",
            "- Verify claims align with real extension behavior.",
            "- Keep one clear CTA link per channel post.",
            "- Replace placeholders before publishing.",
            "- Keep bilingual meaning consistent (ZH/EN).",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"[ERROR] root is not a directory: {root}", file=sys.stderr)
        return 1

    manifest_path = (root / args.manifest).resolve()
    listing_path = (root / args.listing).resolve()
    out_path = (root / args.out).resolve()

    if not manifest_path.is_file():
        print(f"[ERROR] manifest not found: {manifest_path}", file=sys.stderr)
        return 1
    if args.max_features < 1:
        print("[ERROR] --max-features must be >= 1", file=sys.stderr)
        return 1
    if args.variants < 1:
        print("[ERROR] --variants must be >= 1", file=sys.stderr)
        return 1

    channels: list[str] = []
    for channel in args.channels:
        token = channel.strip().lower()
        if not token:
            continue
        if token not in SUPPORTED_CHANNELS:
            print(
                f"[ERROR] unsupported channel: {token}. "
                f"Supported: {', '.join(sorted(SUPPORTED_CHANNELS))}",
                file=sys.stderr,
            )
            return 1
        if token not in channels:
            channels.append(token)
    if not channels:
        channels = list(DEFAULT_CHANNELS)

    try:
        manifest = read_manifest(manifest_path)
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    listing = parse_listing(listing_path)
    user_tags = normalize_hashtags(args.hashtags)
    default_zh = default_hashtags(str(manifest.get("name", "")), "zh")
    default_en = default_hashtags(str(manifest.get("name", "")), "en")

    if args.lang == "zh":
        hashtags_zh = user_tags or default_zh
        hashtags_en = []
    elif args.lang == "en":
        hashtags_zh = []
        hashtags_en = user_tags or default_en
    else:
        if user_tags:
            hashtags_zh = user_tags
            hashtags_en = user_tags
        else:
            hashtags_zh = default_zh
            hashtags_en = default_en

    output = build_output(args, manifest, listing, channels, hashtags_zh, hashtags_en)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(output, encoding="utf-8")
    print(f"[OK] social promo generated: {out_path}")
    print(f"[OK] channels: {', '.join(channels)}")
    print(f"[OK] language mode: {args.lang}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
