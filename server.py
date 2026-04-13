"""
Platzi Viewer - Drive API Server
Serves content from Google Drive via the service account API.
Course structure is loaded from courses_cache.json (built by rebuild_cache_drive.py).
"""

import os
import sys
import json
import re
import errno
import gzip
import unicodedata
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import unquote, urlparse
import threading
import time
import subprocess
import shutil
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIEWER_PATH = os.environ.get("PLATZI_VIEWER_PATH", BASE_DIR)
DATA_PATH = os.environ.get("PLATZI_DATA_PATH", VIEWER_PATH)
PORT = int(os.environ.get("PORT", "8080"))
BIND_HOST = os.environ.get("HOST", "127.0.0.1")
DISPLAY_HOST = os.environ.get("PUBLIC_HOST", BIND_HOST)
PROGRESS_FILE = os.path.join(DATA_PATH, "progress.json")
VIEWER_CACHE_FILE = os.path.join(VIEWER_PATH, "courses_cache.json")
DATA_CACHE_FILE = os.path.join(DATA_PATH, "courses_cache.json")
MAX_PROGRESS_BYTES = int(os.environ.get("MAX_PROGRESS_BYTES", "2097152"))  # 2MB
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
EMPTY_STATS = {
    "totalCategories": 0,
    "totalRoutes": 0,
    "totalCourses": 0,
    "totalClasses": 0,
}

# Caché global
courses_cache = None
bootstrap_cache = None
cache_meta = {}
cache_lock = threading.Lock()
cache_reload_lock = threading.Lock()
cache_mtime = None
cache_file_path = None
cache_source = "none"
invalid_cache_files = {}

full_cache_json_bytes = b""
full_cache_json_gzip_bytes = b""
bootstrap_cache_json_bytes = b""
bootstrap_cache_json_gzip_bytes = b""
cache_meta_json_bytes = b""
cache_meta_json_gzip_bytes = b""

# Google Drive service (lazy loaded)
_drive_service = None
_drive_service_error = None
_ffmpeg_executable = None
_ffmpeg_checked = False
DRIVE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,}$")
compat_stream_lock = threading.Lock()
compat_stream_stats = {
    "totalRequests": 0,
    "successfulStreams": 0,
    "failedStreams": 0,
    "totalBytes": 0,
    "lastFileId": None,
    "lastError": None,
    "lastDurationSec": None,
    "lastSpeedMBps": None,
    "lastMode": None,
    "lastAt": None,
}

REPAIRED_VIDEOS_DIR = os.path.join(DATA_PATH, "repaired_videos")
REPAIR_STATE_FILE = os.path.join(DATA_PATH, "repair_state.json")
REPAIR_MAX_MB = max(100, int(os.environ.get("PLATZI_REPAIRED_MAX_MB", "5000")))
REPAIR_LOCK_TTL_SECONDS = max(300, int(os.environ.get("PLATZI_REPAIR_LOCK_TTL_SECONDS", "1800")))
REPAIR_FAILED_RETENTION_SECONDS = int(os.environ.get("PLATZI_REPAIR_FAILED_RETENTION_SECONDS", str(7 * 24 * 3600)))

repair_state_lock = threading.Lock()
repair_state = {}
active_repairs = {}


def _now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _repair_paths(file_id):
    safe_file_id = str(file_id or "").strip()
    base = os.path.abspath(REPAIRED_VIDEOS_DIR)
    artifact = os.path.abspath(os.path.join(base, f"{safe_file_id}.mp4"))
    meta = os.path.abspath(os.path.join(base, f"{safe_file_id}.meta.json"))
    lock = os.path.abspath(os.path.join(base, f"{safe_file_id}.lock"))
    return artifact, meta, lock


def _is_within_directory(path_value, directory):
    try:
        abs_path = os.path.abspath(path_value)
        abs_dir = os.path.abspath(directory)
        common = os.path.commonpath([abs_path, abs_dir])
        return common == abs_dir
    except Exception:
        return False


def _persist_repair_state_locked():
    state_dir = os.path.dirname(REPAIR_STATE_FILE)
    if state_dir:
        os.makedirs(state_dir, exist_ok=True)

    temp_path = f"{REPAIR_STATE_FILE}.tmp"
    payload = {
        "updatedAt": _now_iso(),
        "repairs": repair_state,
    }
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(temp_path, REPAIR_STATE_FILE)


def _load_repair_state():
    if not os.path.exists(REPAIR_STATE_FILE):
        return {}
    try:
        with open(REPAIR_STATE_FILE, "r", encoding="utf-8") as f:
            payload = json.load(f)
        repairs = payload.get("repairs") if isinstance(payload, dict) else payload
        if isinstance(repairs, dict):
            return repairs
    except Exception as error:
        print(f"[WARN] Could not load repair state: {error}")
    return {}


def _is_artifact_ready(file_id):
    artifact_path, meta_path, _ = _repair_paths(file_id)
    if not _is_within_directory(artifact_path, REPAIRED_VIDEOS_DIR):
        return False
    if not os.path.exists(artifact_path) or os.path.getsize(artifact_path) <= 0:
        return False
    if not os.path.exists(meta_path):
        return False
    return True


def _set_repair_state(file_id, **updates):
    with repair_state_lock:
        entry = dict(repair_state.get(file_id) or {})
        entry.setdefault("fileId", file_id)
        entry.setdefault("requestedAt", _now_iso())
        entry.update(updates)
        repair_state[file_id] = entry
        _persist_repair_state_locked()
        return dict(entry)


def _repair_health_summary():
    with repair_state_lock:
        entries = list(repair_state.values())

    total = len(entries)
    completed = sum(1 for item in entries if item.get("status") == "completed")
    failed = sum(1 for item in entries if item.get("status") == "failed")
    in_progress = sum(1 for item in entries if item.get("status") == "in_progress")
    pending = sum(1 for item in entries if item.get("status") == "pending")

    disk_bytes = 0
    try:
        base = Path(REPAIRED_VIDEOS_DIR)
        if base.exists():
            for item in base.glob("*.mp4"):
                try:
                    disk_bytes += item.stat().st_size
                except OSError:
                    continue
    except Exception:
        pass

    return {
        "totalRepairs": total,
        "successfulRepairs": completed,
        "failedRepairs": failed,
        "inProgress": in_progress,
        "pending": pending,
        "diskUsageMB": round(disk_bytes / (1024 * 1024), 2),
        "diskLimitMB": REPAIR_MAX_MB,
    }


def _cleanup_old_failed_states_locked(now_epoch):
    removed_any = False
    for file_id in list(repair_state.keys()):
        entry = repair_state.get(file_id) or {}
        if entry.get("status") != "failed":
            continue
        failed_at = entry.get("failedAt") or entry.get("updatedAt") or entry.get("startedAt")
        if not failed_at:
            continue
        try:
            failed_epoch = time.mktime(time.strptime(failed_at, "%Y-%m-%dT%H:%M:%SZ"))
        except Exception:
            continue
        if now_epoch - failed_epoch > REPAIR_FAILED_RETENTION_SECONDS:
            del repair_state[file_id]
            removed_any = True
    return removed_any


