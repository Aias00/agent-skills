#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

JS_SUFFIXES = {".js", ".mjs", ".cjs"}
EXCLUDED_DIRS = {".git", "node_modules", "__pycache__", "release"}


class PipelineError(Exception):
    pass


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description=(
            "Integrated Chrome extension pipeline: dev checks + full publish pipeline "
            "(permissions, package, store assets, bilingual listing draft)."
        )
    )
    parser.add_argument("--root", default=".", help="Extension root directory (default: current directory)")
    parser.add_argument("--manifest", default="manifest.json", help="Manifest path relative to --root")
    parser.add_argument("--python", default=sys.executable, help="Python executable (default: current interpreter)")
    parser.add_argument("--node", default="node", help="Node executable for JS syntax checks (default: node)")
    parser.add_argument("--skip-dev-checks", action="store_true", help="Skip all development checks before publish")
    parser.add_argument("--skip-manifest-check", action="store_true", help="Skip manifest JSON validation")
    parser.add_argument("--skip-js-check", action="store_true", help="Skip JavaScript syntax validation")
    parser.add_argument(
        "--skip-icon-bootstrap",
        action="store_true",
        help="Skip automatic extension icons bootstrap (icons/icon16|48|128 + manifest mapping)",
    )
    parser.add_argument(
        "--auto-capture-if-no-inputs",
        action="store_true",
        default=True,
        help="Auto-enable screenshot capture when asset generation has no image inputs (default: true)",
    )
    parser.add_argument(
        "--no-auto-capture-if-no-inputs",
        dest="auto_capture_if_no_inputs",
        action="store_false",
        help="Disable automatic screenshot capture fallback",
    )
    parser.add_argument("--skip-ui-audit", action="store_true", help="Skip popup UI quality audit")
    parser.add_argument(
        "--popup-audit-out",
        default="release/popup-ui-audit.md",
        help="Popup UI audit report path relative to --root",
    )
    parser.add_argument(
        "--min-popup-width",
        type=int,
        default=560,
        help="Minimum popup width requirement in px for UI audit (default: 560)",
    )
    parser.add_argument(
        "--capture-popup-preview",
        action="store_true",
        help="Capture popup preview screenshot after pipeline (optional, disabled by default)",
    )
    parser.add_argument(
        "--skip-popup-preview",
        action="store_true",
        help="Deprecated compatibility flag. Popup preview is disabled by default unless --capture-popup-preview is set.",
    )
    parser.add_argument(
        "--popup-preview-out",
        default="release/store-assets/screenshots/popup-preview-620x760.png",
        help="Popup preview output path relative to --root",
    )
    parser.add_argument(
        "--popup-preview-size",
        default="620x760",
        help="Popup preview size WIDTHxHEIGHT (default: 620x760)",
    )
    parser.add_argument(
        "--popup-preview-headless",
        action="store_true",
        help="Try capturing popup preview in headless mode first (falls back to headed)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved command and checks without executing publish pipeline",
    )
    return parser.parse_known_args()


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)


def log_cmd(prefix: str, cmd: list[str]) -> None:
    print(f"{prefix} {' '.join(shlex.quote(token) for token in cmd)}")


def validate_manifest_json(root: Path, manifest_rel: str) -> dict:
    manifest_path = (root / manifest_rel).resolve()
    if not manifest_path.is_file():
        raise PipelineError(f"Manifest not found: {manifest_path}")
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PipelineError(f"Invalid manifest JSON: {exc}") from exc


def list_js_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in JS_SUFFIXES:
            continue
        rel_parts = path.relative_to(root).parts
        if rel_parts and rel_parts[0] in EXCLUDED_DIRS:
            continue
        files.append(path)
    return sorted(files)


def needs_module_check(content: str) -> bool:
    return bool(
        re.search(r"^\s*import\s", content, flags=re.MULTILINE)
        or re.search(r"^\s*export\s", content, flags=re.MULTILINE)
    )


def check_js_syntax(node_bin: str, root: Path) -> None:
    js_files = list_js_files(root)
    if not js_files:
        print("[DEV] No JS files found for syntax check.")
        return

    for file_path in js_files:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        is_module = needs_module_check(content)
        cmd = [node_bin]
        if is_module:
            cmd.append("--experimental-default-type=module")
        cmd.extend(["--check", str(file_path)])

        result = run(cmd, cwd=root)
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip()
            raise PipelineError(f"JS syntax check failed: {file_path.relative_to(root).as_posix()}\n{stderr}")

    print(f"[DEV] JS syntax check passed: {len(js_files)} file(s)")


