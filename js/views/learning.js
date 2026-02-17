import { state } from '../services/state.js';

export default class LearningView {
    constructor() {
        this.data = state.getData();
    }

    async render() {
        if (!this.data) return '<div class="loading">Cargando...</div>';

        const overall = state.getOverallProgress();
        const inProgress = state.getInProgressRoutes();
        // Separate completed vs still-in-progress
        const completed = inProgress.filter(r => r.total > 0 && r.completed === r.total);
        const active = inProgress.filter(r => r.total > 0 && r.completed < r.total);

        return `
            <div class="view-learning fade-in">
                <!-- Stats Overview -->
                <section class="learning-hero">
                    <h1>Mi Aprendizaje</h1>
                    <p>Tu progreso de aprendizaje personal</p>
                </section>

                <section class="stats-grid">
                    ${this.renderStatCard('📚', 'Clases Completadas', `${overall.completedClasses}`, `de ${overall.totalClasses}`)}
                    ${this.renderStatCard('🛤️', 'Rutas Iniciadas', `${overall.startedRoutes}`, `de ${overall.totalRoutes}`)}
                    ${this.renderStatCard('🏆', 'Rutas Completadas', `${overall.completedRoutes}`, overall.completedRoutes > 0 ? '¡Sigue así!' : 'Aún ninguna')}
                    ${this.renderStatCard('📊', 'Progreso Global', `${Math.round(overall.percent * 100)}%`, this.getMotivation(overall.percent))}
                </section>

                <!-- Global Progress Bar -->
                <section class="global-progress-section">
                    <div class="global-bar-track">
                        <div class="global-bar-fill" style="width: ${overall.percent * 100}%"></div>
                    </div>
                    <p class="global-bar-label">${overall.completedClasses} de ${overall.totalClasses} clases completadas</p>
                </section>

                <!-- Active Routes (in progress, not completed) -->
                ${active.length > 0 ? `
                    <section class="learning-section">
                        <div class="learning-section-header">
                            <h2>🚀 En Progreso</h2>
                            <span class="section-count">${active.length} rutas</span>
                        </div>
                        <div class="progress-list">
                            ${active.sort((a, b) => b.percent - a.percent).map(r => this.renderProgressCard(r)).join('')}
                        </div>
                    </section>
                ` : ''}

                <!-- Completed Routes -->
                ${completed.length > 0 ? `
                    <section class="learning-section">
                        <div class="learning-section-header">
                            <h2>✅ Completadas</h2>
                            <span class="section-count">${completed.length} rutas</span>
                        </div>
                        <div class="progress-list">
                            ${completed.map(r => this.renderProgressCard(r, true)).join('')}
                        </div>
                    </section>
                ` : ''}

                <!-- Empty state if no progress -->
                ${inProgress.length === 0 ? `
                    <section class="empty-learning">
                        <div class="empty-icon">🎯</div>
                        <h3>¡Comienza tu aprendizaje!</h3>
                        <p>Aún no has marcado ninguna clase como completada. Entra a una ruta y empieza a aprender.</p>
                        <a href="#home" class="btn-primary">Explorar Cursos</a>
                    </section>
                ` : ''}
            </div>
        `;
    }

    renderStatCard(icon, label, value, subtitle) {
        return `
            <div class="stat-card">
                <div class="stat-icon">${icon}</div>
                <div class="stat-value">${value}</div>
                <div class="stat-label">${label}</div>
                <div class="stat-subtitle">${subtitle}</div>
            </div>
        `;
    }

    renderProgressCard(r, isComplete = false) {
        const pct = Math.round(r.percent * 100);
        const href = `#route/${r.catIdx}/${r.routeIdx}`;
        return `
            <div class="progress-card ${isComplete ? 'complete' : ''}" onclick="window.location.hash='${href}'">
                <div class="progress-card-left">
                    <div class="progress-card-icon">${r.route.icon || '🚀'}</div>
                    <div class="progress-card-info">
                        <h4>${r.route.name}</h4>
                        <p class="progress-card-meta">
                            <span class="meta-tag">${r.categoryIcon} ${r.categoryName}</span>
                            <span>${r.completed} / ${r.total} clases</span>
                        </p>
                    </div>
                </div>
                <div class="progress-card-right">
                    <div class="progress-ring">
                        <svg viewBox="0 0 36 36">
                            <path class="ring-bg" d="M18 2.0845
                                a 15.9155 15.9155 0 0 1 0 31.831
                                a 15.9155 15.9155 0 0 1 0 -31.831" />
                            <path class="ring-fill ${isComplete ? 'ring-complete' : ''}" 
                                  stroke-dasharray="${pct}, 100"
                                  d="M18 2.0845
                                a 15.9155 15.9155 0 0 1 0 31.831
                                a 15.9155 15.9155 0 0 1 0 -31.831" />
                        </svg>
                        <span class="ring-text">${pct}%</span>
                    </div>
                </div>
            </div>
        `;
    }

    getMotivation(percent) {
        if (percent === 0) return '¡Empieza hoy!';
        if (percent < 0.1) return '¡Buen inicio!';
        if (percent < 0.3) return '¡Vas avanzando!';
        if (percent < 0.5) return '¡Gran progreso!';
        if (percent < 0.75) return '¡Más de la mitad!';
        if (percent < 1) return '¡Casi lo logras!';
        return '¡Completado! 🎉';
    }
}
