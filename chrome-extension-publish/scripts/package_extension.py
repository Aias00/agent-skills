#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import sys
import zipfile
from pathlib import Path

DEFAULT_EXCLUDES = [
    ".git/**",
    ".github/**",
    "release/**",
    "node_modules/**",
    "__pycache__/**",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
]

WILDCARD_CHARS = set("*?[")


def posix_rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def is_excluded(rel_path: str, excludes: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel_path, pattern) for pattern in excludes)


def add_file_if_valid(
    file_path: Path,
    root: Path,
    selected: set[str],
    excludes: list[str],
) -> bool:
    if not file_path.exists() or not file_path.is_file():
        return False
    rel = posix_rel(file_path, root)
    if is_excluded(rel, excludes):
        return False
    selected.add(rel)
    return True


def expand_input_path(path_expr: str, root: Path) -> list[Path]:
    if any(ch in path_expr for ch in WILDCARD_CHARS):
        return [p for p in root.glob(path_expr) if p.is_file()]

    candidate = (root / path_expr).resolve()
    if candidate.is_file():
        return [candidate]
    if candidate.is_dir():
        return sorted([p for p in candidate.rglob("*") if p.is_file()])
    return []


def collect_source_mode_files(root: Path, out_path: Path, excludes: list[str]) -> set[str]:
    selected: set[str] = set()
    out_rel = out_path.resolve().relative_to(root.resolve()).as_posix() if out_path.resolve().is_relative_to(root.resolve()) else None

    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        rel = posix_rel(file_path, root)
        if out_rel and rel == out_rel:
            continue
        if is_excluded(rel, excludes):
            continue
        selected.add(rel)

    return selected


def collect_manifest_referenced_files(
    root: Path,
    manifest: dict,
    excludes: list[str],
) -> tuple[set[str], list[str]]:
    selected: set[str] = set()
    missing: list[str] = []

    def add_ref(path_expr: str | None, field: str) -> None:
        if not path_expr:
            return
        resolved = expand_input_path(path_expr, root)
        if not resolved:
            missing.append(f"{field}: {path_expr}")
            return
        for file_path in resolved:
            add_file_if_valid(file_path, root, selected, excludes)

    add_ref("manifest.json", "manifest")

    action = manifest.get("action", {}) if isinstance(manifest.get("action"), dict) else {}
    add_ref(action.get("default_popup"), "action.default_popup")

    action_default_icon = action.get("default_icon")
    if isinstance(action_default_icon, str):
        add_ref(action_default_icon, "action.default_icon")
    elif isinstance(action_default_icon, dict):
        for size, icon_path in action_default_icon.items():
            add_ref(icon_path, f"action.default_icon[{size}]")

    icons = manifest.get("icons")
    if isinstance(icons, dict):
        for size, icon_path in icons.items():
            add_ref(icon_path, f"icons[{size}]")

    background = manifest.get("background", {}) if isinstance(manifest.get("background"), dict) else {}
    add_ref(background.get("service_worker"), "background.service_worker")
    scripts = background.get("scripts")
    if isinstance(scripts, list):
        for idx, script_path in enumerate(scripts):
            add_ref(script_path, f"background.scripts[{idx}]")

    content_scripts = manifest.get("content_scripts")
    if isinstance(content_scripts, list):
        for idx, item in enumerate(content_scripts):
            if not isinstance(item, dict):
                continue
            for jdx, script_path in enumerate(item.get("js", []) or []):
                add_ref(script_path, f"content_scripts[{idx}].js[{jdx}]")
            for jdx, css_path in enumerate(item.get("css", []) or []):
                add_ref(css_path, f"content_scripts[{idx}].css[{jdx}]")

    add_ref(manifest.get("options_page"), "options_page")

    options_ui = manifest.get("options_ui")
    if isinstance(options_ui, dict):
        add_ref(options_ui.get("page"), "options_ui.page")

    side_panel = manifest.get("side_panel")
    if isinstance(side_panel, dict):
        add_ref(side_panel.get("default_path"), "side_panel.default_path")

    add_ref(manifest.get("devtools_page"), "devtools_page")

    chrome_overrides = manifest.get("chrome_url_overrides")
    if isinstance(chrome_overrides, dict):
        for key, override_path in chrome_overrides.items():
            add_ref(override_path, f"chrome_url_overrides.{key}")

    sandbox = manifest.get("sandbox")
    if isinstance(sandbox, dict):
        for idx, page_path in enumerate(sandbox.get("pages", []) or []):
            add_ref(page_path, f"sandbox.pages[{idx}]")

    web_accessible = manifest.get("web_accessible_resources")
    if isinstance(web_accessible, list):
        for idx, item in enumerate(web_accessible):
            if not isinstance(item, dict):
                continue
            for jdx, resource in enumerate(item.get("resources", []) or []):
                add_ref(resource, f"web_accessible_resources[{idx}].resources[{jdx}]")

    dnr = manifest.get("declarative_net_request")
    if isinstance(dnr, dict):
        for idx, rule_item in enumerate(dnr.get("rule_resources", []) or []):
            if not isinstance(rule_item, dict):
                continue
            add_ref(rule_item.get("path"), f"declarative_net_request.rule_resources[{idx}].path")

    if manifest.get("default_locale") and (root / "_locales").is_dir():
        for locale_file in sorted((root / "_locales").rglob("*")):
            if locale_file.is_file():
                add_file_if_valid(locale_file, root, selected, excludes)

    return selected, missing


