import { state } from '../services/state.js';
import { ApiService } from '../services/api.js';

export default class PlayerView {
    constructor(params) {
        this.catIdx = parseInt(params.catIdx);
        this.routeIdx = parseInt(params.routeIdx);
        this.courseIdx = parseInt(params.courseIdx);
        this.modIdx = parseInt(params.modIdx);
        this.classIdx = parseInt(params.classIdx);

        this.routeData = null;
        this.courseData = null;
        this.classData = null;
        this.classKey = null;
        this.detailErrorCode = null;

        this._isTouchMode = false;
        this._recommendedQualityLabel = null;
        this._isDestroyed = false;
        this._videoEl = null;
        this._startPlaybackTimeout = null;
        this._startPlaybackCanPlayHandler = null;
        this._videoFrameCallbackId = null;
        this._syncIssueResyncHits = 0;
        this._syncIssueWindowStartMs = 0;
        this._syncPromptVisible = false;
        this._syncPromptDismissed = false;
        this._syncPromptElement = null;
        this._syncPromptHideTimeout = null;
        this._isCompatibilityModeActive = false;
        this._compatibilitySwitchAttempts = 0;
        this._avSyncStats = null;
        this._lastCompatHealthSnapshot = null;
        this._compatHealthFetchInFlight = null;

        window.__playerView = this;
    }

    _getSyncPromptDismissKey() {
        if (!this.classKey) return null;
        return `platzi_sync_prompt_dismiss_${encodeURIComponent(this.classKey)}`;
    }

    _getSyncAutoExternalKey() {
        return 'platzi_sync_auto_external_player';
    }

    _isAutoExternalEnabledForSync() {
        try {
            return localStorage.getItem(this._getSyncAutoExternalKey()) === '1';
        } catch (e) {
            return false;
        }
    }

    _setAutoExternalEnabledForSync(enabled) {
        try {
            localStorage.setItem(this._getSyncAutoExternalKey(), enabled ? '1' : '0');
        } catch (e) {
            // no-op
        }
    }

    _dismissSyncPromptForCurrentClass() {
        this._syncPromptDismissed = true;
        const key = this._getSyncPromptDismissKey();
        if (!key) return;
        try {
            localStorage.setItem(key, '1');
        } catch (e) {
            // no-op
        }
    }

    _loadSyncPromptPreferenceForCurrentClass() {
        this._syncPromptDismissed = false;
        const key = this._getSyncPromptDismissKey();
        if (!key) return;
        try {
            this._syncPromptDismissed = localStorage.getItem(key) === '1';
        } catch (e) {
            this._syncPromptDismissed = false;
        }
    }

    _hideSyncCompatibilityPrompt() {
        if (this._syncPromptHideTimeout) {
            window.clearTimeout(this._syncPromptHideTimeout);
            this._syncPromptHideTimeout = null;
        }
        if (this._syncPromptElement) {
            this._syncPromptElement.remove();
            this._syncPromptElement = null;
        }
        this._syncPromptVisible = false;
    }

    _buildCompatibilityPromptMessage(forceVlcOnly = false) {
        const baseText = forceVlcOnly
            ? 'Este video sigue inestable incluso en modo compatibilidad. VLC suele reproducirlo mejor.'
            : 'Este video parece tener timestamps inestables. Puedes probar modo compatibilidad (FFmpeg) o VLC.';

        const snapshot = this._lastCompatHealthSnapshot;
        if (!snapshot) return baseText;

        const modeLabel = snapshot.lastMode ? `modo ${snapshot.lastMode}` : 'modo desconocido';
        const speedLabel = Number.isFinite(snapshot.lastSpeedMBps) ? `${snapshot.lastSpeedMBps.toFixed(2)} MB/s` : 'velocidad n/d';
        return `${baseText} Diagnóstico backend: ${modeLabel}, ${speedLabel}.`;
    }

    async _captureCompatibilityHealth(reason = 'sync_event') {
        if (this._isDestroyed) return null;
        if (this._compatHealthFetchInFlight) return this._compatHealthFetchInFlight;

        this._compatHealthFetchInFlight = ApiService.getHealth()
            .then((payload) => {
                const snapshot = {
                    reason,
                    capturedAt: Date.now(),
                    ffmpegAvailable: !!payload?.ffmpeg?.available,
                    lastMode: payload?.compatStream?.lastMode || null,
                    lastError: payload?.compatStream?.lastError || null,
                    lastDurationSec: payload?.compatStream?.lastDurationSec,
                    lastSpeedMBps: payload?.compatStream?.lastSpeedMBps,
                    successfulStreams: payload?.compatStream?.successfulStreams,
                    failedStreams: payload?.compatStream?.failedStreams,
                };

                this._lastCompatHealthSnapshot = snapshot;
                if (this._avSyncStats) this._avSyncStats.lastCompatHealth = snapshot;
                return snapshot;
            })
            .catch(() => null)
            .finally(() => {
                this._compatHealthFetchInFlight = null;
            });

        return this._compatHealthFetchInFlight;
    }

    _activateCompatibilityMode() {
        if (this._isDestroyed || this._isCompatibilityModeActive) return false;
        if (!this.videoFileRef) return false;

        this._captureCompatibilityHealth('compat_activate_attempt').catch(() => null);

        const video = this._videoEl || document.getElementById('mainVideo');
        if (!video) return false;

        const compatUrl = ApiService.getCompatibleVideoUrl(this.videoFileRef);
        if (!compatUrl) return false;

        const sourceTag = video.querySelector('source');
        const previousTime = video.currentTime || 0;
        const wasPaused = video.paused;
        const fallbackUrl = video.currentSrc || video.src || this.videoUrl;

        this._compatibilitySwitchAttempts += 1;
        if (this._avSyncStats) this._avSyncStats.compatibilityActivations = this._compatibilitySwitchAttempts;
        this._isCompatibilityModeActive = true;
        this._syncIssueResyncHits = 0;
        this._syncIssueWindowStartMs = Date.now();

        const onCompatError = () => {
            this._isCompatibilityModeActive = false;
            this._captureCompatibilityHealth('compat_activate_error').catch(() => null);

            if (!this._isDestroyed && fallbackUrl) {
                try {
                    if (sourceTag) sourceTag.src = fallbackUrl;
                    video.src = fallbackUrl;
                    video.load();
                    if (!wasPaused) {
                        if (this._playWhenReady) {
                            this._playWhenReady();
                        } else {
                            video.play().catch(() => { });
                        }
                    }
                } catch (e) {
                    // no-op
                }
            }

            this._showSyncCompatibilityPrompt(true);
        };

        video.addEventListener('error', onCompatError, { once: true });

        try {
            video.pause();
            if (sourceTag) sourceTag.src = compatUrl;
            video.src = compatUrl;
            video.load();

            video.addEventListener('loadedmetadata', () => {
                video.removeEventListener('error', onCompatError);

                if (Number.isFinite(previousTime) && previousTime > 0 && previousTime < (video.duration || Infinity)) {
                    video.currentTime = previousTime;
                }

                if (!wasPaused) {
                    if (this._playWhenReady) {
                        this._playWhenReady();
                    } else {
                        video.play().catch(() => { });
                    }
                }
            }, { once: true });

            console.log('[COMPAT] Activated FFmpeg compatibility stream for current class');
            this._captureCompatibilityHealth('compat_activate_success').catch(() => null);
            return true;
        } catch (e) {
            this._isCompatibilityModeActive = false;
            try {
                video.removeEventListener('error', onCompatError);
            } catch (_) {
                // no-op
            }
            return false;
        }
    }

