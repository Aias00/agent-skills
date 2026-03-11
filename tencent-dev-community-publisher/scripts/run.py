#!/usr/bin/env python3
"""
Universal runner for Tencent Developer Community Publisher scripts
Ensures all scripts run with the correct virtual environment.
"""

import os
import subprocess
import sys
from pathlib import Path


def get_venv_python() -> Path:
    """Get the virtual environment Python executable."""
    skill_dir = Path(__file__).parent.parent
    venv_dir = skill_dir / ".venv"

    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def ensure_venv() -> Path:
    """Ensure virtual environment exists."""
    skill_dir = Path(__file__).parent.parent
    venv_dir = skill_dir / ".venv"
    setup_script = skill_dir / "scripts" / "setup_environment.py"

    if not venv_dir.exists():
        print("🔧 First-time setup: creating virtual environment...")
        result = subprocess.run([sys.executable, str(setup_script)])
        if result.returncode != 0:
            print("❌ Failed to set up environment")
            sys.exit(1)
        print("✅ Environment ready")

    return get_venv_python()


def resolve_script_path(skill_dir: Path, raw_script_name: str) -> Path:
    """Resolve script path safely inside the skill scripts directory."""
    scripts_dir = (skill_dir / "scripts").resolve()

    script_name = raw_script_name.strip()
    if script_name.startswith("scripts/"):
        script_name = script_name[8:]

    candidate = Path(script_name)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("Invalid script path. Path traversal is not allowed.")

    if candidate.parent != Path("."):
        raise ValueError("Invalid script path. Please provide script filename only.")

    if not script_name.endswith(".py"):
        candidate = candidate.with_suffix(".py")

    script_path = (scripts_dir / candidate.name).resolve()
    if script_path.parent != scripts_dir:
        raise ValueError("Invalid script path.")

    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {candidate.name}")

    return script_path


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python run.py <script_name> [args...]")
        print("\nAvailable scripts:")
        print("  auth_manager.py      - Handle authentication")
        print("  publisher.py         - Publish article")
        print("  check_permissions.py - Pre-flight environment checks")
        sys.exit(1)

    script_name = sys.argv[1]
    script_args = sys.argv[2:]

    skill_dir = Path(__file__).parent.parent
    try:
        script_path = resolve_script_path(skill_dir, script_name)
    except Exception as e:
        print(f"❌ {e}")
        print(f"   Working directory: {Path.cwd()}")
        print(f"   Skill directory: {skill_dir}")
        sys.exit(1)

    venv_python = ensure_venv()
    cmd = [str(venv_python), str(script_path)] + script_args

    try:
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