def add_extra_entries(
    root: Path,
    selected: set[str],
    extras: list[str],
    excludes: list[str],
) -> list[str]:
    missing: list[str] = []

    for entry in extras:
        resolved = expand_input_path(entry, root)
        if not resolved:
            missing.append(entry)
            continue
        for file_path in resolved:
            add_file_if_valid(file_path, root, selected, excludes)

    return missing


def build_zip(root: Path, out_path: Path, rel_files: list[str]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(out_path, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel in rel_files:
            abs_path = root / rel
            info = zipfile.ZipInfo(rel)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (abs_path.stat().st_mode & 0xFFFF) << 16
            zf.writestr(info, abs_path.read_bytes())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Package a Chrome extension for Chrome Web Store upload.")
    parser.add_argument("--root", default=".", help="Extension root directory (default: current directory)")
    parser.add_argument("--manifest", default="manifest.json", help="Manifest file path relative to --root")
    parser.add_argument("--out", default="release/chrome-webstore.zip", help="Output ZIP path")
    parser.add_argument(
        "--mode",
        choices=["manifest", "source"],
        default="manifest",
        help="manifest: include manifest-referenced files (+extras), source: include all source files minus excludes",
    )
    parser.add_argument(
        "--extra",
        action="append",
        default=[],
        help="Additional file/dir/glob to include (repeatable)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Additional exclude glob relative to root (repeatable)",
    )
    parser.add_argument("--allow-missing", action="store_true", help="Do not fail when referenced files are missing")
    parser.add_argument("--dry-run", action="store_true", help="Print included files without writing ZIP")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    root = Path(args.root).expanduser().resolve()
    manifest_path = (root / args.manifest).resolve()
    out_path = Path(args.out).expanduser().resolve()
    excludes = [*DEFAULT_EXCLUDES, *args.exclude]

    if not root.is_dir():
        print(f"[ERROR] root is not a directory: {root}", file=sys.stderr)
        return 1
    if not manifest_path.is_file():
        print(f"[ERROR] manifest file not found: {manifest_path}", file=sys.stderr)
        return 1

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[ERROR] invalid manifest JSON: {exc}", file=sys.stderr)
        return 1

    selected: set[str]
    missing_refs: list[str] = []

    if args.mode == "manifest":
        selected, missing_refs = collect_manifest_referenced_files(root, manifest, excludes)
    else:
        selected = collect_source_mode_files(root, out_path, excludes)

    missing_extras = add_extra_entries(root, selected, args.extra, excludes)

    missing_all = [*(f"missing referenced file: {item}" for item in missing_refs), *(f"missing extra path: {item}" for item in missing_extras)]
    if missing_all and not args.allow_missing:
        print("[ERROR] packaging aborted due to missing files:", file=sys.stderr)
        for item in missing_all:
            print(f"  - {item}", file=sys.stderr)
        return 1

    rel_files = sorted(selected)
    if not rel_files:
        print("[ERROR] no files selected for packaging", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"[DRY-RUN] selected {len(rel_files)} file(s):")
        for rel in rel_files:
            print(f"  - {rel}")
    else:
        build_zip(root, out_path, rel_files)
        print(f"[OK] packaged {len(rel_files)} file(s)")
        print(f"[OK] zip: {out_path}")

    if missing_all:
        print("[WARN] missing files were ignored:")
        for item in missing_all:
            print(f"  - {item}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
