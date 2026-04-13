from __future__ import annotations

import json
from copy import deepcopy


def test_analyze_drive_references_accepts_drive_only_payload(fresh_server_module, sample_courses_payload):
    summary = fresh_server_module.analyze_drive_references(sample_courses_payload)

    assert summary["ok"] is True
    assert summary["validDriveRefs"] == 4
    assert summary["localRefs"] == 0
    assert summary["invalidRefs"] == 0


def test_analyze_drive_references_flags_local_refs(fresh_server_module, sample_courses_payload):
    payload = deepcopy(sample_courses_payload)
    payload["categories"][0]["routes"][0]["courses"][0]["modules"][0]["classes"][0]["files"]["video"] = "local:C:/video.mp4"

    summary = fresh_server_module.analyze_drive_references(payload)

    assert summary["ok"] is False
    assert summary["localRefs"] == 1
    assert summary["issues"][0]["reason"] == "local_ref_detected"


def test_init_cache_builds_bootstrap_and_metadata(fresh_server_module, temp_cache_env):
    fresh_server_module.init_cache()

    assert fresh_server_module.cache_file_path == str(temp_cache_env["cache_file"])
    assert fresh_server_module.cache_source == "viewer"
    assert fresh_server_module.courses_cache["stats"]["totalCourses"] == 1
    assert fresh_server_module.bootstrap_cache["categories"][0]["routes"][0]["courses"][0]["modules"][0]["classes"] == 2
    assert fresh_server_module.cache_meta["cache_file_name"] == "courses_cache.json"
    assert fresh_server_module.cache_meta["source"] == "viewer"


def test_load_progress_payload_handles_invalid_json(fresh_server_module, temp_cache_env):
    progress_file = temp_cache_env["data_path"] / "progress.json"
    progress_file.write_text("{invalid", encoding="utf-8")

    assert fresh_server_module._load_progress_payload() == {}


def test_load_progress_payload_returns_only_dicts(fresh_server_module, temp_cache_env):
    progress_file = temp_cache_env["data_path"] / "progress.json"
    progress_file.write_text(json.dumps(["unexpected"]), encoding="utf-8")

    assert fresh_server_module._load_progress_payload() == {}