def extract_manifest_icon_candidates(root: Path, manifest: dict) -> list[Path]:
    candidates: list[Path] = []

    def add_candidate(value: str | None) -> None:
        if not value:
            return
        path = (root / value).resolve()
        if path.is_file() and path not in candidates:
            candidates.append(path)

    icons = manifest.get("icons")
    if isinstance(icons, dict):
        for _, value in sorted(icons.items(), reverse=True):
            if isinstance(value, str):
                add_candidate(value)

    action = manifest.get("action")
    if isinstance(action, dict):
        default_icon = action.get("default_icon")
        if isinstance(default_icon, str):
            add_candidate(default_icon)
        elif isinstance(default_icon, dict):
            for _, value in sorted(default_icon.items(), reverse=True):
                if isinstance(value, str):
                    add_candidate(value)

    return candidates


def has_flag(flag: str, passthrough: list[str]) -> bool:
    return flag in passthrough


def has_option_with_value(flag: str, passthrough: list[str]) -> bool:
    for idx, token in enumerate(passthrough):
        if token == flag:
            return True
        if token.startswith(f"{flag}="):
            return True
        if token == flag and idx + 1 < len(passthrough):
            return True
    return False


def has_inputs(passthrough: list[str]) -> bool:
    if has_option_with_value("--inputs", passthrough):
        return True
    return False


def check_playwright_available(python_bin: str, root: Path) -> bool:
    cmd = [python_bin, "-c", "import playwright"]
    result = run(cmd, cwd=root)
    return result.returncode == 0


def resolve_publish_pipeline_script() -> Path:
    script_dir = Path(__file__).resolve().parent
    skill_dir = script_dir.parent
    skills_root = skill_dir.parent
    pipeline = skills_root / "chrome-extension-publish" / "scripts" / "run_full_release_pipeline.py"
    if pipeline.is_file():
        return pipeline
    raise PipelineError(
        f"Required script not found: {pipeline}\n"
        "Install/update `chrome-extension-publish` skill before using this integrated skill."
    )


def resolve_icon_bootstrap_script() -> Path:
    script_dir = Path(__file__).resolve().parent
    script = script_dir / "ensure_extension_icons.py"
    if script.is_file():
        return script
    raise PipelineError(f"Required script not found: {script}")


def resolve_popup_audit_script() -> Path:
    script_dir = Path(__file__).resolve().parent
    script = script_dir / "audit_popup_ui.py"
    if script.is_file():
        return script
    raise PipelineError(f"Required script not found: {script}")


def resolve_popup_preview_script() -> Path:
    script_dir = Path(__file__).resolve().parent
    script = script_dir / "capture_popup_preview.py"
    if script.is_file():
        return script
    raise PipelineError(f"Required script not found: {script}")


def build_pipeline_command(
    args: argparse.Namespace,
    passthrough: list[str],
    root: Path,
    manifest: dict,
) -> list[str]:
    forbidden_flags = {"--root", "--manifest"}
    conflicts = [flag for flag in forbidden_flags if has_flag(flag, passthrough) or has_option_with_value(flag, passthrough)]
    if conflicts:
        joined = ", ".join(conflicts)
        raise PipelineError(f"Do not pass {joined} via passthrough. Use wrapper flags `--root` / `--manifest`.")

    publish_pipeline = resolve_publish_pipeline_script()
    cmd = [
        args.python,
        str(publish_pipeline),
        "--root",
        str(root),
        "--manifest",
        args.manifest,
    ]

    assets_enabled = not has_flag("--skip-assets", passthrough)
    if assets_enabled and not has_option_with_value("--icon-source", passthrough):
        icon_candidates = extract_manifest_icon_candidates(root, manifest)
        if icon_candidates:
            cmd.extend(["--icon-source", str(icon_candidates[0])])
            print(f"[AUTO] icon-source from manifest: {icon_candidates[0]}")
        else:
            print(
                "[WARN] No icon source found in manifest. "
                "Asset generation may fail unless you pass `--icon-source`.",
                file=sys.stderr,
            )

    if (
        assets_enabled
        and args.auto_capture_if_no_inputs
        and not has_inputs(passthrough)
        and not has_flag("--capture-screenshots", passthrough)
    ):
        if not check_playwright_available(args.python, root):
            raise PipelineError(
                "No image inputs found and Playwright is unavailable for auto-capture.\n"
                "Install with:\n"
                "  python3 -m pip install playwright\n"
                "  python3 -m playwright install chromium\n"
                "or pass explicit `--inputs ...`."
            )
        cmd.append("--capture-screenshots")
        print("[AUTO] enabled screenshot auto-capture: --capture-screenshots")

    cmd.extend(passthrough)
    return cmd


