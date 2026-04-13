function isInteractiveDescendant(target) {
    return !!target
        && typeof target.closest === 'function'
        && !!target.closest('a, button, input, textarea, select, label');
}

function normalizeHash(href) {
    if (!href) return '';
    return href.startsWith('#') ? href : `#${href}`;
}

export function safeGetLocalStorage(key, fallback = '') {
    try {
        const value = localStorage.getItem(key);
        return typeof value === 'string' ? value : fallback;
    } catch (error) {
        return fallback;
    }
}

export function safeSetLocalStorage(key, value) {
    try {
        localStorage.setItem(key, value);
        return true;
    } catch (error) {
        return false;
    }
}

export function bindHashNavigation(root = document) {
    root.querySelectorAll('[data-href]').forEach((element) => {
        if (element.dataset.navBound === '1') return;
        const href = normalizeHash(element.dataset.href);
        if (!href) return;

        element.dataset.navBound = '1';
        if (!element.hasAttribute('role')) element.setAttribute('role', 'link');
        if (!element.hasAttribute('tabindex')) element.setAttribute('tabindex', '0');

        const navigate = () => {
            window.location.hash = href;
        };

        element.addEventListener('click', (event) => {
            if (event.defaultPrevented || isInteractiveDescendant(event.target)) return;
            navigate();
        });

        element.addEventListener('keydown', (event) => {
            if (event.key !== 'Enter' && event.key !== ' ') return;
            event.preventDefault();
            navigate();
        });
    });
}

export function bindAccordionToggles(root = document) {
    root.querySelectorAll('[data-toggle-target]').forEach((element) => {
        if (element.dataset.toggleBound === '1') return;

        const targetId = element.dataset.toggleTarget;
        if (!targetId) return;

        element.dataset.toggleBound = '1';
        if (!element.hasAttribute('role')) element.setAttribute('role', 'button');
        if (!element.hasAttribute('tabindex')) element.setAttribute('tabindex', '0');

        const toggle = () => {
            const target = document.getElementById(targetId);
            if (target) target.classList.toggle('active');
        };

        element.addEventListener('click', toggle);
        element.addEventListener('keydown', (event) => {
            if (event.key !== 'Enter' && event.key !== ' ') return;
            event.preventDefault();
            toggle();
        });
    });
}

export function bindStoredTextareas(root = document) {
    root.querySelectorAll('textarea[data-storage-key]').forEach((textarea) => {
        if (textarea.dataset.storageBound === '1') return;

        const key = textarea.dataset.storageKey;
        if (!key) return;

        textarea.dataset.storageBound = '1';
        textarea.addEventListener('input', () => {
            safeSetLocalStorage(key, textarea.value);
        });
    });
}
