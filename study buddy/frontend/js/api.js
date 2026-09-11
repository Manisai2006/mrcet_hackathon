// API Client Service with Timeout Protection
const API_BASE_URL = 'http://127.0.0.1:8000/api';
const DEFAULT_TIMEOUT_MS = 30000; // 30 seconds max timeout

const API = {
    // Session token helpers
    getToken() {
        return localStorage.getItem('study_buddy_token');
    },

    setToken(token) {
        localStorage.setItem('study_buddy_token', token);
    },

    removeToken() {
        localStorage.removeItem('study_buddy_token');
        localStorage.removeItem('study_buddy_user');
    },

    getUser() {
        const user = localStorage.getItem('study_buddy_user');
        return user ? JSON.parse(user) : null;
    },

    setUser(user) {
        localStorage.setItem('study_buddy_user', JSON.stringify(user));
    },

    // Universal HTTP Request Handler with AbortController Timeout
    async request(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        const token = this.getToken();

        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        // Setup AbortController timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), options.timeoutMs || DEFAULT_TIMEOUT_MS);

        const config = {
            ...options,
            headers,
            signal: controller.signal
        };

        try {
            const response = await fetch(url, config);
            clearTimeout(timeoutId);
            
            // Handle unauthenticated state
            if (response.status === 401 && !endpoint.includes('/auth/login')) {
                this.removeToken();
                if (!window.location.pathname.includes('login.html') && !window.location.pathname.includes('register.html')) {
                    window.location.href = 'login.html';
                }
                throw new Error('Session expired. Please log in again.');
            }

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || 'An unexpected error occurred.');
            }

            return data;
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                console.error(`API Timeout [${endpoint}]: Request exceeded ${options.timeoutMs || DEFAULT_TIMEOUT_MS}ms`);
                throw new Error('Request timed out. The server is taking longer than expected. Please try again.');
            }
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    },

    // Auth specific API methods
    async register(data) {
        return this.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async login(email, password) {
        const tokenData = await this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
        
        if (tokenData && tokenData.access_token) {
            this.setToken(tokenData.access_token);
            const user = await this.getMe();
            this.setUser(user);
        }
        return tokenData;
    },

    async getMe() {
        return this.request('/auth/me');
    },

    async updateProfile(profileData) {
        const updated = await this.request('/auth/profile', {
            method: 'PUT',
            body: JSON.stringify(profileData)
        });
        const user = this.getUser();
        if (user) {
            user.profile = updated;
            this.setUser(user);
        }
        return updated;
    },

    async logout() {
        try {
            await this.request('/auth/logout', { method: 'POST' });
        } catch (e) {
            // Ignore server logout errors
        } finally {
            this.removeToken();
            window.location.href = 'login.html';
        }
    }
};

// Global Toast Alert Notification Utility
function showToast(message, type = 'info') {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const bgClass = type === 'error' ? 'bg-danger' : type === 'success' ? 'bg-success' : 'bg-primary';
    toast.className = `custom-toast p-3 mb-2 shadow d-flex align-items-center justify-content-between text-white ${bgClass} bg-opacity-90`;
    toast.style.borderRadius = '12px';
    toast.style.minWidth = '280px';
    toast.innerHTML = `
        <div class="d-flex align-items-center gap-2">
            <i class="fa-solid ${type === 'error' ? 'fa-circle-exclamation' : type === 'success' ? 'fa-circle-check' : 'fa-circle-info'}"></i>
            <span>${message}</span>
        </div>
        <button type="button" class="btn-close btn-close-white ms-3" onclick="this.parentElement.remove()"></button>
    `;
    container.appendChild(toast);
    setTimeout(() => {
        if (toast.parentElement) toast.remove();
    }, 4000);
}