def _cleanup_repaired_artifacts():
    os.makedirs(REPAIRED_VIDEOS_DIR, exist_ok=True)
    max_bytes = REPAIR_MAX_MB * 1024 * 1024

    files = []
    total_bytes = 0
    for item in Path(REPAIRED_VIDEOS_DIR).glob("*.mp4"):
        try:
            stats = item.stat()
        except OSError:
            continue
        total_bytes += stats.st_size
        files.append((stats.st_mtime, stats.st_size, item))

    if total_bytes > max_bytes:
        files.sort(key=lambda pair: pair[0])
        for _, size, path_obj in files:
            if total_bytes <= max_bytes:
                break
            file_id = path_obj.stem
            meta_path = Path(REPAIRED_VIDEOS_DIR) / f"{file_id}.meta.json"
            try:
                path_obj.unlink(missing_ok=True)
                meta_path.unlink(missing_ok=True)
                total_bytes -= size
            except OSError:
                continue

            with repair_state_lock:
                if file_id in repair_state:
                    entry = dict(repair_state[file_id])
                    entry["status"] = "evicted"
                    entry["updatedAt"] = _now_iso()
                    entry["error"] = "artifact_evicted_by_cleanup"
                    repair_state[file_id] = entry
                    _persist_repair_state_locked()

    now_epoch = time.time()
    with repair_state_lock:
        if _cleanup_old_failed_states_locked(now_epoch):
            _persist_repair_state_locked()


def _init_repair_system():
    os.makedirs(REPAIRED_VIDEOS_DIR, exist_ok=True)
    loaded = _load_repair_state()
    with repair_state_lock:
        repair_state.clear()
        if isinstance(loaded, dict):
            repair_state.update(loaded)

    # Recover statuses for artifacts that already exist in disk.
    for artifact in Path(REPAIRED_VIDEOS_DIR).glob("*.mp4"):
        file_id = artifact.stem
        if not _is_artifact_ready(file_id):
            continue
        size = 0
        try:
            size = artifact.stat().st_size
        except OSError:
            pass
        _set_repair_state(
            file_id,
            status="completed",
            completedAt=_now_iso(),
            updatedAt=_now_iso(),
            progress=1.0,
            error=None,
            artifactPath=f"repaired_videos/{file_id}.mp4",
            artifactSize=size,
            ffmpegMode="remux_audio",
        )

    # Remove stale locks.
    now_epoch = time.time()
    for lock_file in Path(REPAIRED_VIDEOS_DIR).glob("*.lock"):
        try:
            age = now_epoch - lock_file.stat().st_mtime
            if age > REPAIR_LOCK_TTL_SECONDS:
                lock_file.unlink(missing_ok=True)
        except OSError:
            continue

    _cleanup_repaired_artifacts()


def _parse_single_range(range_header, total_size):
    if not range_header:
        return None
    text = str(range_header).strip()
    if "," in text or not text.startswith("bytes="):
        raise ValueError("invalid_range")
    value = text[6:].strip()
    if "-" not in value:
        raise ValueError("invalid_range")
    start_text, end_text = value.split("-", 1)
    if start_text == "" and end_text == "":
        raise ValueError("invalid_range")

    if start_text == "":
        length = int(end_text)
        if length <= 0:
            raise ValueError("invalid_range")
        if length >= total_size:
            return 0, total_size - 1
        return total_size - length, total_size - 1

    start = int(start_text)
    end = total_size - 1 if end_text == "" else int(end_text)
    if start < 0 or end < 0 or start > end or start >= total_size:
        raise ValueError("range_not_satisfiable")
    end = min(end, total_size - 1)
    return start, end


def _repair_video_file(file_id, output_path, server_port):
    ffmpeg_executable = _get_ffmpeg_executable()
    if not ffmpeg_executable:
        raise RuntimeError("ffmpeg_not_available")

    source_url = f"http://127.0.0.1:{server_port}/drive/files/{file_id}?raw=1"
    cmd = [
        ffmpeg_executable,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-fflags",
        "+genpts+igndts+discardcorrupt",
        "-avoid_negative_ts",
        "make_zero",
        "-i",
        source_url,
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-ar",
        "48000",
        "-af",
        "aresample=async=1:min_hard_comp=0.100:first_pts=0",
        "-movflags",
        "+faststart",
        "-f",
        "mp4",
        output_path,
    ]

    completed = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60 * 60 * 2,
        check=False,
        creationflags=CREATE_NO_WINDOW,
    )

    if completed.returncode != 0:
        stderr_text = (completed.stderr or b"").decode("utf-8", errors="ignore").strip()
        detail = stderr_text[:300] if stderr_text else f"ffmpeg_exit_{completed.returncode}"
        raise RuntimeError(f"ffmpeg_failed:{detail}")

    return {
        "ffmpegMode": "remux_audio",
        "artifactSize": os.path.getsize(output_path),
    }


def _repair_worker(file_id, server_port):
    artifact_path, meta_path, lock_path = _repair_paths(file_id)
    try:
        _set_repair_state(
            file_id,
            status="in_progress",
            startedAt=_now_iso(),
            updatedAt=_now_iso(),
            progress=0.05,
            error=None,
            artifactPath=f"repaired_videos/{file_id}.mp4",
            artifactSize=0,
            ffmpegMode="pending",
        )

        result = _repair_video_file(file_id, artifact_path, server_port)

        meta_payload = {
            "fileId": file_id,
            "ffmpegMode": result.get("ffmpegMode", "remux_audio"),
            "fileSize": _safe_int(result.get("artifactSize"), default=os.path.getsize(artifact_path)),
            "repairedAt": _now_iso(),
        }
        with open(meta_path, "w", encoding="utf-8") as meta_file:
            json.dump(meta_payload, meta_file, ensure_ascii=False)

        _set_repair_state(
            file_id,
            status="completed",
            completedAt=_now_iso(),
            updatedAt=_now_iso(),
            progress=1.0,
            error=None,
            artifactPath=f"repaired_videos/{file_id}.mp4",
            artifactSize=meta_payload["fileSize"],
            ffmpegMode=meta_payload["ffmpegMode"],
        )

        _cleanup_repaired_artifacts()

    except Exception as error:
        _set_repair_state(
            file_id,
            status="failed",
            failedAt=_now_iso(),
            updatedAt=_now_iso(),
            progress=0.0,
            error=str(error),
            artifactPath=f"repaired_videos/{file_id}.mp4",
            ffmpegMode="failed",
        )
        try:
            os.remove(artifact_path)
        except OSError:
            pass
        try:
            os.remove(meta_path)
        except OSError:
            pass
    finally:
        with repair_state_lock:
            active_repairs.pop(file_id, None)
        try:
            os.remove(lock_path)
        except OSError:
            pass


