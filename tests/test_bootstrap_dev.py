from __future__ import annotations

import importlib.util
import tempfile
import venv
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "bootstrap-dev.py"
SPEC = importlib.util.spec_from_file_location("bootstrap_dev", SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_resolve_venv_python_uses_windows_layout() -> None:
    root = Path("workspace") / ".venv"

    assert MODULE.resolve_venv_python(root, "nt") == root / "Scripts" / "python.exe"


def test_resolve_venv_python_uses_posix_layout() -> None:
    root = Path("workspace") / ".venv"

    assert MODULE.resolve_venv_python(root, "posix") == root / "bin" / "python"


def test_resolve_venv_python_finds_current_platform_temporary_interpreter() -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        venv_dir = Path(temporary_directory) / ".venv"
        venv.EnvBuilder(with_pip=False).create(venv_dir)

        interpreter = MODULE.resolve_venv_python(venv_dir)

        assert interpreter.is_file()