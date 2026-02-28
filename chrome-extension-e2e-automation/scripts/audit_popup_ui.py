#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Finding:
    level: str
    code: str
    message: str


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit Chrome extension popup UI readiness. "
            "Checks popup width, stylesheet wiring, and icon quality guardrails."
        )
    )
    parser.add_argument("--root", default=".", help="Extension root directory (default: current directory)")
    parser.add_argument("--manifest", default="manifest.json", help="Manifest path relative to --root")
    parser.add_argument("--out", default="release/popup-ui-audit.md", help="Audit report path relative to --root")
    parser.add_argument("--min-popup-width", type=int, default=560, help="Minimum required popup width in px")
    return parser.parse_args()


def parse_manifest(root: Path, manifest_rel: str) -> dict:
    manifest_path = (root / manifest_rel).resolve()
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def resolve_popup_path(root: Path, manifest: dict) -> Path:
    action = manifest.get("action")
    popup_rel = ""
    if isinstance(action, dict):
        value = action.get("default_popup")
        if isinstance(value, str):
            popup_rel = value
    if not popup_rel:
        raise ValueError("manifest.action.default_popup is missing; cannot audit popup UI.")
    popup_path = (root / popup_rel).resolve()
    if not popup_path.is_file():
        raise FileNotFoundError(f"popup file not found: {popup_path}")
    return popup_path


def extract_stylesheets(popup_html: str, popup_path: Path) -> tuple[list[Path], str]:
    css_files: list[Path] = []
    for match in re.finditer(r"<link[^>]*>", popup_html, flags=re.IGNORECASE):
        token = match.group(0)
        if "stylesheet" not in token.lower():
            continue
        href_match = re.search(r'href=["\']([^"\']+)["\']', token, flags=re.IGNORECASE)
        if not href_match:
            continue
        href = href_match.group(1).strip()
        if not href or href.startswith(("http://", "https://", "//", "data:")):
            continue
        css_files.append((popup_path.parent / href).resolve())

    inline_css = "\n".join(
        match.group(1)
        for match in re.finditer(r"<style[^>]*>(.*?)</style>", popup_html, flags=re.IGNORECASE | re.DOTALL)
    )
    return css_files, inline_css


