/**
 * OppGrid API Client
 * Connects the frontend to the backend API
 */

class OppGridAPI {
    constructor() {
        this.baseURL = (typeof CONFIG !== 'undefined' && CONFIG.API_BASE_URL) 
            ? CONFIG.API_BASE_URL 
            : '/api/v1';

        // Check for auth cookies from Replit Auth (short-lived, set after login)
        this._processAuthCookies();

        // Token storage: canonical key is `access_token`.
        // Migrate legacy `token` (older builds) to `access_token` to avoid re-auth loops.
        const accessToken = localStorage.getItem('access_token');
        const legacyToken = localStorage.getItem('token');
        if (!accessToken && legacyToken) {
            localStorage.setItem('access_token', legacyToken);
            localStorage.removeItem('token');
            this.token = legacyToken;
        } else {
            // Keep memory and storage aligned; drop legacy key if it exists.
            if (legacyToken) localStorage.removeItem('token');
            this.token = accessToken;
        }
    }

    _processAuthCookies() {
        // Pick up auth data from short-lived cookies (set after Replit Auth login)
        const cookies = document.cookie.split(';').reduce((acc, c) => {
            const [key, val] = c.trim().split('=');
            if (key && val) acc[key] = val;
            return acc;
        }, {});

        if (cookies.auth_token) {
            localStorage.setItem('access_token', decodeURIComponent(cookies.auth_token));
            document.cookie = 'auth_token=; max-age=0; path=/';
        }
        if (cookies.auth_user) {
            try {
                const userJson = atob(decodeURIComponent(cookies.auth_user));
                localStorage.setItem('user', userJson);
            } catch (e) {
                console.error('Failed to decode user data:', e);
            }
            document.cookie = 'auth_user=; max-age=0; path=/';
        }
    }

    // Helper method to get headers
    getHeaders(includeAuth = true) {
        const headers = {
            'Content-Type': 'application/json',
        };

        if (includeAuth && this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        return headers;
    }

    // Helper method to handle responses
    async handleResponse(response) {
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
            const err = new Error(error.detail || `HTTP error! status: ${response.status}`);
            // Attach status for callers that want to branch on auth/permission errors.
            err.status = response.status;
            throw err;
        }
        return response.json();
    }

    // Authentication
    async register(email, password, name, bio = '') {
        const response = await fetch(`${this.baseURL}/auth/register`, {
            method: 'POST',
            headers: this.getHeaders(false),
            body: JSON.stringify({ email, password, name, bio })
        });
        return this.handleResponse(response);
    }

