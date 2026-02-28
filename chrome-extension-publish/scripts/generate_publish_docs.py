#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCAN_SUFFIXES = {".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".html"}
RISKY_REMOTE_CODE_PATTERNS = {
    "eval(": "Uses eval()",
    "new Function(": "Uses new Function()",
    "WebAssembly.compileStreaming(": "Uses WebAssembly.compileStreaming()",
    "WebAssembly.instantiateStreaming(": "Uses WebAssembly.instantiateStreaming()",
    "import(\"http": "Dynamic import from remote URL",
    "import('http": "Dynamic import from remote URL",
}

PERMISSION_HINTS = {
    "storage": {
        "zh": "用于在 `chrome.storage` 中保存扩展配置或缓存数据，仅用于核心功能，不上传个人数据。",
        "en": "Used to store extension settings/cache in `chrome.storage` for core functionality only, without transmitting personal data.",
    },
    "activeTab": {
        "zh": "用于在用户主动点击扩展后访问当前活动标签页，以执行当前页面相关功能。",
        "en": "Used to access the active tab only after user action, to run page-specific features.",
    },
    "scripting": {
        "zh": "用于在获授权页面注入或执行扩展脚本，实现声明的页面增强能力。",
        "en": "Used to inject/execute extension scripts on permitted pages for declared page-enhancement features.",
    },
    "tabs": {
        "zh": "用于读取和管理标签页状态，以支持扩展提供的页面交互能力。",
        "en": "Used to read/manage tab state to support extension page interaction features.",
    },
    "alarms": {
        "zh": "用于定时触发后台任务（如刷新缓存或周期性检查），不涉及用户个人数据收集。",
        "en": "Used to schedule background tasks (for example cache refresh), without collecting personal user data.",
    },
}

BROAD_HOST_PATTERNS = {
    "<all_urls>",
    "http://*/*",
    "https://*/*",
    "*://*/*",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate bilingual (ZH/EN) Chrome Web Store listing draft from extension manifest and artifacts."
    )
    parser.add_argument("--root", default=".", help="Extension root directory (default: current directory)")
    parser.add_argument("--manifest", default="manifest.json", help="Manifest file path relative to --root")
    parser.add_argument(
        "--out",
        default="release/cws-listing.zh-en.md",
        help="Output markdown path relative to --root (default: release/cws-listing.zh-en.md)",
    )
    parser.add_argument(
        "--permission-audit",
        default="release/permission-audit.md",
        help="Permission audit report path relative to --root",
    )
    parser.add_argument(
        "--privacy-policy",
        default="privacy-policy.md",
        help="Canonical privacy policy path relative to --root (default: privacy-policy.md)",
    )
    parser.add_argument(
        "--feature",
        action="append",
        default=[],
        help=(
            "Explicit feature bullet (repeatable). "
            "Use `ZH text||EN text` for bilingual split; otherwise one text is reused for both."
        ),
    )
    parser.add_argument(
        "--single-purpose",
        default="",
        help="Optional explicit single-purpose statement (used for both ZH/EN blocks with localized wrappers).",
    )
    return parser.parse_args()


