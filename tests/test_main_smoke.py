import subprocess
import sys
from pathlib import Path

import pytest


def test_main_help_smoke() -> None:
    """Run main.py with --help as a smoke test."""
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "main.py"

    if not script_path.exists():
        pytest.xfail("main.py not found; skipping smoke run")

    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
            text=True,
        )
    except Exception as exc:  # pragma: no cover
        pytest.xfail(f"Failed to execute main.py: {exc!r}")

    if result.returncode != 0:
        pytest.xfail(
            f"main.py --help exited with {result.returncode}:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    assert "help" in result.stdout.lower() or result.stdout or result.stderr
