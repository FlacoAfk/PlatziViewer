// Platzi Courses Viewer - Main Application Logic
// Versión con servidor local - Carga dinámica desde API

const API_URL = 'http://localhost:8080';
let coursesData = null;

// ===== Progress Tracker =====
class ProgressTracker {
    constructor() {
        this.STORAGE_KEY = 'platzi_progress';
        this.progress = this.loadLocal();
        this.syncWithServer();
    }

    loadLocal() {
        try {
            const data = localStorage.getItem(this.STORAGE_KEY);
            return data ? JSON.parse(data) : {};
        } catch (e) {
            console.error('Error loading progress:', e);
            return {};
        }
    }

    async syncWithServer() {
        try {
            const response = await fetch(`${API_URL}/api/progress`);
            if (response.ok) {
                const serverData = await response.json();
                // Combinar datos del servidor con localStorage (servidor tiene prioridad)
                this.progress = { ...this.progress, ...serverData };
                this.saveLocal();
                console.log('✅ Progreso sincronizado con servidor');
            }
        } catch (e) {
            console.log('⚠️ No se pudo sincronizar con servidor, usando localStorage');
        }
    }

    saveLocal() {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.progress));
        } catch (e) {
            console.error('Error saving to localStorage:', e);
        }
    }

    async saveToServer() {
        try {
            await fetch(`${API_URL}/api/progress`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.progress)
            });
        } catch (e) {
            console.error('Error saving to server:', e);
        }
    }

    save() {
        this.saveLocal();
        this.saveToServer(); // Async, no bloqueante
    }

    // Generar clave única para una clase
    getClassKey(categoryId, routeId, courseFolder, moduleFolder, classNum) {
        return `${categoryId}|${routeId}|${courseFolder || 'direct'}|${moduleFolder}|${classNum}`;
    }

    // Marcar clase como vista
    markClassComplete(key) {
        this.progress[key] = {
            status: 'complete',
            completedAt: new Date().toISOString(),
            watchTime: this.progress[key]?.watchTime || 0
        };
        this.save();
    }

    // Marcar clase como en progreso
    markClassInProgress(key, watchTime = 0) {
        if (!this.progress[key] || this.progress[key].status !== 'complete') {
            this.progress[key] = {
                status: 'in_progress',
                lastWatched: new Date().toISOString(),
                watchTime: watchTime
            };
            this.save();
        }
    }

    // Actualizar tiempo de reproducción
    updateWatchTime(key, watchTime) {
        if (this.progress[key]) {
            this.progress[key].watchTime = watchTime;
            this.progress[key].lastWatched = new Date().toISOString();
            this.save();
        }
    }

    // Obtener estado de una clase
    getClassStatus(key) {
        return this.progress[key]?.status || 'not_started';
    }

    // Obtener progreso de un módulo
    getModuleProgress(categoryId, routeId, courseFolder, moduleFolder, totalClasses) {
        let completed = 0;
        let inProgress = 0;

        for (let i = 1; i <= totalClasses; i++) {
            const key = this.getClassKey(categoryId, routeId, courseFolder, moduleFolder, i);
            const status = this.getClassStatus(key);
            if (status === 'complete') completed++;
            else if (status === 'in_progress') inProgress++;
        }

        return { completed, inProgress, total: totalClasses, percentage: Math.round((completed / totalClasses) * 100) || 0 };
    }

    // Obtener progreso de un curso (todos sus módulos)
    getCourseProgress(categoryId, routeId, courseFolder, modules) {
        let totalClasses = 0;
        let completedClasses = 0;
        let inProgressClasses = 0;

        modules.forEach(mod => {
            const classes = mod.classes || [];
            const classCount = Array.isArray(classes) ? classes.length : (typeof classes === 'number' ? classes : 0);

            for (let i = 0; i < classCount; i++) {
                const classNum = Array.isArray(classes) ? classes[i]?.num || (i + 1) : (i + 1);
                const key = this.getClassKey(categoryId, routeId, courseFolder, mod.folderName, classNum);
                const status = this.getClassStatus(key);
                totalClasses++;
                if (status === 'complete') completedClasses++;
                else if (status === 'in_progress') inProgressClasses++;
            }
        });

        return {
            completed: completedClasses,
            inProgress: inProgressClasses,
            total: totalClasses,
            percentage: Math.round((completedClasses / totalClasses) * 100) || 0
        };
    }

    // Obtener progreso de una ruta
    getRouteProgress(categoryId, routeId, routeData) {
        let totalCourses = 0;
        let completedCourses = 0;
        let totalClasses = 0;
        let completedClasses = 0;

        if (routeData.isCourse) {
            // Es un curso directo
            const progress = this.getCourseProgress(categoryId, routeId, routeData.folderName, routeData.modules || []);
            return {
                totalCourses: 1,
                completedCourses: progress.percentage === 100 ? 1 : 0,
                totalClasses: progress.total,
                completedClasses: progress.completed,
                percentage: progress.percentage
            };
        }

        // Es una ruta con múltiples cursos
        (routeData.courses || []).forEach(course => {
            const progress = this.getCourseProgress(categoryId, routeId, course.folderName, course.modules || []);
            totalCourses++;
            totalClasses += progress.total;
            completedClasses += progress.completed;
            if (progress.percentage === 100) completedCourses++;
        });

        return {
            totalCourses,
            completedCourses,
            totalClasses,
            completedClasses,
            percentage: Math.round((completedClasses / totalClasses) * 100) || 0
        };
    }

    // Obtener progreso de una categoría
    getCategoryProgress(categoryId, categoryData) {
        let totalClasses = 0;
        let completedClasses = 0;

        (categoryData.routes || []).forEach(route => {
            const progress = this.getRouteProgress(categoryId, route.id, route);
            totalClasses += progress.totalClasses;
            completedClasses += progress.completedClasses;
        });

        return {
            total: totalClasses,
            completed: completedClasses,
            percentage: Math.round((completedClasses / totalClasses) * 100) || 0
        };
    }

    // Limpiar todo el progreso
    clearAll() {
        this.progress = {};
        this.save();
    }
}

// Instancia global del tracker
const progressTracker = new ProgressTracker();


