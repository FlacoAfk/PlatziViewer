from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_package_scripts_are_real_commands():
    package_json = json.loads((PROJECT_ROOT / "package.json").read_text(encoding="utf-8"))
    scripts = package_json["scripts"]
    serialized_scripts = json.dumps(scripts).lower()

    assert "not implemented" not in serialized_scripts
    assert "removed for shared runtime build" not in serialized_scripts
    assert scripts["test"].startswith("python tools/run_with_repo_python.py -m pytest")
    assert "ruff check ." in scripts["lint"]
    assert "eslint@8.57.1 js --ext .js" in scripts["lint"]
    assert "stylelint" in scripts["lint"]


def test_gitignore_covers_generated_quality_artifacts():
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

    for expected_entry in [
        "dist/",
        "build/",
        "courses_cache.json",
        "progress.json",
        ".ruff_cache/",
        ".eslintcache",
    ]:
        assert expected_entry in gitignore