def main() -> int:
    args, passthrough = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"[ERROR] root is not a directory: {root}", file=sys.stderr)
        return 1
    if args.min_popup_width < 320:
        print("[ERROR] --min-popup-width must be >= 320", file=sys.stderr)
        return 1
    preview_enabled = args.capture_popup_preview and not args.skip_popup_preview

    try:
        if not args.skip_icon_bootstrap:
            icon_bootstrap_script = resolve_icon_bootstrap_script()
            icon_cmd = [
                args.python,
                str(icon_bootstrap_script),
                "--root",
                str(root),
                "--manifest",
                args.manifest,
            ]
            if args.dry_run:
                icon_cmd.append("--dry-run")
            log_cmd("[ICON]", icon_cmd)
            icon_result = run(icon_cmd, cwd=root)
            if icon_result.stdout.strip():
                print(icon_result.stdout.strip())
            if icon_result.returncode != 0:
                stderr = icon_result.stderr.strip() or icon_result.stdout.strip() or "Icon bootstrap failed."
                raise PipelineError(stderr)

        manifest = validate_manifest_json(root, args.manifest)
        print(f"[DEV] Manifest JSON valid: {(root / args.manifest).resolve()}")

        if not args.skip_dev_checks:
            if not args.skip_manifest_check:
                _ = manifest
            if not args.skip_js_check:
                check_js_syntax(args.node, root)

        if not args.skip_ui_audit:
            popup_audit_script = resolve_popup_audit_script()
            popup_audit_cmd = [
                args.python,
                str(popup_audit_script),
                "--root",
                str(root),
                "--manifest",
                args.manifest,
                "--out",
                args.popup_audit_out,
                "--min-popup-width",
                str(args.min_popup_width),
            ]
            log_cmd("[UI-AUDIT]", popup_audit_cmd)
            popup_audit_result = run(popup_audit_cmd, cwd=root)
            if popup_audit_result.stdout.strip():
                print(popup_audit_result.stdout.strip())
            if popup_audit_result.returncode != 0:
                stderr = popup_audit_result.stderr.strip() or popup_audit_result.stdout.strip() or "Popup UI audit failed."
                raise PipelineError(stderr)

        pipeline_cmd = build_pipeline_command(args, passthrough, root, manifest)
        log_cmd("[PIPELINE]", pipeline_cmd)

        if args.dry_run:
            if preview_enabled:
                preview_script = resolve_popup_preview_script()
                preview_cmd = [
                    args.python,
                    str(preview_script),
                    "--extension-root",
                    str(root),
                    "--manifest",
                    args.manifest,
                    "--out",
                    args.popup_preview_out,
                    "--size",
                    args.popup_preview_size,
                ]
                if args.popup_preview_headless:
                    preview_cmd.append("--headless")
                log_cmd("[PREVIEW]", preview_cmd)
            print("[DRY-RUN] command resolved; execution skipped.")
            return 0

        completed = run(pipeline_cmd, cwd=root)
        if completed.stdout.strip():
            print(completed.stdout.strip())
        if completed.returncode != 0:
            stderr = completed.stderr.strip() or "Pipeline execution failed."
            raise PipelineError(stderr)

        if preview_enabled:
            preview_script = resolve_popup_preview_script()
            preview_cmd = [
                args.python,
                str(preview_script),
                "--extension-root",
                str(root),
                "--manifest",
                args.manifest,
                "--out",
                args.popup_preview_out,
                "--size",
                args.popup_preview_size,
            ]
            if args.popup_preview_headless:
                preview_cmd.append("--headless")
            log_cmd("[PREVIEW]", preview_cmd)
            preview_result = run(preview_cmd, cwd=root)
            if preview_result.stdout.strip():
                print(preview_result.stdout.strip())
            if preview_result.returncode != 0:
                stderr = preview_result.stderr.strip() or preview_result.stdout.strip() or "Popup preview capture failed."
                raise PipelineError(stderr)
        return 0
    except PipelineError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
