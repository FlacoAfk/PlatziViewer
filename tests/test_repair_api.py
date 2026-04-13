from __future__ import annotations

import http.client
import json
import threading
import time


def _request_json(port: int, method: str, path: str):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        conn.request(method, path)
        response = conn.getresponse()
        body = response.read()
        payload = json.loads(body.decode("utf-8")) if body else {}
        return response.status, payload
    finally:
        conn.close()


def test_repair_trigger_and_status_complete(fresh_server_module, monkeypatch):
    file_id = "1RepairRefAA"

    monkeypatch.setattr(fresh_server_module, "_get_ffmpeg_executable", lambda: "ffmpeg")
    monkeypatch.setattr(fresh_server_module, "get_drive_service", lambda: object())

    def fake_repair(file_id, output_path, server_port):
        with open(output_path, "wb") as f:
            f.write(b"video-repaired-content")
        return {"ffmpegMode": "remux_audio", "artifactSize": 21}

    monkeypatch.setattr(fresh_server_module, "_repair_video_file", fake_repair)

    server = fresh_server_module.create_server("127.0.0.1", 0)
    port = server.server_address[1]
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        status_code, payload = _request_json(port, "POST", f"/api/repair/{file_id}")
        assert status_code in (200, 202)
        assert payload["status"] in {"pending", "in_progress", "completed"}

        deadline = time.time() + 5
        current_payload = {}
        while time.time() < deadline:
            status_code, current_payload = _request_json(port, "GET", f"/api/repair-status/{file_id}")
            assert status_code == 200
            if current_payload.get("status") == "completed":
                break
            time.sleep(0.1)

        assert current_payload.get("status") == "completed"
        assert current_payload.get("artifactPath", "").endswith(f"{file_id}.mp4")
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=3)


def test_repaired_video_supports_range_requests(fresh_server_module, monkeypatch):
    file_id = "1RepairRefAB"

    monkeypatch.setattr(fresh_server_module, "_get_ffmpeg_executable", lambda: "ffmpeg")
    monkeypatch.setattr(fresh_server_module, "get_drive_service", lambda: object())

    def fake_repair(file_id, output_path, server_port):
        with open(output_path, "wb") as f:
            f.write(b"0123456789")
        return {"ffmpegMode": "remux_audio", "artifactSize": 10}

    monkeypatch.setattr(fresh_server_module, "_repair_video_file", fake_repair)

    server = fresh_server_module.create_server("127.0.0.1", 0)
    port = server.server_address[1]
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        status_code, _ = _request_json(port, "POST", f"/api/repair/{file_id}")
        assert status_code in (200, 202)

        deadline = time.time() + 5
        while time.time() < deadline:
            status_code, payload = _request_json(port, "GET", f"/api/repair-status/{file_id}")
            assert status_code == 200
            if payload.get("status") == "completed":
                break
            time.sleep(0.1)

        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        try:
            conn.request("GET", f"/api/repaired/{file_id}", headers={"Range": "bytes=2-5"})
            response = conn.getresponse()
            body = response.read()
            assert response.status == 206
            assert response.getheader("Accept-Ranges") == "bytes"
            assert response.getheader("Content-Range") == "bytes 2-5/10"
            assert body == b"2345"
        finally:
            conn.close()
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=3)

import subprocess
import os

def test_repair_video_file_subprocess_call(fresh_server_module, monkeypatch):
    file_id = '1RepairRefAC'
    monkeypatch.setattr(fresh_server_module, '_get_ffmpeg_executable', lambda: 'fake-ffmpeg')

    cmd_called = []

    def fake_subprocess_run(cmd, **kwargs):
        cmd_called.extend(cmd)
        class Completed:
            returncode = 0
            stderr = b''
        with open(cmd[-1], 'wb') as f:
            f.write(b'fake-data')
        return Completed()

    monkeypatch.setattr(subprocess, 'run', fake_subprocess_run)

    out_path = 'dummy_out.mp4'
    if os.path.exists(out_path):
        os.remove(out_path)
        
    try:
        result = fresh_server_module._repair_video_file(file_id, out_path, 9999)
        assert result['ffmpegMode'] == 'remux_audio'
        assert 'fake-ffmpeg' in cmd_called
        assert 'http://127.0.0.1:9999/drive/files/1RepairRefAC?raw=1' in cmd_called
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)
