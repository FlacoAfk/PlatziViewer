from __future__ import annotations

import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_frontend_views_render_without_runtime_errors():
    result = subprocess.run(
        [
            "node",
            str(PROJECT_ROOT / "tests" / "js_smoke_runner.mjs"),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