class PlatziViewer {
    constructor() {
        this.currentView = 'categories';
        this.currentCategory = null;
        this.currentRoute = null;
        this.currentCourse = null;
        this.currentModule = null;
        this.currentModuleData = null;
        this.currentClassIndex = 0;
        this.currentFilter = 'all';
        this.searchQuery = '';

        this.init();
    }

    async init() {
        this.cacheElements();
        this.showLoading();

        try {
            await this.loadCoursesData();
            this.bindEvents();
            this.updateStats();
            this.renderCategories();
        } catch (error) {
            this.showError(error.message);
        }
    }

    async loadCoursesData(retries = 60) {
        for (let i = 0; i < retries; i++) {
            try {
                const response = await fetch(`${API_URL}/api/courses`);
                if (!response.ok) {
                    throw new Error('No se pudo conectar al servidor');
                }
                coursesData = await response.json();

                // Si hay datos, continuar
                if (coursesData && coursesData.categories && coursesData.categories.length > 0) {
                    console.log('Datos cargados:', coursesData.stats);
                    return;
                }

                // Si no hay datos, el servidor aún está escaneando
                console.log(`Esperando datos del servidor... (intento ${i + 1}/${retries})`);
                this.showLoadingMessage(`
                    <strong>Escaneando cursos en Google Drive...</strong><br>
                    <span style="font-size: 0.9em; opacity: 0.8;">
                    (Intento ${i + 1}/${retries})<br>
                    Esto puede tomar varios minutos la primera vez.<br>
                    Por favor espera, no cierres la ventana.
                    </span>
                `);
                await new Promise(resolve => setTimeout(resolve, 2000));

            } catch (error) {
                if (i === retries - 1) {
                    throw new Error(`Error al cargar datos: ${error.message}. ¿Está el servidor corriendo?`);
                }
                console.log(`Error, reintentando... (${i + 1}/${retries})`);
                await new Promise(resolve => setTimeout(resolve, 2000));
            }
        }
        throw new Error('No se pudieron cargar los datos después de varios intentos');
    }

    showLoadingMessage(message) {
        this.routesGrid.innerHTML = `
            <div class="loading">
                <div class="loading-spinner"></div>
                <p style="margin-top: 16px; color: var(--text-secondary);">${message}</p>
            </div>
        `;
    }


    showLoading() {
        this.routesGrid.innerHTML = `
            <div class="loading">
                <div class="loading-spinner"></div>
            </div>
        `;
    }

