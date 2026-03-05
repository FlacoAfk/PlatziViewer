import { Router } from './router.js';
import { state } from './services/state.js';
import { Navbar } from './components/navbar.js';
import HomeView from './views/home.js';
import ExploreView from './views/explore.js';
import LearningView from './views/learning.js';
import RouteView from './views/route.js';
import CourseView from './views/course.js';
import PlayerView from './views/player.js';

const routes = {
    '#home': HomeView,
    '#explore': ExploreView,
    '#learning': LearningView,
    '#route/:catIdx/:routeIdx': RouteView,
    '#course/:catIdx/:routeIdx/:courseIdx': CourseView,
    '#player/:catIdx/:routeIdx/:courseIdx/:modIdx/:classIdx': PlayerView,
};

function inferEndpointFromErrorCode(code) {
    const normalized = String(code || '').toLowerCase();
    if (normalized.startsWith('bootstrap')) return '/api/bootstrap';
    if (normalized.startsWith('courses')) return '/api/courses';
    if (normalized.startsWith('progress')) return '/api/progress';
    if (normalized.startsWith('course_detail')) return '/api/course-detail/...';
    return 'desconocido';
}

// Initialize App
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 Initializing Platzi Viewer 2.0...');
    const app = document.getElementById('app');

    // Show loading while data loads
    app.innerHTML = `
        <div class="loading">
            <div class="loading-spinner"></div>
            <p style="margin-top: 1rem; color: var(--text-muted)">Cargando plataforma...</p>
        </div>
    `;

    try {
        await state.init();
    } catch (error) {
        window.__platziBootDone = true;
        const code = error?.code || 'bootstrap_unavailable';
        const endpoint = inferEndpointFromErrorCode(code);
        app.innerHTML = `
            <div class="loading">
                <div style="font-size: 3rem; margin-bottom: 1rem">⚠️</div>
                <p style="color: var(--text-secondary)">Error al conectar con el servidor</p>
                <p style="color: var(--text-muted); margin-top: 0.5rem; font-size: 0.85rem">
                    Código: <code style="background: var(--bg-card); padding: 4px 8px; border-radius: 4px">${code}</code>
                    • Endpoint: <code style="background: var(--bg-card); padding: 4px 8px; border-radius: 4px">${endpoint}</code>
                </p>
                <p style="color: var(--text-muted); margin-top: 0.5rem; font-size: 0.85rem">
                    Verifica diagnóstico rápido en: <code style="background: var(--bg-card); padding: 4px 8px; border-radius: 4px">/api/cache-meta</code>
                </p>
            </div>
        `;
        return;
    }

    const warnings = state.getInitWarnings();
    const warningBanner = warnings.length > 0
        ? `
        <div style="margin: 12px 16px 0; padding: 10px 12px; border: 1px solid rgba(255,196,0,.25); background: rgba(255,196,0,.08); color: #ffd36a; border-radius: 10px; font-size: .9rem;">
            ⚠️ ${warnings[0].message || 'Se detectó una advertencia no bloqueante'} 
            <span style="opacity:.9">(${warnings[0].code || 'warning'} • ${warnings[0].endpoint || 'n/a'})</span>
        </div>
        `
        : '';

    // Build layout shell
    app.innerHTML = `
        ${Navbar.render()}
        ${warningBanner}
        <div id="main-content"></div>
    `;
    state.clearInitWarnings();

    // Start Router
    const router = new Router(routes);
    router.appContainer = document.getElementById('main-content');
    router.handleRoute();
    window.__platziBootDone = true;

    // Set initial active nav link
    Navbar.updateActive();
    Navbar.init();
});
