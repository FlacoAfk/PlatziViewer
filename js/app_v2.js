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
        app.innerHTML = `
            <div class="loading">
                <div style="font-size: 3rem; margin-bottom: 1rem">⚠️</div>
                <p style="color: var(--text-secondary)">Error al conectar con el servidor</p>
                <p style="color: var(--text-muted); margin-top: 0.5rem; font-size: 0.85rem">
                    Ejecuta: <code style="background: var(--bg-card); padding: 4px 8px; border-radius: 4px">python server.py</code>
                </p>
            </div>
        `;
        return;
    }

    // Build layout shell
    app.innerHTML = `
        ${Navbar.render()}
        <div id="main-content"></div>
    `;

    // Start Router
    const router = new Router(routes);
    router.appContainer = document.getElementById('main-content');
    router.handleRoute();

    // Set initial active nav link
    Navbar.updateActive();
    Navbar.init();
});
