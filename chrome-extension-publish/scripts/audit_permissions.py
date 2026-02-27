#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SCAN_SUFFIXES = {".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".html", ".json"}
DEFAULT_EXCLUDES = {
    ".git",
    "node_modules",
    "release",
    "__pycache__",
}
URL_RE = re.compile(r"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+")

PERMISSION_ALIASES = {
    "activeTab": ["chrome.tabs", "chrome.scripting"],
    "alarms": ["chrome.alarms"],
    "bookmarks": ["chrome.bookmarks"],
    "commands": ["chrome.commands"],
    "contextMenus": ["chrome.contextMenus"],
    "cookies": ["chrome.cookies"],
    "declarativeNetRequest": ["chrome.declarativeNetRequest"],
    "declarativeNetRequestWithHostAccess": ["chrome.declarativeNetRequest"],
    "downloads": ["chrome.downloads"],
    "history": ["chrome.history"],
    "identity": ["chrome.identity"],
    "idle": ["chrome.idle"],
    "management": ["chrome.management"],
    "nativeMessaging": ["chrome.runtime.connectNative", "chrome.runtime.sendNativeMessage"],
    "notifications": ["chrome.notifications"],
    "offscreen": ["chrome.offscreen"],
    "permissions": ["chrome.permissions"],
    "scripting": ["chrome.scripting"],
    "sidePanel": ["chrome.sidePanel"],
    "storage": ["chrome.storage"],
    "tabs": ["chrome.tabs"],
    "topSites": ["chrome.topSites"],
    "webNavigation": ["chrome.webNavigation"],
    "webRequest": ["chrome.webRequest"],
}


@dataclass
class Evidence:
    file: str
    line: int
    text: str


class AuditError(Exception):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit manifest permissions against extension source usage.")
    parser.add_argument("--root", default=".", help="Extension root directory (default: current directory)")
    parser.add_argument("--manifest", default="manifest.json", help="Manifest path relative to --root")
    parser.add_argument(
        "--out",
        default="release/permission-audit.md",
        help="Output report path (default: release/permission-audit.md)",
    )
    parser.add_argument("--max-evidence", type=int, default=5, help="Maximum evidence lines per permission")
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Exit non-zero if permissions have no evidence or host URLs are uncovered",
    )
    return parser.parse_args()


def scan_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SCAN_SUFFIXES:
            continue
        rel_parts = path.relative_to(root).parts
        if rel_parts and rel_parts[0] in DEFAULT_EXCLUDES:
            continue
        files.append(path)
    return sorted(files)