    _showSyncCompatibilityPrompt(forceVlcOnly = false) {
        if (this._isDestroyed || this._syncPromptDismissed || this._syncPromptVisible) return;

        const container = document.getElementById('videoContainer');
        if (!container) return;

        this._hideSyncCompatibilityPrompt();

        const prompt = document.createElement('div');
        prompt.style.position = 'absolute';
        prompt.style.left = '12px';
        prompt.style.right = '12px';
        prompt.style.bottom = '70px';
        prompt.style.zIndex = '35';
        prompt.style.display = 'flex';
        prompt.style.alignItems = 'center';
        prompt.style.justifyContent = 'space-between';
        prompt.style.gap = '10px';
        prompt.style.padding = '10px 12px';
        prompt.style.borderRadius = '10px';
        prompt.style.background = 'rgba(0, 0, 0, 0.78)';
        prompt.style.border = '1px solid rgba(255, 255, 255, 0.2)';
        prompt.style.color = '#fff';
        prompt.style.backdropFilter = 'blur(4px)';

        const text = document.createElement('div');
        text.style.fontSize = '0.82rem';
        text.style.lineHeight = '1.3';
        text.textContent = this._buildCompatibilityPromptMessage(forceVlcOnly);

        this._captureCompatibilityHealth('sync_prompt').then(() => {
            if (this._isDestroyed || !this._syncPromptVisible || !this._syncPromptElement?.contains(text)) return;
            text.textContent = this._buildCompatibilityPromptMessage(forceVlcOnly);
        }).catch(() => null);

        const actions = document.createElement('div');
        actions.style.display = 'flex';
        actions.style.gap = '8px';
        actions.style.flexShrink = '0';

        if (!forceVlcOnly && !this._isCompatibilityModeActive) {
            const compatBtn = document.createElement('button');
            compatBtn.type = 'button';
            compatBtn.textContent = 'Modo compat.';
            compatBtn.style.border = '1px solid rgba(0,180,216,.5)';
            compatBtn.style.background = 'rgba(0,180,216,.18)';
            compatBtn.style.color = '#9feeff';
            compatBtn.style.borderRadius = '8px';
            compatBtn.style.padding = '6px 10px';
            compatBtn.style.cursor = 'pointer';
            compatBtn.onclick = () => {
                const switched = this._activateCompatibilityMode();
                this._hideSyncCompatibilityPrompt();
                if (!switched) {
                    this.openInExternalPlayer();
                }
            };
            actions.appendChild(compatBtn);
        }

        const openBtn = document.createElement('button');
        openBtn.type = 'button';
        openBtn.textContent = 'Abrir VLC';
        openBtn.style.border = '1px solid rgba(0,214,143,.5)';
        openBtn.style.background = 'rgba(0,214,143,.18)';
        openBtn.style.color = '#9fffdc';
        openBtn.style.borderRadius = '8px';
        openBtn.style.padding = '6px 10px';
        openBtn.style.cursor = 'pointer';
        openBtn.onclick = () => {
            this.openInExternalPlayer();
            this._hideSyncCompatibilityPrompt();
        };

        const alwaysBtn = document.createElement('button');
        alwaysBtn.type = 'button';
        alwaysBtn.textContent = 'Siempre';
        alwaysBtn.style.border = '1px solid rgba(255,255,255,.25)';
        alwaysBtn.style.background = 'rgba(255,255,255,.1)';
        alwaysBtn.style.color = '#fff';
        alwaysBtn.style.borderRadius = '8px';
        alwaysBtn.style.padding = '6px 10px';
        alwaysBtn.style.cursor = 'pointer';
        alwaysBtn.onclick = () => {
            this._setAutoExternalEnabledForSync(true);
            this.openInExternalPlayer();
            this._hideSyncCompatibilityPrompt();
        };

        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.textContent = '×';
        closeBtn.style.border = 'none';
        closeBtn.style.background = 'transparent';
        closeBtn.style.color = '#fff';
        closeBtn.style.fontSize = '1rem';
        closeBtn.style.cursor = 'pointer';
        closeBtn.style.padding = '0 4px';
        closeBtn.onclick = () => {
            this._dismissSyncPromptForCurrentClass();
            this._hideSyncCompatibilityPrompt();
        };

        actions.appendChild(openBtn);
        actions.appendChild(alwaysBtn);
        actions.appendChild(closeBtn);

        prompt.appendChild(text);
        prompt.appendChild(actions);

        container.appendChild(prompt);
        this._syncPromptElement = prompt;
        this._syncPromptVisible = true;
        this._syncPromptHideTimeout = window.setTimeout(() => {
            this._hideSyncCompatibilityPrompt();
        }, 12000);
    }

    _registerHardResyncEvent() {
        if (this._isDestroyed) return;

        if (this._avSyncStats) {
            this._avSyncStats.hardResyncEvents += 1;
            this._avSyncStats.lastHardResyncAt = Date.now();
        }

        const now = Date.now();
        if (!this._syncIssueWindowStartMs || now - this._syncIssueWindowStartMs > 120000) {
            this._syncIssueWindowStartMs = now;
            this._syncIssueResyncHits = 0;
        }

        this._syncIssueResyncHits += 1;

        if (this._syncIssueResyncHits >= 3) {
            if (!this._isCompatibilityModeActive && this._activateCompatibilityMode()) {
                this._syncIssueResyncHits = 0;
                this._syncIssueWindowStartMs = now;
                return;
            }

            if (this._isAutoExternalEnabledForSync()) {
                this.openInExternalPlayer();
            } else {
                this._showSyncCompatibilityPrompt();
            }
            this._syncIssueResyncHits = 0;
            this._syncIssueWindowStartMs = now;
        }
    }

    _isTouchDevice() {
        return (
            window.matchMedia('(hover: none), (pointer: coarse)').matches
            || 'ontouchstart' in window
            || navigator.maxTouchPoints > 0
        );
    }

    _getRecommendedQualityLabel(qualities) {
        if (!qualities?.length) return 'Original';

        const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
        const saveData = !!connection?.saveData;
        const effectiveType = connection?.effectiveType || '';
        const vh = Math.max(window.innerHeight || 0, window.innerWidth || 0);

        const list = [...qualities].sort((a, b) => (a.height || 0) - (b.height || 0));

        let target = 720;
        if (saveData || /(^|[^a-z])2g|slow-2g/.test(effectiveType)) target = 360;
        else if (/3g/.test(effectiveType)) target = 480;
        else if (vh <= 800) target = 480;
        else if (vh >= 1200) target = 1080;

        const selected = list.find((item) => (item.height || 0) >= target) || list[list.length - 1];
        return selected?.label || 'Original';
    }

    _getQualitySources() {
        const candidates = [
            this.classData?.videoQualities,
            this.classData?.qualities,
            this.classData?.videoSources,
            this.classData?.sources,
            this.classData?.streams,
            this.classData?.files?.videoQualities,
            this.classData?.files?.qualities,
            this.classData?.files?.videoSources,
            this.classData?.files?.sources,
            this.classData?.files?.streams,
        ];

        const normalized = [];

        const normalizeItem = (item, fallbackLabel = '') => {
            if (!item) return null;
            if (typeof item === 'string') {
                return {
                    label: fallbackLabel || 'Original',
                    url: item,
                    height: parseInt(String(fallbackLabel).replace(/[^\d]/g, ''), 10) || 0,
                };
            }

            const rawUrl = item.url || item.src || item.path || item.video;
            const fileRef = item.fileId || item.file || item.id;
            const url = rawUrl || (fileRef ? ApiService.getVideoUrl(fileRef) : null);
            if (!url) return null;

            const numericHeight = parseInt(item.height || item.resolution || item.quality || 0, 10);
            const rawLabel = item.label || item.name || (numericHeight ? `${numericHeight}p` : fallbackLabel || 'Original');
            const parsedFromLabel = parseInt(String(rawLabel).replace(/[^\d]/g, ''), 10) || 0;

            return {
                label: String(rawLabel).replace(/\s+/g, ' ').trim(),
                url,
                height: numericHeight || parsedFromLabel || 0,
            };
        };

        candidates.forEach((candidate) => {
            if (!candidate) return;

            if (Array.isArray(candidate)) {
                candidate.forEach((item) => {
                    const parsed = normalizeItem(item);
                    if (parsed) normalized.push(parsed);
                });
                return;
            }

            if (typeof candidate === 'object') {
                Object.entries(candidate).forEach(([key, value]) => {
                    const parsed = normalizeItem(value, key);
                    if (parsed) normalized.push(parsed);
                });
            }
        });

        if (this.videoUrl && !normalized.some((q) => q.url === this.videoUrl)) {
            normalized.push({ label: 'Original', url: this.videoUrl, height: 0 });
        }

        const uniqueByUrl = [];
        const seen = new Set();
        normalized.forEach((item) => {
            if (!item?.url || seen.has(item.url)) return;
            seen.add(item.url);
            uniqueByUrl.push(item);
        });

        return uniqueByUrl.sort((a, b) => (b.height || 0) - (a.height || 0));
    }

