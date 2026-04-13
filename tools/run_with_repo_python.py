from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _candidate_interpreters(repo_root: Path) -> list[Path]:
    return [
        repo_root / ".venv" / "Scripts" / "python.exe",
        repo_root / ".venv" / "bin" / "python",
        repo_root / "venv" / "Scripts" / "python.exe",
        repo_root / "venv" / "bin" / "python",
    ]


def _resolve_python(repo_root: Path) -> str:
    for candidate in _candidate_interpreters(repo_root):
        if candidate.exists():
            return str(candidate.resolve())
    return str(Path(sys.executable).resolve())


def main(argv: list[str]) -> int:
    if not argv:
        print("Usage: python tools/run_with_repo_python.py <args...>", file=sys.stderr)
        return 2

    repo_root = Path(__file__).resolve().parents[1]
    interpreter = _resolve_python(repo_root)
    completed = subprocess.run([interpreter, *argv], cwd=repo_root)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
