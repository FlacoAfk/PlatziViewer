export const API_URL = window.location?.origin || 'http://localhost:8080';
const RETRY_DELAY_MS = 1200;
const DEFAULT_TIMEOUT_MS = 12000;

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
                    console.log('📦 Data loaded:', data.stats);
                    return data;
                }

                console.log(`⏳ Waiting for data... (${i + 1}/${retries})`);
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
                    console.log('🚀 Bootstrap loaded:', data.stats);
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

    static getVideoUrl(fileId) {
        const safeRef = this._normalizeDriveRef(fileId);
        if (!safeRef) return '';
        return `${API_URL}/drive/files/${safeRef}`;
    }

    static getFileUrl(fileId) {
        const safeRef = this._normalizeDriveRef(fileId);
        if (!safeRef) return '';
        return `${API_URL}/drive/files/${safeRef}`;
    }
}