    showError(message) {
        this.routesGrid.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <p class="empty-state-text">${message}</p>
                <p style="color: var(--text-muted); margin-top: 12px; font-size: 13px;">
                    Ejecuta: <code style="background: var(--bg-card); padding: 4px 8px; border-radius: 4px;">python server.py</code>
                </p>
            </div>
        `;
    }

    cacheElements() {
        this.routesGrid = document.getElementById('routesGrid');
        this.coursePanel = document.getElementById('coursePanel');
        this.courseHeader = document.getElementById('courseHeader');
        this.modulesList = document.getElementById('modulesList');
        this.backBtn = document.getElementById('backBtn');
        this.searchInput = document.getElementById('searchInput');
        this.filterBtns = document.querySelectorAll('.filter-btn');
        this.totalCoursesEl = document.getElementById('totalCourses');
        this.totalClassesEl = document.getElementById('totalClasses');
        this.totalRoutesEl = document.getElementById('totalRoutes');

        // Modal elements
        this.playerModal = document.getElementById('playerModal');
        this.closeModalBtn = document.getElementById('closeModal');
        this.videoPlayer = document.getElementById('videoPlayer');
        this.videoSource = document.getElementById('videoSource');
        this.videoSubtitles = document.getElementById('videoSubtitles');
        this.classTitle = document.getElementById('classTitle');
        this.videoSection = document.getElementById('videoSection');
        this.htmlSection = document.getElementById('htmlSection');
        this.htmlClassTitle = document.getElementById('htmlClassTitle');
        this.htmlFrame = document.getElementById('htmlFrame');
        this.summarySection = document.getElementById('summarySection');
        this.summaryContent = document.getElementById('summaryContent');
        this.summaryFrame = document.getElementById('summaryFrame');
        this.toggleSummaryBtn = document.getElementById('toggleSummary');
        this.readingSection = document.getElementById('readingSection');
        this.readingContent = document.getElementById('readingContent');
        this.prevClassBtn = document.getElementById('prevClass');
        this.nextClassBtn = document.getElementById('nextClass');
        this.openExternalBtn = document.getElementById('openExternalBtn');

        // Video loading overlay elements
        this.videoLoadingOverlay = document.getElementById('videoLoadingOverlay');
        this.videoLoadingBar = document.getElementById('videoLoadingBar');
        this.videoLoadingPercent = document.getElementById('videoLoadingPercent');

        // Presentation modal
        this.presentationModal = document.getElementById('presentationModal');
        this.closePresentationBtn = document.getElementById('closePresentationModal');
        this.presentationFrame = document.getElementById('presentationFrame');
    }

    bindEvents() {
        this.backBtn.addEventListener('click', () => this.goBack());

        this.searchInput.addEventListener('input', (e) => {
            this.searchQuery = e.target.value.toLowerCase();
            this.applyFilters();
        });

        this.filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                this.filterBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentFilter = btn.dataset.filter;
                this.applyFilters();
            });
        });

        // Modal events
        this.closeModalBtn.addEventListener('click', () => this.closePlayerModal());
        this.playerModal.addEventListener('click', (e) => {
            if (e.target === this.playerModal) this.closePlayerModal();
        });

        // Summary toggle
        this.toggleSummaryBtn.addEventListener('click', () => this.toggleSummary());
        document.querySelector('.summary-header').addEventListener('click', () => this.toggleSummary());

        // Navigation buttons
        this.prevClassBtn.addEventListener('click', () => this.navigateClass(-1));
        this.nextClassBtn.addEventListener('click', () => this.navigateClass(1));

        if (this.openExternalBtn) {
            this.openExternalBtn.addEventListener('click', () => this.openInExternalPlayer());
        }

        // Presentation modal
        this.closePresentationBtn.addEventListener('click', () => this.closePresentationModal());
        this.presentationModal.addEventListener('click', (e) => {
            if (e.target === this.presentationModal) this.closePresentationModal();
        });

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (!this.playerModal.classList.contains('hidden')) {
                if (e.key === 'Escape') this.closePlayerModal();
                if (e.key === 'ArrowLeft') this.navigateClass(-1);
                if (e.key === 'ArrowRight') this.navigateClass(1);
            }
            if (!this.presentationModal.classList.contains('hidden')) {
                if (e.key === 'Escape') this.closePresentationModal();
            }
        });
    }

    updateStats() {
        if (coursesData && coursesData.stats) {
            this.totalRoutesEl.textContent = coursesData.stats.totalRoutes;
            this.totalCoursesEl.textContent = coursesData.stats.totalCourses;
            this.totalClassesEl.textContent = coursesData.stats.totalClasses;
        }
    }

    // ===== Build File URL =====
    buildFileUrl(fileId) {
        if (!fileId) return '';
        return `${API_URL}/drive/files/${fileId}`;
    }

    // ===== Render Categories =====
    renderCategories() {
        this.currentView = 'categories';
        this.currentCategory = null;
        this.routesGrid.classList.remove('hidden');
        this.coursePanel.classList.add('hidden');

        this.routesGrid.innerHTML = coursesData.categories.map(cat => `
            <div class="route-card" data-route="${cat.id}" onclick="viewer.openCategory('${cat.id}')">
                <span class="route-icon">${cat.icon}</span>
                <h3 class="route-title">${cat.name}</h3>
                <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 12px;">
                    ${cat.description}
                </p>
                <div class="route-stats">
                    <span class="route-stat">
                        <span class="route-stat-icon">📂</span>
                        ${cat.routeCount || cat.routes.length} rutas
                    </span>
                    <span class="route-stat">
                        <span class="route-stat-icon">📚</span>
                        ${cat.courseCount || 0} cursos
                    </span>
                    <span class="route-stat">
                        <span class="route-stat-icon">🎬</span>
                        ${cat.classCount || 0} clases
                    </span>
                </div>
            </div>
        `).join('');
    }

    // ===== Open Category =====
    openCategory(categoryId) {
        this.currentCategory = coursesData.categories.find(c => c.id === categoryId);
        this.currentView = 'routes';

        this.routesGrid.classList.add('hidden');
        this.coursePanel.classList.remove('hidden');

        this.courseHeader.innerHTML = `
            <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 12px;">
                <span style="font-size: 40px;">${this.currentCategory.icon}</span>
                <div>
                    <h2>${this.currentCategory.name}</h2>
                    <p>${this.currentCategory.description}</p>
                </div>
            </div>
            <div style="display: flex; gap: 20px; margin-top: 16px;">
                <span style="display: flex; align-items: center; gap: 8px; color: var(--text-secondary); font-size: 14px;">
                    <span>📂</span> ${this.currentCategory.routes.length} rutas
                </span>
                <span style="display: flex; align-items: center; gap: 8px; color: var(--text-secondary); font-size: 14px;">
                    <span>📚</span> ${this.currentCategory.courseCount || 0} cursos
                </span>
                <span style="display: flex; align-items: center; gap: 8px; color: var(--text-secondary); font-size: 14px;">
                    <span>🎬</span> ${this.currentCategory.classCount || 0} clases
                </span>
            </div>
        `;

        this.backBtn.textContent = '← Volver a Categorías';
        this.renderRoutesList();
    }

    renderRoutesList() {
        let routes = this.currentCategory.routes;

        if (this.searchQuery) {
            routes = routes.filter(route =>
                route.name.toLowerCase().includes(this.searchQuery)
            );
        }

        if (routes.length === 0) {
            this.modulesList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🔍</div>
                    <p class="empty-state-text">No se encontraron rutas</p>
                </div>
            `;
            return;
        }

        this.modulesList.innerHTML = `
            <div class="courses-list">
                ${routes.map(route => `
                    <div class="course-item" onclick="viewer.openRoute('${route.id}')">
                        <div class="course-item-header">
                            <span class="course-item-title">
                                ${route.isCourse ? '📖' : '📂'} ${route.name}
                            </span>
                            <span class="course-item-count">
                                ${route.isCourse
                ? (route.moduleCount || 0) + ' módulos'
                : (route.courseCount || 0) + ' cursos'
            }
                            </span>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    // ===== Open Route =====
    openRoute(routeId) {
        this.currentRoute = this.currentCategory.routes.find(r => r.id === routeId);

        if (this.currentRoute.isCourse) {
            this.currentCourse = null;
            this.currentView = 'modules';
            this.renderCourseModules();
        } else {
            this.currentView = 'courses';
            this.renderCoursesList();
        }
    }