def read_manifest(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid manifest JSON: {exc}") from exc


def extract_match_patterns(entries: object) -> list[str]:
    patterns: list[str] = []
    if not isinstance(entries, list):
        return patterns
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        matches = entry.get("matches")
        if not isinstance(matches, list):
            continue
        for item in matches:
            if isinstance(item, str) and item.strip():
                patterns.append(item.strip())
    return patterns


def collect_declared_host_patterns(manifest: dict) -> list[tuple[str, str, str]]:
    merged: dict[str, dict[str, object]] = {}

    def add(pattern: str, scope: str, source: str) -> None:
        token = pattern.strip()
        if not token:
            return
        info = merged.setdefault(token, {"scope": scope, "sources": []})
        if scope == "required":
            info["scope"] = "required"
        sources = info["sources"]
        if isinstance(sources, list) and source not in sources:
            sources.append(source)

    for pattern in manifest.get("host_permissions", []) or []:
        if isinstance(pattern, str):
            add(pattern, "required", "host_permissions")

    for pattern in manifest.get("optional_host_permissions", []) or []:
        if isinstance(pattern, str):
            add(pattern, "optional", "optional_host_permissions")

    for pattern in extract_match_patterns(manifest.get("content_scripts")):
        add(pattern, "required", "content_scripts.matches")

    result: list[tuple[str, str, str]] = []
    for pattern in sorted(merged):
        info = merged[pattern]
        scope = str(info.get("scope", "required"))
        sources = info.get("sources", [])
        source_text = ", ".join(sources) if isinstance(sources, list) else str(sources)
        result.append((pattern, scope, source_text))
    return result


def infer_features(manifest: dict, explicit_features: list[str]) -> list[tuple[str, str]]:
    if explicit_features:
        features: list[tuple[str, str]] = []
        for item in explicit_features:
            token = item.strip()
            if not token:
                continue
            if "||" in token:
                zh, en = token.split("||", 1)
                features.append((zh.strip(), en.strip()))
            else:
                features.append((token, token))
        return features

    inferred: list[tuple[str, str]] = []
    description = str(manifest.get("description", "")).strip()
    if description:
        inferred.append((description, description))

    permissions = [str(item) for item in manifest.get("permissions", []) or []]
    if "storage" in permissions:
        inferred.append(("本地存储配置与缓存", "Local settings and cache storage"))
    if "activeTab" in permissions:
        inferred.append(("当前标签页一键触发能力", "One-click action on active tab"))
    if "scripting" in permissions:
        inferred.append(("按需页面脚本执行", "On-demand page scripting"))

    if not inferred:
        inferred.append(("浏览器内核心辅助功能", "Core in-browser utility features"))
    return inferred[:6]


def detect_remote_code_risk(root: Path) -> list[str]:
    findings: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SCAN_SUFFIXES:
            continue
        rel_parts = path.relative_to(root).parts
        if rel_parts and rel_parts[0] in {"release", "node_modules", ".git", "__pycache__"}:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        for marker, reason in RISKY_REMOTE_CODE_PATTERNS.items():
            if marker in content:
                findings.append(f"{path.relative_to(root).as_posix()}: {reason}")
    return findings


def short_summary(name: str, features: list[tuple[str, str]]) -> tuple[str, str]:
    feature_zh = re.sub(r"\s+", " ", features[0][0]).strip()
    feature_en = re.sub(r"\s+", " ", features[0][1]).strip()
    zh = f"在浏览器工具栏快速使用 {name}，支持 {feature_zh}，帮助用户高效完成核心目标。"
    en = f"Quickly use {name} from the browser toolbar, with {feature_en}, to help users complete the core task efficiently."
    return zh, en


def single_purpose(name: str, manifest_description: str, explicit: str) -> tuple[str, str]:
    if explicit.strip():
        purpose = explicit.strip()
        return (
            f"{name} 的单一用途是：{purpose}。所有功能均服务该目的，不包含无关能力。",
            f"The single purpose of {name} is: {purpose}. All features serve this purpose and avoid unrelated functionality.",
        )

    desc = manifest_description.strip() or "为用户提供与当前页面相关的高效操作能力"
    zh = f"{name} 的单一用途是：{desc}。扩展内所有主要功能均围绕这一目标设计，不提供与该目标无关的功能。"
    en = f"The single purpose of {name} is: {desc}. All major features are designed around this objective and do not provide unrelated functionality."
    return zh, en


def permission_rationale(permission: str) -> tuple[str, str]:
    hint = PERMISSION_HINTS.get(permission)
    if hint:
        return hint["zh"], hint["en"]
    return (
        f"权限 `{permission}` 仅用于实现扩展声明功能，并遵循最小权限原则。",
        f"Permission `{permission}` is requested only for declared extension functionality under least-privilege principles.",
    )


def is_broad_host_pattern(pattern: str) -> bool:
    token = pattern.strip()
    if token in BROAD_HOST_PATTERNS:
        return True
    if token.startswith("*://*.") and token.endswith("/*"):
        return True
    return False


def host_pattern_rationale(pattern: str, scope: str, source: str) -> tuple[str, str]:
    source_desc_zh = f"来源 `{source}`"
    source_desc_en = f"from `{source}`"
    if is_broad_host_pattern(pattern):
        return (
            f"匹配模式 `{pattern}`（{source_desc_zh}，{scope}）用于在用户触发时支持跨站点页面能力；仅用于声明功能，不采集无关数据。",
            f"Match pattern `{pattern}` ({source_desc_en}, {scope}) is required to support cross-site page features after user action; used only for declared functionality.",
        )
    return (
        f"匹配模式 `{pattern}`（{source_desc_zh}，{scope}）仅用于扩展声明的目标站点范围内功能。",
        f"Match pattern `{pattern}` ({source_desc_en}, {scope}) is limited to declared functionality on the specified origins.",
    )


def build_output(
    root: Path,
    manifest: dict,
    permission_audit_path: Path,
    privacy_policy_path: Path,
    out_rel: str,
    features: list[tuple[str, str]],
    single_purpose_text: tuple[str, str],
    remote_code_findings: list[str],
) -> str:
    name = str(manifest.get("name", "Chrome Extension")).strip() or "Chrome Extension"
    version = str(manifest.get("version", "")).strip()
    description = str(manifest.get("description", "")).strip()
    permissions = [str(item) for item in manifest.get("permissions", []) or []]
    host_patterns = collect_declared_host_patterns(manifest)

    short_zh, short_en = short_summary(name, features)
    purpose_zh, purpose_en = single_purpose_text
    zh_description = description or "帮助用户完成扩展定义的核心任务"
    en_description = description or "help users complete the extension's core task"
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    remote_code_zh = (
        "否，本扩展不使用远程代码。所有可执行代码均随扩展包本地打包。"
        if not remote_code_findings
        else "检测到可能涉及远程/动态执行的代码迹象，提交前请人工复核下列项。"
    )
    remote_code_en = (
        "No. This extension does not use remote code. All executable code is packaged locally in the extension bundle."
        if not remote_code_findings
        else "Potential remote/dynamic execution patterns were detected. Please review the following items before submission."
    )

    data_use_zh = "本扩展默认不收集、出售或共享个人用户数据。数据仅用于扩展核心功能并尽量本地处理。"
    data_use_en = "This extension does not collect, sell, or share personal user data by default. Data is used only for core functionality and processed locally where possible."

    policy_status_zh = "存在" if privacy_policy_path.is_file() else "缺失（需补齐）"
    policy_status_en = "exists" if privacy_policy_path.is_file() else "missing (must be added)"
    policy_decision_zh = "建议更新或确认无变更后沿用"
    policy_decision_en = "Update if behavior changed; otherwise keep current policy with an explicit no-change note"

    lines: list[str] = [
        "# CWS Listing Draft (ZH/EN)",
        "",
        f"Generated at: `{generated_at}`",
        "",
        "## Release Context",
        "",
        f"- Extension: `{name}`",
        f"- Version: `{version}`",
        f"- Output file: `{out_rel}`",
        f"- Permission audit: `{permission_audit_path.relative_to(root).as_posix()}` ({'exists' if permission_audit_path.is_file() else 'missing'})",
        f"- Privacy policy: `{privacy_policy_path.relative_to(root).as_posix()}` ({policy_status_en})",
        "",
        "## 1) Store Short Summary",
        "",
        "### ZH",
        short_zh,
        "",
        "### EN",
        short_en,
        "",
        "## 2) Listing Description (Long)",
        "",
        "### ZH",
        f"`{name}` 用于：{zh_description}。",
        "核心功能：",
    ]

    for idx, item in enumerate(features, start=1):
        lines.append(f"{idx}. {item[0]}")

    lines.extend([
        "",
        "### EN",
        f"`{name}` is designed to: {en_description}.",
        "Key features:",
    ])

    for idx, item in enumerate(features, start=1):
        lines.append(f"{idx}. {item[1]}")

    lines.extend([
        "",
        "## 3) Single Purpose Statement",
        "",
        "### ZH",
        purpose_zh,
        "",
        "### EN",
        purpose_en,
        "",
        "## 4) Permissions Rationale",
        "",
        "### ZH",
    ])

    if permissions:
        for perm in permissions:
            zh, _ = permission_rationale(perm)
            lines.append(f"- `{perm}`: {zh}")
    else:
        lines.append("- 无显式 permissions。")

    lines.extend(["", "### EN"])
    if permissions:
        for perm in permissions:
            _, en = permission_rationale(perm)
            lines.append(f"- `{perm}`: {en}")
    else:
        lines.append("- No explicit permissions declared.")

    lines.extend([
        "",
        "## 4.1) Host Match Patterns Rationale (CWS)",
        "",
        "### ZH",
    ])
    if host_patterns:
        for pattern, scope, source in host_patterns:
            zh, _ = host_pattern_rationale(pattern, scope, source)
            lines.append(f"- `{pattern}`: {zh}")
    else:
        lines.append("- 未声明 `host_permissions` 或 `content_scripts.matches`，通常无需填写主机权限理由。")

    lines.extend(["", "### EN"])
    if host_patterns:
        for pattern, scope, source in host_patterns:
            _, en = host_pattern_rationale(pattern, scope, source)
            lines.append(f"- `{pattern}`: {en}")
    else:
        lines.append("- No `host_permissions` or `content_scripts.matches` declared; host-permission reason is typically not required.")

    lines.extend([
        "",
        "## 5) Remote Code Answer",
        "",
        "### ZH",
        remote_code_zh,
        "",
        "### EN",
        remote_code_en,
    ])

    if remote_code_findings:
        lines.extend(["", "Detected patterns:"])
        for finding in remote_code_findings[:20]:
            lines.append(f"- `{finding}`")

    lines.extend([
        "",
        "## 6) Data Use Disclosure",
        "",
        "### ZH",
        data_use_zh,
        "",
        "### EN",
        data_use_en,
        "",
        "## 7) Reviewer Notes",
        "",
        "### ZH",
        f"本次提交版本 `{version}`，重点更新 `{name}` 的核心功能并执行权限最小化检查。请参考权限审计报告与隐私政策文件。",
        "",
        "### EN",
        f"This submission updates version `{version}` with core `{name}` improvements and a least-privilege permission check. Please refer to the permission audit report and privacy policy file.",
        "",
        "## 8) Privacy Policy Decision",
        "",
        "### ZH",
        f"隐私政策路径固定为 `privacy-policy.md`（根目录）。当前状态：{policy_status_zh}。结论：{policy_decision_zh}。",
        "",
        "### EN",
        f"Privacy policy path is fixed at `privacy-policy.md` (root). Current status: {policy_status_en}. Decision: {policy_decision_en}.",
        "",
    ])

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    manifest_path = (root / args.manifest).resolve()
    out_path = (root / args.out).resolve()
    permission_audit_path = (root / args.permission_audit).resolve()
    privacy_policy_path = (root / args.privacy_policy).resolve()

    if not root.is_dir():
        print(f"[ERROR] root is not a directory: {root}", file=sys.stderr)
        return 1
    if not manifest_path.is_file():
        print(f"[ERROR] manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    try:
        manifest = read_manifest(manifest_path)
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    features = infer_features(manifest, args.feature)
    purpose = single_purpose(
        str(manifest.get("name", "Chrome Extension")),
        str(manifest.get("description", "")),
        args.single_purpose,
    )
    remote_code_findings = detect_remote_code_risk(root)
    out_text = build_output(
        root=root,
        manifest=manifest,
        permission_audit_path=permission_audit_path,
        privacy_policy_path=privacy_policy_path,
        out_rel=Path(args.out).as_posix(),
        features=features,
        single_purpose_text=purpose,
        remote_code_findings=remote_code_findings,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out_text, encoding="utf-8")
    print(f"[OK] generated bilingual CWS draft: {out_path}")
    print(f"[OK] feature bullets: {len(features)}")
    print(f"[OK] remote code findings: {len(remote_code_findings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
