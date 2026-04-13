## Exploration: video-av-sync-fix

### Current State
The player is an HTML5 `<video>` with custom controls in `js/views/player.js`. On app startup, `state.init()` calls `ApiService.detectFfmpeg()` before any player view loads, and `ApiService.getVideoUrl()` returns `/api/video-compatible/{id}` whenever FFmpeg is available (`js/services/state.js:16-21`, `js/services/api.js:51-60`, `js/services/api.js:209-216`).

The raw Drive path `/drive/files/{id}` proxies Google Drive byte ranges and preserves `Accept-Ranges: bytes` plus `Content-Range` (`server.py:1331-1358`, `drive_service.py:212-250`). That path is seek-friendly.

The compatibility path `/api/video-compatible/{id}` runs FFmpeg against the raw Drive URL with timestamp-repair flags (`+genpts+igndts+discardcorrupt`, `avoid_negative_ts make_zero`) and audio resampling (`aresample=async=1:min_hard_comp=0.100:first_pts=0`) to stabilize damaged timestamps (`server.py:1133-1189`). It streams a fragmented MP4 to stdout and explicitly sends `Accept-Ranges: none` (`server.py:1202-1207`).

This means the codebase already assumes the root playback issue is malformed/missing source timestamps from some Drive-hosted files, not a bug in the custom controls themselves. The player also contains client-side drift detectors and auto-resync seeks, but those are mitigations layered on top of the media source (`js/views/player.js:1395-1424`, `js/views/player.js:1687-1799`).

### Affected Areas
- `js/views/player.js` — builds the player, custom seek UI, auto-resync logic, compatibility-mode activation, and sync prompts.
- `js/services/api.js` — chooses raw vs compatibility endpoint; today defaults to compatibility whenever FFmpeg exists.
- `js/services/state.js` — eagerly detects FFmpeg at startup, which effectively turns compatibility mode on globally.
- `server.py` — implements both `/drive/files/{id}` and `/api/video-compatible/{id}`, plus the initial remux path for non-range raw requests.
- `drive_service.py` — Drive proxy layer; preserves identity encoding and forwards byte-range requests to Google Drive.
- `README.md` — documents the intended diagnosis matrix and confirms the compatibility path is for videos with damaged timestamps.

### Approaches
1. **Server-side remux/transcode to a seekable artifact** — Generate a repaired MP4/HLS asset ahead of playback (temporary cache on disk or preprocessed artifact), then serve it with `Content-Length` and `Accept-Ranges: bytes`.
   - Pros: Fixes the real source problem; preserves native browser seek; cleanest UX; works with existing player controls.
   - Cons: Higher CPU/storage; needs cache invalidation and lifecycle management; first-play latency if generated on demand.
   - Effort: Medium

2. **On-the-fly compatibility stream only when explicitly requested** — Keep raw `/drive/files/{id}` as default, and switch to FFmpeg compatibility only for files/users that hit sync issues.
   - Pros: Restores seek for the majority path immediately; low backend change; keeps existing compat fallback.
   - Cons: Problematic videos still lose seek while in compat mode; user-visible mode switching; issue remains partially unresolved.
   - Effort: Low

3. **Hybrid detection of problematic files** — Probe files (ffprobe/manual allowlist/health telemetry) and route only suspicious videos to a repaired cached asset or compat mode.
   - Pros: Best tradeoff between cost and UX; avoids penalizing all videos; can evolve from allowlist to automated detection.
   - Cons: Detection can be imperfect; requires metadata/probing pipeline not present today; more moving parts than a global toggle.
   - Effort: Medium

4. **Client-only/player-only fix** — Rely on HTML5 player tweaks, custom resync seeks, or third-party player wrappers without changing the media source.
   - Pros: Lowest infrastructure impact.
   - Cons: Does not repair broken timestamps/container interleave; wrappers still depend on browser demux/decoder; unlikely to guarantee sync + seek together.
   - Effort: Low

### Recommendation
Choose **Approach 3: hybrid detection plus server-side repaired artifacts for flagged videos**.

Why: the code already shows the real defect is in the source media timeline, because the only reliable stabilization path is FFmpeg timestamp regeneration and audio resampling (`server.py:1144-1185`). But the current implementation delivers that fix as a non-seekable live-style stream (`Accept-Ranges: none`), which is exactly why seek breaks. A hybrid strategy lets normal videos stay on raw Drive byte-range streaming, while problematic files get a repaired seekable artifact served with range support. That gives us BOTH sync and seek, without forcing every video through CPU-heavy transcoding.

### Risks
- We do not currently have codec/container/ffprobe metadata in the cache, so automatic detection needs new probing or manual rollout criteria.
- Generating repaired assets on demand can add startup latency and disk usage if caching is not bounded.
- Chromium/WebView appears to be the primary target of the current workaround (`server.py:1135-1137`), but the repository does not contain a full cross-browser test matrix proving scope beyond those engines.

### Ready for Proposal
Yes — the proposal should state that the root cause is damaged source timestamps/interleave in some Drive videos, the current FFmpeg compatibility stream fixes sync by regenerating timestamps but disables byte-range seeking, and the preferred next step is a hybrid server-side repaired-asset strategy rather than more client-side player tuning.
