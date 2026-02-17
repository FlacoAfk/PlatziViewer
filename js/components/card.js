export class Card {
    /**
     * Renders a route card for the home grid.
     * @param {Object} route - Route data from API
     * @param {number} catIdx - Category index
     * @param {number} routeIdx - Route index within category
     */
    static renderRoute(route, catIdx, routeIdx) {
        const typeLabel = route.isCourse ? 'Curso' : 'Ruta';
        const typeIcon = route.isCourse ? '🎓' : '🚀';

        // Count available courses (foundInDrive)
        const courses = route.courses || [];
        const totalCourses = courses.length;
        const availableCourses = courses.filter(c => c.foundInDrive).length;
        const hasAll = availableCourses === totalCourses && totalCourses > 0;
        const hasSome = availableCourses > 0;

        const countLabel = route.isCourse
            ? `${route.moduleCount || 0} Módulos`
            : `${availableCourses}/${totalCourses} Cursos`;

        const availabilityClass = hasAll ? 'route-complete' : (hasSome ? 'route-partial' : 'route-empty');

        return `
            <div class="route-card ${availabilityClass}" onclick="window.location.hash='#route/${catIdx}/${routeIdx}'">
                <div class="route-icon">${typeIcon}</div>
                <h3 class="route-title">${route.name}</h3>
                <p class="route-desc">
                    <span class="badge-type">${typeLabel}</span> • ${countLabel}
                </p>
                <div class="progress-bar-sm">
                    <div class="progress-fill" style="width: ${totalCourses > 0 ? (availableCourses / totalCourses * 100) : 0}%"></div>
                </div>
            </div>
        `;
    }

    /**
     * Renders a course card for the route timeline.
     * @param {Object} course - Course data from API
     * @param {number} catIdx - Category index
     * @param {number} routeIdx - Route index
     * @param {number} courseIdx - Course index within route
     */
    static renderCourse(course, catIdx, routeIdx, courseIdx) {
        const moduleCount = course.moduleCount || (Array.isArray(course.modules) ? course.modules.length : 0);
        const isAvailable = course.foundInDrive !== false;
        const availClass = isAvailable ? '' : 'course-unavailable';
        const badge = isAvailable ? '' : '<span class="badge-unavailable">No disponible</span>';

        return `
            <div class="course-card ${availClass}" ${isAvailable ? `onclick="window.location.hash='#course/${catIdx}/${routeIdx}/${courseIdx}'"` : ''}>
                <div class="course-thumbnail">
                    <div class="thumbnail-placeholder">${isAvailable ? '📖' : '📕'}</div>
                </div>
                <div class="course-info">
                    <h4>${course.name}</h4>
                    ${badge}
                    <p class="course-meta-text">${isAvailable ? `${moduleCount} módulos` : 'No encontrado en Drive'}</p>
                </div>
            </div>
        `;
    }
}