    async render() {
        this.routeData = state.getRoute(this.catIdx, this.routeIdx);
        this.courseData = state.getCourse(this.catIdx, this.routeIdx, this.courseIdx);

        if (!this.courseData) {
            return `
                <div class="error-state">
                    <h2>⚠️ Curso no encontrado</h2>
                    <a href="#home">← Volver al inicio</a>
                </div>
            `;
        }

        try {
            this.courseData = await state.ensureCourseDetail(this.catIdx, this.routeIdx, this.courseIdx) || this.courseData;
        } catch (error) {
            this.detailErrorCode = error?.code || 'course_detail_unavailable';
            this.courseData = state.getCourse(this.catIdx, this.routeIdx, this.courseIdx) || this.courseData;
        }

        this.routeData = state.getRoute(this.catIdx, this.routeIdx);
        this.classData = state.getClass(this.catIdx, this.routeIdx, this.courseIdx, this.modIdx, this.classIdx);
        this.classKey = state.getClassKey(this.catIdx, this.routeIdx, this.courseIdx, this.modIdx, this.classIdx);

        if (!this.classData) {
            return `
                <div class="error-state">
                    <h2>⚠️ Clase no encontrada</h2>
                    <p style="color: var(--text-muted); margin-top: .75rem;">
                        Código: <code style="background: var(--bg-card); padding: 4px 8px; border-radius: 4px;">${this.detailErrorCode || 'course_detail_missing'}</code>
                        • Endpoint: <code style="background: var(--bg-card); padding: 4px 8px; border-radius: 4px;">/api/course-detail/${this.catIdx}/${this.routeIdx}/${this.courseIdx}</code>
                    </p>
                    <a href="#home">← Volver al inicio</a>
                </div>
            `;
        }

        this.videoUrl = this.classData.hasVideo && this.classData.files?.video
            ? ApiService.getVideoUrl(this.classData.files.video)
            : null;
        this.videoFileRef = this.classData.files?.video || null;
        const subtitleUrl = this.classData.hasSubtitles && this.classData.files?.subtitles
            ? ApiService.getFileUrl(this.classData.files.subtitles)
            : null;
        const summaryUrl = this.classData.hasSummary && this.classData.files?.summary
            ? ApiService.getFileUrl(this.classData.files.summary)
            : null;
        const readingUrl = this.classData.hasReading && this.classData.files?.reading
            ? ApiService.getFileUrl(this.classData.files.reading)
            : null;
        const htmlUrl = this.classData.hasHtml && this.classData.files?.html
            ? ApiService.getFileUrl(this.classData.files.html)
            : null;

        const backHash = this.routeData?.isCourse
            ? `#route/${this.catIdx}/${this.routeIdx}`
            : `#course/${this.catIdx}/${this.routeIdx}/${this.courseIdx}`;

        const qualitySources = this._getQualitySources();
        this._recommendedQualityLabel = this._getRecommendedQualityLabel(qualitySources);

        return `
            <div class="view-player fade-in">
                <main class="player-main">
                    <div class="video-wrapper" id="videoWrapper">
                        <div class="video-container" id="videoContainer">
                            ${this.videoUrl ? `
                                <video id="mainVideo" preload="auto" playsinline crossorigin="anonymous" style="width:100%; height:100%; background:#000">
                                    <source src="${this.videoUrl}" type="video/mp4">
                                    ${subtitleUrl ? `<track id="subtitleTrack" kind="subtitles" src="${subtitleUrl}" srclang="es" label="Español" default>` : ''}
                                    Tu navegador no soporta video.
                                </video>
                            ` : `
                                <div class="no-video-placeholder">
                                    <span style="font-size:3rem">📝</span>
                                    <p>Esta clase no tiene video</p>
                                </div>
                            `}

                            ${this.videoUrl ? `
                            <!-- Floating overlay (Opera-style, top-center) -->
                            <div class="video-overlay" id="videoOverlay">
                                <button class="overlay-btn" onclick="window.__playerView.openInExternalPlayer()" title="Abrir en Reproductor Externo (VLC)">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
                                </button>
                                <a href="${this.videoUrl}" download class="overlay-btn" title="Descargar video">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                                </a>
                                <button class="overlay-btn" onclick="window.__playerView.navigateClass(-1)" title="Anterior">
                                    <svg class="overlay-nav-icon overlay-nav-icon-prev" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M6 6h2v12H6zM9.5 12l8.5 6V6z"/></svg>
                                </button>
                                <button class="overlay-btn" onclick="window.__playerView.navigateClass(1)" title="Siguiente">
                                    <svg class="overlay-nav-icon overlay-nav-icon-next" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M6 6h2v12H6zM9.5 12l8.5 6V6z"/></svg>
                                </button>
                            </div>

                            <!-- YouTube-style custom controls -->
                            <div class="yt-controls" id="ytControls">
                                <div class="yt-progress" id="ytProgress">
                                    <div class="yt-progress-buffered" id="ytBuffered"></div>
                                    <div class="yt-progress-played" id="ytPlayed"></div>
                                    <div class="yt-progress-thumb" id="ytThumb"></div>
                                </div>
                                <div class="yt-controls-row">
                                    <div class="yt-controls-left">
                                        <button class="yt-btn" id="ytPlayPause" title="Reproducir/Pausar">
                                            <svg id="ytIconPlay" width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
                                            <svg id="ytIconPause" width="22" height="22" viewBox="0 0 24 24" fill="currentColor" style="display:none"><path d="M6 4h4v16H6zm8 0h4v16h-4z"/></svg>
                                        </button>
                                        <div class="yt-volume-group">
                                            <button class="yt-btn" id="ytMuteBtn" title="Silenciar">
                                                <svg id="ytIconVol" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3A4.5 4.5 0 0014 8.14v7.72A4.49 4.49 0 0016.5 12zM14 3.23v2.06a6.5 6.5 0 010 13.42v2.06A8.51 8.51 0 0022 12 8.51 8.51 0 0014 3.23z"/></svg>
                                                <svg id="ytIconMute" width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style="display:none"><path d="M16.5 12A4.5 4.5 0 0014 8.14v2.72l2.44 2.44c.04-.2.06-.4.06-.6zM19 12a6.47 6.47 0 01-.53 2.61l1.53 1.53A8.46 8.46 0 0021 12c0-4.28-3-7.86-7-8.77v2.06A6.51 6.51 0 0119 12zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06a8.46 8.46 0 003.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4l-1.88 1.88L12 7.76V4z"/></svg>
                                            </button>
                                            <input type="range" class="yt-volume-slider" id="ytVolume" min="0" max="1" step="0.05" value="1">
                                        </div>
                                        <span class="yt-time" id="ytTime">0:00 / 0:00</span>
                                    </div>
                                    <div class="yt-controls-right">
                                        ${subtitleUrl ? `
                                        <button class="yt-btn yt-cc-btn" id="ytCCBtn" title="Subtítulos">
                                            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 14H4V6h16v12zM7 15h3c.55 0 1-.45 1-1v-1H9.5v.5h-2v-3h2v.5H11v-1c0-.55-.45-1-1-1H7c-.55 0-1 .45-1 1v4c0 .55.45 1 1 1zm7 0h3c.55 0 1-.45 1-1v-1h-1.5v.5h-2v-3h2v.5H18v-1c0-.55-.45-1-1-1h-3c-.55 0-1 .45-1 1v4c0 .55.45 1 1 1z"/></svg>
                                        </button>
                                        ` : ''}
                                        ${qualitySources.length > 0 ? `
                                        <div class="yt-quality-wrap" id="ytQualityWrap">
                                            <button class="yt-btn yt-quality-btn" id="ytQualityBtn" title="Calidad">Auto (${this._recommendedQualityLabel})</button>
                                            <div class="yt-quality-menu" id="ytQualityMenu">
                                                <button class="yt-quality-option active" data-quality="auto" data-label="${this._recommendedQualityLabel}">
                                                    <span>Auto</span>
                                                    <small>${this._recommendedQualityLabel}</small>
                                                </button>
                                                ${qualitySources.map((source) => `
                                                    <button class="yt-quality-option" data-quality="manual" data-label="${source.label}" data-url="${source.url}">
                                                        ${source.label}
                                                    </button>
                                                `).join('')}
                                            </div>
                                        </div>
                                        ` : ''}
                                        <button class="yt-btn" onclick="window.__playerView.openInExternalPlayer()" title="Abrir en Reproductor Externo (VLC)">
                                             <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
                                        </button>
                                        <button class="yt-btn" id="ytSpeed" title="Velocidad">1x</button>
                                        <button class="yt-btn" id="ytFullscreen" title="Pantalla completa">
                                            <svg id="ytIconExpand" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/></svg>
                                            <svg id="ytIconCompress" width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style="display:none"><path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z"/></svg>
                                        </button>
                                    </div>
                                </div>
                            </div>
                            ` : ''}

                            ${this.videoUrl ? `
                                <button
                                    class="player-sidebar-fab"
                                    id="playerSidebarFab"
                                    onclick="window.__playerView.toggleSidebar(event)"
                                    title="Ocultar/Mostrar temario"
                                    aria-label="Ocultar/Mostrar temario"
                                    aria-pressed="false"
                                >
                                    <span class="player-sidebar-fab-icon" aria-hidden="true">
                                        <svg class="fab-frame" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                                            <rect x="3" y="4" width="18" height="16" rx="3"></rect>
                                            <path d="M9 4v16"></path>
                                        </svg>
                                        <svg class="fab-arrow" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                            <path d="M14 6l-6 6 6 6"></path>
                                        </svg>
                                    </span>
                                </button>
                            ` : ''}
                        </div>
                    </div>

                    <!-- Info bar below video -->
                    <div class="player-info-bar">
                        <div class="player-info">
                            <h2 id="videoTitle">${this.classData.name}</h2>
                            <p class="player-course-name">${this.courseData?.name || ''}</p>
                        </div>
                        <div class="player-actions">
                            <a href="${backHash}" class="btn-action-pill btn-back">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5m7-7l-7 7 7 7"/></svg>
                                Volver
                            </a>
                            <button class="btn-action-pill btn-complete" onclick="window.__playerView.markComplete()">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                                Completada
                            </button>
                        </div>
                    </div>

                    ${this._renderResourcesSection(summaryUrl, readingUrl, htmlUrl)}
                </main>

                <aside class="player-sidebar">
                    <div class="sidebar-header">
                        <div class="sidebar-header-main">
                            <h3>📋 Temario</h3>
                            <p class="sidebar-subtitle">${this.courseData?.name || ''}</p>
                        </div>
                        <button
                            class="sidebar-classes-toggle"
                            id="sidebarClassesToggle"
                            onclick="window.__playerView.toggleSidebarClasses(event)"
                            title="Ocultar/Mostrar clases"
                            aria-label="Ocultar/Mostrar clases"
                            aria-pressed="false"
                        >
                            <span id="sidebarClassesToggleIcon">▼</span>
                        </button>
                    </div>
                    <div class="sidebar-content">
                        ${this.renderSidebar()}
                    </div>
                </aside>
            </div>
        `;
    }

