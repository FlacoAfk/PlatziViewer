export class Router {
    constructor(routes) {
        this.routes = routes;
        this.currentView = null;
        this.appContainer = document.getElementById('app');

        window.addEventListener('hashchange', () => this.handleRoute());
    }

    _stopAllMediaPlayback() {
        const mediaElements = document.querySelectorAll('video, audio');
        mediaElements.forEach((mediaEl) => {
            try {
                mediaEl.pause();
            } catch (error) {
                // no-op
            }

            try {
                if (mediaEl.srcObject) mediaEl.srcObject = null;
                mediaEl.removeAttribute('src');
                const sourceTags = mediaEl.querySelectorAll('source');
                sourceTags.forEach((source) => source.removeAttribute('src'));
                mediaEl.load();
            } catch (error) {
                // no-op
            }
        });
    }

    async handleRoute() {
        const hash = window.location.hash || '#home';

        let route = null;
        let params = {};

        for (const [path, viewClass] of Object.entries(this.routes)) {
            // Convert route pattern to regex
            // #course/:catIdx/:routeIdx/:courseIdx -> ^#course/([^/]+)/([^/]+)/([^/]+)$
            const regexPath = '^' + path.replace(/:[^\s/]+/g, '([^/]+)') + '$';
            const regex = new RegExp(regexPath);
            const found = hash.match(regex);

            if (found) {
                route = viewClass;
                // Extract param names and values
                const paramNames = (path.match(/:[^\s/]+/g) || []).map(n => n.slice(1));
                paramNames.forEach((name, index) => {
                    params[name] = decodeURIComponent(found[index + 1]);
                });
                break;
            }
        }

        if (!route) {
            // Default to home
            if (hash !== '#home') {
                window.location.hash = '#home';
            } else {
                // Render home directly
                const HomeView = this.routes['#home'];
                if (HomeView) this.renderView(HomeView, {});
            }
            return;
        }

        this.renderView(route, params);
    }

    async renderView(ViewClass, params) {
        this._stopAllMediaPlayback();

        if (this.currentView && this.currentView.destroy) {
            this.currentView.destroy();
        }

        // Show loading
        this.appContainer.innerHTML = `
            <div class="loading" style="min-height: 50vh">
                <div class="loading-spinner"></div>
            </div>
        `;

        try {
            this.currentView = new ViewClass(params);
            const html = await this.currentView.render();
            this.appContainer.innerHTML = html;

            if (this.currentView.mounted) {
                this.currentView.mounted();
            }
        } catch (error) {
            console.error('Error rendering view:', error);
            this.appContainer.innerHTML = `
                <div class="loading" style="min-height: 50vh">
                    <div style="font-size: 2rem; margin-bottom: 1rem">⚠️</div>
                    <p style="color: var(--text-secondary)">Error al cargar la vista</p>
                    <a href="#home" style="color: var(--accent-primary); margin-top: 1rem; display: inline-block">← Volver al inicio</a>
                </div>
            `;
        }

        // Scroll to top
        window.scrollTo(0, 0);
    }
}
