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
                
                <button class="hamburger-btn" aria-label="Menu">
                    <span></span>
                    <span></span>
                    <span></span>
                </button>

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

    static init() {
        setTimeout(() => {
            const hamburger = document.querySelector('.hamburger-btn');
            const navLinks = document.querySelector('.nav-links');
            const links = document.querySelectorAll('.nav-link');

            if (hamburger && navLinks) {
                hamburger.addEventListener('click', () => {
                    hamburger.classList.toggle('active');
                    navLinks.classList.toggle('active');
                    document.body.classList.toggle('no-scroll'); // Prevent background scrolling
                });

                // Close menu when a link is clicked
                links.forEach(link => {
                    link.addEventListener('click', () => {
                        hamburger.classList.remove('active');
                        navLinks.classList.remove('active');
                        document.body.classList.remove('no-scroll');
                    });
                });
            }
        }, 0);
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
