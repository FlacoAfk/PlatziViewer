from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def import_fresh(module_name: str):
    sys.modules.pop(module_name, None)
    importlib.invalidate_caches()
    return importlib.import_module(module_name)


@pytest.fixture
def sample_courses_payload():
    return {
        "categories": [
            {
                "id": "dev",
                "name": "Desarrollo",
                "icon": "💻",
                "description": "Backend y frontend",
                "type": "category",
                "courseCount": 1,
                "routes": [
                    {
                        "id": "backend",
                        "name": "Ruta Backend",
                        "url": "https://platzi.com/ruta/backend/",
                        "isCourse": False,
                        "courseCount": 1,
                        "courses": [
                            {
                                "id": "api-course",
                                "name": "Curso de APIs",
                                "url": "https://platzi.com/cursos/api-course/",
                                "folderName": "01. Curso de APIs",
                                "moduleCount": 1,
                                "classCount": 2,
                                "foundInDrive": True,
                                "modules": [
                                    {
                                        "name": "Fundamentos",
                                        "classes": [
                                            {
                                                "name": "Introducción",
                                                "hasVideo": True,
                                                "hasSummary": True,
                                                "hasReading": False,
                                                "files": {
                                                    "video": "1ValidDriveRefAA",
                                                    "summary": "1ValidDriveRefAB",
                                                },
                                                "resources": [
                                                    {
                                                        "name": "slides.pdf",
                                                        "file": "1ValidDriveRefAC",
                                                    }
                                                ],
                                            },
                                            {
                                                "name": "HTTP práctico",
                                                "hasVideo": False,
                                                "hasHtml": True,
                                                "files": {
                                                    "html": "1ValidDriveRefAD",
                                                },
                                                "resources": [],
                                            },
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
        "stats": {
            "totalCategories": 1,
            "totalRoutes": 1,
            "totalCourses": 1,
            "totalClasses": 2,
        },
    }


@pytest.fixture
def temp_cache_env(tmp_path, monkeypatch, sample_courses_payload):
    viewer_path = tmp_path / "viewer"
    data_path = tmp_path / "data"
    viewer_path.mkdir()
    data_path.mkdir()

    cache_file = viewer_path / "courses_cache.json"
    cache_file.write_text(json.dumps(sample_courses_payload), encoding="utf-8")

    monkeypatch.setenv("PLATZI_VIEWER_PATH", str(viewer_path))
    monkeypatch.setenv("PLATZI_DATA_PATH", str(data_path))
    monkeypatch.setenv("PLATZI_PREFER_DATA_CACHE", "0")
    monkeypatch.setenv("PORT", "18080")
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PUBLIC_HOST", "127.0.0.1")

    return {
        "viewer_path": viewer_path,
        "data_path": data_path,
        "cache_file": cache_file,
    }


@pytest.fixture
def fresh_server_module(temp_cache_env):
    return import_fresh("server")
