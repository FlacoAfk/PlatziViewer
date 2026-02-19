import { ApiService, API_URL } from './api.js';

class StateService {
    constructor() {
        this.coursesData = null;
        this.progress = {};
        this.storageKey = 'platzi_progress';
        this.listeners = [];
        this._syncTimer = null;
    }

    async init() {
        // Load courses data (required)
        this.coursesData = await ApiService.getCourses();

        const localProgress = this.loadLocalProgress();
        const serverProgress = await this.loadServerProgress();

        this.progress = this.mergeProgress(localProgress, serverProgress);
        this.saveProgress({ syncServer: false });

        console.log('✅ State Initialized:', this.coursesData?.stats);
    }

    async loadServerProgress() {
        try {
            const response = await fetch(`${API_URL}/api/progress`, { cache: 'no-store' });
            if (!response.ok) return {};
            const data = await response.json();
            return data && typeof data === 'object' && !Array.isArray(data) ? data : {};
        } catch (e) {
            console.warn('Error loading server progress:', e);
            return {};
        }
    }

    _statusRank(status) {
        if (status === 'complete') return 2;
        if (status === 'in_progress') return 1;
        return 0;
    }

    _recordTimestamp(record) {
        if (!record || typeof record !== 'object') return 0;
        const raw = record.completedAt || record.lastWatched || '';
        const ts = raw ? Date.parse(raw) : NaN;
        return Number.isFinite(ts) ? ts : 0;
    }

    mergeProgress(localProgress, serverProgress) {
        const local = localProgress && typeof localProgress === 'object' ? localProgress : {};
        const server = serverProgress && typeof serverProgress === 'object' ? serverProgress : {};
        const merged = {};
        const keys = new Set([...Object.keys(local), ...Object.keys(server)]);

        keys.forEach((key) => {
            const localRecord = local[key];
            const serverRecord = server[key];

            if (!localRecord) {
                merged[key] = serverRecord;
                return;
            }
            if (!serverRecord) {
                merged[key] = localRecord;
                return;
            }

            const localRank = this._statusRank(localRecord.status);
            const serverRank = this._statusRank(serverRecord.status);

            if (localRank > serverRank) {
                merged[key] = localRecord;
                return;
            }
            if (serverRank > localRank) {
                merged[key] = serverRecord;
                return;
            }

            merged[key] = this._recordTimestamp(serverRecord) >= this._recordTimestamp(localRecord)
                ? serverRecord
                : localRecord;
        });

        return merged;
    }

    queueServerSync() {
        if (this._syncTimer) {
            clearTimeout(this._syncTimer);
        }

        this._syncTimer = setTimeout(() => {
            this._syncTimer = null;
            this.saveServerProgress();
        }, 400);
    }

