#!/usr/bin/env python3
"""Unified preflight: banned check + HTML check + cover check + publisher dry-run."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_step(name: str, cmd: list[str], capture: bool = True) -> bool:
    print(f"[PREFLIGHT] Step: {name}")
    result = subprocess.run(cmd, capture_output=capture, text=True)
    if result.returncode != 0:
        if result.stderr:
            for line in result.stderr.strip().splitlines():
                print(f"  {line}", file=sys.stderr)
        print(f"[FAIL] {name}", file=sys.stderr)
        return False
    if result.stdout:
        for line in result.stdout.strip().splitlines():
            print(f"  {line}")
    print(f"  [OK]")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--markdown", required=True)
    parser.add_argument("--html")
    parser.add_argument("--cover")
    parser.add_argument("--skip-banned", action="store_true")
    parser.add_argument("--skip-dry-run", action="store_true")
    args = parser.parse_args()

    md_path = Path(args.markdown).resolve()
    html_path = Path(args.html).resolve() if args.html else md_path.with_name(
        md_path.stem + ".wechat-publisher.html"
    )
    python3 = sys.executable
    bun = "bun"
    blockers: list[str] = []

    if not args.skip_banned:
        cmd = [python3, str(REPO_ROOT / "technical-article-review/scripts/check_banned_scaffolding.py"), "--input", str(md_path)]
        if not run_step("Banned scaffolding check", cmd):
            blockers.append("Banned patterns found in prose")

    if not html_path.exists():
        print(f"[FAIL] HTML not generated — run wechat-article-formatter first: {html_path}", file=sys.stderr)
        blockers.append("HTML not generated")
    else:
        cmd = [python3, str(REPO_ROOT / "technical-article-preflight/scripts/check_html.py"), "--html", str(html_path)]
        if not run_step("HTML structure check", cmd):
            blockers.append("HTML structure issues")

    cmd = [python3, str(REPO_ROOT / "technical-article-preflight/scripts/check_cover.py"), "--markdown", str(md_path)]
    if args.cover:
        cmd += ["--cover", args.cover]
    if not run_step("Cover check", cmd):
        blockers.append("Cover image issue")

    if not args.skip_dry_run:
        cmd = [bun, str(REPO_ROOT / "wechat-publisher/scripts/wechat-publish.ts"), str(html_path), "--dry-run"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[FAIL] Publisher dry-run failed", file=sys.stderr)
            for line in result.stderr.strip().splitlines():
                print(f"  {line}", file=sys.stderr)
            blockers.append("Publisher dry-run failed")
        else:
            try:
                data = json.loads(result.stdout)
                if data.get("ok"):
                    print(f"[PREFLIGHT] Dry-run: ok (method={data.get('method')}, title={data.get('command', [''])[3] if len(data.get('command', [])) > 3 else 'unknown'})")
                else:
                    blockers.append("Dry-run returned ok=false")
            except json.JSONDecodeError:
                print(f"  [WARN] Could not parse dry-run JSON output")
            for line in result.stdout.strip().splitlines()[:2]:
                print(f"  {line}")

    if blockers:
        print(f"\n[PREFLIGHT] Needs revision ({len(blockers)} blocker(s)):")
        for b in blockers:
            print(f"  - {b}")
        return 1

    print("\n[PREFLIGHT] Ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
