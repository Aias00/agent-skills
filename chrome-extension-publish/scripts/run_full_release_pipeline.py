#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ALLOWED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}


@dataclass
class StepResult:
    name: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


class PipelineError(Exception):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run end-to-end Chrome extension release automation: "
            "prepare baseline files, audit permissions, package zip, generate/validate assets, and draft CWS docs."
        )
    )
    parser.add_argument("--root", default=".", help="Extension root directory (default: current directory)")
    parser.add_argument("--manifest", default="manifest.json", help="Manifest path relative to --root")
    parser.add_argument("--python", default=sys.executable, help="Python executable (default: current interpreter)")
    parser.add_argument("--mode", choices=["manifest", "source"], default="manifest", help="Packaging mode")
    parser.add_argument("--zip-out", default="release/chrome-webstore.zip", help="Zip output path relative to --root")
    parser.add_argument(
        "--permission-audit-out",
        default="release/permission-audit.md",
        help="Permission audit report path relative to --root",
    )
    parser.add_argument(
        "--listing-out",
        default="release/cws-listing.zh-en.md",
        help="Bilingual listing draft output path relative to --root",
    )
    parser.add_argument(
        "--privacy-policy",
        default="privacy-policy.md",
        help="Canonical privacy policy path relative to --root",
    )
    parser.add_argument("--assets-root", default="release/store-assets", help="Store assets output root relative to --root")
    parser.add_argument("--inputs", nargs="*", default=[], help="Input image paths for asset generation")
    parser.add_argument("--icon-source", default="", help="Explicit icon source image path")
    parser.add_argument("--small-promo-source", default="", help="Explicit small promo source image path")
    parser.add_argument("--marquee-source", default="", help="Explicit marquee source image path")
    parser.add_argument("--include-marquee", action="store_true", help="Generate optional marquee asset")
    parser.add_argument("--allow-icon-fallback", action="store_true", help="Allow icon fallback from single input image")
    parser.add_argument("--capture-screenshots", action="store_true", help="Capture screenshots before asset generation")
    parser.add_argument(
        "--auto-capture-if-no-inputs",
        action="store_true",
        default=True,
        help="Auto-enable screenshot capture when --inputs is not provided (default: true)",
    )
    parser.add_argument(
        "--no-auto-capture-if-no-inputs",
        dest="auto_capture_if_no_inputs",
        action="store_false",
        help="Disable automatic screenshot capture fallback when --inputs is missing",
    )
    parser.add_argument("--skip-assets", action="store_true", help="Skip store asset generation/validation")
    parser.add_argument("--skip-docs", action="store_true", help="Skip bilingual CWS listing doc generation")
    parser.add_argument("--skip-prepare", action="store_true", help="Skip prepare_publish_basics step")
    parser.add_argument("--skip-audit", action="store_true", help="Skip permission audit step")
    parser.add_argument("--skip-package", action="store_true", help="Skip extension packaging step")
    parser.add_argument("--screenshot-size", default="1280x800", help="Screenshot size for capture/generation")
    parser.add_argument("--max-screenshots", type=int, default=5, help="Max screenshots for capture/generation")
    parser.add_argument("--options-path", default="", help="Options page path for screenshot capture")
    parser.add_argument("--urls", nargs="*", default=[], help="Additional URLs to capture as screenshots")
    parser.add_argument("--headless", action="store_true", help="Use headless mode when capturing screenshots")
    parser.add_argument(
        "--summary-out",
        default="release/full-release-summary.md",
        help="Pipeline summary output path relative to --root",
    )
    parser.add_argument(
        "--submit-playwright",
        action="store_true",
        help="Run optional Playwright-based CWS dashboard automation after artifact generation",
    )
    parser.add_argument(
        "--submit-item-id",
        default="",
        help="Chrome Web Store item id for submit automation (recommended for updates)",
    )
    parser.add_argument(
        "--submit-item-name",
        default="",
        help="Extension item name for dashboard auto-selection when --submit-item-id is omitted",
    )
    parser.add_argument(
        "--submit-locale",
        choices=["zh", "en"],
        default="en",
        help="Locale to use when auto-filling listing fields (default: en)",
    )
    parser.add_argument(
        "--submit-privacy-policy-url",
        default="",
        help="Optional privacy policy URL to auto-fill in CWS dashboard",
    )
    parser.add_argument(
        "--submit-review-notes",
        default="",
        help="Optional explicit reviewer notes override",
    )
    parser.add_argument(
        "--submit-dashboard-url",
        default="https://chrome.google.com/webstore/devconsole",
        help="CWS developer dashboard URL for Playwright submit flow",
    )
    parser.add_argument(
        "--submit-item-url-template",
        default="https://chrome.google.com/webstore/devconsole/{item_id}/edit",
        help="CWS item edit URL template; must contain {item_id}",
    )
    parser.add_argument(
        "--submit-user-data-dir",
        default="",
        help="Optional persistent browser user-data-dir for Playwright submit flow",
    )
    parser.add_argument(
        "--submit-headless",
        action="store_true",
        help="Use headless mode in Playwright submit flow (not recommended for login/2FA)",
    )
    parser.add_argument(
        "--submit-for-review",
        action="store_true",
        help="Click final submit-for-review button in Playwright submit flow",
    )
    parser.add_argument(
        "--submit-login-timeout-ms",
        type=int,
        default=300000,
        help="Max login/session wait time in Playwright submit flow (default: 300000)",
    )
    parser.add_argument(
        "--submit-timeout-ms",
        type=int,
        default=25000,
        help="Control timeout in Playwright submit flow (default: 25000)",
    )
    parser.add_argument(
        "--submit-wait-ms",
        type=int,
        default=1200,
        help="Post-action wait in Playwright submit flow (default: 1200)",
    )
    parser.add_argument(
        "--submit-evidence-out",
        default="release/cws-submit-proof.png",
        help="Submit-flow evidence screenshot path relative to --root",
    )
    parser.add_argument(
        "--submit-hold-ms",
        type=int,
        default=0,
        help="Keep browser open for extra review in Playwright submit flow (default: 0)",
    )
    return parser.parse_args()