    renderCoursesList() {
        this.courseHeader.innerHTML = `
            <nav class="breadcrumb">
                <span class="breadcrumb-item" onclick="viewer.renderCategories()">🏠 Categorías</span>
                <span class="breadcrumb-separator">›</span>
                <span class="breadcrumb-item" onclick="viewer.openCategory('${this.currentCategory.id}')">${this.currentCategory.icon} ${this.currentCategory.name}</span>
                <span class="breadcrumb-separator">›</span>
                <span style="color: var(--accent-primary);">📂 ${this.currentRoute.name}</span>
            </nav>
            <h2 style="margin-top: 16px;">${this.currentRoute.name}</h2>
            <p style="color: var(--text-secondary); margin-top: 8px;">
                ${this.currentRoute.courses ? this.currentRoute.courses.length : 0} cursos disponibles
            </p>
        `;

        this.backBtn.textContent = `← Volver a ${this.currentCategory.name}`;

        let courses = this.currentRoute.courses || [];

        if (this.searchQuery) {
            courses = courses.filter(course =>
                course.name.toLowerCase().includes(this.searchQuery)
            );
        }

        if (courses.length === 0) {
            this.modulesList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <p class="empty-state-text">No hay cursos registrados en esta ruta</p>
                </div>
            `;
            return;
        }

        this.modulesList.innerHTML = `
            <div class="courses-list">
                ${courses.map((course, idx) => `
                    <div class="course-item" onclick="viewer.openCourse(${idx})">
                        <div class="course-item-header">
                            <span class="course-item-title">📖 ${course.name}</span>
                            <span class="course-item-count">
                                ${course.moduleCount || 0} módulos
                            </span>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    // ===== Open Course =====
    openCourse(courseIndex) {
        this.currentCourse = this.currentRoute.courses[courseIndex];
        this.currentView = 'modules';
        this.renderCourseModules();
    }

    renderCourseModules() {
        const isDirectCourse = this.currentRoute?.isCourse;
        const courseData = isDirectCourse ? this.currentRoute : this.currentCourse;
        const courseName = courseData.name;

        this.courseHeader.innerHTML = `
            <nav class="breadcrumb">
                <span class="breadcrumb-item" onclick="viewer.renderCategories()">🏠 Categorías</span>
                <span class="breadcrumb-separator">›</span>
                <span class="breadcrumb-item" onclick="viewer.openCategory('${this.currentCategory.id}')">${this.currentCategory.icon} ${this.currentCategory.name}</span>
                ${!isDirectCourse ? `
                    <span class="breadcrumb-separator">›</span>
                    <span class="breadcrumb-item" onclick="viewer.openRoute('${this.currentRoute.id}')">📂 ${this.currentRoute.name}</span>
                ` : ''}
                <span class="breadcrumb-separator">›</span>
                <span style="color: var(--accent-primary);">📖 ${courseName}</span>
            </nav>
            <h2 style="margin-top: 16px;">${courseName}</h2>
            <p style="color: var(--text-secondary); margin-top: 8px;">
                ${courseData.moduleCount || (courseData.modules ? courseData.modules.length : 0)} módulos
            </p>
            ${courseData.hasPresentation ? `
                <button class="presentation-btn" onclick="viewer.openPresentation()">
                    🖥️ Ver presentación del curso
                </button>
            ` : ''}
        `;

        this.backBtn.textContent = isDirectCourse
            ? `← Volver a ${this.currentCategory.name}`
            : `← Volver a ${this.currentRoute.name}`;

        this.renderModules(courseData);
    }

    renderModules(courseData) {
        const modules = courseData.modules || [];

        if (modules.length === 0) {
            this.modulesList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <p class="empty-state-text">Este curso aún no tiene módulos</p>
                </div>
            `;
            return;
        }

        // Obtener información de progreso del curso
        const isDirectCourse = this.currentRoute?.isCourse;
        const courseFolder = isDirectCourse ? this.currentRoute.folderName : this.currentCourse?.folderName;
        const categoryId = this.currentCategory.id;
        const routeId = this.currentRoute.id;

        this.modulesList.innerHTML = modules.map((module, index) => {
            const classCount = module.classCount || (module.classes ? module.classes.length : 0);

            // Calcular progreso del módulo
            let completed = 0;
            let inProgress = 0;
            if (module.classes && Array.isArray(module.classes)) {
                module.classes.forEach(cls => {
                    const key = progressTracker.getClassKey(categoryId, routeId, courseFolder, module.folderName, cls.num);
                    const status = progressTracker.getClassStatus(key);
                    if (status === 'complete') completed++;
                    else if (status === 'in_progress') inProgress++;
                });
            }
            const percentage = classCount > 0 ? Math.round((completed / classCount) * 100) : 0;

            return `
            <div class="module-card ${percentage === 100 ? 'completed' : ''}" id="module-${index}">
                <div class="module-header" onclick="viewer.toggleModule(${index})">
                    <div class="module-title">
                        <span class="module-icon">${percentage === 100 ? '✅' : '📁'}</span>
                        <span>${module.name}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span class="module-progress-text">
                            ${completed}/${classCount} clases
                            ${inProgress > 0 ? `<span class="in-progress-badge">${inProgress} en progreso</span>` : ''}
                        </span>
                        <div class="progress-bar-mini">
                            <div class="progress-fill" style="width: ${percentage}%"></div>
                        </div>
                        <span class="module-toggle">▼</span>
                    </div>
                </div>
                <div class="module-content">
                    ${this.renderClasses(module, index)}
                </div>
            </div>
        `}).join('');
    }


    renderClasses(module, moduleIndex) {
        const classes = module.classes || [];

        if (classes.length === 0) {
            return '<p style="color: var(--text-muted); font-size: 13px; padding: 10px 0;">Sin clases disponibles</p>';
        }

        let filteredClasses = classes;
        if (this.currentFilter !== 'all') {
            filteredClasses = classes.filter(cls => {
                switch (this.currentFilter) {
                    case 'video': return cls.hasVideo;
                    case 'summary': return cls.hasSummary;
                    case 'reading': return cls.hasReading;
                    case 'sandbox': return cls.hasHtml && !cls.hasVideo;
                    default: return true;
                }
            });
        }

        if (filteredClasses.length === 0) {
            return '<p style="color: var(--text-muted); font-size: 13px; padding: 10px 0;">No hay clases que coincidan con el filtro</p>';
        }

        // Obtener información de progreso
        const isDirectCourse = this.currentRoute?.isCourse;
        const courseFolder = isDirectCourse ? this.currentRoute.folderName : this.currentCourse?.folderName;
        const categoryId = this.currentCategory.id;
        const routeId = this.currentRoute.id;

        return `
            <div class="classes-list">
                ${filteredClasses.map((cls, classIndex) => {
            const classKey = progressTracker.getClassKey(categoryId, routeId, courseFolder, module.folderName, cls.num);
            const status = progressTracker.getClassStatus(classKey);

            let statusIcon = '';
            let statusClass = '';
            if (status === 'complete') {
                statusIcon = '✅';
                statusClass = 'class-complete';
            } else if (status === 'in_progress') {
                statusIcon = '🕐';
                statusClass = 'class-in-progress';
            }

            return `
                    <div class="class-item clickable ${statusClass}" onclick="viewer.openClass(${moduleIndex}, ${classes.indexOf(cls)})">
                        <span class="class-status">${statusIcon}</span>
                        <span class="class-icon">${cls.hasVideo ? '📹' : (cls.hasHtml ? '⚡' : '📝')}</span>
                        <span class="class-name">${cls.name}</span>
                        <div class="class-badges">
                            ${cls.hasVideo ? '<span class="badge video" title="Video">📹</span>' : ''}
                            ${cls.hasSummary ? '<span class="badge summary" title="Resumen">📄</span>' : ''}
                            ${cls.hasReading ? '<span class="badge reading" title="Lectura">📚</span>' : ''}
                            ${cls.hasHtml && !cls.hasVideo ? '<span class="badge sandbox" title="Sandbox/HTML">⚡</span>' : ''}
                        </div>
                    </div>
                `}).join('')}
            </div>
        `;
    }


    toggleModule(index) {
        const moduleCard = document.getElementById(`module-${index}`);
        moduleCard.classList.toggle('expanded');
    }

    // ===== Video Player Modal =====
    openClass(moduleIndex, classIndex) {
        this.currentModule = moduleIndex;
        this.currentClassIndex = classIndex;

        const isDirectCourse = this.currentRoute?.isCourse;
        const courseData = isDirectCourse ? this.currentRoute : this.currentCourse;

        if (!courseData || !courseData.modules) {
            alert('Datos del curso no disponibles');
            return;
        }

        const moduleData = courseData.modules[moduleIndex];
        this.currentModuleData = moduleData;

        if (!moduleData || !moduleData.classes) {
            alert('Datos del módulo no disponibles');
            return;
        }

        const classData = moduleData.classes[classIndex];

        if (!classData) {
            alert('Datos de la clase no disponibles');
            return;
        }

        // Guardar clave de clase actual para tracking
        const categoryId = this.currentCategory.id;
        const routeId = this.currentRoute.id;
        const courseFolder = isDirectCourse ? this.currentRoute.folderName : courseData.folderName;
        this.currentClassKey = progressTracker.getClassKey(categoryId, routeId, courseFolder, moduleData.folderName, classData.num);
        this.currentClassData = classData;

        // Marcar como en progreso si no está completa
        const currentStatus = progressTracker.getClassStatus(this.currentClassKey);
        if (currentStatus !== 'complete') {
            progressTracker.markClassInProgress(this.currentClassKey);
        }

        // Show modal
        this.playerModal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';

        this.loadClassContent(classData, moduleData, courseData);
        this.updateNavigationButtons();
        this.setupVideoTracking();
    }

    setupVideoTracking() {
        // Limpiar countdown anterior si existe
        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
            this.countdownInterval = null;
        }

        // Agregar eventos de video para tracking
        if (this.videoPlayer) {
            // Al terminar el video, marcar como completa y auto-avanzar
            this.videoPlayer.onended = () => {
                progressTracker.markClassComplete(this.currentClassKey);
                this.handleClassCompleted();
            };

            // Actualizar tiempo de reproducción periódicamente
            this.videoPlayer.ontimeupdate = () => {
                const currentTime = this.videoPlayer.currentTime;
                const duration = this.videoPlayer.duration;

                // Si ha visto más del 90%, marcar como completa
                if (duration && currentTime / duration > 0.9) {
                    const status = progressTracker.getClassStatus(this.currentClassKey);
                    if (status !== 'complete') {
                        progressTracker.markClassComplete(this.currentClassKey);
                    }
                }
            };
        }
    }

    // ===== Video Preload System =====
    showVideoLoading() {
        if (this.videoLoadingOverlay) {
            this.videoLoadingOverlay.classList.remove('hidden');
            this.updateLoadingProgress(0);
        }
    }

    hideVideoLoading() {
        if (this.videoLoadingOverlay) {
            this.videoLoadingOverlay.classList.add('hidden');
        }
    }

    updateLoadingProgress(percent) {
        if (this.videoLoadingBar) {
            this.videoLoadingBar.style.width = `${percent}%`;
        }
        if (this.videoLoadingPercent) {
            this.videoLoadingPercent.textContent = `${Math.round(percent)}%`;
        }
    }

    cleanupVideoListeners() {
        if (this.videoPlayer) {
            // Remove previous event listeners by setting to null
            this.videoPlayer.onprogress = null;
            this.videoPlayer.oncanplaythrough = null;
            this.videoPlayer.onwaiting = null;
            this.videoPlayer.onplaying = null;
            this.videoPlayer.onerror = null;
            this.videoPlayer.onloadstart = null;
        }
        // Remove buffering overlay if exists
        const bufferingOverlay = document.getElementById('bufferingOverlay');
        if (bufferingOverlay) {
            bufferingOverlay.remove();
        }
    }

    setupVideoPreload() {
        if (!this.videoPlayer) return;

        let hasStartedPlaying = false;

        // Reset sync monitoring state
        this.syncMonitor = {
            lastVideoTime: 0,
            frameCount: 0,
            lastFpsCheck: performance.now(),
            currentFps: 0,
            isMonitoring: false,
            syncCheckInterval: null,
            frameCallback: null
        };

        // Track loading progress
        this.videoPlayer.onprogress = () => {
            if (this.videoPlayer.buffered.length > 0) {
                const duration = this.videoPlayer.duration;
                if (duration > 0) {
                    const bufferedEnd = this.videoPlayer.buffered.end(this.videoPlayer.buffered.length - 1);
                    const percent = (bufferedEnd / duration) * 100;
                    this.updateLoadingProgress(Math.min(percent, 100));
                }
            }
        };

        // Also update on loadstart
        this.videoPlayer.onloadstart = () => {
            this.showVideoLoading();
            this.updateLoadingProgress(0);
        };

        // Wait for enough buffer before allowing playback (5 seconds or entire video)
        this.videoPlayer.oncanplay = () => {
            const duration = this.videoPlayer.duration || 0;
            const minBuffer = Math.min(5, duration); // 5 seconds or full video

            if (this.videoPlayer.buffered.length > 0) {
                const bufferedEnd = this.videoPlayer.buffered.end(0);
                if (bufferedEnd >= minBuffer) {
                    console.log(`✅ Sufficient buffer: ${bufferedEnd.toFixed(1)}s buffered`);
                    this.hideVideoLoading();
                    this.updateLoadingProgress(100);
                }
            }
        };

        // Video is ready to play through without buffering
        this.videoPlayer.oncanplaythrough = () => {
            console.log('✅ Video ready to play through');
            this.hideVideoLoading();
            this.updateLoadingProgress(100);
        };

        // Handle video loading errors
        this.videoPlayer.onerror = (e) => {
            console.error('❌ Video loading error:', e);
            this.hideVideoLoading();
            if (this.videoLoadingOverlay) {
                const loadingContent = this.videoLoadingOverlay.querySelector('.video-loading-content');
                if (loadingContent) {
                    loadingContent.innerHTML = `
                        <div style="font-size: 48px;">❌</div>
                        <p class="video-loading-text">Error al cargar el video</p>
                        <p style="color: var(--text-muted); font-size: 12px;">Intenta recargar la página</p>
                    `;
                    this.videoLoadingOverlay.classList.remove('hidden');
                }
            }
        };

        // Handle buffering during playback - with sync check
        this.videoPlayer.onwaiting = () => {
            if (hasStartedPlaying) {
                this.showBufferingIndicator();
                console.log('⏳ Video buffering...');
            }
        };

        // Start advanced sync monitoring when playing
        this.videoPlayer.onplaying = () => {
            hasStartedPlaying = true;
            this.hideBufferingIndicator();
            this.startSyncMonitoring();
        };

        // Stop monitoring when paused
        this.videoPlayer.onpause = () => {
            this.stopSyncMonitoring();
        };

        // Handle seeking - reset sync state
        this.videoPlayer.onseeked = () => {
            if (this.syncMonitor) {
                this.syncMonitor.lastVideoTime = this.videoPlayer.currentTime;
            }
        };
    }

    // ===== Advanced A/V Sync Monitoring =====
    startSyncMonitoring() {
        if (this.syncMonitor.isMonitoring) return;
        this.syncMonitor.isMonitoring = true;

        // Use requestVideoFrameCallback if available (Chrome 83+)
        if ('requestVideoFrameCallback' in HTMLVideoElement.prototype) {
            this.monitorWithVideoFrameCallback();
        } else {
            // Fallback: use requestAnimationFrame
            this.monitorWithAnimationFrame();
        }

        // Check sync every 2 seconds
        this.syncMonitor.syncCheckInterval = setInterval(() => {
            this.checkAndCorrectSync();
        }, 2000);
    }

    stopSyncMonitoring() {
        if (!this.syncMonitor) return;
        this.syncMonitor.isMonitoring = false;

        if (this.syncMonitor.syncCheckInterval) {
            clearInterval(this.syncMonitor.syncCheckInterval);
            this.syncMonitor.syncCheckInterval = null;
        }
    }

    monitorWithVideoFrameCallback() {
        const video = this.videoPlayer;

        const frameCallback = (now, metadata) => {
            if (!this.syncMonitor.isMonitoring) return;

            this.syncMonitor.frameCount++;

            // Calculate FPS every second
            const elapsed = now - this.syncMonitor.lastFpsCheck;
            if (elapsed >= 1000) {
                this.syncMonitor.currentFps = Math.round((this.syncMonitor.frameCount * 1000) / elapsed);
                this.syncMonitor.frameCount = 0;
                this.syncMonitor.lastFpsCheck = now;

                // Log if FPS drops significantly
                if (this.syncMonitor.currentFps < 25 && this.syncMonitor.currentFps > 0) {
                    console.warn(`⚠️ Low FPS detected: ${this.syncMonitor.currentFps}`);
                }
            }

            this.syncMonitor.lastVideoTime = metadata.mediaTime;

            // Continue monitoring
            video.requestVideoFrameCallback(frameCallback);
        };

        video.requestVideoFrameCallback(frameCallback);
    }

    monitorWithAnimationFrame() {
        const monitor = () => {
            if (!this.syncMonitor.isMonitoring) return;

            const now = performance.now();
            this.syncMonitor.frameCount++;

            // Calculate FPS every second
            const elapsed = now - this.syncMonitor.lastFpsCheck;
            if (elapsed >= 1000) {
                this.syncMonitor.currentFps = Math.round((this.syncMonitor.frameCount * 1000) / elapsed);
                this.syncMonitor.frameCount = 0;
                this.syncMonitor.lastFpsCheck = now;
            }

            this.syncMonitor.lastVideoTime = this.videoPlayer.currentTime;

            requestAnimationFrame(monitor);
        };

        requestAnimationFrame(monitor);
    }

    checkAndCorrectSync() {
        if (!this.videoPlayer || this.videoPlayer.paused) return;

        // Check if video frames are keeping up with audio
        // This is a simplified check - the browser's internal sync should handle most cases
        const buffered = this.videoPlayer.buffered;
        const currentTime = this.videoPlayer.currentTime;

        if (buffered.length > 0) {
            const bufferedEnd = buffered.end(buffered.length - 1);
            const bufferAhead = bufferedEnd - currentTime;

            // If buffer is very low and video is playing, pause briefly to buffer
            if (bufferAhead < 0.5 && !this.videoPlayer.paused) {
                console.log('⚠️ Buffer running low, pausing to rebuffer');
                this.videoPlayer.pause();
                this.showBufferingIndicator();

                // Resume when buffer is adequate
                const checkBuffer = setInterval(() => {
                    if (this.videoPlayer.buffered.length > 0) {
                        const newBufferEnd = this.videoPlayer.buffered.end(this.videoPlayer.buffered.length - 1);
                        const newBufferAhead = newBufferEnd - this.videoPlayer.currentTime;

                        if (newBufferAhead >= 2) {
                            clearInterval(checkBuffer);
                            this.hideBufferingIndicator();
                            this.videoPlayer.play().catch(e => console.log('Auto-resume failed:', e));
                            console.log('✅ Buffer restored, resuming');
                        }
                    }
                }, 500);

                // Safety: clear after 10 seconds regardless
                setTimeout(() => clearInterval(checkBuffer), 10000);
            }
        }

        // Check playback rate - ensure it's normal
        if (this.videoPlayer.playbackRate !== 1.0 && !this.userSetPlaybackRate) {
            console.log('⚠️ Playback rate anomaly detected, resetting to 1.0');
            this.videoPlayer.playbackRate = 1.0;
        }
    }

    showBufferingIndicator() {
        // Check if buffering overlay already exists
        let bufferingOverlay = document.getElementById('bufferingOverlay');
        if (!bufferingOverlay) {
            bufferingOverlay = document.createElement('div');
            bufferingOverlay.id = 'bufferingOverlay';
            bufferingOverlay.className = 'video-buffering-overlay';
            bufferingOverlay.innerHTML = `
                <div class="video-buffering-spinner"></div>
                <span class="video-buffering-text">Cargando buffer...</span>
            `;
            const videoWrapper = this.videoPlayer.parentElement;
            if (videoWrapper) {
                videoWrapper.appendChild(bufferingOverlay);
            }
        }
        bufferingOverlay.classList.add('visible');
    }

    hideBufferingIndicator() {
        const bufferingOverlay = document.getElementById('bufferingOverlay');
        if (bufferingOverlay) {
            bufferingOverlay.classList.remove('visible');
        }
    }

    handleClassCompleted() {
        const isDirectCourse = this.currentRoute?.isCourse;
        const courseData = isDirectCourse ? this.currentRoute : this.currentCourse;
        const module = courseData?.modules?.[this.currentModule];

        const isLastClass = this.currentClassIndex >= (module?.classes?.length || 0) - 1;
        const isLastModule = this.currentModule >= (courseData?.modules?.length || 0) - 1;

        if (isLastClass && isLastModule) {
            // ¡Curso completado!
            this.showCourseCompletedModal();
        } else if (isLastClass) {
            // Última clase del módulo, ir al siguiente módulo
            this.showAutoAdvanceToast(true);
        } else {
            // Hay más clases, mostrar countdown y auto-avanzar
            this.showAutoAdvanceToast(false);
        }
    }

    showAutoAdvanceToast(nextModule) {
        let countdown = 5;
        const toast = document.createElement('div');
        toast.className = 'completion-toast auto-advance';
        toast.innerHTML = `
            <div>✅ ¡Clase completada!</div>
            <div class="countdown-text">Siguiente clase en <span id="countdownNum">${countdown}</span>s</div>
            <button class="cancel-advance-btn" onclick="viewer.cancelAutoAdvance()">Cancelar</button>
        `;
        document.body.appendChild(toast);
        this.currentToast = toast;

        setTimeout(() => toast.classList.add('show'), 100);

        this.countdownInterval = setInterval(() => {
            countdown--;
            const countdownEl = document.getElementById('countdownNum');
            if (countdownEl) countdownEl.textContent = countdown;

            if (countdown <= 0) {
                clearInterval(this.countdownInterval);
                this.countdownInterval = null;
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 300);

                // Avanzar a siguiente clase o módulo
                if (nextModule) {
                    this.advanceToNextModule();
                } else {
                    this.navigateClass(1);
                }
            }
        }, 1000);
    }