    async login(email, password) {
        const formData = new URLSearchParams();
        formData.append('username', email);  // OAuth2 uses 'username' field
        formData.append('password', password);

        const response = await fetch(`${this.baseURL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData
        });

        const data = await this.handleResponse(response);
        // If 2FA is enabled, backend will not return an access token yet.
        if (!data.requires_2fa && data.access_token) {
            this.token = data.access_token;
            localStorage.setItem('access_token', data.access_token);
        }
        return data;
    }

    async verifyTwoFactor(email, otp_code) {
        const response = await fetch(`${this.baseURL}/2fa/verify`, {
            method: 'POST',
            headers: this.getHeaders(false),
            body: JSON.stringify({ email, otp_code })
        });

        const data = await this.handleResponse(response);
        if (data.access_token) {
            this.token = data.access_token;
            localStorage.setItem('access_token', data.access_token);
        }
        return data;
    }

    logout() {
        this.token = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('token');
    }

    // Users
    async getCurrentUser() {
        const response = await fetch(`${this.baseURL}/users/me`, {
            headers: this.getHeaders()
        });
        return this.handleResponse(response);
    }

    async updateCurrentUser(userData) {
        const response = await fetch(`${this.baseURL}/users/me`, {
            method: 'PUT',
            headers: this.getHeaders(),
            body: JSON.stringify(userData)
        });
        return this.handleResponse(response);
    }

    async changePassword(currentPassword, newPassword) {
        const response = await fetch(`${this.baseURL}/users/me/change-password`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
        });
        return this.handleResponse(response);
    }

    async getNotificationPreferences() {
        const response = await fetch(`${this.baseURL}/users/me/preferences`, {
            headers: this.getHeaders()
        });
        return this.handleResponse(response);
    }

    async updateNotificationPreferences(prefs) {
        const response = await fetch(`${this.baseURL}/users/me/preferences`, {
            method: 'PUT',
            headers: this.getHeaders(),
            body: JSON.stringify(prefs)
        });
        return this.handleResponse(response);
    }

    async deleteCurrentUser() {
        const response = await fetch(`${this.baseURL}/users/me`, {
            method: 'DELETE',
            headers: this.getHeaders()
        });
        if (response.status === 200) return this.handleResponse(response);
        return this.handleResponse(response);
    }

    async getAIPreferences() {
        const response = await fetch(`${this.baseURL}/ai-preferences`, {
            headers: this.getHeaders()
        });
        return this.handleResponse(response);
    }

    async updateAIPreferences(prefs) {
        const response = await fetch(`${this.baseURL}/ai-preferences`, {
            method: 'PUT',
            headers: this.getHeaders(),
            body: JSON.stringify(prefs)
        });
        return this.handleResponse(response);
    }

    async saveOpenAIKey(apiKey) {
        const response = await fetch(`${this.baseURL}/ai-preferences/openai-key`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({ api_key: apiKey })
        });
        return this.handleResponse(response);
    }

    async deleteOpenAIKey() {
        const response = await fetch(`${this.baseURL}/ai-preferences/openai-key`, {
            method: 'DELETE',
            headers: this.getHeaders()
        });
        return this.handleResponse(response);
    }

    async saveClaudeKey(apiKey) {
        const response = await fetch(`${this.baseURL}/ai-preferences/claude-key`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({ api_key: apiKey })
        });
        return this.handleResponse(response);
    }

    async deleteClaudeKey() {
        const response = await fetch(`${this.baseURL}/ai-preferences/claude-key`, {
            method: 'DELETE',
            headers: this.getHeaders()
        });
        return this.handleResponse(response);
    }

    async get2FAStatus() {
        const response = await fetch(`${this.baseURL}/2fa/status`, {
            headers: this.getHeaders()
        });
        return this.handleResponse(response);
    }

    async setup2FA() {
        const response = await fetch(`${this.baseURL}/2fa/setup`, {
            method: 'POST',
            headers: this.getHeaders()
        });
        return this.handleResponse(response);
    }

    async enable2FA(code) {
        const response = await fetch(`${this.baseURL}/2fa/enable`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({ code })
        });
        return this.handleResponse(response);
    }

    async disable2FA(code) {
        const response = await fetch(`${this.baseURL}/2fa/disable`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({ code })
        });
        return this.handleResponse(response);
    }

    async getUser(userId) {
        const response = await fetch(`${this.baseURL}/users/${userId}`, {
            headers: this.getHeaders(false)
        });
        return this.handleResponse(response);
    }

    // Opportunities
    async createOpportunity(opportunityData) {
        const response = await fetch(`${this.baseURL}/opportunities/`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify(opportunityData)
        });
        return this.handleResponse(response);
    }

    async getOpportunities(params = {}) {
        const queryParams = new URLSearchParams(params).toString();
        const url = `${this.baseURL}/opportunities/${queryParams ? '?' + queryParams : ''}`;

        const response = await fetch(url, {
            headers: this.getHeaders(false)
        });
        return this.handleResponse(response);
    }

    async getOpportunity(opportunityId) {
        const response = await fetch(`${this.baseURL}/opportunities/${opportunityId}`, {
            headers: this.getHeaders(false)
        });
        return this.handleResponse(response);
    }

    async updateOpportunity(opportunityId, opportunityData) {
        const response = await fetch(`${this.baseURL}/opportunities/${opportunityId}`, {
            method: 'PUT',
            headers: this.getHeaders(),
            body: JSON.stringify(opportunityData)
        });
        return this.handleResponse(response);
    }

    async deleteOpportunity(opportunityId) {
        const response = await fetch(`${this.baseURL}/opportunities/${opportunityId}`, {
            method: 'DELETE',
            headers: this.getHeaders()
        });
        if (response.status === 204) {
            return { success: true };
        }
        return this.handleResponse(response);
    }

    async searchOpportunities(query, params = {}) {
        const queryParams = new URLSearchParams({ q: query, ...params }).toString();
        const response = await fetch(`${this.baseURL}/opportunities/search/?${queryParams}`, {
            headers: this.getHeaders(false)
        });
        return this.handleResponse(response);
    }

    // Validations
    async createValidation(opportunityId) {
        const response = await fetch(`${this.baseURL}/validations/`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({ opportunity_id: opportunityId })
        });
        return this.handleResponse(response);
    }

    async deleteValidation(validationId) {
        const response = await fetch(`${this.baseURL}/validations/${validationId}`, {
            method: 'DELETE',
            headers: this.getHeaders()
        });
        if (response.status === 204) {
            return { success: true };
        }
        return this.handleResponse(response);
    }

    async getOpportunityValidations(opportunityId) {
        const response = await fetch(`${this.baseURL}/validations/opportunity/${opportunityId}`, {
            headers: this.getHeaders(false)
        });
        return this.handleResponse(response);
    }

    // Comments
    async createComment(opportunityId, content) {
        const response = await fetch(`${this.baseURL}/comments/`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({ opportunity_id: opportunityId, content })
        });
        return this.handleResponse(response);
    }

    async getOpportunityComments(opportunityId) {
        const response = await fetch(`${this.baseURL}/comments/opportunity/${opportunityId}`, {
            headers: this.getHeaders(false)
        });
        return this.handleResponse(response);
    }

    async updateComment(commentId, content) {
        const response = await fetch(`${this.baseURL}/comments/${commentId}`, {
            method: 'PUT',
            headers: this.getHeaders(),
            body: JSON.stringify({ content })
        });
        return this.handleResponse(response);
    }

    async deleteComment(commentId) {
        const response = await fetch(`${this.baseURL}/comments/${commentId}`, {
            method: 'DELETE',
            headers: this.getHeaders()
        });
        if (response.status === 204) {
            return { success: true };
        }
        return this.handleResponse(response);
    }

    async likeComment(commentId) {
        const response = await fetch(`${this.baseURL}/comments/${commentId}/like`, {
            method: 'POST',
            headers: this.getHeaders()
        });
        return this.handleResponse(response);
    }

    // Analytics
    async checkDuplicate(title, description) {
        const response = await fetch(`${this.baseURL}/analytics/check-duplicate`, {
            method: 'POST',
            headers: this.getHeaders(false),
            body: JSON.stringify({ title, description })
        });
        return this.handleResponse(response);
    }

    async getFeasibilityAnalysis(opportunityId) {
        const response = await fetch(`${this.baseURL}/analytics/feasibility/${opportunityId}`, {
            headers: this.getHeaders(false)
        });
        return this.handleResponse(response);
    }

    async getTopFeasible(minScore = 50.0, limit = 20) {
        const queryParams = new URLSearchParams({ min_score: minScore, limit }).toString();
        const response = await fetch(`${this.baseURL}/analytics/top-feasible?${queryParams}`, {
            headers: this.getHeaders(false)
        });
        return this.handleResponse(response);
    }

    async getCompletionStats() {
        const response = await fetch(`${this.baseURL}/analytics/completion-stats`, {
            headers: this.getHeaders(false)
        });
        return this.handleResponse(response);
    }

    async getGeographicByScope(scope) {
        const queryParams = new URLSearchParams({ scope }).toString();
        const response = await fetch(`${this.baseURL}/analytics/geographic/by-scope?${queryParams}`, {
            headers: this.getHeaders(false)
        });
        return this.handleResponse(response);
    }

    async getGeographicByLocation(country, region = null, city = null) {
        const params = { country };
        if (region) params.region = region;
        if (city) params.city = city;
        const queryParams = new URLSearchParams(params).toString();
        const response = await fetch(`${this.baseURL}/analytics/geographic/by-location?${queryParams}`, {
            headers: this.getHeaders(false)
        });
        return this.handleResponse(response);
    }

    async getGeographicDistribution() {
        const response = await fetch(`${this.baseURL}/analytics/geographic/distribution`, {
            headers: this.getHeaders(false)
        });
        return this.handleResponse(response);
    }

    // Watchlist
    async addToWatchlist(opportunityId) {
        const response = await fetch(`${this.baseURL}/watchlist/`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({ opportunity_id: opportunityId })
        });
        return this.handleResponse(response);
    }

    async removeFromWatchlist(watchlistItemId) {
        const response = await fetch(`${this.baseURL}/watchlist/${watchlistItemId}`, {
            method: 'DELETE',
            headers: this.getHeaders()
        });
        if (response.status === 204) {
            return { success: true };
        }
        return this.handleResponse(response);
    }

    async removeFromWatchlistByOpportunity(opportunityId) {
        const response = await fetch(`${this.baseURL}/watchlist/opportunity/${opportunityId}`, {
            method: 'DELETE',
            headers: this.getHeaders()
        });
        if (response.status === 204) {
            return { success: true };
        }
        return this.handleResponse(response);
    }

    async getWatchlist() {
        const response = await fetch(`${this.baseURL}/watchlist/`, {
            headers: this.getHeaders()
        });
        return this.handleResponse(response);
    }

    async checkInWatchlist(opportunityId) {
        const response = await fetch(`${this.baseURL}/watchlist/check/${opportunityId}`, {
            headers: this.getHeaders()
        });
        return this.handleResponse(response);
    }

    // AI Chat
    async sendAIMessage(message, opportunityId, conversationHistory = [], category = null, bookmarkedInsights = []) {
        const response = await fetch(`${this.baseURL}/ai/chat`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({
                message,
                opportunity_id: opportunityId,
                conversation_history: conversationHistory,
                category: category,
                bookmarked_insights: bookmarkedInsights
            })
        });
        return this.handleResponse(response);
    }

    async getAISuggestions(opportunityId) {
        const response = await fetch(`${this.baseURL}/ai/suggestions/${opportunityId}`, {
            headers: this.getHeaders()
        });
        return this.handleResponse(response);
    }

    // Subscriptions & billing
    async createCheckoutSession(tier, success_url, cancel_url) {
        const response = await fetch(`${this.baseURL}/subscriptions/checkout`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({ tier, success_url, cancel_url })
        });
        return this.handleResponse(response);
    }

    async createPortalSession(return_url) {
        const response = await fetch(`${this.baseURL}/subscriptions/portal`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({ return_url })
        });
        return this.handleResponse(response);
    }

    async getMySubscription() {
        const response = await fetch(`${this.baseURL}/subscriptions/my-subscription`, {
            headers: this.getHeaders()
        });
        return this.handleResponse(response);
    }

    // Helper: Check if user is authenticated
    isAuthenticated() {
        return !!this.token;
    }
}

// Create a global instance
const api = new OppGridAPI();
