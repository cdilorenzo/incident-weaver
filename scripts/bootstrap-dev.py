from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
LOCK = ROOT / "requirements-dev.lock.txt"


def main() -> int:
    if sys.version_info[:2] != (3, 13):
        print("IncidentWeaver requires Python 3.13.", file=sys.stderr)
        return 2
    if not LOCK.exists():
        print(f"Missing {LOCK}.", file=sys.stderr)
        return 2

    venv.EnvBuilder(with_pip=True, clear=False).create(VENV)
    python = VENV / ("Scripts" if os.name == "nt" else "bin") / "python"
    subprocess.run([str(python), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "--requirement", str(LOCK)], check=True)
    print(f"Development environment ready: {VENV}")
    print("Configure VS Code/Pylance to use .venv.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