    _getExtIcon(ext) {
        const icons = {
            '.pdf': '📕', '.zip': '📦', '.rar': '📦', '.7z': '📦', '.tar': '📦', '.gz': '📦',
            '.js': '📜', '.py': '🐍', '.css': '🎨', '.json': '📋', '.csv': '📊',
            '.sql': '🗃️', '.md': '📝', '.txt': '📄', '.html': '🌐', '.xml': '📰',
            '.png': '🖼️', '.jpg': '🖼️', '.jpeg': '🖼️', '.svg': '🎨', '.webp': '🖼️', '.gif': '🖼️',
            '.drawio': '📐', '.dbml': '📐', '.sln': '⚙️', '.gitignore': '⚙️',
            '.license': '📜', '.xlsx': '📊', '.xls': '📊', '.pptx': '📽️',
        };
        return icons[ext] || '📎';
    }

    _renderResourcesSection(summaryUrl, readingUrl, htmlUrl) {
        const resources = this.classData.resources || [];
        const hasAnyResource = summaryUrl || readingUrl || htmlUrl || resources.length > 0;
        if (!hasAnyResource) return '';

        // Resource file list
        let fileListHtml = '';
        if (resources.length > 0) {
            const fileItems = resources.map(r => {
                const icon = this._getExtIcon(r.ext);
                const url = ApiService.getFileUrl(r.file);
                if (r.viewable) {
                    return `
                        <div class="resource-file-item">
                            <span class="rf-icon">${icon}</span>
                            <a href="${url}" target="_blank" class="rf-name" title="${r.name}">${r.name}</a>
                            <span class="rf-ext">${r.ext}</span>
                            <a href="${url}" download class="rf-action rf-download" title="Descargar">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                            </a>
                        </div>
                    `;
                } else {
                    return `
                        <div class="resource-file-item">
                            <span class="rf-icon">${icon}</span>
                            <span class="rf-name" title="${r.name}">${r.name}</span>
                            <span class="rf-ext">${r.ext}</span>
                            <a href="${url}" download class="rf-action rf-download" title="Descargar">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                                Descargar
                            </a>
                        </div>
                    `;
                }
            }).join('');

            fileListHtml = `
                <div class="resources-file-list">
                    <div class="rf-header">📎 Archivos de la clase</div>
                    ${fileItems}
                </div>
            `;
        }

        // Summary iframe (always open if available)
        const summaryFrame = summaryUrl ? `
            <div class="resources-summary">
                <div class="rs-header" onclick="this.parentElement.classList.toggle('collapsed')">
                    <span>📄 Resumen de la clase</span>
                    <span class="rs-toggle">▼</span>
                </div>
                <div class="rs-content">
                    <iframe src="${summaryUrl}" class="summary-frame"></iframe>
                </div>
            </div>
        ` : '';

        const readingFrame = readingUrl ? `
            <div class="resources-summary collapsed">
                <div class="rs-header" onclick="this.parentElement.classList.toggle('collapsed')">
                    <span>📚 Lecturas recomendadas</span>
                    <span class="rs-toggle">▼</span>
                </div>
                <div class="rs-content">
                    <iframe src="${readingUrl}" class="summary-frame" title="Lecturas recomendadas"></iframe>
                </div>
            </div>
        ` : '';

        const htmlFrame = htmlUrl ? `
            <div class="resources-summary collapsed">
                <div class="rs-header" onclick="this.parentElement.classList.toggle('collapsed')">
                    <span>🌐 Contenido HTML</span>
                    <span class="rs-toggle">▼</span>
                </div>
                <div class="rs-content">
                    <iframe src="${htmlUrl}" class="summary-frame" title="Contenido HTML"></iframe>
                </div>
            </div>
        ` : '';

        return `
            <div class="player-resources-section">
                ${fileListHtml}
                ${summaryFrame}
                ${readingFrame}
                ${htmlFrame}
            </div>
        `;
    }

    renderSidebar() {
        if (!this.courseData || !this.courseData.modules) return '<p class="no-classes">No hay temario</p>';

        return this.courseData.modules.map((mod, modIdx) => {
            const classes = state.getModuleClasses(mod);
            if (classes.length === 0) return '';

            const isActiveModule = modIdx === this.modIdx;
            const completedInMod = classes.filter((_, i) => {
                const key = state.getClassKey(this.catIdx, this.routeIdx, this.courseIdx, modIdx, i);
                return state.isClassComplete(key);
            }).length;

            return `
                <div class="sb-module ${isActiveModule ? 'sb-module-active' : ''}">
                    <div class="sb-module-header">
                        <span class="sb-module-badge">${modIdx + 1}</span>
                        <div class="sb-module-info">
                            <span class="sb-module-name">${mod.name}</span>
                            <span class="sb-module-meta">${completedInMod}/${classes.length} clases</span>
                        </div>
                    </div>
                    <div class="sb-class-list">
                        ${classes.map((cls, classIdx) => {
                const key = state.getClassKey(this.catIdx, this.routeIdx, this.courseIdx, modIdx, classIdx);
                const isActive = modIdx === this.modIdx && classIdx === this.classIdx;
                const isComplete = state.isClassComplete(key);
                const hasVideo = cls.hasVideo && cls.files?.video;
                const typeIcon = cls.hasVideo ? '📹' : cls.hasHtml ? '⚡' : '📝';

                return `
                            <div class="sb-class ${isActive ? 'sb-active' : ''} ${isComplete ? 'sb-complete' : ''} ${hasVideo ? 'sb-clickable' : ''}"
                                 onclick="${hasVideo ? `window.location.hash='#player/${this.catIdx}/${this.routeIdx}/${this.courseIdx}/${modIdx}/${classIdx}'` : ''}">
                                <div class="sb-class-indicator">
                                    ${isComplete ? '<span class="sb-check">✓</span>' : isActive ? '<span class="sb-playing">▶</span>' : `<span class="sb-idx">${classIdx + 1}</span>`}
                                </div>
                                <div class="sb-class-content">
                                    <span class="sb-class-name">${cls.name}</span>
                                    <span class="sb-class-type">${typeIcon}</span>
                                </div>
                            </div>
                        `;
            }).join('')}
                    </div>
                </div>
            `;
        }).join('');
    }

