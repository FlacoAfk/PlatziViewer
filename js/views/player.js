import { state } from '../services/state.js';
import { ApiService } from '../services/api.js';

export default class PlayerView {
    constructor(params) {
        this.catIdx = parseInt(params.catIdx);
        this.routeIdx = parseInt(params.routeIdx);
        this.courseIdx = parseInt(params.courseIdx);
        this.modIdx = parseInt(params.modIdx);
        this.classIdx = parseInt(params.classIdx);

        this.routeData = state.getRoute(this.catIdx, this.routeIdx);
        this.courseData = state.getCourse(this.catIdx, this.routeIdx, this.courseIdx);
        this.classData = state.getClass(this.catIdx, this.routeIdx, this.courseIdx, this.modIdx, this.classIdx);
        this.classKey = state.getClassKey(this.catIdx, this.routeIdx, this.courseIdx, this.modIdx, this.classIdx);

        window.__playerView = this;
    }

    async render() {
        if (!this.classData) {
            return `
                <div class="error-state">
                    <h2>⚠️ Clase no encontrada</h2>
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

        return `
            <div class="view-player fade-in">
                <main class="player-main">
                    <div class="video-wrapper" id="videoWrapper">
                        <div class="video-container" id="videoContainer">
                            ${this.videoUrl ? `
                                <video id="mainVideo" preload="metadata" crossorigin="anonymous" style="width:100%; height:100%; background:#000">
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
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/></svg>
                                </button>
                                <button class="overlay-btn" onclick="window.__playerView.navigateClass(1)" title="Siguiente">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M16 6h2v12h-2zm-10 6l8.5 6V6z" transform="scale(-1,1) translate(-24,0)"/></svg>
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
                                        <button class="yt-btn" onclick="window.__playerView.navigateClass(1)" title="Siguiente">
                                            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M16 6h2v12h-2zm-10 6l8.5 6V6z" transform="scale(-1,1) translate(-24,0)"/></svg>
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
                        </div>
                    </div>

                    <!-- Info bar below video -->
                    <div class="player-info-bar">
                        <div class="player-info">
                            <h2 id="videoTitle">${this.classData.name}</h2>
                            <p class="player-course-name">${this.courseData?.name || ''}</p>
                        </div>
                        <div class="player-actions">
                            ${this.videoUrl ? `
                            <button class="btn-action-pill" onclick="window.__playerView.openInExternalPlayer()">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h6v6"/><path d="M10 14L21 3"/><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/></svg>
                                Abrir Externo
                            </button>
                            ` : ''}
                            <a href="${backHash}" class="btn-action-pill">
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
                        <h3>📋 Temario</h3>
                        <p class="sidebar-subtitle">${this.courseData?.name || ''}</p>
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

        // Collapsible iframe sections for reading, summary, and html
        const readingFrame = readingUrl ? `
            <div class="resources-summary collapsed">
                <div class="rs-header" onclick="this.parentElement.classList.toggle('collapsed')">
                    <span>📚 Lecturas recomendadas</span>
                    <span class="rs-toggle">▼</span>
                </div>
                <div class="rs-content">
                    <iframe src="${readingUrl}" class="summary-frame"></iframe>
                </div>
            </div>
        ` : '';

        const summaryFrame = summaryUrl ? `
            <div class="resources-summary collapsed">
                <div class="rs-header" onclick="this.parentElement.classList.toggle('collapsed')">
                    <span>📄 Resumen de la clase</span>
                    <span class="rs-toggle">▼</span>
                </div>
                <div class="rs-content">
                    <iframe src="${summaryUrl}" class="summary-frame"></iframe>
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
                    <iframe src="${htmlUrl}" class="summary-frame"></iframe>
                </div>
            </div>
        ` : '';

        // Resource file list (download cards)
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

        return `
            <div class="player-resources-section">
                ${readingFrame}
                ${summaryFrame}
                ${htmlFrame}
                ${fileListHtml}
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
        if (!this.videoFileRef) return;

        try {
            const btn = document.querySelector('.btn-action-pill');
            const originalText = btn ? btn.innerHTML : '';
            if (btn) btn.innerHTML = '⏳ Abriendo...';

            const resp = await fetch('http://localhost:8080/api/open', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: this.videoFileRef })
            });

            if (!resp.ok) {
                const errText = await resp.text();
                throw new Error(errText || `HTTP ${resp.status}`);
            }

            // Restore button text after a moment
            setTimeout(() => {
                if (btn) btn.innerHTML = originalText;
            }, 2000);
        } catch (e) {
            console.error('Error opening external player:', e);
            // Fallback: open video URL in new tab
            if (this.videoUrl) {
                window.open(this.videoUrl, '_blank');
            }
        }
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
        const overlay = document.getElementById('videoOverlay');
        const controls = document.getElementById('ytControls');

