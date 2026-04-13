export const API_URL = window.location?.origin || 'http://localhost:8080';
const RETRY_DELAY_MS = 1200;
const DEFAULT_TIMEOUT_MS = 12000;

// FFmpeg availability — used for compatibility fallback only.
let _ffmpegAvailable = null;
const _repairedCache = new Map();

export class ApiService {
    static _buildError(code, cause = null) {
        const error = new Error(code);
        error.code = code;
        if (cause) error.cause = cause;
        return error;
    }

    static async _fetchWithTimeout(url, options = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
        const controller = new AbortController();
        const timer = window.setTimeout(() => controller.abort(), timeoutMs);
        try {
            return await fetch(url, {
                ...options,
                signal: controller.signal,
            });
        } catch (error) {
            if (error?.name === 'AbortError') {
                throw this._buildError('request_timeout', error);
            }
            throw error;
        } finally {
            window.clearTimeout(timer);
        }
    }

    static async _wait(ms) {
        return new Promise((resolve) => window.setTimeout(resolve, ms));
    }

    static _normalizeDriveRef(fileRef) {
        if (!fileRef) return '';
        const value = String(fileRef).trim();
        if (!value || value.startsWith('local:')) return '';
        return encodeURIComponent(value);
    }

    /**
     * Detect ffmpeg availability from the server. Called once at startup;
     * result is cached so subsequent calls are instant.
     */
    static async detectFfmpeg() {
        if (_ffmpegAvailable !== null) return _ffmpegAvailable;
        try {
            const health = await this.getHealth();
            _ffmpegAvailable = !!health?.ffmpeg?.available;
        } catch {
            _ffmpegAvailable = false;
        }
        console.log(`[A/V] FFmpeg ${_ffmpegAvailable ? 'disponible \u2192 video remux activo' : 'no disponible \u2192 video raw'}`);
        return _ffmpegAvailable;
    }

    static _isCompletedRepair(payload) {
        return payload?.status === 'completed' && !!payload?.artifactPath;
    }

    static rememberRepairedArtifact(fileId, payload = null) {
        const safeRef = this._normalizeDriveRef(fileId);
        if (!safeRef) return false;
        if (payload && !this._isCompletedRepair(payload)) return false;
        _repairedCache.set(safeRef, {
            status: 'completed',
            artifactPath: payload?.artifactPath || `repaired_videos/${decodeURIComponent(safeRef)}.mp4`,
            updatedAt: Date.now(),
        });
        return true;
    }

    static getRepairedVideoUrl(fileId) {
        const safeRef = this._normalizeDriveRef(fileId);
        if (!safeRef) return '';
        return `${API_URL}/api/repaired/${safeRef}`;
    }

