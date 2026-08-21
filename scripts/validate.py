from __future__ import annotations

import os
import tempfile
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin")
PYTHON = BIN / ("python.exe" if os.name == "nt" else "python")
PYRIGHT = BIN / ("pyright.exe" if os.name == "nt" else "pyright")


def run(name: str, command: list[str], cwd: Path = ROOT, env: dict[str, str] | None = None) -> bool:
    print(f"\n$ {' '.join(command)}")
    try:
        completed = subprocess.run(command, cwd=cwd, env=env, check=False)
    except OSError as exc:
        print(f"[FAIL] {name}: {exc}")
        return False
    result = completed.returncode == 0
    print(f"[{'PASS' if result else 'FAIL'}] {name}")
    return result


def main() -> int:
    if not PYTHON.exists() or not PYRIGHT.exists():
        print(f"[FAIL] environment: canonical interpreter missing at {PYTHON}")
        return 1
    wheel_dir = Path(tempfile.mkdtemp(prefix="incident-weaver-wheels-"))
    checks: list[tuple[str, list[str], Path, dict[str, str] | None]] = [
        ("pyright", [str(PYRIGHT), "--project", "pyrightconfig.json"], ROOT, None),
        ("pytest", [str(PYTHON), "-m", "pytest"], ROOT, None),
        ("public FastMCP import", [str(PYTHON), "-c", "from mcp.server.fastmcp import FastMCP; print(FastMCP)"], ROOT, None),
        ("ai-runtime build", [str(PYTHON), "-m", "pip", "wheel", "--no-deps", "--wheel-dir", str(wheel_dir), "."], ROOT / "src" / "ai-runtime", None),
        ("ops-mcp build", [str(PYTHON), "-m", "pip", "wheel", "--no-deps", "--wheel-dir", str(wheel_dir), "."], ROOT / "src" / "ops-mcp", None),
        ("dotnet format", ["dotnet", "format", "IncidentWeaver.sln", "--verify-no-changes", "--verbosity", "minimal"], ROOT, None),
        ("dotnet build", ["dotnet", "build", "IncidentWeaver.sln", "--nologo", "--verbosity", "minimal"], ROOT, None),
        ("dotnet test", ["dotnet", "test", "IncidentWeaver.sln", "--nologo", "--verbosity", "minimal"], ROOT, None),
        ("docker compose config", ["docker", "compose", "config"], ROOT, {**os.environ, "INCIDENTWEAVER_KNOWLEDGE_DB_PASSWORD": "validation-placeholder"}),
        ("git diff --check", ["git", "diff", "--check"], ROOT, None),
    ]
    results = [run(name, command, cwd, env) for name, command, cwd, env in checks]
    failures = len(results) - sum(results)
    print(f"\nQUALITY GATE {'PASSED' if failures == 0 else 'FAILED'}")
    print(f"{len(results)} mandatory checks, {failures} failed")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
