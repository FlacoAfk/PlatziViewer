import { state } from '../services/state.js';
import { Card } from '../components/card.js';

export default class RouteView {
    constructor(params) {
        this.catIdx = parseInt(params.catIdx);
        this.routeIdx = parseInt(params.routeIdx);
        this.routeData = state.getRoute(this.catIdx, this.routeIdx);
        this.category = state.getCategory(this.catIdx);
        this.detailErrorCode = null;
    }

    async render() {
        this.routeData = state.getRoute(this.catIdx, this.routeIdx);
        if (!this.routeData) return '<div class="error-state"><h2>⚠️ Ruta no encontrada</h2><a href="#home">← Volver al inicio</a></div>';

        // If this "route" is actually a single course, render as course view
        if (this.routeData.isCourse) {
            try {
                this.routeData = await state.ensureCourseDetail(this.catIdx, this.routeIdx, 0) || this.routeData;
            } catch (error) {
                this.detailErrorCode = error?.code || 'course_detail_unavailable';
                this.routeData = state.getRoute(this.catIdx, this.routeIdx) || this.routeData;
            }
            return this.renderAsCourse();
        }

        return this.renderAsRoute();
    }

    renderAsRoute() {
        const courses = this.routeData.courses || [];
        const totalModules = courses.reduce((sum, c) => sum + (c.moduleCount || (c.modules?.length || 0)), 0);

        return `
            <div class="view-route fade-in">
                <header class="route-header">
                    <nav class="breadcrumb">
                        <a href="#home" class="breadcrumb-link">🏠 Inicio</a>
                        <span class="breadcrumb-sep">›</span>
                        <span class="breadcrumb-current">${this.routeData.name}</span>
                    </nav>
                    <h1>${this.routeData.name}</h1>
                    <div class="route-meta">
                        <span class="meta-chip">📚 ${courses.length} Cursos</span>
                        <span class="meta-chip">📁 ${totalModules} Módulos</span>
                    </div>
                </header>

                <div class="route-timeline">
                    ${courses.map((course, courseIdx) => {
            const driveNum = this.extractDriveNum(course.folderName || course.name);
            const markerText = driveNum || (courseIdx + 1);
            return `
                        <div class="timeline-item fade-in" style="animation-delay: ${courseIdx * 0.05}s">
                            <div class="timeline-marker">${markerText}</div>
                            <div class="timeline-content">
                                ${Card.renderCourse(course, this.catIdx, this.routeIdx, courseIdx)}
                            </div>
                        </div>
                    `;
        }).join('')}
                    ${courses.length === 0 ? '<p style="color: var(--text-muted); text-align: center; padding: 2rem">No hay cursos registrados en esta ruta</p>' : ''}
                </div>
            </div>
        `;
    }

    renderAsCourse() {
        // Redirect to course view for direct courses
        const modules = this.routeData.modules || [];

        return `
            <div class="view-course fade-in">
                ${this.detailErrorCode ? `
                    <div style="margin-bottom: 1rem; padding: 10px 12px; border: 1px solid rgba(255,196,0,.22); background: rgba(255,196,0,.07); color: #ffd36a; border-radius: 10px; font-size: .9rem;">
                        ⚠️ No se pudo cargar el detalle completo del curso (<code style="background: rgba(0,0,0,.25); padding: 2px 6px; border-radius: 6px;">${this.detailErrorCode}</code>).
                    </div>
                ` : ''}
                <header class="course-hero">
                    <nav class="breadcrumb">
                        <a href="#home" class="breadcrumb-link">🏠 Inicio</a>
                        <span class="breadcrumb-sep">›</span>
                        <span class="breadcrumb-current">${this.routeData.name}</span>
                    </nav>
                    <div class="hero-content">
                        <span class="badge-type">Curso Independiente</span>
                        <h1>${this.routeData.name}</h1>
                        <p class="course-desc">${modules.length} módulos disponibles</p>
                    </div>
                </header>

                <section class="syllabus-section">
                    <h2>📖 Temario del Curso</h2>
                    <div class="accordion-list">
                        ${this.renderModules(modules)}
                    </div>
                </section>
            </div>
        `;
    }

    renderModules(modules) {
        return modules.map((mod, modIdx) => {
            const classes = state.getModuleClasses(mod);
            const classCount = classes.length || (typeof mod.classes === 'number' ? mod.classes : 0);

            return `
                <div class="module-item" id="mod-${modIdx}">
                    <div class="module-header" onclick="document.getElementById('mod-${modIdx}').classList.toggle('active')">
                        <div class="module-header-left">
                            <span class="module-num">${modIdx + 1}</span>
                            <h3>${mod.name}</h3>
                        </div>
                        <div class="module-header-right">
                            <span class="class-count">${classCount} clases</span>
                            <span class="toggle-icon">▼</span>
                        </div>
                    </div>
                    <div class="module-body">
                        ${classes.length > 0 ? classes.map((cls, classIdx) => {
                const classKey = state.getClassKey(this.catIdx, this.routeIdx, 0, modIdx, classIdx);
                const status = state.getClassStatus(classKey);
                const statusIcon = status === 'complete' ? '✅' : status === 'in_progress' ? '🕐' : '○';
                const hasVideo = cls.hasVideo && cls.files?.video;

                return `
                                <div class="class-row ${status}" onclick="${hasVideo ? `window.location.hash='#player/${this.catIdx}/${this.routeIdx}/0/${modIdx}/${classIdx}'` : ''}">
                                    <span class="status-icon">${statusIcon}</span>
                                    <span class="class-icon">${cls.hasVideo ? '📹' : cls.hasHtml ? '⚡' : '📝'}</span>
                                    <span class="class-name">${cls.name}</span>
                                    <div class="class-badges">
                                        ${cls.hasVideo ? '<span class="mini-badge" title="Video">📹</span>' : ''}
                                        ${cls.hasSummary ? '<span class="mini-badge" title="Resumen">📄</span>' : ''}
                                        ${cls.hasReading ? '<span class="mini-badge" title="Lectura">📚</span>' : ''}
                                    </div>
                                </div>
                            `;
            }).join('') : `<p class="no-classes">Detalles no disponibles (${classCount} clases estimadas)</p>`}
                    </div>
                </div>
            `;
        }).join('');
    }

    /** Extract numeric prefix from Drive folder name: "05. Curso..." → 5 */
    extractDriveNum(folderName) {
        if (!folderName) return null;
        const match = folderName.match(/^(\d+)\.\s/);
        return match ? parseInt(match[1], 10) : null;
    }
}
