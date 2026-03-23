#!/usr/bin/env python3
"""
Publish a reviewed GitHub Trending candidate draft via article-multi-publisher.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ARTICLE_MULTI_PUBLISHER = Path("/Users/aias/.codex/skills/article-multi-publisher/scripts/publish.py")
DEFAULT_SOURCE_PRIORITY = [
    "article.md",
    "translation-draft.zh.md",
    "review-draft.zh.md",
]


def resolve_candidate_by_index(root: Path, index: int) -> Path:
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found under {root}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, list):
        raise RuntimeError(f"Invalid manifest format: {manifest_path}")

    for offset, item in enumerate(manifest, start=1):
        item_index = item.get("index", offset)
        if int(item_index) != index:
            continue
        candidate_dir = Path(item["dir"]).expanduser().resolve()
        if not candidate_dir.exists():
            raise FileNotFoundError(f"Candidate dir not found: {candidate_dir}")
        return candidate_dir

    raise FileNotFoundError(f"Candidate index {index} not found in {manifest_path}")


def resolve_source(base: Path, explicit_source: str | None) -> Path:
    if base.is_file():
        return base.resolve()

    if explicit_source:
        candidate = (base / explicit_source).resolve()
        if not candidate.exists():
            raise FileNotFoundError(f"Specified source file not found: {candidate}")
        return candidate

    for name in DEFAULT_SOURCE_PRIORITY:
        candidate = (base / name).resolve()
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        f"No reviewed draft found under {base}. Expected one of: {', '.join(DEFAULT_SOURCE_PRIORITY)}"
    )


def build_command(source: Path, args: argparse.Namespace) -> list[str]:
    cmd = ["python3", str(ARTICLE_MULTI_PUBLISHER), str(source)]
    if args.platforms:
        cmd += ["--platforms", args.platforms]
    if args.title:
        cmd += ["--title", args.title]
    if args.wechat_author:
        cmd += ["--wechat-author", args.wechat_author]
    if args.wechat_summary:
        cmd += ["--wechat-summary", args.wechat_summary]
    if args.wechat_cover:
        cmd += ["--wechat-cover", args.wechat_cover]
    if args.xhs_mode:
        cmd += ["--xhs-mode", args.xhs_mode]
    if args.xhs_template:
        cmd += ["--xhs-template", args.xhs_template]
    if args.xhs_account:
        cmd += ["--xhs-account", args.xhs_account]
    if args.toutiao_cover:
        cmd += ["--toutiao-cover", args.toutiao_cover]
    if args.dry_run:
        cmd += ["--dry-run"]
    return cmd


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish a reviewed GitHub Trending draft via article-multi-publisher.")
    parser.add_argument("path", help="Candidate directory, curated root, or reviewed draft file")
    parser.add_argument("--index", type=int, help="Candidate number from manifest.json when the input is a curated root directory")
    parser.add_argument("--source", help="Specific source filename when the input is a directory")
    parser.add_argument("--platforms", help="Comma-separated platforms: wechat,xhs,toutiao")
    parser.add_argument("--title", help="Override title for all platforms")
    parser.add_argument("--wechat-author", help="Override WeChat author")
    parser.add_argument("--wechat-summary", help="Override WeChat summary")
    parser.add_argument("--wechat-cover", help="Override WeChat cover path")
    parser.add_argument("--xhs-mode", choices=["auto", "image-text", "long-article"], help="Xiaohongshu mode")
    parser.add_argument("--xhs-template", help="Xiaohongshu long-article template")
    parser.add_argument("--xhs-account", help="Xiaohongshu account")
    parser.add_argument("--toutiao-cover", help="Override Toutiao cover path")
    parser.add_argument("--dry-run", action="store_true", help="Resolve source and command without publishing")
    args = parser.parse_args()

    input_path = Path(args.path).expanduser().resolve()
    if not input_path.exists():
        print(json.dumps({"ok": False, "error": f"Path not found: {input_path}"}, ensure_ascii=False, indent=2))
        sys.exit(1)

    try:
        base = resolve_candidate_by_index(input_path, args.index) if args.index else input_path
        source = resolve_source(base, args.source)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        sys.exit(1)

    cmd = build_command(source, args)

    if args.dry_run:
        print(json.dumps({"ok": True, "source": str(source), "command": cmd}, ensure_ascii=False, indent=2))
        return

    result = subprocess.run(cmd, capture_output=True, text=True)
    payload = {
        "ok": result.returncode == 0,
        "source": str(source),
        "command": cmd,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if result.returncode != 0:
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
