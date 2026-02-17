import { state } from '../services/state.js';

export default class CourseView {
    constructor(params) {
        this.catIdx = parseInt(params.catIdx);
        this.routeIdx = parseInt(params.routeIdx);
        this.courseIdx = parseInt(params.courseIdx);
        this.courseData = state.getCourse(this.catIdx, this.routeIdx, this.courseIdx);
        this.routeData = state.getRoute(this.catIdx, this.routeIdx);
    }

    async render() {
        if (!this.courseData) return '<div class="error-state"><h2>⚠️ Curso no encontrado</h2><a href="#home">← Volver al inicio</a></div>';

        const modules = this.courseData.modules || [];
        const totalClasses = modules.reduce((sum, m) => {
            const classes = state.getModuleClasses(m);
            return sum + (classes.length || (typeof m.classes === 'number' ? m.classes : 0));
        }, 0);

        const firstPlayable = this.getFirstPlayableClass();

        // Progress calculation
        const completedClasses = state.countCourseCompleted(this.catIdx, this.routeIdx, this.courseIdx);
        const totalAll = state.countCourseClasses(this.courseData);
        const progressPct = totalAll > 0 ? Math.round((completedClasses / totalAll) * 100) : 0;
        const circumference = 2 * Math.PI * 52;
        const dashArray = (progressPct / 100) * circumference;

        // Notes key
        const notesKey = `platzi_notes_${this.catIdx}_${this.routeIdx}_${this.courseIdx}`;
        const savedNotes = localStorage.getItem(notesKey) || '';

        return `
            <div class="view-course fade-in">
                <nav class="breadcrumb">
                    <a href="#home" class="breadcrumb-link">🏠 Inicio</a>
                    <span class="breadcrumb-sep">›</span>
                    <a href="#route/${this.catIdx}/${this.routeIdx}" class="breadcrumb-link">${this.routeData?.name || 'Ruta'}</a>
                    <span class="breadcrumb-sep">›</span>
                    <span class="breadcrumb-current">${this.courseData.name}</span>
                </nav>

                <div class="course-layout">
                    <!-- ═══ Left Column: Main Content ═══ -->
                    <div class="course-main">
                        <header class="course-hero">
                            <div class="hero-content" style="text-align:left;">
                                ${this.routeData && !this.routeData.isCourse ? `<span class="badge-route">📂 ${this.routeData.name}</span>` : ''}
                                <h1>${this.courseData.name}</h1>
                                <p class="course-desc">${modules.length} módulos • ${totalClasses} clases</p>
                                ${firstPlayable ? `
                                    <a href="${firstPlayable}" class="btn-primary">▶ Continuar Curso</a>
                                ` : ''}
                            </div>
                        </header>

                        <section class="syllabus-section">
                            <h2>📖 Temario del Curso</h2>
                            <div class="accordion-list">
                                ${this.renderModules(modules)}
                            </div>
                        </section>
                    </div>

                    <!-- ═══ Right Column: Sidebar ═══ -->
                    <aside class="course-sidebar">
                        <!-- Progress Ring -->
                        <div class="sidebar-panel panel-progress">
                            <h3 class="panel-title">📊 Progreso del Curso</h3>
                            <div class="progress-ring-lg">
                                <svg viewBox="0 0 120 120">
                                    <circle class="ring-bg-lg" cx="60" cy="60" r="52"></circle>
                                    <circle class="ring-fill-lg ${progressPct === 100 ? 'ring-complete' : ''}"
                                        cx="60" cy="60" r="52"
                                        stroke-dasharray="${dashArray} ${circumference}"
                                        stroke-dashoffset="0">
                                    </circle>
                                </svg>
                                <div class="ring-text-lg">
                                    <span class="ring-pct">${progressPct}%</span>
                                </div>
                            </div>
                            <div class="progress-stats">
                                <span class="progress-stat-item">
                                    <span class="stat-dot complete"></span>
                                    ${completedClasses} completadas
                                </span>
                                <span class="progress-stat-item">
                                    <span class="stat-dot remaining"></span>
                                    ${totalAll - completedClasses} restantes
                                </span>
                            </div>
                        </div>

                        <!-- Module Resources -->
                        <div class="sidebar-panel panel-resources">
                            <h3 class="panel-title">🔗 Recursos del Módulo</h3>
                            <div class="resource-list">
                                <a href="https://developer.mozilla.org/es/docs/Web/HTTP" target="_blank" rel="noopener" class="resource-link">
                                    <span class="resource-icon">🌐</span>
                                    <span class="resource-text">MDN — HTTP Docs</span>
                                    <span class="resource-arrow">↗</span>
                                </a>
                                <a href="https://www.postman.com/downloads/" target="_blank" rel="noopener" class="resource-link">
                                    <span class="resource-icon">🚀</span>
                                    <span class="resource-text">Descargar Postman</span>
                                    <span class="resource-arrow">↗</span>
                                </a>
                                <a href="https://restfulapi.net/" target="_blank" rel="noopener" class="resource-link">
                                    <span class="resource-icon">📡</span>
                                    <span class="resource-text">REST API Tutorial</span>
                                    <span class="resource-arrow">↗</span>
                                </a>
                                <a href="https://nodejs.org/es/docs" target="_blank" rel="noopener" class="resource-link">
                                    <span class="resource-icon">💚</span>
                                    <span class="resource-text">Node.js Docs</span>
                                    <span class="resource-arrow">↗</span>
                                </a>
                                <a href="https://devdocs.io/" target="_blank" rel="noopener" class="resource-link">
                                    <span class="resource-icon">📚</span>
                                    <span class="resource-text">DevDocs.io</span>
                                    <span class="resource-arrow">↗</span>
                                </a>
                            </div>
                        </div>

                        <!-- Personal Notes -->
                        <div class="sidebar-panel panel-notes">
                            <h3 class="panel-title">📝 Notas & Snippets</h3>
                            <textarea
                                class="notes-textarea"
                                id="course-notes"
                                placeholder="Escribe tus notas, snippets de código, o ideas aquí..."
                                oninput="localStorage.setItem('${notesKey}', this.value)"
                            >${savedNotes}</textarea>
                            <div class="notes-footer">
                                <span class="notes-hint">💾 Guardado automático en tu navegador</span>
                            </div>
                        </div>
                    </aside>
                </div>
            </div>
        `;
    }

