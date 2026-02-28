#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

DEFAULT_GITIGNORE_LINES = [
    "release/",
    "__pycache__/",
    "*.py[cod]",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare publish baseline files for a Chrome extension project: "
            "ensure root privacy-policy.md and update .gitignore."
        )
    )
    parser.add_argument("--root", default=".", help="Extension project root directory (default: current directory)")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing files")
    return parser.parse_args()


def read_manifest_name(root: Path) -> str:
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        return "Chrome Extension"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "Chrome Extension"
    name = manifest.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return "Chrome Extension"


def slugify(value: str) -> str:
    lowered = value.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "-", lowered)
    normalized = normalized.strip("-")
    return normalized or "chrome-extension"


def privacy_policy_template(extension_name: str) -> str:
    today = date.today().isoformat()
    extension_slug = slugify(extension_name)
    return (
        "# Privacy Policy\n\n"
        f"Last updated: {today}\n\n"
        f"This Privacy Policy describes how **{extension_name}** handles data.\n\n"
        "## Data Collection\n\n"
        "- This extension does not collect personal information.\n"
        "- Extension data is stored locally in the browser (for example via `chrome.storage`).\n\n"
        "## Data Sharing\n\n"
        "- No personal data is sold, shared, or transferred to third parties.\n"
        "- Network requests, if any, are used only to provide core extension functionality.\n\n"
        "## Permissions Use\n\n"
        "- Permissions requested in `manifest.json` are used only for the declared extension features.\n\n"
        "## Data Retention\n\n"
        "- Locally stored data remains on the user's device until the user clears browser data or removes the extension.\n\n"
        "## Contact\n\n"
        f"If you have questions about this policy, contact: `support@{extension_slug}.local`.\n"
    )


def ensure_privacy_policy(root: Path, dry_run: bool) -> tuple[bool, str]:
    policy_path = root / "privacy-policy.md"
    if policy_path.exists():
        return False, f"[OK] privacy policy exists: {policy_path}"

    extension_name = read_manifest_name(root)
    content = privacy_policy_template(extension_name)
    if dry_run:
        return True, f"[DRY-RUN] create: {policy_path}"

    policy_path.write_text(content, encoding="utf-8")
    return True, f"[OK] created: {policy_path}"


def ensure_gitignore(root: Path, dry_run: bool) -> tuple[bool, str]:
    gitignore_path = root / ".gitignore"
    changed = False

    if gitignore_path.exists():
        original = gitignore_path.read_text(encoding="utf-8", errors="ignore")
    else:
        original = ""

    lines = original.splitlines()
    existing = {line.strip() for line in lines if line.strip()}
    missing_lines = [line for line in DEFAULT_GITIGNORE_LINES if line not in existing]

    if not missing_lines:
        return False, f"[OK] .gitignore already contains required entries: {gitignore_path}"

    changed = True
    if dry_run:
        return changed, f"[DRY-RUN] update: {gitignore_path} (+{', '.join(missing_lines)})"

    new_lines = lines[:]
    if new_lines and new_lines[-1].strip():
        new_lines.append("")
    new_lines.extend(missing_lines)
    new_content = "\n".join(new_lines).rstrip("\n") + "\n"
    gitignore_path.write_text(new_content, encoding="utf-8")
    return changed, f"[OK] updated: {gitignore_path} (+{', '.join(missing_lines)})"


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()

    if not root.is_dir():
        print(f"[ERROR] root is not a directory: {root}", file=sys.stderr)
        return 1

    changed_policy, policy_msg = ensure_privacy_policy(root, args.dry_run)
    changed_gitignore, gitignore_msg = ensure_gitignore(root, args.dry_run)

    print(policy_msg)
    print(gitignore_msg)
    print(f"[OK] canonical privacy policy path: {root / 'privacy-policy.md'}")

    changed_count = int(changed_policy) + int(changed_gitignore)
    if args.dry_run:
        print(f"[DRY-RUN] planned changes: {changed_count}")
    else:
        print(f"[OK] changed files: {changed_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