def _get_ffmpeg_executable():
    global _ffmpeg_executable, _ffmpeg_checked

    if _ffmpeg_checked:
        return _ffmpeg_executable

    candidates = []
    env_path = os.environ.get("FFMPEG_PATH", "").strip()
    if env_path:
        candidates.append(env_path)

    which_ffmpeg = shutil.which("ffmpeg")
    if which_ffmpeg:
        candidates.append(which_ffmpeg)

    # When running as a frozen PyInstaller .exe, check for ffmpeg next to the
    # executable and inside the bundled temp directory.
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        candidates.append(os.path.join(exe_dir, "ffmpeg.exe"))
        candidates.append(os.path.join(exe_dir, "ffmpeg", "ffmpeg.exe"))
        candidates.append(os.path.join(exe_dir, "ffmpeg", "bin", "ffmpeg.exe"))
        if hasattr(sys, "_MEIPASS"):
            candidates.append(os.path.join(sys._MEIPASS, "ffmpeg.exe"))
            candidates.append(os.path.join(sys._MEIPASS, "ffmpeg", "ffmpeg.exe"))

    if os.name == "nt":
        candidates.extend(
            [
                r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
                r"C:\ffmpeg\bin\ffmpeg.exe",
                r"C:\Ffmpeg\bin\ffmpeg.exe",
            ]
        )

    seen = set()
    unique_candidates = []
    for item in candidates:
        if not item:
            continue
        normalized = os.path.abspath(item)
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_candidates.append(normalized)

    for candidate in unique_candidates:
        try:
            completed = subprocess.run(
                [candidate, "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=4,
                check=False,
                creationflags=CREATE_NO_WINDOW
            )
            if completed.returncode == 0:
                _ffmpeg_executable = candidate
                break
        except Exception:
            continue

    _ffmpeg_checked = True
    return _ffmpeg_executable


def analyze_drive_references(data):
    """Validate that file references in cache are Drive IDs (not local refs)."""
    summary = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "totalRefs": 0,
        "validDriveRefs": 0,
        "localRefs": 0,
        "invalidRefs": 0,
        "emptyRefs": 0,
        "issues": [],
    }

    def add_issue(location, value, reason):
        if len(summary["issues"]) < 30:
            summary["issues"].append({"location": location, "value": value, "reason": reason})

    def validate_ref(ref, location):
        summary["totalRefs"] += 1

        if ref is None:
            summary["emptyRefs"] += 1
            return

        if not isinstance(ref, str):
            summary["invalidRefs"] += 1
            add_issue(location, str(ref), "non_string_ref")
            return

        value = ref.strip()
        if not value:
            summary["emptyRefs"] += 1
            return

        if value.startswith("local:"):
            summary["localRefs"] += 1
            add_issue(location, value, "local_ref_detected")
            return

        if value.startswith("http://") or value.startswith("https://"):
            summary["invalidRefs"] += 1
            add_issue(location, value, "url_ref_detected")
            return

        if not DRIVE_ID_RE.match(value):
            summary["invalidRefs"] += 1
            add_issue(location, value, "invalid_drive_id_format")
            return

        summary["validDriveRefs"] += 1

    categories = (data or {}).get("categories", [])
    for cat_idx, category in enumerate(categories):
        routes = category.get("routes", [])
        for route_idx, route in enumerate(routes):
            courses = [route] if route.get("isCourse") else route.get("courses", [])
            for course_idx, course in enumerate(courses):
                modules = course.get("modules", [])
                for mod_idx, module in enumerate(modules):
                    classes = module.get("classes", [])
                    for cls_idx, cls in enumerate(classes):
                        files = cls.get("files", {}) or {}
                        for field_name, ref in files.items():
                            validate_ref(
                                ref,
                                f"cat[{cat_idx}].route[{route_idx}].course[{course_idx}].mod[{mod_idx}].class[{cls_idx}].files.{field_name}",
                            )

                        resources = cls.get("resources", []) or []
                        for res_idx, resource in enumerate(resources):
                            validate_ref(
                                resource.get("file"),
                                f"cat[{cat_idx}].route[{route_idx}].course[{course_idx}].mod[{mod_idx}].class[{cls_idx}].resources[{res_idx}].file",
                            )

    summary["ok"] = summary["localRefs"] == 0 and summary["invalidRefs"] == 0
    summary["message"] = "drive_only_ok" if summary["ok"] else "drive_only_issues_found"
    return summary


def get_drive_service():
    global _drive_service, _drive_service_error
    if _drive_service is None:
        try:
            from drive_service import drive_service

            _drive_service = drive_service
            _drive_service_error = None
        except Exception as e:
            _drive_service_error = str(e)
            print(f"[WARN] Drive service not available: {_drive_service_error}")
    return _drive_service


def get_drive_service_error():
    return _drive_service_error


def _empty_courses_payload():
    return {"categories": [], "stats": dict(EMPTY_STATS)}


def _normalize_stats(stats):
    raw = stats if isinstance(stats, dict) else {}
    return {
        "totalCategories": int(raw.get("totalCategories", 0) or 0),
        "totalRoutes": int(raw.get("totalRoutes", 0) or 0),
        "totalCourses": int(raw.get("totalCourses", 0) or 0),
        "totalClasses": int(raw.get("totalClasses", 0) or 0),
    }


def _payload_to_bytes(payload):
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _load_progress_payload():
    if not os.path.exists(PROGRESS_FILE):
        return {}

    try:
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        print(f"[WARN] Could not load progress file '{PROGRESS_FILE}': {error}")
        return {}

    return data if isinstance(data, dict) else {}


def _gzip_payload(raw_bytes):
    return gzip.compress(raw_bytes, compresslevel=5) if raw_bytes else b""


def _is_cache_data_valid(data):
    if not isinstance(data, dict):
        return False
    categories = data.get("categories")
    if not isinstance(categories, list):
        return False
    stats = data.get("stats")
    if stats is not None and not isinstance(stats, dict):
        return False
    return True


def _get_cache_preference_order():
    prefer_data = str(os.environ.get("PLATZI_PREFER_DATA_CACHE", "1")).strip().lower() in {"1", "true", "yes", "on"}
    if prefer_data:
        return [DATA_CACHE_FILE, VIEWER_CACHE_FILE]
    return [VIEWER_CACHE_FILE, DATA_CACHE_FILE]


def _cache_source_from_path(path):
    if not path:
        return "none"
    normalized = os.path.abspath(path)
    if normalized == os.path.abspath(DATA_CACHE_FILE):
        return "data"
    if normalized == os.path.abspath(VIEWER_CACHE_FILE):
        return "viewer"
    return "external"


def _mark_cache_invalid(path, mtime):
    if path and mtime is not None:
        invalid_cache_files[path] = float(mtime)


def _clear_invalid_cache_mark(path):
    if path in invalid_cache_files:
        del invalid_cache_files[path]


def _is_known_invalid_cache(path, mtime):
    invalid_mtime = invalid_cache_files.get(path)
    if invalid_mtime is None or mtime is None:
        return False
    return float(mtime) <= invalid_mtime


def _load_cache_file(path):
    if not os.path.exists(path):
        return None, None, "missing_file"

    try:
        mtime = os.path.getmtime(path)
    except OSError as e:
        return None, None, str(e)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not _is_cache_data_valid(data):
            raise ValueError("courses_cache.json inválido: schema básico no cumple")
        return data, mtime, None
    except Exception as e:
        return None, mtime, str(e)


def _slugify(value):
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def _extract_url_slug(url_value):
    try:
        parsed = urlparse(str(url_value or "").strip())
        pieces = [segment for segment in parsed.path.split("/") if segment]
        return pieces[-1] if pieces else ""
    except Exception:
        return ""


def _module_class_count(module):
    classes = (module or {}).get("classes", [])
    if isinstance(classes, list):
        return len(classes)
    if isinstance(classes, int):
        return max(classes, 0)
    return 0


def _summarize_modules(modules):
    summaries = []
    total_classes = 0
    for idx, module in enumerate(modules or []):
        class_count = _module_class_count(module)
        total_classes += class_count
        summaries.append(
            {
                "name": (module or {}).get("name") or f"Módulo {idx + 1}",
                "classCount": class_count,
                # Mantener compatibilidad con frontend actual: classes numérico.
                "classes": class_count,
            }
        )
    return summaries, total_classes


def _course_public_id(course):
    slug = _extract_url_slug((course or {}).get("url"))
    if slug:
        return slug

    course_id = str((course or {}).get("id") or "").strip()
    if course_id:
        return course_id

    return _slugify((course or {}).get("name") or "")


def _build_bootstrap_course(course):
    raw = course or {}
    modules_summary, computed_classes = _summarize_modules(raw.get("modules", []))

    module_count = raw.get("moduleCount")
    if not isinstance(module_count, int):
        module_count = len(modules_summary)

    class_count = raw.get("classCount")
    if not isinstance(class_count, int):
        class_count = computed_classes

    return {
        "name": raw.get("name", ""),
        "folderName": raw.get("folderName", ""),
        "url": raw.get("url", ""),
        "id": raw.get("id", ""),
        "publicId": _course_public_id(raw),
        "moduleCount": module_count,
        "classCount": class_count,
        "foundInDrive": raw.get("foundInDrive", True),
        "matchType": raw.get("matchType"),
        "matchedFolder": raw.get("matchedFolder"),
        "hasPresentation": raw.get("hasPresentation", False),
        "presentationId": raw.get("presentationId", ""),
        "modules": modules_summary,
    }