    renderModules(modules) {
        return modules.map((mod, modIdx) => {
            const classes = state.getModuleClasses(mod);
            const classCount = classes.length || (typeof mod.classes === 'number' ? mod.classes : 0);
            const completedCount = classes.filter((_, i) => {
                const key = state.getClassKey(this.catIdx, this.routeIdx, this.courseIdx, modIdx, i);
                return state.isClassComplete(key);
            }).length;
            const pct = classCount > 0 ? Math.round((completedCount / classCount) * 100) : 0;

            return `
                <div class="module-item" id="cmod-${modIdx}">
                    <div class="module-header" onclick="document.getElementById('cmod-${modIdx}').classList.toggle('active')">
                        <div class="module-header-left">
                            <span class="module-num">${pct === 100 ? '✅' : modIdx + 1}</span>
                            <h3>${mod.name}</h3>
                        </div>
                        <div class="module-header-right">
                            <span class="class-count">${completedCount}/${classCount}</span>
                            <div class="progress-bar-mini">
                                <div class="progress-fill" style="width: ${pct}%"></div>
                            </div>
                            <span class="toggle-icon">▼</span>
                        </div>
                    </div>
                    <div class="module-body">
                        ${classes.length > 0 ? classes.map((cls, classIdx) => {
                const classKey = state.getClassKey(this.catIdx, this.routeIdx, this.courseIdx, modIdx, classIdx);
                const status = state.getClassStatus(classKey);
                const hasVideo = cls.hasVideo && cls.files?.video;
                const typeLabel = cls.hasVideo ? 'Video' : cls.hasHtml ? 'Lectura' : 'Texto';
                const typeClass = cls.hasVideo ? 'type-video' : cls.hasHtml ? 'type-html' : 'type-text';

                return `
                                <div class="class-card ${status} ${hasVideo ? 'clickable' : ''}" onclick="${hasVideo ? `window.location.hash='#player/${this.catIdx}/${this.routeIdx}/${this.courseIdx}/${modIdx}/${classIdx}'` : ''}">
                                    <div class="class-card-left">
                                        <span class="class-num ${status}">${status === 'complete' ? '✓' : classIdx + 1}</span>
                                        <div class="class-info">
                                            <span class="class-name">${cls.name}</span>
                                            <div class="class-meta-row">
                                                <span class="class-type-tag ${typeClass}">${typeLabel}</span>
                                                ${cls.hasSummary ? '<span class="class-material-badge">📄 Resumen</span>' : ''}
                                                ${cls.hasReading ? '<span class="class-material-badge">📚 Lectura</span>' : ''}
                                            </div>
                                        </div>
                                    </div>
                                    ${hasVideo ? '<span class="class-play-icon">▶</span>' : ''}
                                </div>
                            `;
            }).join('') : `<p class="no-classes">Detalles no disponibles (${classCount} clases estimadas)</p>`}
                    </div>
                </div>
            `;
        }).join('');
    }

    getFirstPlayableClass() {
        const modules = this.courseData.modules || [];
        for (let modIdx = 0; modIdx < modules.length; modIdx++) {
            const classes = state.getModuleClasses(modules[modIdx]);
            for (let classIdx = 0; classIdx < classes.length; classIdx++) {
                const cls = classes[classIdx];
                if (cls.hasVideo && cls.files?.video) {
                    return `#player/${this.catIdx}/${this.routeIdx}/${this.courseIdx}/${modIdx}/${classIdx}`;
                }
            }
        }
        return null;
    }
}