    markComplete() {
        state.markClassComplete(this.classKey);
        const sidebar = document.querySelector('.sidebar-content');
        if (sidebar) sidebar.innerHTML = this.renderSidebar();
        // Visual feedback on the button
        const btn = document.querySelector('.btn-complete');
        if (btn) {
            btn.classList.add('completed');
            btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> ✅ Completada`;
        }
    }

    navigateClass(direction) {
        const modules = this.courseData?.modules || [];
        let modIdx = this.modIdx;
        let classIdx = this.classIdx + direction;

        while (modIdx >= 0 && modIdx < modules.length) {
            const classes = state.getModuleClasses(modules[modIdx]);
            if (classIdx >= 0 && classIdx < classes.length) {
                window.location.hash = `#player/${this.catIdx}/${this.routeIdx}/${this.courseIdx}/${modIdx}/${classIdx}`;
                return;
            }
            modIdx += direction;
            if (modIdx >= 0 && modIdx < modules.length) {
                const nextClasses = state.getModuleClasses(modules[modIdx]);
                classIdx = direction > 0 ? 0 : nextClasses.length - 1;
            }
        }
        console.log('No more classes in this direction');
    }

    async openInExternalPlayer() {
        if (!this.videoUrl) return;

        const streamUrl = this.videoUrl;

        // 1. Try to open via backend (local server functionality)
        try {
            const response = await fetch('/api/open-external', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: streamUrl })
            });

            if (response.ok) {
                console.log('Opened in external player via backend');
                return;
            } else {
                console.warn('Backend failed to open external player, falling back to client-side');
            }
        } catch (e) {
            console.warn('Network/API error opening external player:', e);
        }

        // 2. Fallback to client-side protocol handlers (Mobile / Default behavior)
        const ua = navigator.userAgent || '';
        const isAndroid = /Android/i.test(ua);
        const isIOS = /iPhone|iPad|iPod/i.test(ua);

        const fallbackOpen = () => {
            window.open(streamUrl, '_blank', 'noopener,noreferrer');
        };

        const copyLink = async () => {
            if (!navigator.clipboard?.writeText) return;
            try {
                await navigator.clipboard.writeText(streamUrl);
            } catch {
                // Ignore clipboard errors
            }
        };

        if (isAndroid) {
            const noScheme = streamUrl.replace(/^https?:\/\//i, '');
            const scheme = streamUrl.startsWith('https://') ? 'https' : 'http';
            const vlcIntent = `intent://${noScheme}#Intent;scheme=${scheme};package=org.videolan.vlc;action=android.intent.action.VIEW;type=video/*;end`;

            await copyLink();
            window.location.href = vlcIntent;
            setTimeout(fallbackOpen, 900);
            return;
        }

        if (isIOS) {
            const iosVlc = `vlc-x-callback://x-callback-url/stream?url=${encodeURIComponent(streamUrl)}`;

            await copyLink();
            window.location.href = iosVlc;
            setTimeout(fallbackOpen, 900);
            return;
        }

        const desktopVlc = `vlc://${streamUrl.replace(/^https?:\/\//i, '')}`;
        await copyLink();
        window.location.href = desktopVlc;
        setTimeout(fallbackOpen, 700);
    }

    _syncSidebarToggleButtons() {
        const view = document.querySelector('.view-player');
        const fab = document.getElementById('playerSidebarFab');
        if (!view || !fab) return;

        const collapsed = view.classList.contains('sidebar-collapsed');
        fab.setAttribute('aria-pressed', collapsed ? 'true' : 'false');
        fab.setAttribute('title', collapsed ? 'Mostrar temario' : 'Ocultar temario');
        fab.setAttribute('aria-label', collapsed ? 'Mostrar temario' : 'Ocultar temario');
        fab.classList.toggle('is-collapsed', collapsed);
    }

    toggleSidebar(event) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }

        if (this._isTouchMode) return;

        const view = document.querySelector('.view-player');
        if (!view) return;
        view.classList.toggle('sidebar-collapsed');
        this._syncSidebarToggleButtons();
    }

    _syncSidebarClassesToggleButtons() {
        const view = document.querySelector('.view-player');
        const toggle = document.getElementById('sidebarClassesToggle');
        const icon = document.getElementById('sidebarClassesToggleIcon');
        if (!view || !toggle || !icon) return;

        const collapsed = view.classList.contains('sidebar-classes-collapsed');
        toggle.setAttribute('aria-pressed', collapsed ? 'true' : 'false');
        toggle.setAttribute('title', collapsed ? 'Mostrar clases' : 'Ocultar clases');
        toggle.setAttribute('aria-label', collapsed ? 'Mostrar clases' : 'Ocultar clases');
        icon.textContent = collapsed ? '▲' : '▼';
    }

    toggleSidebarClasses(event) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }

        if (!this._isTouchMode) return;

        const view = document.querySelector('.view-player');
        if (!view) return;

        view.classList.toggle('sidebar-classes-collapsed');
        this._syncSidebarClassesToggleButtons();
    }

    // ─── YouTube-style custom controls logic ───
    _setupCustomControls() {
        const video = document.getElementById('mainVideo');
        const container = document.getElementById('videoContainer');
        if (!video || !container) return;

        const playPauseBtn = document.getElementById('ytPlayPause');
        const iconPlay = document.getElementById('ytIconPlay');
        const iconPause = document.getElementById('ytIconPause');
        const progressBar = document.getElementById('ytProgress');
        const playedBar = document.getElementById('ytPlayed');
        const bufferedBar = document.getElementById('ytBuffered');
        const thumb = document.getElementById('ytThumb');
        const timeDisplay = document.getElementById('ytTime');
        const muteBtn = document.getElementById('ytMuteBtn');
        const iconVol = document.getElementById('ytIconVol');
        const iconMute = document.getElementById('ytIconMute');
        const volumeSlider = document.getElementById('ytVolume');
        const speedBtn = document.getElementById('ytSpeed');
        const fullscreenBtn = document.getElementById('ytFullscreen');
        const iconExpand = document.getElementById('ytIconExpand');
        const iconCompress = document.getElementById('ytIconCompress');
        const qualityWrap = document.getElementById('ytQualityWrap');
        const qualityBtn = document.getElementById('ytQualityBtn');
        const qualityMenu = document.getElementById('ytQualityMenu');
        const overlay = document.getElementById('videoOverlay');
        const controls = document.getElementById('ytControls');

        const speeds = [0.5, 0.75, 1, 1.25, 1.5, 2];
        let currentSpeedIdx = 2;
        let pendingSeekResume = false;
        let manualSpeedOverride = false;
        let lastFrameStats = null;
        let lastAutoResyncMs = 0;
        let dropSpikeStreak = 0;
        let severeDropStreak = 0;
        let lastQualityDownshiftMs = 0;
        let lastHardResyncMs = 0;
        let qualitySources = [];
        let applyQuality = null;
        let autoDownshiftQuality = null;
        let lastQualitySwitchMs = 0;
        let driftStreak = 0;
        let severeDriftStreak = 0;
        let lastDriftSampleMs = 0;
        let lastSoftResyncMs = 0;

        const DRIFT_SOFT_THRESHOLD_SECONDS = 0.28;
        const DRIFT_HARD_THRESHOLD_SECONDS = 0.42;
        const MIN_DRIFT_SAMPLES_FOR_SOFT = 4;
        const MIN_DRIFT_SAMPLES_FOR_HARD = 6;
        const SOFT_RESYNC_COOLDOWN_MS = 9000;
        const HARD_RESYNC_COOLDOWN_MS = 12000;
        const QUALITY_SWITCH_MIN_INTERVAL_MS = 7000;

        this._avSyncStats = {
            startedAt: Date.now(),
            hardResyncEvents: 0,
            softResyncEvents: 0,
            frameDriftSoftHits: 0,
            frameDriftHardHits: 0,
            autoQualityDownshifts: 0,
            qualitySwitches: 0,
            compatibilityActivations: this._compatibilitySwitchAttempts || 0,
            lastHardResyncAt: 0,
            lastSoftResyncAt: 0,
        };

        const updateSpeedOverrideState = () => {
            manualSpeedOverride = Math.abs(video.playbackRate - 1) > 0.001;
        };

        // Format time
        const fmt = (s) => {
            const m = Math.floor(s / 60);
            const sec = Math.floor(s % 60);
            return `${m}:${sec < 10 ? '0' : ''}${sec}`;
        };

        const playWhenReady = () => {
            if (video.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA) {
                video.play().catch(() => { });
            } else {
                video.addEventListener('canplay', () => video.play().catch(() => { }), { once: true });
            }
        };

        const seekToTime = (targetTime) => {
            if (!Number.isFinite(video.duration) || video.duration <= 0) return;
            const clamped = Math.max(0, Math.min(video.duration, targetTime));
            const wasPlaying = !video.paused;
            pendingSeekResume = wasPlaying;
            if (wasPlaying) video.pause();
            video.currentTime = clamped;
        };

        const previewSeekFromClientX = (clientX) => {
            const rect = progressBar.getBoundingClientRect();
            const pct = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
            const target = pct * (video.duration || 0);
            playedBar.style.width = pct * 100 + '%';
            thumb.style.left = pct * 100 + '%';
            if (video.duration) {
                timeDisplay.textContent = `${fmt(target)} / ${fmt(video.duration)}`;
            }
            return target;
        };

        const getBufferAhead = () => {
            const t = video.currentTime;
            for (let i = 0; i < video.buffered.length; i++) {
                const start = video.buffered.start(i);
                const end = video.buffered.end(i);
                if (t >= start && t <= end) return Math.max(0, end - t);
            }
            return 0;
        };

        const hardResync = () => {
            const now = Date.now();
            if (now - lastHardResyncMs < HARD_RESYNC_COOLDOWN_MS) return;
            lastHardResyncMs = now;

            if (video.paused || video.seeking) return;

            this._registerHardResyncEvent();
            const targetTime = Math.max(0, (video.currentTime || 0) - 0.08);
            seekToTime(targetTime);
        };

        const softResync = () => {
            const now = Date.now();
            if (now - lastSoftResyncMs < SOFT_RESYNC_COOLDOWN_MS) return;
            if (video.paused || video.seeking) return;

            const bufferAhead = getBufferAhead();
            if (bufferAhead < 0.3) return;

            lastSoftResyncMs = now;
            if (this._avSyncStats) {
                this._avSyncStats.softResyncEvents += 1;
                this._avSyncStats.lastSoftResyncAt = now;
            }

            seekToTime(Math.max(0, (video.currentTime || 0) - 0.03));
        };

        this._playWhenReady = playWhenReady;
        this._seekToTime = seekToTime;
        this._getBufferAhead = getBufferAhead;

        const urlsMatch = (a, b) => {
            if (!a || !b) return false;
            try {
                return new URL(a, window.location.href).href === new URL(b, window.location.href).href;
            } catch (_) {
                return String(a) === String(b);
            }
        };

        // Play / Pause
        const updatePlayIcon = () => {
            const paused = video.paused;
            iconPlay.style.display = paused ? '' : 'none';
            iconPause.style.display = paused ? 'none' : '';
        };
        playPauseBtn.addEventListener('click', () => {
            video.paused ? video.play() : video.pause();
        });
        video.addEventListener('play', updatePlayIcon);
        video.addEventListener('pause', updatePlayIcon);

        // Click on video to play/pause
        video.addEventListener('click', () => {
            video.paused ? video.play() : video.pause();
        });

        // Time update → progress bar + time text
        video.addEventListener('timeupdate', () => {
            if (video.duration) {
                const pct = (video.currentTime / video.duration) * 100;
                playedBar.style.width = pct + '%';
                thumb.style.left = pct + '%';
                timeDisplay.textContent = `${fmt(video.currentTime)} / ${fmt(video.duration)}`;
            }
        });

        // Buffered
        video.addEventListener('progress', () => {
            if (video.buffered.length && video.duration) {
                bufferedBar.style.background = 'transparent';
                bufferedBar.innerHTML = '';
                for (let i = 0; i < video.buffered.length; i++) {
                    const start = video.buffered.start(i);
                    const end = video.buffered.end(i);
                    const left = (start / video.duration) * 100;
                    const width = ((end - start) / video.duration) * 100;
                    const chunk = document.createElement('div');
                    chunk.style.position = 'absolute';
                    chunk.style.left = left + '%';
                    chunk.style.width = width + '%';
                    chunk.style.height = '100%';
                    chunk.style.background = 'rgba(255, 255, 255, 0.3)';
                    chunk.style.borderRadius = '2px';
                    bufferedBar.appendChild(chunk);
                }
                bufferedBar.style.width = '100%';
            }
        });

        // Seek on progress bar (single commit on mouseup to avoid double-seek races)
        let isSeeking = false;
        let pendingSeekTarget = null;
        video.addEventListener('seeked', () => {
            if (!pendingSeekResume) return;
            pendingSeekResume = false;
            playWhenReady();
        });
        progressBar.addEventListener('mousedown', (e) => {
            isSeeking = true;
            pendingSeekTarget = previewSeekFromClientX(e.clientX);
        });
        this._progressMouseMoveHandler = (e) => {
            if (isSeeking) {
                pendingSeekTarget = previewSeekFromClientX(e.clientX);
            }
        };
        this._progressMouseUpHandler = () => {
            if (isSeeking) {
                isSeeking = false;
                if (Number.isFinite(pendingSeekTarget)) {
                    seekToTime(pendingSeekTarget);
                }
                pendingSeekTarget = null;
            }
        };
        document.addEventListener('mousemove', this._progressMouseMoveHandler);
        document.addEventListener('mouseup', this._progressMouseUpHandler);

        // Volume
        volumeSlider.addEventListener('input', () => {
            video.volume = parseFloat(volumeSlider.value);
            video.muted = false;
            updateVolIcon();
        });
        muteBtn.addEventListener('click', () => {
            video.muted = !video.muted;
            updateVolIcon();
        });
        const updateVolIcon = () => {
            const muted = video.muted || video.volume === 0;
            iconVol.style.display = muted ? 'none' : '';
            iconMute.style.display = muted ? '' : 'none';
            if (!video.muted) volumeSlider.value = video.volume;
        };

        // Speed
        speedBtn.addEventListener('click', () => {
            currentSpeedIdx = (currentSpeedIdx + 1) % speeds.length;
            video.playbackRate = speeds[currentSpeedIdx];
            updateSpeedOverrideState();
            speedBtn.textContent = speeds[currentSpeedIdx] + 'x';
        });

        // Subtitles (CC toggle)
        const ccBtn = document.getElementById('ytCCBtn');
        const subtitleTrack = document.getElementById('subtitleTrack');
        if (ccBtn && video.textTracks.length > 0) {
            // Start with subtitles OFF
            video.textTracks[0].mode = 'hidden';
            let ccActive = false;
            ccBtn.addEventListener('click', () => {
                ccActive = !ccActive;
                video.textTracks[0].mode = ccActive ? 'showing' : 'hidden';
                ccBtn.classList.toggle('yt-cc-active', ccActive);
            });
        }

        // Quality menu
        if (qualityWrap && qualityBtn && qualityMenu) {
            qualitySources = this._getQualitySources();
            const sourceTag = video.querySelector('source');

            const setActiveQualityOption = (mode, label) => {
                qualityMenu.querySelectorAll('.yt-quality-option').forEach((option) => {
                    const isAuto = mode === 'auto' && option.dataset.quality === 'auto';
                    const isManual = mode === 'manual'
                        && option.dataset.quality === 'manual'
                        && option.dataset.label === label;
                    option.classList.toggle('active', isAuto || isManual);
                });
            };

            applyQuality = (url, label, mode) => {
                if (!url) return;

                const currentSource = sourceTag?.src || video.currentSrc || video.src;
                if (urlsMatch(currentSource, url)) return;

                const now = Date.now();
                const isAutoMode = mode === 'auto';
                if (isAutoMode && now - lastQualitySwitchMs < QUALITY_SWITCH_MIN_INTERVAL_MS) return;
                lastQualitySwitchMs = now;

                const previousTime = video.currentTime || 0;
                const wasPaused = video.paused;

                video.pause();
                if (sourceTag) sourceTag.src = url;
                video.src = url;
                video.load();

                video.addEventListener('loadedmetadata', () => {
                    if (Number.isFinite(previousTime) && previousTime > 0 && previousTime < video.duration) {
                        video.currentTime = previousTime;
                    }
                    if (!wasPaused) {
                        if (video.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA) {
                            video.play().catch(() => { });
                        } else {
                            video.addEventListener('canplay', () => video.play().catch(() => { }), { once: true });
                        }
                    }
                }, { once: true });

                qualityBtn.textContent = mode === 'auto' ? `Auto (${label})` : label;
                setActiveQualityOption(mode, label);
                qualityWrap.classList.remove('open');
                if (this._avSyncStats) {
                    this._avSyncStats.qualitySwitches += 1;
                }
            };

            const getCurrentQualityIndex = () => {
                const currentSource = sourceTag?.src || video.currentSrc || video.src;
                const byUrlIdx = qualitySources.findIndex((item) => urlsMatch(item.url, currentSource));
                if (byUrlIdx !== -1) return byUrlIdx;

                const activeLabel = (qualityBtn.textContent || '').replace(/^Auto\s*\(|\)$/g, '').trim();
                const byLabelIdx = qualitySources.findIndex((item) => item.label === activeLabel);
                return byLabelIdx;
            };

            autoDownshiftQuality = () => {
                if (!qualitySources.length || !applyQuality) return false;
                if (!String(qualityBtn.textContent || '').trim().startsWith('Auto')) return false;

                const currentIdx = getCurrentQualityIndex();
                if (currentIdx < 0 || currentIdx >= qualitySources.length - 1) return false;

                const lowerQuality = qualitySources[currentIdx + 1];
                if (!lowerQuality?.url) return false;

                applyQuality(lowerQuality.url, lowerQuality.label || 'Original', 'auto');
                return true;
            };

            qualityBtn.addEventListener('click', (event) => {
                event.preventDefault();
                event.stopPropagation();
                qualityWrap.classList.toggle('open');
            });

            qualityMenu.addEventListener('click', (event) => {
                const option = event.target.closest('.yt-quality-option');
                if (!option) return;

                event.preventDefault();
                event.stopPropagation();

                if (option.dataset.quality === 'auto') {
                    const recommended = this._recommendedQualityLabel || this._getRecommendedQualityLabel(qualitySources);
                    const fallback = qualitySources[qualitySources.length - 1];
                    const selected = qualitySources.find((item) => item.label === recommended) || fallback;
                    if (selected) applyQuality(selected.url, recommended, 'auto');
                    return;
                }

                const selectedUrl = option.dataset.url;
                const selectedLabel = option.dataset.label || 'Original';
                applyQuality(selectedUrl, selectedLabel, 'manual');
            });

            const recommended = this._recommendedQualityLabel || this._getRecommendedQualityLabel(qualitySources);
            const fallback = qualitySources[qualitySources.length - 1];
            const selected = qualitySources.find((item) => item.label === recommended) || fallback;
            if (selected) {
                const selectedLabel = selected.label || recommended;
                qualityBtn.textContent = `Auto (${selectedLabel})`;
                setActiveQualityOption('auto', selectedLabel);
                const currentSource = sourceTag?.src || video.currentSrc || video.src;
                if (!urlsMatch(currentSource, selected.url)) {
                    applyQuality(selected.url, selectedLabel, 'auto');
                }
            }

            this._qualityOutsideHandler = (event) => {
                if (!qualityWrap.contains(event.target)) qualityWrap.classList.remove('open');
            };
            document.addEventListener('click', this._qualityOutsideHandler);

        }

        this._syncGuardTimer = window.setInterval(() => {
            if (manualSpeedOverride || video.paused || video.seeking || Math.abs(video.playbackRate - 1) > 0.001) {
                dropSpikeStreak = 0;
                severeDropStreak = 0;
                return;
            }
            if (typeof video.getVideoPlaybackQuality !== 'function') return;

            const qualityStats = video.getVideoPlaybackQuality();
            const dropped = qualityStats?.droppedVideoFrames || 0;
            const total = qualityStats?.totalVideoFrames || 0;

            if (!lastFrameStats) {
                lastFrameStats = { dropped, total };
                return;
            }

            const droppedDelta = dropped - lastFrameStats.dropped;
            const totalDelta = total - lastFrameStats.total;
            lastFrameStats = { dropped, total };

            const sampledFrames = droppedDelta + totalDelta;
            if (sampledFrames < 45) return;

            const dropRatio = droppedDelta / sampledFrames;
            const bufferAhead = getBufferAhead();

            const isModerateDrop = dropRatio >= 0.12 && sampledFrames >= 60;
            const isSevereDrop = dropRatio >= 0.2 && sampledFrames >= 60;

            dropSpikeStreak = isModerateDrop ? dropSpikeStreak + 1 : 0;
            severeDropStreak = isSevereDrop ? severeDropStreak + 1 : 0;

            if (severeDropStreak >= 2 && bufferAhead >= 0.35) {
                const now = Date.now();
                const canDownshift = now - lastQualityDownshiftMs >= 9000;

                if (canDownshift && autoDownshiftQuality && autoDownshiftQuality()) {
                    lastQualityDownshiftMs = now;
                    dropSpikeStreak = 0;
                    severeDropStreak = 0;
                    if (this._avSyncStats) {
                        this._avSyncStats.autoQualityDownshifts += 1;
                    }
                    return;
                }

                softResync();
                severeDropStreak = 0;
                return;
            }

            if (dropSpikeStreak < 3 || bufferAhead < 0.6) return;

            const now = Date.now();
            if (now - lastAutoResyncMs < 8000) return;
            lastAutoResyncMs = now;
            dropSpikeStreak = 0;
            softResync();
        }, 3000);

        if (typeof video.requestVideoFrameCallback === 'function') {
            const frameSyncLoop = (_timestamp, metadata) => {
                if (this._isDestroyed) return;

                updateSpeedOverrideState();

                const now = Date.now();
                if (now - lastDriftSampleMs < 700) {
                    this._videoFrameCallbackId = video.requestVideoFrameCallback(frameSyncLoop);
                    return;
                }
                lastDriftSampleMs = now;

                if (!video.paused && !video.seeking && !manualSpeedOverride && Number.isFinite(metadata?.mediaTime)) {
                    const driftSeconds = Math.abs((video.currentTime || 0) - metadata.mediaTime);

                    if (driftSeconds >= DRIFT_SOFT_THRESHOLD_SECONDS) {
                        driftStreak += 1;
                        if (this._avSyncStats) this._avSyncStats.frameDriftSoftHits += 1;
                    } else {
                        driftStreak = 0;
                    }

                    if (driftSeconds >= DRIFT_HARD_THRESHOLD_SECONDS) {
                        severeDriftStreak += 1;
                        if (this._avSyncStats) this._avSyncStats.frameDriftHardHits += 1;
                    } else {
                        severeDriftStreak = 0;
                    }

                    if (severeDriftStreak >= MIN_DRIFT_SAMPLES_FOR_HARD) {
                        hardResync();
                        severeDriftStreak = 0;
                        driftStreak = 0;
                    } else if (driftStreak >= MIN_DRIFT_SAMPLES_FOR_SOFT) {
                        softResync();
                        driftStreak = 0;
                    }
                } else {
                    driftStreak = 0;
                    severeDriftStreak = 0;
                }

                this._videoFrameCallbackId = video.requestVideoFrameCallback(frameSyncLoop);
            };

            this._videoFrameCallbackId = video.requestVideoFrameCallback(frameSyncLoop);
        }

        // Fullscreen (proper API on the wrapper, not video element)
        const wrapper = document.getElementById('videoWrapper');
        fullscreenBtn.addEventListener('click', () => {
            if (!document.fullscreenElement) {
                (wrapper.requestFullscreen || wrapper.webkitRequestFullscreen || wrapper.msRequestFullscreen).call(wrapper);
            } else {
                (document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen).call(document);
            }
        });
        const onFsChange = () => {
            const isFs = !!document.fullscreenElement;
            iconExpand.style.display = isFs ? 'none' : '';
            iconCompress.style.display = isFs ? '' : 'none';
            wrapper.classList.toggle('fullscreen', isFs);
        };
        document.addEventListener('fullscreenchange', onFsChange);
        document.addEventListener('webkitfullscreenchange', onFsChange);
        this._fsChangeHandler = onFsChange;

        // Show/hide overlay + controls on mouse move
        let hideTimeout;
        const showControls = () => {
            container.classList.add('show-ui');
            clearTimeout(hideTimeout);
            hideTimeout = setTimeout(() => {
                if (!video.paused) container.classList.remove('show-ui');
            }, 2500);
        };
        container.addEventListener('mousemove', showControls);
        container.addEventListener('mouseenter', showControls);
        container.addEventListener('mouseleave', () => {
            clearTimeout(hideTimeout);
            if (!video.paused) container.classList.remove('show-ui');
        });
        video.addEventListener('pause', () => container.classList.add('show-ui'));
        video.addEventListener('play', () => {
            hideTimeout = setTimeout(() => container.classList.remove('show-ui'), 2500);
        });

        // Initial state
        container.classList.add('show-ui');
        updatePlayIcon();

        // Double click to fullscreen
        video.addEventListener('dblclick', () => {
            fullscreenBtn.click();
        });
    }

    mounted() {
        this._isDestroyed = false;
        this._loadSyncPromptPreferenceForCurrentClass();
        this._syncIssueResyncHits = 0;
        this._syncIssueWindowStartMs = 0;
        this._isCompatibilityModeActive = false;
        this._compatibilitySwitchAttempts = 0;
        this._avSyncStats = null;
        this._lastCompatHealthSnapshot = null;
        this._compatHealthFetchInFlight = null;
        const video = document.getElementById('mainVideo');
        this._videoEl = video || null;
        if (video) {
            this._setupCustomControls();

            // Start only when we have enough forward buffer to reduce A/V drift on heavy classes.
            const startPlayback = () => {
                if (this._isDestroyed) return;
                if (video.readyState < HTMLMediaElement.HAVE_FUTURE_DATA) {
                    if (!this._startPlaybackCanPlayHandler) {
                        this._startPlaybackCanPlayHandler = () => {
                            this._startPlaybackCanPlayHandler = null;
                            startPlayback();
                        };
                        video.addEventListener('canplay', this._startPlaybackCanPlayHandler, { once: true });
                    }
                    return;
                }

                const bufferAhead = this._getBufferAhead ? this._getBufferAhead() : 0;
                if (bufferAhead < 0.25) {
                    if (this._startPlaybackTimeout) {
                        window.clearTimeout(this._startPlaybackTimeout);
                    }
                    this._startPlaybackTimeout = window.setTimeout(() => {
                        this._startPlaybackTimeout = null;
                        startPlayback();
                    }, 120);
                    return;
                }

                if (this._isDestroyed) return;
                video.play().catch(() => { });
            };
            startPlayback();

            video.addEventListener('play', () => {
                state.markClassInProgress(this.classKey, video.currentTime);
            });
            video.addEventListener('ended', () => {
                state.markClassComplete(this.classKey);
                const sidebar = document.querySelector('.sidebar-content');
                if (sidebar) sidebar.innerHTML = this.renderSidebar();
                setTimeout(() => this.navigateClass(1), 1500);
            });
        }

        this._isTouchMode = this._isTouchDevice();
        const view = document.querySelector('.view-player');
        if (view) {
            view.classList.toggle('touch-mode', this._isTouchMode);
            if (this._isTouchMode) {
                view.classList.remove('sidebar-collapsed');
            } else {
                view.classList.remove('sidebar-classes-collapsed');
            }
        }
        this._syncSidebarToggleButtons();
        this._syncSidebarClassesToggleButtons();

        this._viewportModeHandler = () => {
            const touchNow = this._isTouchDevice();
            if (touchNow === this._isTouchMode) return;
            this._isTouchMode = touchNow;

            const playerView = document.querySelector('.view-player');
            if (!playerView) return;
            playerView.classList.toggle('touch-mode', this._isTouchMode);

            if (this._isTouchMode) {
                playerView.classList.remove('sidebar-collapsed');
            } else {
                playerView.classList.remove('sidebar-classes-collapsed');
            }
            this._syncSidebarToggleButtons();
            this._syncSidebarClassesToggleButtons();
        };
        window.addEventListener('resize', this._viewportModeHandler);

        // Keyboard shortcuts
        this._keyHandler = (e) => {
            const video = document.getElementById('mainVideo');
            if (e.key === 'ArrowLeft' && e.altKey) this.navigateClass(-1);
            if (e.key === 'ArrowRight' && e.altKey) this.navigateClass(1);
            // Spacebar to play/pause
            if (e.key === ' ' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
                e.preventDefault();
                if (video) video.paused ? video.play() : video.pause();
            }
            // F for fullscreen
            if (e.key === 'f' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
                const fsBtn = document.getElementById('ytFullscreen');
                if (fsBtn) fsBtn.click();
            }
            // Left/Right arrows to seek 5s (with sync fix)
            if (e.key === 'ArrowLeft' && !e.altKey && video) {
                e.preventDefault();
                if (this._seekToTime) this._seekToTime(video.currentTime - 5);
            }
            if (e.key === 'ArrowRight' && !e.altKey && video) {
                e.preventDefault();
                if (this._seekToTime) this._seekToTime(video.currentTime + 5);
            }
        };
        document.addEventListener('keydown', this._keyHandler);
    }

    _stopVideoPlayback() {
        const video = this._videoEl || document.getElementById('mainVideo');
        if (!video) return;

        try {
            video.pause();
        } catch (e) {
            // no-op
        }

        try {
            video.removeAttribute('src');
            const source = video.querySelector('source');
            if (source) source.removeAttribute('src');
            video.load();
        } catch (e) {
            // no-op
        }

        try {
            if (document.fullscreenElement) {
                (document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen).call(document);
            }
        } catch (e) {
            // no-op
        }
    }

    destroy() {
        this._isDestroyed = true;
        this._hideSyncCompatibilityPrompt();

        if (this._avSyncStats) {
            const elapsedSec = Math.max(1, Math.round((Date.now() - this._avSyncStats.startedAt) / 1000));
            console.log('[A/V SYNC]', {
                elapsedSec,
                hardResyncEvents: this._avSyncStats.hardResyncEvents,
                softResyncEvents: this._avSyncStats.softResyncEvents,
                frameDriftSoftHits: this._avSyncStats.frameDriftSoftHits,
                frameDriftHardHits: this._avSyncStats.frameDriftHardHits,
                autoQualityDownshifts: this._avSyncStats.autoQualityDownshifts,
                qualitySwitches: this._avSyncStats.qualitySwitches,
                compatibilityActivations: this._avSyncStats.compatibilityActivations,
                lastCompatHealth: this._lastCompatHealthSnapshot,
            });
            window.__platziAvSyncLastStats = {
                ...this._avSyncStats,
                elapsedSec,
                lastCompatHealth: this._lastCompatHealthSnapshot,
            };
        }

        if (this._startPlaybackTimeout) {
            window.clearTimeout(this._startPlaybackTimeout);
            this._startPlaybackTimeout = null;
        }

        if (this._videoEl && this._startPlaybackCanPlayHandler) {
            this._videoEl.removeEventListener('canplay', this._startPlaybackCanPlayHandler);
            this._startPlaybackCanPlayHandler = null;
        }

        if (this._videoEl && this._videoFrameCallbackId !== null && typeof this._videoEl.cancelVideoFrameCallback === 'function') {
            this._videoEl.cancelVideoFrameCallback(this._videoFrameCallbackId);
            this._videoFrameCallbackId = null;
        }

        this._stopVideoPlayback();
        if (this._keyHandler) document.removeEventListener('keydown', this._keyHandler);
        if (this._progressMouseMoveHandler) document.removeEventListener('mousemove', this._progressMouseMoveHandler);
        if (this._progressMouseUpHandler) document.removeEventListener('mouseup', this._progressMouseUpHandler);
        if (this._syncGuardTimer) window.clearInterval(this._syncGuardTimer);
        if (this._viewportModeHandler) window.removeEventListener('resize', this._viewportModeHandler);
        if (this._qualityOutsideHandler) document.removeEventListener('click', this._qualityOutsideHandler);
        if (this._fsChangeHandler) {
            document.removeEventListener('fullscreenchange', this._fsChangeHandler);
            document.removeEventListener('webkitfullscreenchange', this._fsChangeHandler);
        }
        this._videoFrameCallbackId = null;
        this._videoEl = null;
        this._avSyncStats = null;
        this._lastCompatHealthSnapshot = null;
        this._compatHealthFetchInFlight = null;
        window.__playerView = null;
    }
}