def _build_bootstrap_route(route):
    raw = route or {}

    base = {
        "id": raw.get("id", ""),
        "name": raw.get("name", ""),
        "url": raw.get("url", ""),
        "isCourse": bool(raw.get("isCourse")),
    }

    if raw.get("isCourse"):
        summary = _build_bootstrap_course(raw)
        base.update(summary)
        base["isCourse"] = True
        return base

    courses = [_build_bootstrap_course(c) for c in raw.get("courses", [])]
    base["courses"] = courses
    base["courseCount"] = raw.get("courseCount", len(courses))
    return base


def _build_bootstrap_payload(data):
    raw = data if isinstance(data, dict) else _empty_courses_payload()
    categories = []

    for category in raw.get("categories", []):
        routes = [_build_bootstrap_route(route) for route in (category or {}).get("routes", [])]
        cat_payload = {
            "id": (category or {}).get("id", ""),
            "name": (category or {}).get("name", ""),
            "icon": (category or {}).get("icon", ""),
            "description": (category or {}).get("description", ""),
            "type": (category or {}).get("type", ""),
            "routes": routes,
        }
        if "courseCount" in (category or {}):
            cat_payload["courseCount"] = (category or {}).get("courseCount")
        categories.append(cat_payload)

    return {
        "categories": categories,
        "stats": _normalize_stats(raw.get("stats")),
    }


def _format_epoch_to_iso(epoch_value):
    if epoch_value is None:
        return None
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(epoch_value)))
    except Exception:
        return None


def _build_cache_meta_payload(selected_cache_file, selected_mtime, data, full_bytes_len, bootstrap_bytes_len):
    return {
        "cache_file_path": selected_cache_file,
        "cache_file_name": os.path.basename(selected_cache_file) if selected_cache_file else None,
        "source": _cache_source_from_path(selected_cache_file),
        "mtime": _format_epoch_to_iso(selected_mtime),
        "mtimeEpoch": selected_mtime,
        "stats": _normalize_stats((data or {}).get("stats")),
        "payloadBytes": {
            "full": int(full_bytes_len or 0),
            "bootstrap": int(bootstrap_bytes_len or 0),
        },
    }


def _ref_matches(ref_value, idx, candidates):
    normalized = str(ref_value or "").strip().lower()
    if not normalized:
        return False

    if normalized == str(idx).lower():
        return True

    for candidate in candidates:
        c = str(candidate or "").strip().lower()
        if c and normalized == c:
            return True
    return False


def _resolve_course_detail_refs(data, cat_ref, route_ref, course_ref):
    categories = (data or {}).get("categories", [])

    for cat_idx, category in enumerate(categories):
        cat_candidates = [
            category.get("id"),
            category.get("name"),
            _slugify(category.get("name")),
        ]
        if not _ref_matches(cat_ref, cat_idx, cat_candidates):
            continue

        for route_idx, route in enumerate(category.get("routes", [])):
            route_candidates = [
                route.get("id"),
                route.get("name"),
                _slugify(route.get("name")),
                _extract_url_slug(route.get("url")),
            ]
            if not _ref_matches(route_ref, route_idx, route_candidates):
                continue

            if route.get("isCourse"):
                course_candidates = [
                    route.get("id"),
                    route.get("name"),
                    _slugify(route.get("name")),
                    _extract_url_slug(route.get("url")),
                    _course_public_id(route),
                ]
                # Para rutas de curso único permitimos "0" además de IDs/slug.
                if _ref_matches(course_ref, 0, course_candidates):
                    return {
                        "catIdx": cat_idx,
                        "routeIdx": route_idx,
                        "courseIdx": 0,
                        "category": category,
                        "route": route,
                        "course": route,
                    }
                continue

            for course_idx, course in enumerate(route.get("courses", [])):
                course_candidates = [
                    course.get("id"),
                    course.get("name"),
                    _slugify(course.get("name")),
                    _extract_url_slug(course.get("url")),
                    _course_public_id(course),
                ]
                if _ref_matches(course_ref, course_idx, course_candidates):
                    return {
                        "catIdx": cat_idx,
                        "routeIdx": route_idx,
                        "courseIdx": course_idx,
                        "category": category,
                        "route": route,
                        "course": course,
                    }

    return None


def _build_course_detail_payload(match):
    category = match["category"]
    route = match["route"]
    course = match["course"]

    return {
        "catId": category.get("id") or str(match["catIdx"]),
        "routeId": route.get("id") or str(match["routeIdx"]),
        "courseId": _course_public_id(course) or str(match["courseIdx"]),
        "indices": {
            "catIdx": match["catIdx"],
            "routeIdx": match["routeIdx"],
            "courseIdx": match["courseIdx"],
        },
        "course": course,
        "isCourseRoute": bool(route.get("isCourse")),
    }


def resolve_cache_file_path():
    order = _get_cache_preference_order()
    fallback = order[0] if order else VIEWER_CACHE_FILE

    for candidate in order:
        if not os.path.exists(candidate):
            continue
        try:
            mtime = os.path.getmtime(candidate)
        except OSError:
            continue
        if _is_known_invalid_cache(candidate, mtime):
            continue
        return candidate

    return fallback


def init_cache():
    """Inicializa el caché cargando courses_cache.json."""
    global courses_cache, bootstrap_cache, cache_meta
    global cache_mtime, cache_file_path, cache_source
    global full_cache_json_bytes, full_cache_json_gzip_bytes
    global bootstrap_cache_json_bytes, bootstrap_cache_json_gzip_bytes
    global cache_meta_json_bytes, cache_meta_json_gzip_bytes

    selected_cache_file = None
    selected_mtime = None
    selected_data = None
    load_errors = []

    for candidate in _get_cache_preference_order():
        if not os.path.exists(candidate):
            continue

        data, mtime, error = _load_cache_file(candidate)
        if error:
            load_errors.append((candidate, error))
            _mark_cache_invalid(candidate, mtime)
            print(f"[WARN] Cache inválido en {candidate}: {error}")
            continue

        selected_cache_file = candidate
        selected_mtime = mtime
        selected_data = data
        _clear_invalid_cache_mark(candidate)
        break

    if selected_data is None:
        with cache_lock:
            has_previous_cache = courses_cache is not None

        if load_errors:
            print("[ERROR] No se encontró un courses_cache.json válido en las rutas preferidas.")
        else:
            print("[ERROR] courses_cache.json no encontrado.")
            print("   Ejecuta: python rebuild_cache_drive.py")

        if has_previous_cache:
            print("[WARN] Conservando caché anterior en memoria por error temporal de lectura")
        else:
            empty_data = _empty_courses_payload()
            empty_bootstrap = _build_bootstrap_payload(empty_data)
            full_bytes = _payload_to_bytes(empty_data)
            bootstrap_bytes = _payload_to_bytes(empty_bootstrap)
            meta_payload = _build_cache_meta_payload(
                selected_cache_file or resolve_cache_file_path(),
                None,
                empty_data,
                len(full_bytes),
                len(bootstrap_bytes),
            )
            meta_bytes = _payload_to_bytes(meta_payload)

            with cache_lock:
                courses_cache = empty_data
                bootstrap_cache = empty_bootstrap
                cache_meta = meta_payload
                cache_mtime = None
                cache_file_path = selected_cache_file or resolve_cache_file_path()
                cache_source = _cache_source_from_path(cache_file_path)

                full_cache_json_bytes = full_bytes
                full_cache_json_gzip_bytes = _gzip_payload(full_bytes)
                bootstrap_cache_json_bytes = bootstrap_bytes
                bootstrap_cache_json_gzip_bytes = _gzip_payload(bootstrap_bytes)
                cache_meta_json_bytes = meta_bytes
                cache_meta_json_gzip_bytes = _gzip_payload(meta_bytes)
    else:
        bootstrap_data = _build_bootstrap_payload(selected_data)
        full_bytes = _payload_to_bytes(selected_data)
        bootstrap_bytes = _payload_to_bytes(bootstrap_data)
        meta_payload = _build_cache_meta_payload(
            selected_cache_file,
            selected_mtime,
            selected_data,
            len(full_bytes),
            len(bootstrap_bytes),
        )
        meta_bytes = _payload_to_bytes(meta_payload)

        with cache_lock:
            courses_cache = selected_data
            bootstrap_cache = bootstrap_data
            cache_meta = meta_payload
            cache_mtime = selected_mtime
            cache_file_path = selected_cache_file
            cache_source = _cache_source_from_path(selected_cache_file)

            full_cache_json_bytes = full_bytes
            full_cache_json_gzip_bytes = _gzip_payload(full_bytes)
            bootstrap_cache_json_bytes = bootstrap_bytes
            bootstrap_cache_json_gzip_bytes = _gzip_payload(bootstrap_bytes)
            cache_meta_json_bytes = meta_bytes
            cache_meta_json_gzip_bytes = _gzip_payload(meta_bytes)

        stats = _normalize_stats(selected_data.get("stats"))
        print(f"[INFO] Cache seleccionado ({cache_source}): {selected_cache_file}")
        print(
            f"\n[OK] Datos cargados: {stats.get('totalCategories', 0)} categorías, "
            f"{stats.get('totalRoutes', 0)} rutas, {stats.get('totalCourses', 0)} cursos, "
            f"{stats.get('totalClasses', 0)} clases"
        )

    print(f"[INFO] Servidor listo en http://{DISPLAY_HOST}:{PORT}\n")


