import assert from 'node:assert/strict';

function createStorage() {
    const store = new Map();
    return {
        getItem(key) {
            return store.has(key) ? store.get(key) : null;
        },
        setItem(key, value) {
            store.set(key, String(value));
        },
        removeItem(key) {
            store.delete(key);
        },
    };
}

globalThis.window = {
    location: { origin: 'http://localhost:8080', hash: '#home' },
    matchMedia: () => ({ matches: false }),
    addEventListener() {},
    removeEventListener() {},
    scrollTo() {},
    setTimeout,
    clearTimeout,
};
globalThis.localStorage = createStorage();
Object.defineProperty(globalThis, 'navigator', {
    configurable: true,
    value: { maxTouchPoints: 0 },
});
Object.defineProperty(globalThis, 'document', {
    configurable: true,
    value: {
    addEventListener() {},
    removeEventListener() {},
    querySelector() {
        return null;
    },
    querySelectorAll() {
        return [];
    },
    getElementById() {
        return null;
    },
    },
});

const sampleData = {
    stats: {
        totalCategories: 1,
        totalRoutes: 2,
        totalCourses: 2,
        totalClasses: 3,
    },
    categories: [
        {
            id: 'dev',
            name: 'Desarrollo',
            icon: '💻',
            description: 'Backend y frontend',
            courseCount: 2,
            routes: [
                {
                    id: 'backend',
                    name: 'Ruta Backend',
                    isCourse: false,
                    courses: [
                        {
                            id: 'api-course',
                            name: 'Curso de APIs',
                            folderName: '01. Curso de APIs',
                            moduleCount: 1,
                            classCount: 2,
                            foundInDrive: true,
                            modules: [
                                {
                                    name: 'Fundamentos',
                                    classes: [
                                        {
                                            name: 'Introducción',
                                            hasVideo: true,
                                            hasSummary: true,
                                            hasReading: true,
                                            files: { video: '1ValidDriveRefAA' },
                                        },
                                        {
                                            name: 'HTTP práctico',
                                            hasHtml: true,
                                            hasSummary: false,
                                            hasReading: false,
                                            files: {},
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
                {
                    id: 'standalone',
                    name: 'Curso Standalone',
                    isCourse: true,
                    moduleCount: 1,
                    classCount: 1,
                    foundInDrive: true,
                    modules: [
                        {
                            name: 'Inicio',
                            classes: [
                                {
                                    name: 'Primera clase',
                                    hasVideo: true,
                                    hasSummary: false,
                                    hasReading: false,
                                    files: { video: '1ValidDriveRefZZ' },
                                },
                            ],
                        },
                    ],
                },
            ],
        },
    ],
};

const { state } = await import('../js/services/state.js');

state.getData = () => sampleData;
state.getCategory = (catIdx) => sampleData.categories[catIdx] || null;
state.getRoute = (catIdx, routeIdx) => sampleData.categories[catIdx]?.routes?.[routeIdx] || null;
state.getCourse = (catIdx, routeIdx, courseIdx) => {
    const route = sampleData.categories[catIdx]?.routes?.[routeIdx];
    if (!route) return null;
    if (route.isCourse) return route;
    return route.courses?.[courseIdx] || null;
};
state.getClass = (catIdx, routeIdx, courseIdx, modIdx, classIdx) => {
    const course = state.getCourse(catIdx, routeIdx, courseIdx);
    return course?.modules?.[modIdx]?.classes?.[classIdx] || null;
};
state.getModuleClasses = (module) => Array.isArray(module?.classes) ? module.classes : [];
state.getClassKey = (...parts) => parts.join('|');
state.getClassStatus = (key) => (key.endsWith('|0') ? 'complete' : 'pending');
state.isClassComplete = (key) => key.endsWith('|0');
state.countCourseCompleted = () => 1;
state.countCourseClasses = (course) => (course.modules || []).reduce(
    (total, module) => total + (Array.isArray(module.classes) ? module.classes.length : 0),
    0
);
state.ensureCourseDetail = async (catIdx, routeIdx, courseIdx) => state.getCourse(catIdx, routeIdx, courseIdx);
state.getOverallProgress = () => ({
    completedClasses: 1,
    totalClasses: 3,
    startedRoutes: 1,
    totalRoutes: 2,
    completedRoutes: 0,
    percent: 1 / 3,
});
state.getInProgressRoutes = () => [
    {
        catIdx: 0,
        routeIdx: 0,
        route: sampleData.categories[0].routes[0],
        categoryIcon: '💻',
        categoryName: 'Desarrollo',
        completed: 1,
        total: 2,
        percent: 0.5,
    },
];
state.search = () => [
    {
        type: 'route',
        item: sampleData.categories[0].routes[0],
        catIdx: 0,
        routeIdx: 0,
        categoryName: 'Desarrollo',
    },
];
state.filterByCategory = () => state.search();

const { Card } = await import('../js/components/card.js');
const { safeGetLocalStorage, safeSetLocalStorage } = await import('../js/utils/view-helpers.js');
const { default: HomeView } = await import('../js/views/home.js');
const { default: ExploreView } = await import('../js/views/explore.js');
const { default: RouteView } = await import('../js/views/route.js');
const { default: CourseView } = await import('../js/views/course.js');
const { default: LearningView } = await import('../js/views/learning.js');
const { default: PlayerView } = await import('../js/views/player.js');

assert.equal(safeGetLocalStorage('missing-key', 'fallback'), 'fallback');
assert.equal(safeSetLocalStorage('player-smoke-key', 'ok'), true);
assert.equal(safeGetLocalStorage('player-smoke-key', ''), 'ok');

const routeCardHtml = Card.renderRoute(sampleData.categories[0].routes[0], 0, 0);
assert.match(routeCardHtml, /data-href="#route\/0\/0"/);

const homeView = new HomeView();
const homeHtml = await homeView.render();
assert.match(homeHtml, /Explorar por Categorías/);
assert.match(homeHtml, /data-href="#route\/0\/0"/);
homeView.mounted();

const exploreView = new ExploreView();
const exploreHtml = await exploreView.render();
assert.match(exploreHtml, /explore-search/);
assert.match(exploreHtml, /data-href="#route\/0\/0"/);
exploreView.mounted();

const routeView = new RouteView({ catIdx: '0', routeIdx: '0' });
const routeHtml = await routeView.render();
assert.match(routeHtml, /Ruta Backend/);
assert.match(routeHtml, /data-href="#course\/0\/0\/0"/);
routeView.mounted();

const courseView = new CourseView({ catIdx: '0', routeIdx: '0', courseIdx: '0' });
const courseHtml = await courseView.render();
assert.match(courseHtml, /Temario del Curso/);
assert.match(courseHtml, /data-storage-key="platzi_notes_0_0_0"/);
assert.doesNotMatch(courseHtml, /MDN — HTTP Docs/);
courseView.mounted();

const learningView = new LearningView();
const learningHtml = await learningView.render();
assert.match(learningHtml, /Mi Aprendizaje/);
assert.match(learningHtml, /data-href="#route\/0\/0"/);
learningView.mounted();

const playerView = new PlayerView({
    catIdx: '0',
    routeIdx: '0',
    courseIdx: '0',
    modIdx: '0',
    classIdx: '0',
});
assert.equal(playerView._isEditableShortcutTarget({ tagName: 'INPUT' }), true);
assert.equal(playerView._isEditableShortcutTarget({ tagName: 'DIV', isContentEditable: true }), true);
assert.equal(playerView._isEditableShortcutTarget({ tagName: 'BUTTON' }), false);
playerView.videoFileRef = '1ValidDriveRefAA';
playerView.videoTotalDuration = 0;
assert.equal(playerView._hasDriveVideoRef(), true);
assert.equal(playerView._getDisplayDuration({ duration: 203 }), 0);
assert.equal(playerView._getProgressDuration({ duration: 203 }), 203);
assert.equal(playerView._getSeekTarget({ duration: 95 }, 40), 40);
const timeDisplay = { textContent: '' };
playerView._renderTimeDisplay(timeDisplay, { currentTime: 59, duration: 203 });
assert.equal(timeDisplay.textContent, '0:59 / --:--');
playerView.videoTotalDuration = 203;
assert.equal(playerView._getDisplayDuration({ duration: 120 }), 203);
assert.equal(playerView._getProgressDuration({ duration: 120 }), 203);
assert.equal(playerView._getSeekTarget({ duration: 95 }, 150), 150);
assert.equal(playerView._getSeekTarget({ duration: 95 }, 260), 203);
assert.equal(playerView._getSeekTarget({
    duration: 95,
    seekable: {
        length: 1,
        end: () => 90,
    },
}, 150), 90);
assert.equal(playerView._getSeekTarget({
    duration: 95,
    seekable: {
        length: 1,
        end: () => 203,
    },
}, 150), 150);
playerView._renderTimeDisplay(timeDisplay, { currentTime: 59, duration: 120 });
assert.equal(timeDisplay.textContent, '0:59 / 3:23');
playerView.videoFileRef = null;
playerView.videoTotalDuration = 0;
assert.equal(playerView._getDisplayDuration({ duration: 95 }), 95);
assert.equal(playerView._getProgressDuration({ duration: 95 }), 95);
assert.equal(playerView._refreshSidebar(), null);
const playerHtml = await playerView.render();
assert.match(playerHtml, /data-player-action="open-external"/);
assert.match(playerHtml, /data-player-action="download"/);
assert.match(playerHtml, /data-href="#player\/0\/0\/0\/0\/0"/);
assert.doesNotMatch(playerHtml, /__playerView/);

// Test API repair methods (mocked fetch)
globalThis.fetch = async (url, options) => {
    if (url.includes('/api/repair/')) {
        return { ok: true, json: async () => ({ status: 'pending' }) };
    }
    if (url.includes('/api/repair-status/')) {
        return { ok: true, json: async () => ({ status: 'completed', artifactPath: 'repaired_videos/123.mp4' }) };
    }
    return { ok: false };
};
const { ApiService } = await import('../js/services/api.js');
const repairRes = await ApiService.requestRepair('123');
assert.equal(repairRes.status, 'pending');
const statusRes = await ApiService.getRepairStatus('123');
assert.equal(statusRes.status, 'completed');
assert.equal(ApiService.getVideoUrl('123').includes('/api/repaired/123'), true);

console.log('frontend smoke ok');