def run_step(name: str, cmd: list[str], cwd: Path) -> StepResult:
    print(f"[STEP] {name}")
    print(f"       {' '.join(shlex.quote(token) for token in cmd)}")
    completed = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if completed.stdout.strip():
        print(completed.stdout.strip())
    if completed.returncode != 0 and completed.stderr.strip():
        print(completed.stderr.strip(), file=sys.stderr)
    if completed.returncode != 0:
        raise PipelineError(f"{name} failed with exit code {completed.returncode}")
    return StepResult(
        name=name,
        command=cmd,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def collect_existing_screenshots(assets_root: Path) -> list[Path]:
    shots_dir = assets_root / "screenshots"
    if not shots_dir.is_dir():
        return []
    return sorted(
        [
            path.resolve()
            for path in shots_dir.iterdir()
            if path.is_file() and path.suffix.lower() in ALLOWED_IMAGE_SUFFIXES
        ]
    )


def write_summary(
    root: Path,
    summary_out: Path,
    results: list[StepResult],
    zip_out: Path,
    permission_audit_out: Path,
    listing_out: Path,
    assets_root: Path,
) -> None:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    lines = [
        "# Full Release Pipeline Summary",
        "",
        f"Generated at: `{generated_at}`",
        "",
        "## Artifacts",
        "",
        f"- ZIP: `{zip_out.relative_to(root).as_posix()}` ({'exists' if zip_out.is_file() else 'missing'})",
        f"- Permission audit: `{permission_audit_out.relative_to(root).as_posix()}` ({'exists' if permission_audit_out.is_file() else 'missing'})",
        f"- Listing draft: `{listing_out.relative_to(root).as_posix()}` ({'exists' if listing_out.is_file() else 'missing'})",
        f"- Store assets root: `{assets_root.relative_to(root).as_posix()}` ({'exists' if assets_root.is_dir() else 'missing'})",
        "",
        "## Steps",
        "",
    ]
    for result in results:
        cmd = " ".join(shlex.quote(token) for token in result.command)
        lines.append(f"- `{result.name}`: `ok`")
        lines.append(f"  - command: `{cmd}`")

    summary_out.parent.mkdir(parents=True, exist_ok=True)
    summary_out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()

    root = Path(args.root).expanduser().resolve()
    manifest_path = (root / args.manifest).resolve()
    zip_out = (root / args.zip_out).resolve()
    permission_audit_out = (root / args.permission_audit_out).resolve()
    listing_out = (root / args.listing_out).resolve()
    assets_root = (root / args.assets_root).resolve()
    summary_out = (root / args.summary_out).resolve()
    privacy_policy_rel = Path(args.privacy_policy).as_posix()

    if not root.is_dir():
        print(f"[ERROR] root is not a directory: {root}", file=sys.stderr)
        return 1
    if not manifest_path.is_file():
        print(f"[ERROR] manifest not found: {manifest_path}", file=sys.stderr)
        return 1
    if args.max_screenshots < 1:
        print("[ERROR] --max-screenshots must be >= 1", file=sys.stderr)
        return 1

    script_dir = Path(__file__).resolve().parent
    publish_dir = script_dir.parent
    skills_root = publish_dir.parent
    image_skill_script = skills_root / "chrome-webstore-image-generator" / "scripts" / "capture_extension_screenshots.py"

    prepare_script = script_dir / "prepare_publish_basics.py"
    audit_script = script_dir / "audit_permissions.py"
    package_script = script_dir / "package_extension.py"
    generate_assets_script = script_dir / "generate_store_assets.py"
    validate_assets_script = script_dir / "validate_store_assets.py"
    docs_script = script_dir / "generate_publish_docs.py"
    submit_script = script_dir / "submit_cws_playwright.py"

    results: list[StepResult] = []
    python = args.python

    try:
        if not args.skip_prepare:
            results.append(
                run_step(
                    "prepare_publish_basics",
                    [python, str(prepare_script), "--root", str(root)],
                    cwd=root,
                )
            )

        if not args.skip_audit:
            results.append(
                run_step(
                    "audit_permissions",
                    [
                        python,
                        str(audit_script),
                        "--root",
                        str(root),
                        "--manifest",
                        str(Path(args.manifest).as_posix()),
                        "--out",
                        str(Path(args.permission_audit_out).as_posix()),
                    ],
                    cwd=root,
                )
            )

        if not args.skip_package:
            results.append(
                run_step(
                    "package_extension",
                    [
                        python,
                        str(package_script),
                        "--root",
                        str(root),
                        "--manifest",
                        str(Path(args.manifest).as_posix()),
                        "--mode",
                        args.mode,
                        "--out",
                        str(Path(args.zip_out).as_posix()),
                    ],
                    cwd=root,
                )
            )

        if not args.skip_assets:
            assets_root.mkdir(parents=True, exist_ok=True)

            input_paths = [Path(item).expanduser().resolve() for item in args.inputs]
            capture_required = args.capture_screenshots
            if not input_paths and args.auto_capture_if_no_inputs:
                if not capture_required:
                    print("[AUTO] no --inputs provided; enabling screenshot auto-capture.")
                capture_required = True

            if capture_required:
                if not image_skill_script.is_file():
                    raise PipelineError(
                        f"Screenshot capture script not found: {image_skill_script}. "
                        "Install chrome-webstore-image-generator skill first."
                    )

                capture_cmd = [
                    python,
                    str(image_skill_script),
                    "--extension-root",
                    str(root),
                    "--root",
                    str(assets_root),
                    "--screenshot-size",
                    args.screenshot_size,
                    "--max-screenshots",
                    str(args.max_screenshots),
                ]
                if args.options_path:
                    capture_cmd.extend(["--options-path", args.options_path])
                if args.urls:
                    capture_cmd.extend(["--urls", *args.urls])
                if args.headless:
                    capture_cmd.append("--headless")
                results.append(run_step("capture_screenshots", capture_cmd, cwd=root))

            if not input_paths:
                input_paths = collect_existing_screenshots(assets_root)

            if not input_paths:
                raise PipelineError(
                    "No image inputs available for asset generation after screenshot capture attempt. "
                    "Provide --inputs, or verify Playwright/chrome-extension screenshot capture setup."
                )

            generate_cmd = [
                python,
                str(generate_assets_script),
                "--inputs",
                *[str(path) for path in input_paths],
                "--root",
                str(assets_root),
                "--screenshot-size",
                args.screenshot_size,
                "--max-screenshots",
                str(args.max_screenshots),
            ]
            if args.icon_source:
                generate_cmd.extend(["--icon-source", str(Path(args.icon_source).expanduser().resolve())])
            if args.small_promo_source:
                generate_cmd.extend(
                    ["--small-promo-source", str(Path(args.small_promo_source).expanduser().resolve())]
                )
            if args.marquee_source:
                generate_cmd.extend(["--marquee-source", str(Path(args.marquee_source).expanduser().resolve())])
            if args.include_marquee:
                generate_cmd.append("--include-marquee")
            if args.allow_icon_fallback:
                generate_cmd.append("--allow-icon-fallback")

            results.append(run_step("generate_store_assets", generate_cmd, cwd=root))
            results.append(
                run_step(
                    "validate_store_assets",
                    [python, str(validate_assets_script), "--root", str(assets_root)],
                    cwd=root,
                )
            )

        if not args.skip_docs:
            results.append(
                run_step(
                    "generate_publish_docs",
                    [
                        python,
                        str(docs_script),
                        "--root",
                        str(root),
                        "--manifest",
                        str(Path(args.manifest).as_posix()),
                        "--out",
                        str(Path(args.listing_out).as_posix()),
                        "--permission-audit",
                        str(Path(args.permission_audit_out).as_posix()),
                        "--privacy-policy",
                        privacy_policy_rel,
                    ],
                    cwd=root,
                )
            )

        if args.submit_playwright:
            submit_cmd = [
                python,
                str(submit_script),
                "--root",
                str(root),
                "--zip",
                str(Path(args.zip_out).as_posix()),
                "--listing",
                str(Path(args.listing_out).as_posix()),
                "--locale",
                args.submit_locale,
                "--dashboard-url",
                args.submit_dashboard_url,
                "--item-url-template",
                args.submit_item_url_template,
                "--login-timeout-ms",
                str(args.submit_login_timeout_ms),
                "--timeout-ms",
                str(args.submit_timeout_ms),
                "--wait-ms",
                str(args.submit_wait_ms),
                "--evidence-out",
                str(Path(args.submit_evidence_out).as_posix()),
                "--hold-ms",
                str(args.submit_hold_ms),
            ]
            if args.submit_item_id:
                submit_cmd.extend(["--item-id", args.submit_item_id])
            if args.submit_item_name:
                submit_cmd.extend(["--item-name", args.submit_item_name])
            if args.submit_privacy_policy_url:
                submit_cmd.extend(["--privacy-policy-url", args.submit_privacy_policy_url])
            if args.submit_review_notes:
                submit_cmd.extend(["--review-notes", args.submit_review_notes])
            if args.submit_user_data_dir:
                submit_cmd.extend(["--user-data-dir", args.submit_user_data_dir])
            if args.submit_headless:
                submit_cmd.append("--headless")
            if args.submit_for_review:
                submit_cmd.append("--submit-for-review")

            results.append(run_step("submit_cws_playwright", submit_cmd, cwd=root))

        write_summary(
            root=root,
            summary_out=summary_out,
            results=results,
            zip_out=zip_out,
            permission_audit_out=permission_audit_out,
            listing_out=listing_out,
            assets_root=assets_root,
        )
        print(f"[OK] pipeline summary: {summary_out}")
        return 0
    except PipelineError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
