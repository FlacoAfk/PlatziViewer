import { state } from '../services/state.js';
import { Card } from '../components/card.js';

export default class HomeView {
    constructor() {
        this.data = state.getData();
    }

    async render() {
        if (!this.data) return '<div class="loading">Cargando cursos...</div>';

        const stats = this.data.stats || {};

        return `
            <div class="view-home fade-in">
                <!-- Hero -->
                <section class="hero-section">
                    <h1>Nunca pares de aprender 🚀</h1>
                    <p>Explora ${stats.totalCourses || 0} cursos y ${stats.totalClasses || 0} clases disponibles.</p>
                </section>

                <!-- Categories -->
                <section class="categories-section">
                    <h2>Explorar por Categorías</h2>
                    <div class="categories-scroll">
                        ${this.renderCategories()}
                    </div>
                </section>

                <!-- All Categories with their routes -->
                ${this.renderAllCategories()}
            </div>
        `;
    }

    renderCategories() {
        return this.data.categories.map((cat, catIdx) => `
            <a href="#" class="category-pill" onclick="event.preventDefault(); document.getElementById('cat-section-${catIdx}').scrollIntoView({behavior:'smooth'})">
                ${cat.icon} ${cat.name}
            </a>
        `).join('');
    }

    renderAllCategories() {
        return this.data.categories.map((cat, catIdx) => {
            const allItems = cat.routes || [];
            const realRoutes = [];
            const standaloneCourses = [];

            allItems.forEach((item, routeIdx) => {
                if (item.isCourse) {
                    standaloneCourses.push({ item, routeIdx });
                } else {
                    realRoutes.push({ item, routeIdx });
                }
            });

            const routeCards = realRoutes.map(({ item, routeIdx }) =>
                Card.renderRoute(item, catIdx, routeIdx)
            ).join('');

            const courseCards = standaloneCourses.map(({ item, routeIdx }) =>
                Card.renderRoute(item, catIdx, routeIdx)
            ).join('');

            return `
                <section class="routes-section" id="cat-section-${catIdx}">
                    <div class="section-header">
                        <h2>${cat.icon} ${cat.name}</h2>
                        <p class="section-subtitle">${cat.description} • ${realRoutes.length} rutas • ${standaloneCourses.length > 0 ? standaloneCourses.length + ' cursos independientes' : (cat.courseCount || 0) + ' cursos'}</p>
                    </div>

                    ${realRoutes.length > 0 ? `
                        <div class="subsection-header">
                            <span class="subsection-icon">🛤️</span>
                            <span>Rutas de Aprendizaje</span>
                            <span class="subsection-count">${realRoutes.length}</span>
                        </div>
                        <div class="grid-routes">
                            ${routeCards}
                        </div>
                    ` : ''}

                    ${standaloneCourses.length > 0 ? `
                        <div class="subsection-header standalone-header">
                            <span class="subsection-icon">🎓</span>
                            <span>Cursos Independientes</span>
                            <span class="subsection-count">${standaloneCourses.length}</span>
                        </div>
                        <div class="grid-routes">
                            ${courseCards}
                        </div>
                    ` : ''}

                    ${allItems.length === 0 ? '<p style="color: var(--text-muted)">No hay contenido disponible</p>' : ''}
                </section>
            `;
        }).join('');
    }
}
