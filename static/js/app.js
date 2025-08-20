// OCDify Web UI JavaScript

class OCDifyApp {
    constructor() {
        this.apiBaseUrl = 'http://127.0.0.1:5000/api';
        this.currentUser = null;
        this.spotifyAuth = null;
        this.config = null;
        this.init();
    }

    async init() {
        await this.loadConfig();
        this.checkAuthOnLoad();
        this.setupEventListeners();
        this.setupSpotifyAuth();
    }

    // Load configuration from backend
    async loadConfig() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/config`);
            if (response.ok) {
                this.config = await response.json();
                console.log('Configuration loaded successfully');
            } else {
                console.error('Failed to load configuration');
                // Fallback to defaults
                this.config = {
                    spotify_client_id: 'YOUR_SPOTIFY_CLIENT_ID',
                    spotify_redirect_uri: 'http://127.0.0.1:5000/callback'
                };
            }
        } catch (error) {
            console.error('Error loading configuration:', error);
            // Fallback to defaults
            this.config = {
                spotify_client_id: 'YOUR_SPOTIFY_CLIENT_ID',
                spotify_redirect_uri: 'http://127.0.0.1:5000/callback'
            };
        }
    }

    // Spotify OAuth Setup
    setupSpotifyAuth() {
        // Use configuration from backend
        this.spotifyClientId = this.config.spotify_client_id;
        this.redirectUri = this.config.spotify_redirect_uri;
        this.scopes = [
            'user-read-private',
            'user-read-email',
            'user-modify-playback-state',
            'user-read-currently-playing',
            'user-read-playback-state'
        ].join(' ');
    }

    // Event Listeners
    setupEventListeners() {
        // Auth
        document.getElementById('spotifyLoginBtn').addEventListener('click', () => this.loginWithSpotify());
        document.getElementById('logoutBtn').addEventListener('click', () => this.logout());

        // Monitoring
        document.getElementById('startMonitoring').addEventListener('click', () => this.startMonitoring());
        document.getElementById('stopMonitoring').addEventListener('click', () => this.stopMonitoring());

        // Categories
        document.getElementById('addCategoryBtn').addEventListener('click', () => this.showCategoryModal());
        document.getElementById('closeModal').addEventListener('click', () => this.hideCategoryModal());
        document.getElementById('cancelCategory').addEventListener('click', () => this.hideCategoryModal());
        document.getElementById('categoryForm').addEventListener('submit', (e) => this.saveCategoryForm(e));

        // Songs
        document.getElementById('searchBtn').addEventListener('click', () => this.searchSongs());
        document.getElementById('songSearch').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.searchSongs();
        });

        // Lyrics Scanner
        document.getElementById('scanLyricsBtn').addEventListener('click', () => this.scanLyrics());

        // Modal close on backdrop click
        document.getElementById('categoryModal').addEventListener('click', (e) => {
            if (e.target.id === 'categoryModal') this.hideCategoryModal();
        });
    }

    // Authentication
    checkAuthOnLoad() {
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get('code');
        
        if (code) {
            // Handle Spotify callback
            this.handleSpotifyCallback(code);
        } else {
            // Check if user is already logged in
            const userData = localStorage.getItem('ocdify_user');
            if (userData) {
                this.currentUser = JSON.parse(userData);
                this.showDashboard();
                this.loadDashboardData();
            }
        }
    }

    loginWithSpotify() {
        const authUrl = new URL('https://accounts.spotify.com/authorize');
        authUrl.searchParams.append('client_id', this.spotifyClientId);
        authUrl.searchParams.append('response_type', 'code');
        authUrl.searchParams.append('redirect_uri', this.redirectUri);
        authUrl.searchParams.append('scope', this.scopes);
        authUrl.searchParams.append('show_dialog', 'true');
        
        window.location.href = authUrl.toString();
    }

    async handleSpotifyCallback(code) {
        this.showLoading();
        
        try {
            // Exchange code for tokens via our backend
            const authResponse = await this.exchangeCodeForTokens(code);
            
            if (authResponse.success) {
                this.currentUser = authResponse.data;
                localStorage.setItem('ocdify_user', JSON.stringify(this.currentUser));
                this.showNotification('Successfully logged in!', 'success');
                this.showDashboard();
                this.loadDashboardData();
                
                // Clean up URL
                window.history.replaceState({}, document.title, window.location.pathname);
            } else {
                throw new Error(authResponse.error || 'Authentication failed');
            }
        } catch (error) {
            console.error('Auth error:', error);
            this.showNotification('Authentication failed. Please try again.', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async exchangeCodeForTokens(code) {
        // Use our secure backend endpoint to exchange the code
        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/spotify-token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ code: code })
            });

            const result = await response.json();
            
            if (result.success) {
                return {
                    success: true,
                    data: result.data
                };
            } else {
                throw new Error(result.error || 'Token exchange failed');
            }
        } catch (error) {
            console.error('Token exchange error:', error);
            return { success: false, error: error.message };
        }
    }

    logout() {
        this.currentUser = null;
        localStorage.removeItem('ocdify_user');
        this.showLogin();
        this.showNotification('Logged out successfully', 'success');
    }

    // UI Navigation
    showLogin() {
        document.getElementById('loginSection').style.display = 'block';
        document.getElementById('dashboard').style.display = 'none';
        document.getElementById('userInfo').style.display = 'none';
    }

    showDashboard() {
        document.getElementById('loginSection').style.display = 'none';
        document.getElementById('dashboard').style.display = 'block';
        document.getElementById('userInfo').style.display = 'flex';
        document.getElementById('userName').textContent = this.currentUser.display_name;
    }

    // API Calls
    async apiCall(endpoint, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-Spotify-User-ID': this.currentUser?.spotify_user_id
            }
        };

        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: { ...defaultOptions.headers, ...options.headers }
        };

        console.log(`API Call: ${mergedOptions.method || 'GET'} ${this.apiBaseUrl}${endpoint}`);
        console.log('Headers:', mergedOptions.headers);
        if (mergedOptions.body) {
            console.log('Body:', mergedOptions.body);
        }

        const response = await fetch(`${this.apiBaseUrl}${endpoint}`, mergedOptions);
        console.log('Response status:', response.status);
        
        const result = await response.json();
        console.log('Response data:', result);
        
        return result;
    }

    // Dashboard Data Loading
    async loadDashboardData() {
        try {
            await Promise.all([
                this.loadStats(),
                this.loadMonitoringStatus(),
                this.loadCategories(),
                this.loadContaminatedSongs()
            ]);
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.showNotification('Error loading dashboard data', 'error');
        }
    }

    async loadStats() {
        const response = await this.apiCall('/stats');
        if (response.success) {
            const stats = response.data;
            document.getElementById('totalSongs').textContent = stats.total_songs;
            document.getElementById('contaminatedSongs').textContent = stats.contaminated_songs;
            document.getElementById('cleanSongs').textContent = stats.clean_songs;
            document.getElementById('userCategories').textContent = stats.user_categories;
        }
    }

    async loadMonitoringStatus() {
        const response = await this.apiCall('/monitoring/status');
        if (response.success) {
            const status = response.data;
            const statusElement = document.getElementById('monitoringStatus');
            const dot = statusElement.querySelector('.status-dot');
            const text = statusElement.querySelector('span:last-child');
            
            if (status.is_running) {
                dot.className = 'status-dot online';
                text.textContent = 'Online';
            } else {
                dot.className = 'status-dot offline';
                text.textContent = 'Offline';
            }
        }
    }

    async loadCategories() {
        const response = await this.apiCall('/trigger-categories');
        if (response.success) {
            this.renderCategories(response.data);
        }
    }

    async loadContaminatedSongs() {
        const response = await this.apiCall('/songs/contaminated');
        if (response.success) {
            this.renderSongs(response.data);
        }
    }

    // Monitoring Controls
    async startMonitoring() {
        this.showLoading();
        try {
            const response = await this.apiCall('/monitoring/start', { method: 'POST' });
            if (response.success) {
                this.showNotification('Monitoring started successfully', 'success');
                this.loadMonitoringStatus();
            } else {
                this.showNotification('Failed to start monitoring', 'error');
            }
        } catch (error) {
            this.showNotification('Error starting monitoring', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async stopMonitoring() {
        this.showLoading();
        try {
            const response = await this.apiCall('/monitoring/stop', { method: 'POST' });
            if (response.success) {
                this.showNotification('Monitoring stopped successfully', 'success');
                this.loadMonitoringStatus();
            } else {
                this.showNotification('Failed to stop monitoring', 'error');
            }
        } catch (error) {
            this.showNotification('Error stopping monitoring', 'error');
        } finally {
            this.hideLoading();
        }
    }

    // Category Management
    showCategoryModal(category = null) {
        document.getElementById('categoryModal').style.display = 'flex';
        
        if (category) {
            document.getElementById('modalTitle').textContent = 'Edit Category';
            document.getElementById('categoryName').value = category.name;
            document.getElementById('categoryWords').value = category.words.join(', ');
            document.getElementById('categoryActive').checked = category.is_active;
            document.getElementById('categoryForm').dataset.categoryId = category.id;
        } else {
            document.getElementById('modalTitle').textContent = 'Add Category';
            document.getElementById('categoryForm').reset();
            delete document.getElementById('categoryForm').dataset.categoryId;
        }
    }

    hideCategoryModal() {
        document.getElementById('categoryModal').style.display = 'none';
    }

    async saveCategoryForm(e) {
        e.preventDefault();
        this.showLoading();

        try {
            console.log('Starting category save process...');
            
            const formData = new FormData(e.target);
            const categoryId = e.target.dataset.categoryId;
            
            console.log('Form data:', {
                name: formData.get('categoryName'),
                words: formData.get('categoryWords'),
                active: document.getElementById('categoryActive').checked,
                categoryId: categoryId
            });
            
            const words = formData.get('categoryWords').split(',').map(w => w.trim()).filter(w => w);
            
            const data = {
                name: formData.get('categoryName'),
                words: words,
                is_active: document.getElementById('categoryActive').checked
            };

            console.log('Request data:', data);

            const endpoint = categoryId ? `/trigger-categories/${categoryId}` : '/trigger-categories';
            const method = categoryId ? 'PUT' : 'POST';

            console.log(`Making ${method} request to ${endpoint}`);

            const response = await this.apiCall(endpoint, {
                method: method,
                body: JSON.stringify(data)
            });

            console.log('API response:', response);

            if (response.success) {
                this.showNotification(`Category ${categoryId ? 'updated' : 'created'} successfully`, 'success');
                this.hideCategoryModal();
                this.loadCategories();
            } else {
                console.error('API returned error:', response);
                this.showNotification('Failed to save category', 'error');
            }
        } catch (error) {
            console.error('Error in saveCategoryForm:', error);
            this.showNotification('Error saving category', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async deleteCategory(categoryId) {
        if (!confirm('Are you sure you want to delete this category?')) return;

        this.showLoading();
        try {
            const response = await this.apiCall(`/trigger-categories/${categoryId}`, {
                method: 'DELETE'
            });

            if (response.success) {
                this.showNotification('Category deleted successfully', 'success');
                this.loadCategories();
            } else {
                this.showNotification('Failed to delete category', 'error');
            }
        } catch (error) {
            this.showNotification('Error deleting category', 'error');
        } finally {
            this.hideLoading();
        }
    }

    // Song Search
    async searchSongs() {
        const query = document.getElementById('songSearch').value.trim();
        if (!query) {
            this.loadContaminatedSongs();
            return;
        }

        this.showLoading();
        try {
            const response = await this.apiCall(`/songs/search?q=${encodeURIComponent(query)}`);
            if (response.success) {
                this.renderSongs(response.data);
            }
        } catch (error) {
            this.showNotification('Error searching songs', 'error');
        } finally {
            this.hideLoading();
        }
    }

    // Lyrics Scanner
    async scanLyrics() {
        const lyrics = document.getElementById('lyricsInput').value.trim();
        if (!lyrics) {
            this.showNotification('Please enter lyrics to scan', 'warning');
            return;
        }

        this.showLoading();
        try {
            const response = await this.apiCall('/lyrics/scan', {
                method: 'POST',
                body: JSON.stringify({ lyrics: lyrics })
            });

            if (response.success) {
                this.renderScanResults(response.data);
            }
        } catch (error) {
            this.showNotification('Error scanning lyrics', 'error');
        } finally {
            this.hideLoading();
        }
    }

    // Rendering Methods
    renderCategories(categories) {
        const container = document.getElementById('categoriesList');
        
        if (categories.length === 0) {
            container.innerHTML = '<p>No trigger categories found. Add one to get started!</p>';
            return;
        }

        container.innerHTML = categories.map(category => `
            <div class="category-item">
                <div class="category-info">
                    <h4>${category.name} ${!category.is_active ? '(Inactive)' : ''}</h4>
                    <div class="category-words">${category.words.join(', ')}</div>
                </div>
                <div class="category-actions">
                    <button class="btn btn-secondary" onclick="app.showCategoryModal(${JSON.stringify(category).replace(/"/g, '&quot;')})">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                    <button class="btn btn-danger" onclick="app.deleteCategory(${category.id})">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
            </div>
        `).join('');
    }

    renderSongs(songs) {
        const container = document.getElementById('songsList');
        
        if (songs.length === 0) {
            container.innerHTML = '<p>No songs found.</p>';
            return;
        }

        container.innerHTML = songs.map(song => `
            <div class="song-item">
                <div class="song-info">
                    <h4>${song.title}</h4>
                    <div class="song-details">
                        ${song.artist} • ${song.album}
                        ${song.trigger_count ? `<span class="trigger-count">${song.trigger_count} triggers</span>` : ''}
                    </div>
                </div>
            </div>
        `).join('');
    }

    renderScanResults(scanData) {
        const container = document.getElementById('scanResults');
        
        if (scanData.has_triggers) {
            container.innerHTML = `
                <h4>Found ${scanData.trigger_count} trigger(s):</h4>
                ${scanData.triggers.map(trigger => `
                    <div class="scan-result-item">
                        Line ${trigger.line_number}: "${trigger.trigger_word}"
                    </div>
                `).join('')}
            `;
        } else {
            container.innerHTML = '<p style="color: var(--primary-color);">No triggers found in these lyrics!</p>';
        }
        
        container.style.display = 'block';
    }

    // Utility Methods
    showLoading() {
        document.getElementById('loadingOverlay').style.display = 'flex';
    }

    hideLoading() {
        document.getElementById('loadingOverlay').style.display = 'none';
    }

    showNotification(message, type = 'info') {
        const container = document.getElementById('notifications');
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        container.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

// Initialize the app when the page loads
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new OCDifyApp();
});