    async saveServerProgress() {
        try {
            await fetch(`${API_URL}/api/progress`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.progress)
            });
        } catch (e) {
            console.warn('Error saving server progress:', e);
        }
    }

    loadLocalProgress() {
        try {
            return JSON.parse(localStorage.getItem(this.storageKey) || '{}');
        } catch (e) {
            console.warn('Error loading local progress:', e);
            return {};
        }
    }

    saveProgress({ syncServer = true } = {}) {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.progress));
        } catch (e) {
            console.error('Error saving progress:', e);
        }

        if (syncServer) {
            this.queueServerSync();
        }

        this.notifyListeners();
    }

    // --- Lookup Helpers ---

    getCategory(catIdx) {
        return this.coursesData?.categories?.[catIdx] || null;
    }

    getRoute(catIdx, routeIdx) {
        return this.getCategory(catIdx)?.routes?.[routeIdx] || null;
    }

    getCourse(catIdx, routeIdx, courseIdx) {
        const route = this.getRoute(catIdx, routeIdx);
        if (!route) return null;
        if (route.isCourse) return route; // The route IS the course
        return route.courses?.[courseIdx] || null;
    }

    getModule(catIdx, routeIdx, courseIdx, modIdx) {
        const course = this.getCourse(catIdx, routeIdx, courseIdx);
        return course?.modules?.[modIdx] || null;
    }

    getClass(catIdx, routeIdx, courseIdx, modIdx, classIdx) {
        const mod = this.getModule(catIdx, routeIdx, courseIdx, modIdx);
        if (!mod || !Array.isArray(mod.classes)) return null;
        return mod.classes[classIdx] || null;
    }

    // Safe accessor for module classes (handles number vs array)
    getModuleClasses(mod) {
        if (!mod) return [];
        if (Array.isArray(mod.classes)) return mod.classes;
        return []; // It's a number (count) — no class details available
    }

    // --- Progress Actions ---

    getClassKey(catIdx, routeIdx, courseIdx, modIdx, classIdx) {
        return `${catIdx}|${routeIdx}|${courseIdx}|${modIdx}|${classIdx}`;
    }

    markClassComplete(classKey) {
        this.progress[classKey] = {
            status: 'complete',
            completedAt: new Date().toISOString()
        };
        this.saveProgress();
    }

    markClassInProgress(classKey, time = 0) {
        const current = this.progress[classKey];
        if (!current || current.status !== 'complete') {
            this.progress[classKey] = {
                status: 'in_progress',
                lastWatched: new Date().toISOString(),
                watchTime: time
            };
            this.saveProgress();
        }
    }

    isClassComplete(classKey) {
        return this.progress[classKey]?.status === 'complete';
    }

    getClassStatus(classKey) {
        return this.progress[classKey]?.status || 'not_started';
    }

    // --- Progress Calculations ---

    /** Count total classes in a course (handles number-type classes) */
    countCourseClasses(course) {
        if (!course?.modules) return 0;
        return course.modules.reduce((sum, mod) => {
            if (Array.isArray(mod.classes)) return sum + mod.classes.length;
            if (typeof mod.classes === 'number') return sum + mod.classes;
            return sum;
        }, 0);
    }

    /** Count completed classes for a specific course at given indices */
    countCourseCompleted(catIdx, routeIdx, courseIdx) {
        let completed = 0;
        const course = this.getCourse(catIdx, routeIdx, courseIdx);
        if (!course?.modules) return 0;
        course.modules.forEach((mod, modIdx) => {
            const classes = this.getModuleClasses(mod);
            classes.forEach((_, classIdx) => {
                const key = this.getClassKey(catIdx, routeIdx, courseIdx, modIdx, classIdx);
                if (this.isClassComplete(key)) completed++;
            });
        });
        return completed;
    }

    /** Get progress fraction for a course (0-1) */
    getCourseProgress(catIdx, routeIdx, courseIdx) {
        const course = this.getCourse(catIdx, routeIdx, courseIdx);
        const total = this.countCourseClasses(course);
        if (total === 0) return 0;
        const completed = this.countCourseCompleted(catIdx, routeIdx, courseIdx);
        return completed / total;
    }

    /** Get progress info for a route */
    getRouteProgress(catIdx, routeIdx) {
        const route = this.getRoute(catIdx, routeIdx);
        if (!route) return { completed: 0, total: 0, percent: 0 };
        if (route.isCourse) {
            const total = this.countCourseClasses(route);
            const completed = this.countCourseCompleted(catIdx, routeIdx, 0);
            return { completed, total, percent: total ? completed / total : 0 };
        }
        const courses = route.courses || [];
        let totalAll = 0, completedAll = 0;
        courses.forEach((course, courseIdx) => {
            totalAll += this.countCourseClasses(course);
            completedAll += this.countCourseCompleted(catIdx, routeIdx, courseIdx);
        });
        return { completed: completedAll, total: totalAll, percent: totalAll ? completedAll / totalAll : 0 };
    }

    /** Get all routes with their progress, optionally filtered */
    getAllRoutesWithProgress() {
        const results = [];
        const categories = this.coursesData?.categories || [];
        categories.forEach((cat, catIdx) => {
            (cat.routes || []).forEach((route, routeIdx) => {
                const prog = this.getRouteProgress(catIdx, routeIdx);
                results.push({
                    route,
                    catIdx,
                    routeIdx,
                    categoryName: cat.name,
                    categoryIcon: cat.icon,
                    ...prog
                });
            });
        });
        return results;
    }

    /** Get routes that have any progress (in-progress or completed) */
    getInProgressRoutes() {
        return this.getAllRoutesWithProgress().filter(r => r.completed > 0);
    }

    /** Get overall stats across all courses */
    getOverallProgress() {
        const all = this.getAllRoutesWithProgress();
        const totalClasses = all.reduce((s, r) => s + r.total, 0);
        const completedClasses = all.reduce((s, r) => s + r.completed, 0);
        const startedRoutes = all.filter(r => r.completed > 0).length;
        const completedRoutes = all.filter(r => r.total > 0 && r.completed === r.total).length;
        return {
            totalClasses,
            completedClasses,
            totalRoutes: all.length,
            startedRoutes,
            completedRoutes,
            percent: totalClasses ? completedClasses / totalClasses : 0
        };
    }

    /** Search routes and courses by name */
    search(query) {
        const q = query.toLowerCase().trim();
        if (!q) return [];
        const results = [];
        const categories = this.coursesData?.categories || [];
        categories.forEach((cat, catIdx) => {
            (cat.routes || []).forEach((route, routeIdx) => {
                const routeMatch = route.name?.toLowerCase().includes(q);
                if (routeMatch) {
                    results.push({ type: 'route', item: route, catIdx, routeIdx, categoryName: cat.name, categoryIcon: cat.icon });
                }
                if (!route.isCourse && route.courses) {
                    route.courses.forEach((course, courseIdx) => {
                        if (course.name?.toLowerCase().includes(q)) {
                            results.push({ type: 'course', item: course, catIdx, routeIdx, courseIdx, categoryName: cat.name, routeName: route.name });
                        }
                    });
                }
            });
        });
        return results;
    }

    /** Filter routes by category name */
    filterByCategory(categoryName) {
        const categories = this.coursesData?.categories || [];
        const catIdx = categories.findIndex(c => c.name === categoryName);
        if (catIdx === -1) return [];
        const cat = categories[catIdx];
        return (cat.routes || []).map((route, routeIdx) => ({
            type: route.isCourse ? 'course' : 'route',
            item: route,
            catIdx,
            routeIdx,
            categoryName: cat.name,
            categoryIcon: cat.icon
        }));
    }

    // --- Subscribers ---
    subscribe(callback) {
        this.listeners.push(callback);
    }

    notifyListeners() {
        this.listeners.forEach(cb => cb(this.progress));
    }

    getData() { return this.coursesData; }
}

export const state = new StateService();
