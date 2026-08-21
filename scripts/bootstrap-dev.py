from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
LOCK = ROOT / "requirements-dev.lock.txt"


def resolve_venv_python(venv_dir: Path, platform: str | None = None) -> Path:
    """Return the canonical interpreter path for a virtual environment."""

    platform_name = os.name if platform is None else platform
    if platform_name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    if platform_name == "posix":
        return venv_dir / "bin" / "python"
    raise ValueError(f"Unsupported platform: {platform_name}")


def main() -> int:
    if sys.version_info[:2] != (3, 13):
        print("IncidentWeaver requires Python 3.13.", file=sys.stderr)
        return 2
    if not LOCK.exists():
        print(f"Missing {LOCK}.", file=sys.stderr)
        return 2

    venv.EnvBuilder(with_pip=True, clear=False).create(VENV)
    python = resolve_venv_python(VENV)
    if not python.is_file():
        print(f"Created virtual environment is missing its interpreter: {python}", file=sys.stderr)
        return 2
    subprocess.run([str(python), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "--requirement", str(LOCK)], check=True)
    print(f"Development environment ready: {VENV}")
    print("Configure VS Code/Pylance to use .venv.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