def parse_css_blocks(css_text: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    for match in re.finditer(r"([^{]+)\{([^}]*)\}", css_text, flags=re.DOTALL):
        selectors = match.group(1).strip()
        declarations = match.group(2).strip()
        blocks.append((selectors, declarations))
    return blocks


def extract_px_value(declarations: str, prop: str) -> list[int]:
    values: list[int] = []
    pattern = rf"{re.escape(prop)}\s*:\s*(\d+)px"
    for match in re.finditer(pattern, declarations, flags=re.IGNORECASE):
        values.append(int(match.group(1)))
    return values


def collect_popup_widths(css_text: str) -> tuple[list[int], list[int], list[int], list[int]]:
    html_widths: list[int] = []
    body_widths: list[int] = []
    html_min_widths: list[int] = []
    body_min_widths: list[int] = []

    for selectors, declarations in parse_css_blocks(css_text):
        selector_tokens = [token.strip() for token in selectors.split(",")]
        has_html = any(token == "html" or token.endswith(" html") for token in selector_tokens)
        has_body = any(token == "body" or token.endswith(" body") for token in selector_tokens)
        if has_html:
            html_widths.extend(extract_px_value(declarations, "width"))
            html_min_widths.extend(extract_px_value(declarations, "min-width"))
        if has_body:
            body_widths.extend(extract_px_value(declarations, "width"))
            body_min_widths.extend(extract_px_value(declarations, "min-width"))

    return html_widths, body_widths, html_min_widths, body_min_widths


def has_media_width_reset(css_text: str) -> bool:
    pattern = (
        r"@media\s*\(\s*max-width\s*:\s*\d+px\s*\)\s*\{[\s\S]*?"
        r"(html|body)[^{]*\{[^}]*width\s*:\s*100%"
    )
    return re.search(pattern, css_text, flags=re.IGNORECASE) is not None


def read_png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != PNG_SIGNATURE:
        raise ValueError(f"not a valid PNG: {path}")
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    return width, height


def verify_icons(root: Path, manifest: dict) -> list[Finding]:
    findings: list[Finding] = []
    icons = manifest.get("icons")
    if not isinstance(icons, dict):
        findings.append(Finding("FAIL", "icons_map", "manifest.icons missing or not an object."))
        return findings

    required = {"16": 16, "48": 48, "128": 128}
    icon_paths: dict[str, Path] = {}
    for key, expected_size in required.items():
        value = icons.get(key)
        if not isinstance(value, str) or not value:
            findings.append(Finding("FAIL", f"icon_{key}", f"manifest.icons.{key} missing."))
            continue
        icon_path = (root / value).resolve()
        icon_paths[key] = icon_path
        if not icon_path.is_file():
            findings.append(Finding("FAIL", f"icon_{key}", f"icon file not found: {icon_path}"))
            continue
        try:
            width, height = read_png_size(icon_path)
        except ValueError as exc:
            findings.append(Finding("FAIL", f"icon_{key}", str(exc)))
            continue
        if width != expected_size or height != expected_size:
            findings.append(
                Finding(
                    "FAIL",
                    f"icon_{key}_size",
                    f"{icon_path.name} size is {width}x{height}; expected {expected_size}x{expected_size}.",
                )
            )

    # Guardrail: prevent generic fallback icon from being treated as final publish icon.
    try:
        import ensure_extension_icons as bootstrap

        extension_name = str(manifest.get("name", "Chrome Extension")).strip() or "Chrome Extension"
        base_rgb = bootstrap.palette_from_name(extension_name)
        matches = 0
        with tempfile.TemporaryDirectory(prefix="icon-audit-") as tmp_dir:
            tmp_root = Path(tmp_dir)
            for key, size in required.items():
                icon_path = icon_paths.get(key)
                if not icon_path or not icon_path.is_file():
                    continue
                generated = tmp_root / f"icon{size}.png"
                bootstrap.write_png(generated, size, size, bootstrap.render_icon(size, base_rgb))
                if icon_path.read_bytes() == generated.read_bytes():
                    matches += 1

        if matches == 3:
            findings.append(
                Finding(
                    "FAIL",
                    "icon_fallback",
                    "icons match auto-generated fallback style; provide custom brand icon before publish.",
                )
            )
    except Exception:
        findings.append(
            Finding(
                "WARN",
                "icon_fallback_check",
                "could not run fallback-icon similarity check; verify icon uniqueness manually.",
            )
        )

    return findings


def write_report(out_path: Path, findings: list[Finding], popup_path: Path, min_popup_width: int) -> None:
    fail_count = sum(1 for item in findings if item.level == "FAIL")
    warn_count = sum(1 for item in findings if item.level == "WARN")
    ok_count = sum(1 for item in findings if item.level == "OK")

    lines = [
        "# Popup UI Audit",
        "",
        f"- Popup file: `{popup_path}`",
        f"- Required minimum popup width: `{min_popup_width}px`",
        f"- Result: `{'PASS' if fail_count == 0 else 'FAIL'}`",
        "",
        "## Findings",
        "",
    ]
    for item in findings:
        lines.append(f"- `{item.level}` `{item.code}`: {item.message}")
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- FAIL: {fail_count}",
            f"- WARN: {warn_count}",
            f"- OK: {ok_count}",
            "",
        ]
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def audit_popup_ui(root: Path, manifest_rel: str, min_popup_width: int, out_rel: str) -> int:
    manifest = parse_manifest(root, manifest_rel)
    popup_path = resolve_popup_path(root, manifest)
    popup_html = popup_path.read_text(encoding="utf-8", errors="ignore")

    findings: list[Finding] = []
    css_files, inline_css = extract_stylesheets(popup_html, popup_path)

    if not css_files and not inline_css.strip():
        findings.append(Finding("FAIL", "css_missing", "popup has no stylesheet or inline style."))
        report_path = (root / out_rel).resolve()
        write_report(report_path, findings, popup_path, min_popup_width)
        print(f"[ERROR] popup UI audit failed: {report_path}")
        return 1

    css_text_parts: list[str] = []
    for css_path in css_files:
        if not css_path.is_file():
            findings.append(Finding("FAIL", "css_file_missing", f"stylesheet missing: {css_path}"))
            continue
        css_text_parts.append(css_path.read_text(encoding="utf-8", errors="ignore"))
    if inline_css.strip():
        css_text_parts.append(inline_css)

    css_text = "\n".join(css_text_parts)
    html_widths, body_widths, html_min_widths, body_min_widths = collect_popup_widths(css_text)

    width_candidates = html_widths + body_widths + html_min_widths + body_min_widths
    if not width_candidates:
        findings.append(
            Finding(
                "FAIL",
                "popup_width_missing",
                "popup CSS does not define explicit width/min-width on html/body.",
            )
        )
    else:
        resolved_width = max(width_candidates)
        if resolved_width < min_popup_width:
            findings.append(
                Finding(
                    "FAIL",
                    "popup_width_too_small",
                    f"popup width is {resolved_width}px; required >= {min_popup_width}px.",
                )
            )
        else:
            findings.append(Finding("OK", "popup_width", f"popup width {resolved_width}px meets requirement."))

    if has_media_width_reset(css_text):
        findings.append(
            Finding(
                "FAIL",
                "popup_media_reset",
                "media query resets html/body width to 100%, which can collapse popup width in Chrome.",
            )
        )
    else:
        findings.append(Finding("OK", "popup_media_reset", "no popup width reset media query detected."))

    if re.search(r"overflow-y\s*:\s*auto", css_text, flags=re.IGNORECASE):
        has_scrollbar_style = (
            "::-webkit-scrollbar" in css_text
            or re.search(r"scrollbar-width\s*:", css_text, flags=re.IGNORECASE) is not None
        )
        if has_scrollbar_style:
            findings.append(Finding("OK", "scrollbar_style", "custom scrollbar style detected."))
        else:
            findings.append(
                Finding(
                    "WARN",
                    "scrollbar_style",
                    "scrollable container detected without explicit scrollbar style.",
                )
            )

    findings.extend(verify_icons(root, manifest))

    report_path = (root / out_rel).resolve()
    write_report(report_path, findings, popup_path, min_popup_width)

    fail_count = sum(1 for item in findings if item.level == "FAIL")
    if fail_count > 0:
        print(f"[ERROR] popup UI audit failed: {report_path}")
        return 1

    print(f"[OK] popup UI audit passed: {report_path}")
    return 0


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"[ERROR] root is not a directory: {root}", file=sys.stderr)
        return 1
    if args.min_popup_width < 320:
        print("[ERROR] --min-popup-width must be >= 320", file=sys.stderr)
        return 1

    try:
        return audit_popup_ui(root, args.manifest, args.min_popup_width, args.out)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