    static async requestRepair(fileId) {
        const safeRef = this._normalizeDriveRef(fileId);
        if (!safeRef) throw this._buildError('repair_invalid_file_id');

        const response = await this._fetchWithTimeout(
            `${API_URL}/api/repair/${safeRef}`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            },
            12000
        );

        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw this._buildError(`repair_http_${response.status}`, payload);
        }

        if (this._isCompletedRepair(payload)) {
            this.rememberRepairedArtifact(fileId, payload);
        }
        return payload;
    }

    static async getRepairStatus(fileId) {
        const safeRef = this._normalizeDriveRef(fileId);
        if (!safeRef) throw this._buildError('repair_invalid_file_id');

        const response = await this._fetchWithTimeout(
            `${API_URL}/api/repair-status/${safeRef}`,
            { cache: 'no-store' },
            8000
        );

        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw this._buildError(`repair_status_http_${response.status}`, payload);
        }

        if (this._isCompletedRepair(payload)) {
            this.rememberRepairedArtifact(fileId, payload);
        }
        return payload;
    }

    static async getCourses(retries = 5) {
        let lastError = null;
        for (let i = 0; i < retries; i++) {
            try {
                const response = await this._fetchWithTimeout(
                    `${API_URL}/api/courses`,
                    { cache: 'no-store' },
                    30000
                );
                if (!response.ok) throw this._buildError(`courses_http_${response.status}`);
                const data = await response.json();
                if (data?.categories?.length > 0) {
                    console.log('\ud83d\udce6 Data loaded:', data.stats);
                    return data;
                }

                console.log(`\u231b Waiting for data... (${i + 1}/${retries})`);
                lastError = this._buildError('courses_empty');
                await this._wait(RETRY_DELAY_MS);
            } catch (error) {
                lastError = error?.code ? error : this._buildError('courses_network', error);
                if (i === retries - 1) break;
                console.log(`Retrying... (${i + 1}/${retries})`);
                await this._wait(RETRY_DELAY_MS);
            }
        }
        throw lastError || this._buildError('courses_unavailable');
    }

    static async getBootstrap(retries = 8) {
        let lastError = null;
        for (let i = 0; i < retries; i++) {
            try {
                const response = await this._fetchWithTimeout(
                    `${API_URL}/api/bootstrap`,
                    { cache: 'no-store' },
                    10000
                );
                if (!response.ok) throw this._buildError(`bootstrap_http_${response.status}`);

                const data = await response.json();
                if (data?.categories?.length > 0) {
                    console.log('\ud83d\ude80 Bootstrap loaded:', data.stats);
                    return data;
                }

                lastError = this._buildError('bootstrap_empty');
                await this._wait(RETRY_DELAY_MS);
            } catch (error) {
                lastError = error?.code ? error : this._buildError('bootstrap_network', error);
                if (i === retries - 1) break;
                await this._wait(RETRY_DELAY_MS);
            }
        }
        throw lastError || this._buildError('bootstrap_unavailable');
    }

    static async getCourseDetail(catId, routeId, courseId, retries = 2) {
        const cat = encodeURIComponent(String(catId));
        const route = encodeURIComponent(String(routeId));
        const course = encodeURIComponent(String(courseId));
        const endpoint = `${API_URL}/api/course-detail/${cat}/${route}/${course}`;

        let lastError = null;
        for (let i = 0; i < retries; i++) {
            try {
                const response = await this._fetchWithTimeout(endpoint, { cache: 'no-store' }, 10000);
                if (response.status === 404) throw this._buildError('course_detail_not_found');
                if (!response.ok) throw this._buildError(`course_detail_http_${response.status}`);

                const data = await response.json();
                if (!data?.course) throw this._buildError('course_detail_invalid_payload');
                return data;
            } catch (error) {
                lastError = error?.code ? error : this._buildError('course_detail_network', error);
                if (i === retries - 1) break;
                await this._wait(500);
            }
        }
        throw lastError || this._buildError('course_detail_unavailable');
    }

    static async getProgress() {
        try {
            const response = await this._fetchWithTimeout(
                `${API_URL}/api/progress`,
                { cache: 'no-store' },
                6000
            );
            if (!response.ok) throw this._buildError(`progress_http_${response.status}`);
            const data = await response.json();
            return data && typeof data === 'object' && !Array.isArray(data) ? data : {};
        } catch (error) {
            throw error?.code ? error : this._buildError('progress_network', error);
        }
    }

    static async saveProgress(progress) {
        try {
            const response = await this._fetchWithTimeout(
                `${API_URL}/api/progress`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(progress || {}),
                },
                6000
            );
            if (!response.ok) throw this._buildError(`progress_save_http_${response.status}`);
        } catch (error) {
            throw error?.code ? error : this._buildError('progress_save_error', error);
        }
    }

    static async getHealth() {
        try {
            const response = await this._fetchWithTimeout(
                `${API_URL}/api/health`,
                { cache: 'no-store' },
                6000
            );
            if (!response.ok) throw this._buildError(`health_http_${response.status}`);
            return await response.json();
        } catch (error) {
            throw error?.code ? error : this._buildError('health_network', error);
        }
    }

    static async getVideoMetadata(fileId) {
        const safeRef = this._normalizeDriveRef(fileId);
        if (!safeRef) return null;
        try {
            const response = await this._fetchWithTimeout(
                `${API_URL}/api/video-metadata/${safeRef}`,
                { cache: 'force-cache' }, // safe to cache
                12000
            );
            if (!response.ok) return null;
            const data = await response.json();
            return data?.metadata || null;
        } catch (error) {
            console.warn('[API] Error fetching video metadata:', error);
            return null;
        }
    }

    static getVideoUrl(fileId) {
        const safeRef = this._normalizeDriveRef(fileId);
        if (!safeRef) return '';

        // Two-Stage Playback priority:
        // 1) repaired artifact (sync + seek)
        // 2) compat stream (sync, non-seekable while repair runs)
        // 3) raw Drive fallback
        if (_repairedCache.has(safeRef)) {
            return this.getRepairedVideoUrl(fileId);
        }

        // Compat is the default unless ffmpeg was explicitly detected as unavailable.
        if (_ffmpegAvailable !== false) {
            return this.getCompatibleVideoUrl(fileId);
        }

        return `${API_URL}/drive/files/${safeRef}`;
    }

    /** Always returns the raw Drive URL (for downloads, VLC, etc.) */
    static getVideoUrlRaw(fileId) {
        const safeRef = this._normalizeDriveRef(fileId);
        if (!safeRef) return '';
        return `${API_URL}/drive/files/${safeRef}`;
    }

    static getCompatibleVideoUrl(fileId) {
        const safeRef = this._normalizeDriveRef(fileId);
        if (!safeRef) return '';
        return `${API_URL}/api/video-compatible/${safeRef}`;
    }

    static getFileUrl(fileId) {
        const safeRef = this._normalizeDriveRef(fileId);
        if (!safeRef) return '';
        return `${API_URL}/drive/files/${safeRef}`;
    }
}