    cancelAutoAdvance() {
        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
            this.countdownInterval = null;
        }
        if (this.currentToast) {
            this.currentToast.classList.remove('show');
            setTimeout(() => this.currentToast.remove(), 300);
        }
    }

    advanceToNextModule() {
        const isDirectCourse = this.currentRoute?.isCourse;
        const courseData = isDirectCourse ? this.currentRoute : this.currentCourse;

        if (this.currentModule < (courseData?.modules?.length || 0) - 1) {
            this.currentModule++;
            this.currentClassIndex = 0;
            this.openClass(this.currentModule, 0);
        }
    }

    showCourseCompletedModal() {
        const modal = document.createElement('div');
        modal.className = 'course-completed-modal';
        modal.innerHTML = `
            <div class="course-completed-content">
                <div class="celebration-icon">🎉</div>
                <h2>¡Felicidades!</h2>
                <p>Has completado el curso</p>
                <h3>${this.currentCourse?.name || this.currentRoute?.name || 'este curso'}</h3>
                <div class="confetti-container">
                    ${Array(20).fill().map(() => '<div class="confetti"></div>').join('')}
                </div>
                <button class="close-celebration-btn" onclick="viewer.closeCelebrationModal()">
                    🚀 Continuar aprendiendo
                </button>
            </div>
        `;
        document.body.appendChild(modal);
        this.celebrationModal = modal;

        setTimeout(() => modal.classList.add('show'), 100);
    }

    closeCelebrationModal() {
        if (this.celebrationModal) {
            this.celebrationModal.classList.remove('show');
            setTimeout(() => {
                this.celebrationModal.remove();
                this.closePlayerModal();
            }, 300);
        }
    }

    markCurrentClassComplete() {
        progressTracker.markClassComplete(this.currentClassKey);
        this.handleClassCompleted();
    }



    loadClassContent(classData, moduleData, courseData) {
        const className = classData.name;
        const isDirectCourse = this.currentRoute?.isCourse;

        // Build paths
        const categoryFolder = this.currentCategory.folderName;
        const routeFolder = isDirectCourse ? null : this.currentRoute.folderName;
        const courseFolder = isDirectCourse ? this.currentRoute.folderName : courseData.folderName;
        const moduleFolder = moduleData.folderName;

        if (classData.hasVideo && classData.files && classData.files.video) {
            // Show video section
            this.videoSection.classList.remove('hidden');
            this.htmlSection.classList.add('hidden');
            this.classTitle.textContent = className;

            // Show loading overlay
            this.showVideoLoading();

            // Build video URL
            const videoUrl = this.buildFileUrl(classData.files.video);

            // Clean up previous video event listeners
            this.cleanupVideoListeners();

            // Set up new loading events
            this.setupVideoPreload();

            this.videoSource.src = videoUrl;
            this.videoPlayer.load();

            // Subtitles
            if (classData.files.subtitles) {
                const subtitlesUrl = this.buildFileUrl(classData.files.subtitles);
                this.videoSubtitles.src = subtitlesUrl;
            }

            console.log('Video URL:', videoUrl);

        } else if (classData.hasHtml && classData.files && classData.files.html) {
            // Show HTML section
            this.videoSection.classList.add('hidden');
            this.htmlSection.classList.remove('hidden');
            this.htmlClassTitle.textContent = className;

            const htmlUrl = this.buildFileUrl(classData.files.html);
            this.htmlFrame.src = htmlUrl;
        } else {
            this.videoSection.classList.add('hidden');
            this.htmlSection.classList.remove('hidden');
            this.htmlClassTitle.textContent = className;
            this.htmlFrame.srcdoc = '<p style="text-align:center;padding:20px;color:#666;">Contenido no disponible</p>';
        }

        // Summary section
        if (classData.hasSummary && classData.files && classData.files.summary) {
            this.summarySection.style.display = 'block';
            const summaryUrl = this.buildFileUrl(classData.files.summary);
            this.summaryFrame.src = summaryUrl;

            // Reset summary state
            this.summaryContent.classList.add('hidden');
            this.toggleSummaryBtn.textContent = '▼ Mostrar';
        } else {
            this.summarySection.style.display = 'none';
        }

        // Reading section
        if (classData.hasReading && classData.files && classData.files.reading) {
            this.readingSection.classList.remove('hidden');
            const readingUrl = this.buildFileUrl(classData.files.reading);
            this.readingContent.innerHTML = `
                <p>📚 <a href="${readingUrl}" target="_blank">${classData.name} - Lectura</a></p>
            `;
        } else {
            this.readingSection.classList.add('hidden');
        }
    }

    openInExternalPlayer() {
        if (!this.currentClassData || !this.currentClassData.files || !this.currentClassData.files.video) {
            alert('No hay video disponible para esta clase');
            return;
        }

        const classData = this.currentClassData;
        const moduleData = this.currentModuleData;
        const isDirectCourse = this.currentRoute?.isCourse;
        const courseData = isDirectCourse ? this.currentRoute : this.currentCourse;

        const categoryFolder = this.currentCategory.folderName;
        const routeFolder = isDirectCourse ? null : this.currentRoute.folderName;
        const courseFolder = isDirectCourse ? this.currentRoute.folderName : courseData.folderName;
        const moduleFolder = moduleData.folderName;
        const fileName = classData.files.video;

        let path = categoryFolder;
        if (routeFolder) path += '/' + routeFolder;
        if (courseFolder) path += '/' + courseFolder;
        if (moduleFolder) path += '/' + moduleFolder;
        if (fileName) path += '/' + fileName;

        // Button feedback
        const btn = this.openExternalBtn;
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = '⏳ Abriendo...';

        fetch(`${API_URL}/api/open`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: path })
        })
            .then(response => {
                if (response.ok) {
                    if (this.videoPlayer && !this.videoPlayer.paused) {
                        this.videoPlayer.pause();
                    }
                } else {
                    console.error('Error opening external player');
                    // alert('Error al abrir el reproductor externo');
                }
            })
            .catch(err => {
                console.error(err);
                // alert('Error al conectar con el servidor');
            })
            .finally(() => {
                btn.disabled = false;
                btn.textContent = originalText;
            });
    }

    toggleSummary() {
        const isHidden = this.summaryContent.classList.contains('hidden');

        if (isHidden) {
            this.summaryContent.classList.remove('hidden');
            this.toggleSummaryBtn.textContent = '▲ Ocultar';
        } else {
            this.summaryContent.classList.add('hidden');
            this.toggleSummaryBtn.textContent = '▼ Mostrar';
        }
    }

    updateNavigationButtons() {
        const isDirectCourse = this.currentRoute?.isCourse;
        const courseData = isDirectCourse ? this.currentRoute : this.currentCourse;

        if (!courseData || !courseData.modules) {
            this.prevClassBtn.disabled = true;
            this.nextClassBtn.disabled = true;
            return;
        }

        const module = courseData.modules[this.currentModule];
        if (!module || !module.classes) {
            this.prevClassBtn.disabled = true;
            this.nextClassBtn.disabled = true;
            return;
        }

        this.prevClassBtn.disabled = this.currentClassIndex <= 0;
        this.nextClassBtn.disabled = this.currentClassIndex >= module.classes.length - 1;
    }

    navigateClass(direction) {
        const isDirectCourse = this.currentRoute?.isCourse;
        const courseData = isDirectCourse ? this.currentRoute : this.currentCourse;

        if (!courseData || !courseData.modules) return;

        const module = courseData.modules[this.currentModule];
        if (!module || !module.classes) return;

        const newIndex = this.currentClassIndex + direction;

        if (newIndex >= 0 && newIndex < module.classes.length) {
            this.currentClassIndex = newIndex;
            this.openClass(this.currentModule, newIndex);
        }
    }

    closePlayerModal() {
        this.playerModal.classList.add('hidden');
        document.body.style.overflow = '';

        if (this.videoPlayer) {
            this.videoPlayer.pause();
            this.videoSource.src = '';
            this.videoPlayer.load();
        }

        // Refrescar la UI para mostrar progreso actualizado
        if (this.currentView === 'modules') {
            const isDirectCourse = this.currentRoute?.isCourse;
            const courseData = isDirectCourse ? this.currentRoute : this.currentCourse;
            if (courseData) {
                this.renderModules(courseData);
            }
        }
    }


    // ===== Presentation Modal =====
    openPresentation() {
        const isDirectCourse = this.currentRoute?.isCourse;
        const courseData = isDirectCourse ? this.currentRoute : this.currentCourse;

        const presentationUrl = this.buildFileUrl(courseData.presentationId);

        this.presentationFrame.src = presentationUrl;
        this.presentationModal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }

    closePresentationModal() {
        this.presentationModal.classList.add('hidden');
        document.body.style.overflow = '';
        this.presentationFrame.src = '';
    }

    goBack() {
        switch (this.currentView) {
            case 'modules':
                if (this.currentRoute?.isCourse) {
                    this.openCategory(this.currentCategory.id);
                } else {
                    this.openRoute(this.currentRoute.id);
                }
                break;
            case 'courses':
                this.openCategory(this.currentCategory.id);
                break;
            case 'routes':
                this.renderCategories();
                break;
            default:
                this.renderCategories();
        }
    }

    applyFilters() {
        switch (this.currentView) {
            case 'routes':
                this.renderRoutesList();
                break;
            case 'courses':
                this.renderCoursesList();
                break;
            case 'modules':
                this.renderCourseModules();
                break;
            default:
                break;
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.viewer = new PlatziViewer();
});
