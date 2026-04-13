import { state } from '../services/state.js';
import { Card } from '../components/card.js';
import { bindHashNavigation } from '../utils/view-helpers.js';

export default class ExploreView {
    constructor() {
        this.data = state.getData();
        this.query = '';
        this.activeCategory = null;
    }

    async render() {
        if (!this.data) return '<div class="loading">Cargando...</div>';
        const categories = this.data.categories || [];
        const stats = this.data.stats || {};

        return `
            <div class="view-explore fade-in">
                <section class="explore-hero">
                    <h1>Explorar Cursos</h1>
                    <p>Busca entre ${stats.totalCourses || 0} cursos y ${stats.totalRoutes || 0} rutas de aprendizaje</p>
                    <div class="search-box">
                        <span class="search-icon">🔍</span>
                        <input type="text" id="explore-search" class="search-input"
                               placeholder="Buscar cursos, rutas o temas..."
                               autocomplete="off" />
                    </div>
                </section>

                <section class="explore-filters">
                    <button class="filter-chip active" data-cat="all">Todas</button>
                    ${categories.map(cat => `
                        <button class="filter-chip" data-cat="${cat.name}">${cat.icon} ${cat.name}</button>
                    `).join('')}
                </section>

                <div class="explore-stats" id="explore-stats">
                    <span>${stats.totalRoutes || 0} rutas disponibles</span>
                </div>

                <div class="explore-results" id="explore-results">
                    ${this.renderAllRoutes()}
                </div>
            </div>
        `;
    }

    renderAllRoutes() {
        const categories = this.data.categories || [];
        const cards = [];
        categories.forEach((cat, catIdx) => {
            (cat.routes || []).forEach((route, routeIdx) => {
                cards.push(Card.renderRoute(route, catIdx, routeIdx));
            });
        });
        return `<div class="grid-routes">${cards.join('')}</div>`;
    }

    renderResults(results) {
        if (results.length === 0) {
            return `
                <div class="empty-state">
                    <div class="empty-icon">🔍</div>
                    <h3>Sin resultados</h3>
                    <p>Intenta con otros términos de búsqueda</p>
                </div>
            `;
        }
        const cards = results.map(r => {
            if (r.type === 'route' || r.item.isCourse !== undefined) {
                return Card.renderRoute(r.item, r.catIdx, r.routeIdx);
            }
            return Card.renderCourse(r.item, r.catIdx, r.routeIdx, r.courseIdx);
        }).join('');
        return `<div class="grid-routes">${cards}</div>`;
    }

    mounted() {
        const input = document.getElementById('explore-search');
        const results = document.getElementById('explore-results');
        const statsEl = document.getElementById('explore-stats');
        const filterChips = document.querySelectorAll('.filter-chip');

        let debounce = null;

        if (input) {
            input.focus();
            input.addEventListener('input', () => {
                clearTimeout(debounce);
                debounce = setTimeout(() => {
                    this.query = input.value;
                    this.updateResults(results, statsEl);
                }, 200);
            });
        }

        if (results) bindHashNavigation(results);

        filterChips.forEach(chip => {
            chip.addEventListener('click', () => {
                filterChips.forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                this.activeCategory = chip.dataset.cat === 'all' ? null : chip.dataset.cat;
                this.updateResults(results, statsEl);
            });
        });
    }

    updateResults(resultsEl, statsEl) {
        let items;
        const q = this.query.trim();

        if (q && this.activeCategory) {
            // Both search + category filter
            items = state.search(q).filter(r => r.categoryName === this.activeCategory);
        } else if (q) {
            items = state.search(q);
        } else if (this.activeCategory) {
            items = state.filterByCategory(this.activeCategory);
        } else {
            // Show all
            resultsEl.innerHTML = this.renderAllRoutes();
            const total = this.data.stats?.totalRoutes || 0;
            statsEl.innerHTML = `<span>${total} rutas disponibles</span>`;
            bindHashNavigation(resultsEl);
            return;
        }

        resultsEl.innerHTML = this.renderResults(items);
        const label = items.length === 1 ? 'resultado' : 'resultados';
        statsEl.innerHTML = `<span>${items.length} ${label} encontrados</span>`;
        bindHashNavigation(resultsEl);
    }
}
