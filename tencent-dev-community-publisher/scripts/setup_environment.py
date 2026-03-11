#!/usr/bin/env python3
"""
Environment setup for Tencent Developer Community Publisher skill.
"""

import os
import subprocess
import sys
import venv
from pathlib import Path
from typing import List, Optional


class SkillEnvironment:
    """Manages skill-specific virtual environment."""

    def __init__(self) -> None:
        self.skill_dir = Path(__file__).parent.parent
        self.venv_dir = self.skill_dir / ".venv"
        self.requirements_file = self.skill_dir / "requirements.txt"

        if os.name == "nt":
            self.venv_python = self.venv_dir / "Scripts" / "python.exe"
            self.venv_pip = self.venv_dir / "Scripts" / "pip.exe"
        else:
            self.venv_python = self.venv_dir / "bin" / "python"
            self.venv_pip = self.venv_dir / "bin" / "pip"

    def ensure_venv(self) -> bool:
        if self.is_in_skill_venv():
            print("✅ Already running in skill virtual environment")
            return True

        if not self.venv_dir.exists():
            print(f"🔧 Creating virtual environment in {self.venv_dir.name}/")
            try:
                venv.create(self.venv_dir, with_pip=True)
                print("✅ Virtual environment created")
            except Exception as e:
                print(f"❌ Failed to create venv: {e}")
                return False

        if self.requirements_file.exists():
            print("📦 Installing dependencies...")
            try:
                subprocess.run(
                    [str(self.venv_pip), "install", "--upgrade", "pip"],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                subprocess.run(
                    [str(self.venv_pip), "install", "-r", str(self.requirements_file)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                print("✅ Dependencies installed")

                print("🌐 Installing Google Chrome runtime for Patchright...")
                try:
                    subprocess.run(
                        [str(self.venv_python), "-m", "patchright", "install", "chrome"],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    print("✅ Chrome runtime installed")
                except subprocess.CalledProcessError as e:
                    print(f"⚠️ Warning: failed to install Chrome runtime: {e}")
                    print("   You can run manually: python -m patchright install chrome")

                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install dependencies: {e}")
                return False

        print("⚠️ No requirements.txt found, skipping dependency installation")
        return True

    def is_in_skill_venv(self) -> bool:
        if hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        ):
            return Path(sys.prefix) == self.venv_dir
        return False

    def get_python_executable(self) -> str:
        if self.venv_python.exists():
            return str(self.venv_python)
        return sys.executable

    def run_script(self, script_name: str, args: Optional[List[str]] = None) -> int:
        script_path = self.skill_dir / "scripts" / script_name
        if not script_path.exists():
            print(f"❌ Script not found: {script_path}")
            return 1

        if not self.ensure_venv():
            print("❌ Failed to set up environment")
            return 1

        cmd = [str(self.venv_python), str(script_path)]
        if args:
            cmd.extend(args)

        print(f"🚀 Running: {script_name}")
        try:
            result = subprocess.run(cmd)
            return result.returncode
        except Exception as e:
            print(f"❌ Failed to run script: {e}")
            return 1

    def activate_instructions(self) -> str:
        if os.name == "nt":
            return f"Run: {self.venv_dir / 'Scripts' / 'activate.bat'}"
        return f"Run: source {self.venv_dir / 'bin' / 'activate'}"


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Setup Tencent Developer Publisher skill environment"
    )
    parser.add_argument("--check", action="store_true", help="Check environment")
    parser.add_argument("--run", help="Run a script with venv")
    parser.add_argument("args", nargs="*", help="Arguments for script")
    args = parser.parse_args()

    env = SkillEnvironment()

    if args.check:
        if env.venv_dir.exists():
            print(f"✅ Virtual environment exists: {env.venv_dir}")
            print(f"   Python: {env.get_python_executable()}")
            print(f"   To activate manually: {env.activate_instructions()}")
        else:
            print("❌ No virtual environment found")
        return 0

    if args.run:
        return env.run_script(args.run, args.args)

    if env.ensure_venv():
        print("\n✅ Environment ready!")
        print(f"   Virtual env: {env.venv_dir}")
        print(f"   Python: {env.get_python_executable()}")
        return 0

    print("\n❌ Environment setup failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