def refresh_cache_if_changed():
    """Recarga el caché si courses_cache.json cambió en disco."""
    current_cache_file = resolve_cache_file_path()

    if not os.path.exists(current_cache_file):
        return

    try:
        current_mtime = os.path.getmtime(current_cache_file)
    except OSError:
        return

    with cache_lock:
        previous_mtime = cache_mtime
        previous_cache_file = cache_file_path

    if previous_cache_file != current_cache_file:
        with cache_reload_lock:
            with cache_lock:
                if cache_file_path != current_cache_file:
                    print("[INFO] Cambio de origen de caché detectado, recargando...")
                    init_cache()
        return

    if previous_mtime is not None and current_mtime <= previous_mtime:
        return

    with cache_reload_lock:
        with cache_lock:
            latest_mtime = cache_mtime

        if latest_mtime is not None and current_mtime <= latest_mtime:
            return

        print("[INFO] Detectado cambio en courses_cache.json, recargando caché...")
        init_cache()


class PlatziHandler(SimpleHTTPRequestHandler):
    """Manejador HTTP personalizado."""

    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "application/javascript; charset=utf-8",
        ".mjs": "application/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".map": "application/json; charset=utf-8",
        ".svg": "image/svg+xml",
        ".wasm": "application/wasm",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=VIEWER_PATH, **kwargs)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-site")
        super().end_headers()

    def _is_allowed_origin(self, origin):
        if not origin:
            return False
        try:
            parsed = urlparse(origin)
            return parsed.scheme in {"http", "https"} and parsed.hostname in LOOPBACK_HOSTS
        except Exception:
            return False

    def _set_cors_headers(self):
        origin = self.headers.get("Origin")
        if self._is_allowed_origin(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def _accepts_gzip(self):
        return "gzip" in str(self.headers.get("Accept-Encoding", "")).lower()

    def _send_json_bytes(self, status_code, raw_bytes, gzip_bytes=None):
        use_gzip = bool(gzip_bytes) and self._accepts_gzip()
        payload = gzip_bytes if use_gzip else raw_bytes

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        if use_gzip:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(payload)))
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, status_code, payload):
        raw_bytes = _payload_to_bytes(payload)
        gzip_bytes = _gzip_payload(raw_bytes) if len(raw_bytes) >= 1024 else None
        self._send_json_bytes(status_code, raw_bytes, gzip_bytes)

    def _is_local_client(self):
        host = self.client_address[0]
        return host in LOOPBACK_HOSTS

    def _is_client_disconnect_error(self, error):
        if isinstance(error, (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)):
            return True

        winerror = getattr(error, "winerror", None)
        if winerror in {10053, 10054}:
            return True

        err_no = getattr(error, "errno", None)
        if err_no in {errno.EPIPE, errno.ECONNRESET, errno.ECONNABORTED}:
            return True

        return False

    def _safe_send_error(self, code, message):
        try:
            self.send_error(code, message)
        except OSError as error:
            if not self._is_client_disconnect_error(error):
                raise

    def _stream_video_via_ffmpeg(self, file_id, ffmpeg_executable):
        """Stream a Drive video through ffmpeg to fix audio timestamp alignment.

        Re-encodes the audio track with aresample=async=1:first_pts=0 (same as
        VLC's internal timestamp-correction behaviour) while keeping the video
        stream as-is (copy).  Falls back to raw streaming on error.
        """
        source_url = f"http://127.0.0.1:{PORT}/drive/files/{file_id}?raw=1"

        ffmpeg_cmd = [
            ffmpeg_executable,
            "-hide_banner",
            "-loglevel",
            "error",
            "-fflags",
            "+genpts+discardcorrupt",
            "-avoid_negative_ts",
            "make_zero",
            "-max_interleave_delta",
            "0",
            "-i",
            source_url,
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-af",
            "aresample=async=1:first_pts=0",
            "-movflags",
            "+frag_keyframe+empty_moov+default_base_moof",
            "-muxdelay",
            "0",
            "-muxpreload",
            "0",
            "-f",
            "mp4",
            "-",
        ]

        process = None
        try:
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
                creationflags=CREATE_NO_WINDOW
            )

            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Accept-Ranges", "none")
            self._set_cors_headers()
            self.end_headers()

            total_bytes = 0
            start_time = time.time()

            while True:
                if process.stdout is None:
                    break

                chunk = process.stdout.read(1024 * 512)
                if not chunk:
                    break

                self.wfile.write(chunk)
                total_bytes += len(chunk)

            return_code = process.wait(timeout=5)
            duration = max(0.001, time.time() - start_time)
            speed = (total_bytes / 1024 / 1024) / duration

            if return_code != 0:
                stderr_output = b""
                if process.stderr is not None:
                    try:
                        stderr_output = process.stderr.read(4096)
                    except Exception:
                        pass
                stderr_text = stderr_output.decode("utf-8", errors="ignore").strip()
                print(f"[WARN] ffmpeg remux failed ({file_id}): code={return_code} {stderr_text[:300]}")
            else:
                print(f"[REMUX] {file_id} | {total_bytes/1024/1024:.2f} MB in {duration:.2f}s ({speed:.2f} MB/s)")

        except OSError as error:
            if not self._is_client_disconnect_error(error):
                print(f"[ERROR] Remux stream write error for {file_id}: {error}")
            return
        except Exception as error:
            print(f"[ERROR] Remux stream failed for {file_id}: {error}")
            if not self.wfile.closed:
                self._safe_send_error(502, "Failed to stream remuxed video")
            return
        finally:
            if process is not None and process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=1)
                except Exception:
                    try:
                        process.kill()
                    except Exception:
                        pass

    def do_GET(self):
        if self.path == "/api/health":
            ds = get_drive_service()
            ffmpeg_executable = _get_ffmpeg_executable()
            with compat_stream_lock:
                compat_snapshot = dict(compat_stream_stats)
            payload = {
                "status": "ok",
                "drive": {
                    "available": bool(ds),
                    "error": None if ds else get_drive_service_error(),
                },
                "ffmpeg": {
                    "available": bool(ffmpeg_executable),
                    "path": ffmpeg_executable,
                },
                "compatStream": compat_snapshot,
                "repair": _repair_health_summary(),
            }
            self._send_json(200, payload)
            return

        if self.path.startswith("/api/repair-status/"):
            file_id = unquote(self.path[len("/api/repair-status/") :]).strip()
            if not file_id or not DRIVE_ID_RE.match(file_id):
                self._send_json(400, {"error": "invalid_file_id"})
                return

            with repair_state_lock:
                entry = dict(repair_state.get(file_id) or {})

            if not entry:
                if _is_artifact_ready(file_id):
                    entry = _set_repair_state(
                        file_id,
                        status="completed",
                        completedAt=_now_iso(),
                        updatedAt=_now_iso(),
                        progress=1.0,
                        error=None,
                        artifactPath=f"repaired_videos/{file_id}.mp4",
                        artifactSize=os.path.getsize(_repair_paths(file_id)[0]),
                        ffmpegMode="remux_audio",
                    )
                else:
                    self._send_json(404, {"error": "repair_not_found", "status": "missing"})
                    return

            if entry.get("status") == "completed" and _is_artifact_ready(file_id):
                entry["artifactUrl"] = f"/api/repaired/{file_id}"

            self._send_json(200, entry)
            return

        if self.path.startswith("/api/repaired/"):
            file_id = unquote(self.path[len("/api/repaired/") :]).strip()
            if not file_id or not DRIVE_ID_RE.match(file_id):
                self._safe_send_error(400, "Invalid file ID")
                return

            artifact_path, _, _ = _repair_paths(file_id)
            if not _is_within_directory(artifact_path, REPAIRED_VIDEOS_DIR):
                self._safe_send_error(400, "Invalid repaired file path")
                return

            if not _is_artifact_ready(file_id):
                self._safe_send_error(404, "Repaired artifact not found")
                return

            try:
                total_size = os.path.getsize(artifact_path)
                range_header = self.headers.get("Range")
                if range_header:
                    start, end = _parse_single_range(range_header, total_size)
                    length = end - start + 1

                    self.send_response(206)
                    self.send_header("Content-Type", "video/mp4")
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Content-Range", f"bytes {start}-{end}/{total_size}")
                    self.send_header("Content-Length", str(length))
                    self.send_header("Cache-Control", "public, max-age=3600")
                    self._set_cors_headers()
                    self.end_headers()

                    with open(artifact_path, "rb") as f:
                        f.seek(start)
                        remaining = length
                        while remaining > 0:
                            chunk = f.read(min(1024 * 1024, remaining))
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            remaining -= len(chunk)
                    return

                self.send_response(200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Length", str(total_size))
                self.send_header("Cache-Control", "public, max-age=3600")
                self._set_cors_headers()
                self.end_headers()

                with open(artifact_path, "rb") as f:
                    while True:
                        chunk = f.read(1024 * 1024)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                return

            except ValueError:
                self._safe_send_error(416, "Range Not Satisfiable")
                return
            except OSError as error:
                if not self._is_client_disconnect_error(error):
                    print(f"[ERROR] Repaired stream write error for {file_id}: {error}")
                return
            except Exception as error:
                print(f"[ERROR] Failed to stream repaired video {file_id}: {error}")
                self._safe_send_error(500, "Failed to stream repaired artifact")
                return

        # API endpoint
        if self.path == "/api/courses":
            refresh_cache_if_changed()

            with cache_lock:
                raw_bytes = full_cache_json_bytes or _payload_to_bytes(_empty_courses_payload())
                gzip_bytes = full_cache_json_gzip_bytes or None

            self._send_json_bytes(200, raw_bytes, gzip_bytes)
            return

        if self.path == "/api/bootstrap":
            refresh_cache_if_changed()

            with cache_lock:
                raw_bytes = bootstrap_cache_json_bytes or _payload_to_bytes(_empty_courses_payload())
                gzip_bytes = bootstrap_cache_json_gzip_bytes or None

            self._send_json_bytes(200, raw_bytes, gzip_bytes)
            return

        if self.path == "/api/cache-meta":
            refresh_cache_if_changed()

            with cache_lock:
                raw_bytes = cache_meta_json_bytes or _payload_to_bytes(
                    {
                        "cache_file_path": cache_file_path,
                        "source": cache_source,
                        "mtime": _format_epoch_to_iso(cache_mtime),
                        "mtimeEpoch": cache_mtime,
                        "stats": _normalize_stats((courses_cache or {}).get("stats")),
                        "payloadBytes": {"full": 0, "bootstrap": 0},
                    }
                )
                gzip_bytes = cache_meta_json_gzip_bytes or None

            self._send_json_bytes(200, raw_bytes, gzip_bytes)
            return

        if self.path.startswith("/api/course-detail/"):
            refresh_cache_if_changed()

            parsed = urlparse(self.path)
            parts = [unquote(segment) for segment in parsed.path.split("/") if segment]
            if len(parts) != 5:
                self._send_json(
                    400,
                    {
                        "error": "invalid_course_detail_path",
                        "expected": "/api/course-detail/<catId>/<routeId>/<courseId>",
                    },
                )
                return

            _, _, cat_ref, route_ref, course_ref = parts
            with cache_lock:
                data = courses_cache or _empty_courses_payload()

            match = _resolve_course_detail_refs(data, cat_ref, route_ref, course_ref)
            if not match:
                self._send_json(
                    404,
                    {
                        "error": "course_not_found",
                        "catRef": cat_ref,
                        "routeRef": route_ref,
                        "courseRef": course_ref,
                    },
                )
                return

            payload = _build_course_detail_payload(match)
            self._send_json(200, payload)
            return

        # Refrescar caché
        if self.path == "/api/refresh":
            if not self._is_local_client():
                self._send_json(403, {"error": "forbidden"})
                return

            threading.Thread(target=init_cache, daemon=True).start()
            self._send_json(200, {"status": "refreshing"})
            return

        # Cargar progreso desde JSON
        if self.path == "/api/progress":
            self._send_json(200, _load_progress_payload())
            return

        # Self-check: validate cache references are Drive IDs (no local refs)
        if self.path == "/api/self-check-drive":
            with cache_lock:
                data = courses_cache or {"categories": [], "stats": {}}

            report = analyze_drive_references(data)
            self._send_json(200, report)
            return

        # Get video metadata (including duration)
        if self.path.startswith("/api/video-metadata/"):
            if not self._is_local_client():
                self._send_json(403, {"error": "forbidden"})
                return
            file_id = unquote(self.path[len("/api/video-metadata/") :])
            if not file_id or not DRIVE_ID_RE.match(file_id):
                self._send_json(400, {"error": "Invalid file ID"})
                return

            ds = get_drive_service()
            if not ds:
                self._send_json(503, {"error": "Drive service not available"})
                return

            try:
                meta = ds.get_file_metadata(file_id)
                self._send_json(200, {"success": True, "metadata": meta})
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        # Google Drive file streaming (all files served via Drive API)
        if self.path.startswith("/api/video-compatible/"):
            file_id = unquote(self.path[len("/api/video-compatible/") :])

            with compat_stream_lock:
                compat_stream_stats["totalRequests"] += 1
                compat_stream_stats["lastFileId"] = file_id
                compat_stream_stats["lastAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            if not file_id or not DRIVE_ID_RE.match(file_id):
                self._safe_send_error(400, "Invalid file ID")
                return

            ffmpeg_executable = _get_ffmpeg_executable()
            if not ffmpeg_executable:
                self._safe_send_error(503, "ffmpeg_not_available")
                return

            ds = get_drive_service()
            if not ds:
                error_detail = get_drive_service_error()
                hint = (
                    "Drive service not available. "
                    "Check service_account.json, GOOGLE_SERVICE_ACCOUNT_FILE or "
                    "GOOGLE_SERVICE_ACCOUNT_JSON."
                )
                if error_detail:
                    self._safe_send_error(503, f"{hint} Detail: {error_detail}")
                else:
                    self._safe_send_error(503, hint)
                return

            # Use raw source here to avoid nested remux inside /drive/files.
            source_url = f"http://127.0.0.1:{PORT}/drive/files/{file_id}?raw=1"
            # Default to full re-encode for maximum playback stability across
            # Chrome/Opera/WebView (VLC-like behavior for damaged timestamps).
            compat_force_reencode = os.environ.get("PLATZI_COMPAT_FORCE_REENCODE", "1").strip() == "1"

            ffmpeg_cmd = [
                ffmpeg_executable,
                "-hide_banner",
                "-loglevel",
                "error",
                "-fflags",
                "+genpts+igndts+discardcorrupt",
                "-avoid_negative_ts",
                "make_zero",
                "-i",
                source_url,
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
            ]

            if compat_force_reencode:
                ffmpeg_cmd.extend(
                    [
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-pix_fmt",
                        "yuv420p",
                        "-g",
                        "48",
                        "-keyint_min",
                        "48",
                        "-sc_threshold",
                        "0",
                    ]
                )
            else:
                ffmpeg_cmd.extend(["-c:v", "copy"])

            ffmpeg_cmd.extend(
                [
                    "-c:a",
                    "aac",
                    "-ar",
                    "48000",
                    "-af",
                    "aresample=async=1:min_hard_comp=0.100:first_pts=0",
                    "-movflags",
                    "+frag_keyframe+empty_moov+default_base_moof",
                    "-f",
                    "mp4",
                    "-",
                ]
            )

            process = None
            try:
                process = subprocess.Popen(
                    ffmpeg_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=0,
                    creationflags=CREATE_NO_WINDOW
                )

                self.send_response(200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Cache-Control", "no-store, max-age=0")
                self.send_header("Accept-Ranges", "none")
                self._set_cors_headers()
                self.end_headers()

                total_bytes = 0
                start_time = time.time()

                while True:
                    if process.stdout is None:
                        break

                    chunk = process.stdout.read(1024 * 512)
                    if not chunk:
                        break

                    self.wfile.write(chunk)
                    total_bytes += len(chunk)

                return_code = process.wait(timeout=2)
                if return_code != 0:
                    with compat_stream_lock:
                        compat_stream_stats["failedStreams"] += 1
                        compat_stream_stats["lastMode"] = "reencode" if compat_force_reencode else "copy"
                    stderr_output = b""
                    if process.stderr is not None:
                        try:
                            stderr_output = process.stderr.read(4096)
                        except Exception:
                            stderr_output = b""
                    stderr_text = stderr_output.decode("utf-8", errors="ignore").strip()
                    if stderr_text:
                        with compat_stream_lock:
                            compat_stream_stats["lastError"] = stderr_text[:500]
                        print(f"[WARN] ffmpeg compatibility stream failed ({file_id}): {stderr_text}")
                    else:
                        with compat_stream_lock:
                            compat_stream_stats["lastError"] = f"ffmpeg_exit_{return_code}"
                        print(f"[WARN] ffmpeg compatibility stream failed ({file_id}) with code {return_code}")
                else:
                    duration = max(0.001, time.time() - start_time)
                    speed = (total_bytes / 1024 / 1024) / duration
                    with compat_stream_lock:
                        compat_stream_stats["successfulStreams"] += 1
                        compat_stream_stats["totalBytes"] += total_bytes
                        compat_stream_stats["lastError"] = None
                        compat_stream_stats["lastDurationSec"] = round(duration, 3)
                        compat_stream_stats["lastSpeedMBps"] = round(speed, 3)
                        compat_stream_stats["lastMode"] = "reencode" if compat_force_reencode else "copy"
                    print(f"[COMPAT] {file_id} | {total_bytes/1024/1024:.2f} MB in {duration:.2f}s ({speed:.2f} MB/s)")

            except OSError as error:
                with compat_stream_lock:
                    compat_stream_stats["failedStreams"] += 1
                    compat_stream_stats["lastError"] = str(error)[:500]
                if not self._is_client_disconnect_error(error):
                    print(f"[ERROR] Compatibility stream write error for {file_id}: {error}")
                return
            except Exception as error:
                with compat_stream_lock:
                    compat_stream_stats["failedStreams"] += 1
                    compat_stream_stats["lastError"] = str(error)[:500]
                print(f"[ERROR] Compatibility stream failed for {file_id}: {error}")
                if not self.wfile.closed:
                    self._safe_send_error(502, "Failed to stream compatibility video")
                return
            finally:
                if process is not None and process.poll() is None:
                    try:
                        process.terminate()
                        process.wait(timeout=1)
                    except Exception:
                        try:
                            process.kill()
                        except Exception:
                            pass
            return

        if self.path.startswith("/drive/files/"):
            parsed_url = urlparse(self.path)
            file_id = unquote(parsed_url.path[13:])
            query_raw = "raw=1" in (parsed_url.query or "")

            if file_id.startswith("local:"):
                self.send_error(
                    400, "Local file refs are disabled in Drive mode. Rebuild cache with rebuild_cache_drive.py"
                )
                return

            if not file_id or not DRIVE_ID_RE.match(file_id):
                self.send_error(400, "Invalid file ID")
                return

            ds = get_drive_service()
            if not ds:
                error_detail = get_drive_service_error()
                hint = (
                    "Drive service not available. "
                    "Check service_account.json, GOOGLE_SERVICE_ACCOUNT_FILE or "
                    "GOOGLE_SERVICE_ACCOUNT_JSON."
                )
                if error_detail:
                    self._safe_send_error(503, f"{hint} Detail: {error_detail}")
                else:
                    self._safe_send_error(503, hint)
                return

            range_header = self.headers.get("Range")
            ffmpeg_executable = _get_ffmpeg_executable()
            initial_remux_enabled = os.environ.get("PLATZI_DRIVE_INITIAL_REMUX", "0").strip() == "1"
            should_try_initial_remux = (ffmpeg_executable and initial_remux_enabled and not range_header and not query_raw)

            # ── FFmpeg remux path for video files ──
            # When we have ffmpeg available and request is startup/full content,
            # pipe the video through ffmpeg to re-encode audio and fix timestamp
            # alignment (same fix VLC applies internally).
            # We detect video by trying to get file metadata first.
            if ffmpeg_executable and should_try_initial_remux:
                try:
                    file_meta = ds.get_file_metadata(file_id)
                    mime_from_meta = (file_meta or {}).get("mimeType", "") if isinstance(file_meta, dict) else ""
                except Exception:
                    mime_from_meta = ""

                if mime_from_meta.startswith("video"):
                    self._stream_video_via_ffmpeg(file_id, ffmpeg_executable)
                    return

            # ── Raw streaming path (non-video files, Range requests, no ffmpeg, ?raw=1) ──
            try:
                if range_header:
                    sanitized_range = str(range_header).strip()
                    if "," in sanitized_range or not re.match(r"^bytes=\d*-\d*$", sanitized_range):
                        self._safe_send_error(416, "Invalid range header")
                        return
                    resp = ds.download_file_range(file_id, range_header=sanitized_range)
                else:
                    resp = ds.download_file_range(file_id)

                status_code = resp.status_code
                mime_type = resp.headers.get("Content-Type", "application/octet-stream")
                is_video = mime_type.startswith("video")
                content_range = resp.headers.get("Content-Range")
                content_length = resp.headers.get("Content-Length")

                self.send_response(status_code)
                self.send_header("Content-Type", mime_type)
                if content_range:
                    self.send_header("Content-Range", content_range)
                if content_length:
                    self.send_header("Content-Length", content_length)
                self.send_header("Accept-Ranges", "bytes")
                self._set_cors_headers()
                if is_video:
                    self.send_header("Cache-Control", "public, max-age=3600")
                self.end_headers()

                start_time = time.time()
                total_bytes = 0
                try:
                    for chunk in resp.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            self.wfile.write(chunk)
                            total_bytes += len(chunk)
                except OSError as error:
                    if not self._is_client_disconnect_error(error):
                        raise
                finally:
                    duration = time.time() - start_time
                    if duration > 0.5:
                        speed = (total_bytes / 1024 / 1024) / duration
                        print(
                            f"[STREAM] {file_id} | Range: {range_header or 'Full'} | {total_bytes/1024/1024:.2f} MB in {duration:.2f}s ({speed:.2f} MB/s)"
                        )
                    resp.close()
            except Exception as e:
                if self._is_client_disconnect_error(e):
                    return

                drive_status = getattr(getattr(e, "response", None), "status_code", None)
                if isinstance(drive_status, int):
                    self._safe_send_error(drive_status, f"Drive error ({drive_status})")
                    return

                print(f"[ERROR] Drive streaming error for {file_id}: {e}")
                self._safe_send_error(502, "Failed to stream file from Drive")
            return

        # Static files (index.html, js/, css, etc.)
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/repair/"):
            if not self._is_local_client():
                self._send_json(403, {"error": "forbidden"})
                return

            file_id = unquote(self.path[len("/api/repair/") :]).strip()
            if not file_id or not DRIVE_ID_RE.match(file_id):
                self._send_json(400, {"error": "invalid_file_id"})
                return

            ffmpeg_executable = _get_ffmpeg_executable()
            if not ffmpeg_executable:
                self._send_json(503, {"error": "ffmpeg_not_available"})
                return

            ds = get_drive_service()
            if not ds:
                self._send_json(503, {"error": "drive_not_available", "detail": get_drive_service_error()})
                return

            artifact_path, meta_path, lock_path = _repair_paths(file_id)
            if not _is_within_directory(artifact_path, REPAIRED_VIDEOS_DIR):
                self._send_json(400, {"error": "invalid_file_path"})
                return

            os.makedirs(REPAIRED_VIDEOS_DIR, exist_ok=True)

            if _is_artifact_ready(file_id):
                entry = _set_repair_state(
                    file_id,
                    status="completed",
                    completedAt=_now_iso(),
                    updatedAt=_now_iso(),
                    progress=1.0,
                    error=None,
                    artifactPath=f"repaired_videos/{file_id}.mp4",
                    artifactSize=os.path.getsize(artifact_path),
                    ffmpegMode="remux_audio",
                )
                entry["artifactUrl"] = f"/api/repaired/{file_id}"
                self._send_json(200, entry)
                return

            now_epoch = time.time()
            if os.path.exists(lock_path):
                try:
                    age = now_epoch - os.path.getmtime(lock_path)
                except OSError:
                    age = REPAIR_LOCK_TTL_SECONDS + 1
                if age <= REPAIR_LOCK_TTL_SECONDS:
                    self._send_json(409, {"error": "repair_in_progress", "status": "in_progress"})
                    return
                try:
                    os.remove(lock_path)
                except OSError:
                    pass

            with repair_state_lock:
                running = active_repairs.get(file_id)
                if running and running.is_alive():
                    self._send_json(409, {"error": "repair_in_progress", "status": "in_progress"})
                    return

            # Remove stale partial outputs before a new attempt.
            try:
                os.remove(artifact_path)
            except OSError:
                pass
            try:
                os.remove(meta_path)
            except OSError:
                pass

            try:
                with open(lock_path, "w", encoding="utf-8") as lock_file:
                    lock_file.write(json.dumps({"pid": os.getpid(), "at": _now_iso()}))
            except OSError as error:
                self._send_json(507, {"error": "cannot_create_lock", "detail": str(error)})
                return

            entry = _set_repair_state(
                file_id,
                status="pending",
                requestedAt=_now_iso(),
                updatedAt=_now_iso(),
                progress=0.0,
                error=None,
                artifactPath=f"repaired_videos/{file_id}.mp4",
                artifactSize=0,
                ffmpegMode="pending",
            )

            worker = threading.Thread(target=_repair_worker, args=(file_id, self.server.server_port), daemon=True)
            with repair_state_lock:
                active_repairs[file_id] = worker
            worker.start()

            self._send_json(202, entry)
            return

        # Guardar progreso en JSON
        if self.path == "/api/progress":
            content_length = int(self.headers.get("Content-Length", 0))

            if content_length <= 0 or content_length > MAX_PROGRESS_BYTES:
                self._send_json(413, {"error": "payload_too_large"})
                return

            post_data = self.rfile.read(content_length)

            try:
                # Validar que es JSON válido
                parsed = json.loads(post_data.decode("utf-8"))
                if not isinstance(parsed, dict):
                    raise ValueError("progress payload must be a JSON object")
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
                self._send_json(400, {"error": str(error)})
                return

            try:
                # Guardar en archivo
                progress_dir = os.path.dirname(PROGRESS_FILE)
                if progress_dir:
                    os.makedirs(progress_dir, exist_ok=True)
                with open(PROGRESS_FILE, "wb") as f:
                    f.write(post_data)

                self._send_json(200, {"status": "saved"})
            except OSError as error:
                self._send_json(400, {"error": str(error)})
            return

        # Abrir en reproductor externo (VLC)
        if self.path == "/api/open-external":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                post_data = self.rfile.read(content_length)
                payload = json.loads(post_data.decode("utf-8"))
                video_url = payload.get("url")

                if not video_url:
                    self._send_json(400, {"error": "missing_url"})
                    return

                # Si es una ruta relativa, agregar localhost
                if video_url.startswith("/"):
                    video_url = f"http://localhost:{PORT}{video_url}"

                # Buscar VLC en rutas comunes de Windows
                vlc_path = None
                possible_paths = [
                    r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                    r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
                ]

                for path in possible_paths:
                    if os.path.exists(path):
                        vlc_path = path
                        break

                if vlc_path:
                    # subprocess.Popen detaches the process so server keeps running
                    subprocess.Popen([vlc_path, video_url])
                    self._send_json(200, {"status": "opened_vlc", "player": vlc_path})
                else:
                    # Intentar comando global 'vlc'
                    try:
                        subprocess.Popen(["vlc", video_url])
                        self._send_json(200, {"status": "opened_vlc_cmd"})
                    except FileNotFoundError:
                        self._send_json(404, {"error": "vlc_not_found"})

            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

    def do_OPTIONS(self):
        # Manejar CORS preflight
        origin = self.headers.get("Origin")
        if not self._is_allowed_origin(origin):
            self.send_response(403)
            self.end_headers()
            return

        self.send_response(200)
        self._set_cors_headers()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.end_headers()

    def log_message(self, format, *args):
        # Evitar errores cuando args[0] no es un string
        try:
            msg = str(args[0]) if args else ""
            # No mostrar logs de favicon o api
            if "/api/" in msg or "favicon" in msg:
                return
            print(f"[{self.log_date_time_string()}] {msg}")
        except Exception:
            return

    def handle(self):
        try:
            super().handle()
        except OSError as error:
            if not self._is_client_disconnect_error(error):
                raise


def main():
    print("=" * 50)
    print("Platzi Viewer - Drive API Server")
    print("=" * 50)
    print(f"URL: http://{DISPLAY_HOST}:{PORT}")
    print("=" * 50)
    print()

    # Cargar caché ANTES de iniciar el servidor
    server = create_server(BIND_HOST, PORT)

    try:
        run_server(server)
    except KeyboardInterrupt:
        print("\n[INFO] Servidor detenido")
        server.shutdown()


def create_server(host=BIND_HOST, port=PORT):
    init_cache()
    _init_repair_system()
    return ThreadingHTTPServer((host, port), PlatziHandler)


def run_server(server):
    server.serve_forever()


if __name__ == "__main__":
    main()