def load_manifest(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AuditError(f"invalid manifest JSON: {exc}") from exc


def normalize_permission_aliases(permission: str) -> list[str]:
    if permission in PERMISSION_ALIASES:
        return PERMISSION_ALIASES[permission]

    candidate = permission
    if candidate and candidate[0].isupper():
        candidate = candidate[0].lower() + candidate[1:]
    return [f"chrome.{candidate}"]


def collect_permission_evidence(files: list[Path], root: Path, permission: str) -> list[Evidence]:
    aliases = normalize_permission_aliases(permission)
    evidence: list[Evidence] = []

    for file_path in files:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line_num, line in enumerate(content.splitlines(), start=1):
            if any(alias in line for alias in aliases):
                evidence.append(
                    Evidence(
                        file=file_path.relative_to(root).as_posix(),
                        line=line_num,
                        text=line.strip(),
                    )
                )
    return evidence


def collect_detected_urls(files: list[Path], root: Path) -> list[Evidence]:
    evidence: list[Evidence] = []
    for file_path in files:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for line_num, line in enumerate(content.splitlines(), start=1):
            for matched in URL_RE.findall(line):
                evidence.append(
                    Evidence(
                        file=file_path.relative_to(root).as_posix(),
                        line=line_num,
                        text=matched,
                    )
                )
    return evidence


def match_host_pattern(url: str, pattern: str) -> bool:
    if pattern == "<all_urls>":
        return True

    if pattern.startswith("*://"):
        tail = pattern[4:]
        return fnmatch.fnmatch(url, f"http://{tail}") or fnmatch.fnmatch(url, f"https://{tail}")

    return fnmatch.fnmatch(url, pattern)


def build_report(
    manifest: dict,
    required_permissions: list[str],
    optional_permissions: list[str],
    host_permissions: list[str],
    optional_host_permissions: list[str],
    permission_evidence: dict[str, list[Evidence]],
    url_evidence: list[Evidence],
    max_evidence: int,
) -> tuple[str, list[str], list[str]]:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    lines: list[str] = [
        "# Permission Audit Report",
        "",
        f"Generated at: `{timestamp}`",
        "",
        "## Manifest Summary",
        "",
        f"- Name: `{manifest.get('name', '')}`",
        f"- Version: `{manifest.get('version', '')}`",
        f"- Manifest version: `{manifest.get('manifest_version', '')}`",
        "",
        "## Declared Permissions",
        "",
        "| Permission | Scope | Evidence Count | Status |",
        "|---|---|---:|---|",
    ]

    missing_permissions: list[str] = []
    for perm in required_permissions:
        count = len(permission_evidence.get(perm, []))
        status = "OK" if count > 0 else "CHECK"
        if count == 0:
            missing_permissions.append(perm)
        lines.append(f"| `{perm}` | required | {count} | {status} |")

    for perm in optional_permissions:
        count = len(permission_evidence.get(perm, []))
        status = "OK" if count > 0 else "CHECK"
        lines.append(f"| `{perm}` | optional | {count} | {status} |")

    lines.extend([
        "",
        "## Permission Evidence Details",
        "",
    ])

    for perm in [*required_permissions, *optional_permissions]:
        lines.append(f"### `{perm}`")
        ev_list = permission_evidence.get(perm, [])
        if not ev_list:
            lines.append("- No direct API evidence found. Review whether this permission is still needed.")
            lines.append("")
            continue

        for ev in ev_list[:max_evidence]:
            lines.append(f"- `{ev.file}:{ev.line}`: `{ev.text}`")
        if len(ev_list) > max_evidence:
            lines.append(f"- ... and {len(ev_list) - max_evidence} more")
        lines.append("")

    declared_host = [*host_permissions, *optional_host_permissions]
    uncovered_urls: list[str] = []

    lines.extend([
        "## Host Permission Review",
        "",
        "### Declared Host Permissions",
    ])
    if declared_host:
        for pattern in declared_host:
            lines.append(f"- `{pattern}`")
    else:
        lines.append("- None")

    lines.extend(["", "### Detected Remote URLs in Source"])
    if url_evidence:
        unique_urls = sorted({ev.text for ev in url_evidence})
        for url in unique_urls:
            lines.append(f"- `{url}`")
            if declared_host and not any(match_host_pattern(url, pattern) for pattern in declared_host):
                uncovered_urls.append(url)
    else:
        lines.append("- None")

    lines.extend(["", "### Uncovered URLs"])
    if uncovered_urls:
        for url in uncovered_urls:
            lines.append(f"- `{url}`")
    else:
        lines.append("- None")

    lines.extend([
        "",
        "## Recommendations",
        "",
    ])

    if missing_permissions:
        lines.append("- Review and remove permissions with no direct evidence, or add explicit rationale.")
    else:
        lines.append("- Required permissions have direct code evidence.")

    if uncovered_urls:
        lines.append("- Add missing host permissions for uncovered URLs, or remove dead network code.")
    else:
        lines.append("- Declared host permissions cover detected URLs.")

    lines.append("")

    return "\n".join(lines), missing_permissions, uncovered_urls


def main() -> int:
    args = parse_args()

    root = Path(args.root).expanduser().resolve()
    manifest_path = (root / args.manifest).resolve()
    out_path = Path(args.out).expanduser().resolve()

    if not root.is_dir():
        print(f"[ERROR] root is not a directory: {root}", file=sys.stderr)
        return 1
    if not manifest_path.is_file():
        print(f"[ERROR] manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    try:
        manifest = load_manifest(manifest_path)
    except AuditError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    required_permissions = [str(item) for item in manifest.get("permissions", []) or []]
    optional_permissions = [str(item) for item in manifest.get("optional_permissions", []) or []]
    host_permissions = [str(item) for item in manifest.get("host_permissions", []) or []]
    optional_host_permissions = [str(item) for item in manifest.get("optional_host_permissions", []) or []]

    files = scan_source_files(root)
    permission_evidence = {
        perm: collect_permission_evidence(files, root, perm)
        for perm in [*required_permissions, *optional_permissions]
    }
    url_evidence = collect_detected_urls(files, root)

    report, missing_permissions, uncovered_urls = build_report(
        manifest=manifest,
        required_permissions=required_permissions,
        optional_permissions=optional_permissions,
        host_permissions=host_permissions,
        optional_host_permissions=optional_host_permissions,
        permission_evidence=permission_evidence,
        url_evidence=url_evidence,
        max_evidence=max(1, args.max_evidence),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")

    print(f"[OK] permission audit report written: {out_path}")
    print(f"[OK] required permissions: {len(required_permissions)}")
    print(f"[OK] optional permissions: {len(optional_permissions)}")
    print(f"[OK] uncovered URLs: {len(uncovered_urls)}")

    if args.fail_on_missing and (missing_permissions or uncovered_urls):
        print("[FAIL] missing permission evidence or uncovered URLs detected", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
