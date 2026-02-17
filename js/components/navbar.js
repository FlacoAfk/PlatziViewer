export class Navbar {
    static render() {
        // Listen for hash changes to update active state
        window.addEventListener('hashchange', () => Navbar.updateActive());

        return `
            <nav class="navbar">
                <a href="#home" class="logo">
                    <span class="logo-icon">💚</span>
                    <span class="logo-text">PlatziViewer</span>
                </a>
                <div class="nav-links">
                    <a href="#home" class="nav-link" data-nav="home">Inicio</a>
                    <a href="#explore" class="nav-link" data-nav="explore">Explorar</a>
                    <a href="#learning" class="nav-link" data-nav="learning">Mi Aprendizaje</a>
                </div>
                <div class="user-profile">
                    <div class="avatar-circle">US</div>
                </div>
            </nav>
        `;
    }

    static updateActive() {
        const hash = window.location.hash || '#home';
        document.querySelectorAll('.nav-link[data-nav]').forEach(link => {
            const target = link.getAttribute('data-nav');
            // Match: #home for "home", #explore for "explore", etc.
            // But don't match #home for #route, #course, #player
            const isActive = hash === `#${target}` ||
                (target === 'home' && (hash === '' || hash === '#' || hash === '#home'));
            link.classList.toggle('active', isActive);
        });
    }
}
