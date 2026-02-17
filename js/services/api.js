export const API_URL = 'http://localhost:8080';

export class ApiService {
    static async getCourses(retries = 30) {
        for (let i = 0; i < retries; i++) {
            try {
                const response = await fetch(`${API_URL}/api/courses`);
                if (!response.ok) throw new Error('Server error');
                const data = await response.json();

                // If no categories yet, server is still scanning
                if (data && data.categories && data.categories.length > 0) {
                    console.log('📦 Data loaded:', data.stats);
                    return data;
                }

                console.log(`⏳ Waiting for data... (${i + 1}/${retries})`);
                await new Promise(r => setTimeout(r, 2000));
            } catch (error) {
                if (i === retries - 1) throw error;
                console.log(`Retrying... (${i + 1}/${retries})`);
                await new Promise(r => setTimeout(r, 2000));
            }
        }
        throw new Error('No se pudieron cargar los datos');
    }

    static getVideoUrl(fileId) {
        if (!fileId) return '';
        return `${API_URL}/drive/files/${fileId}`;
    }

    static getFileUrl(fileId) {
        if (!fileId) return '';
        return `${API_URL}/drive/files/${fileId}`;
    }
}