        const speeds = [0.5, 0.75, 1, 1.25, 1.5, 2];
        let currentSpeedIdx = 2;

        // Format time
        const fmt = (s) => {
            const m = Math.floor(s / 60);
            const sec = Math.floor(s % 60);
            return `${m}:${sec < 10 ? '0' : ''}${sec}`;
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
                const end = video.buffered.end(video.buffered.length - 1);
                bufferedBar.style.width = (end / video.duration) * 100 + '%';
            }
        });

        // Seek on progress click - with audio sync fix
        const seekToPosition = (e) => {
            const rect = progressBar.getBoundingClientRect();
            const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
            const wasPlaying = !video.paused;
            if (wasPlaying) video.pause();
            video.currentTime = pct * video.duration;
            // Resume after seek completes to prevent audio desync
            if (wasPlaying) {
                video.addEventListener('seeked', () => video.play(), { once: true });
            }
        };
        let isSeeking = false;
        progressBar.addEventListener('mousedown', (e) => {
            isSeeking = true;
            seekToPosition(e);
        });
        document.addEventListener('mousemove', (e) => {
            if (isSeeking) {
                // During drag, just update visual, don't seek continuously
                const rect = progressBar.getBoundingClientRect();
                const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
                playedBar.style.width = pct * 100 + '%';
                thumb.style.left = pct * 100 + '%';
                timeDisplay.textContent = `${fmt(pct * video.duration)} / ${fmt(video.duration)}`;
            }
        });
        document.addEventListener('mouseup', (e) => {
            if (isSeeking) {
                isSeeking = false;
                seekToPosition(e);
            }
        });

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
        const video = document.getElementById('mainVideo');
        if (video) {
            // Fix audio/video sync: wait for metadata then play
            const startPlayback = () => {
                video.play().catch(() => { });
            };
            if (video.readyState >= 1) {
                startPlayback();
            } else {
                video.addEventListener('loadedmetadata', startPlayback, { once: true });
            }

            video.addEventListener('play', () => {
                state.markClassInProgress(this.classKey, video.currentTime);
            });
            video.addEventListener('ended', () => {
                state.markClassComplete(this.classKey);
                const sidebar = document.querySelector('.sidebar-content');
                if (sidebar) sidebar.innerHTML = this.renderSidebar();
                setTimeout(() => this.navigateClass(1), 1500);
            });

            this._setupCustomControls();
        }

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
                const wasPlaying = !video.paused;
                if (wasPlaying) video.pause();
                video.currentTime = Math.max(0, video.currentTime - 5);
                if (wasPlaying) video.addEventListener('seeked', () => video.play(), { once: true });
            }
            if (e.key === 'ArrowRight' && !e.altKey && video) {
                e.preventDefault();
                const wasPlaying = !video.paused;
                if (wasPlaying) video.pause();
                video.currentTime = Math.min(video.duration, video.currentTime + 5);
                if (wasPlaying) video.addEventListener('seeked', () => video.play(), { once: true });
            }
        };
        document.addEventListener('keydown', this._keyHandler);
    }

    destroy() {
        if (this._keyHandler) document.removeEventListener('keydown', this._keyHandler);
        if (this._fsChangeHandler) {
            document.removeEventListener('fullscreenchange', this._fsChangeHandler);
            document.removeEventListener('webkitfullscreenchange', this._fsChangeHandler);
        }
        window.__playerView = null;
    }
}
