// Document Service JavaScript Application
// Uses Alpine.js for reactive components

// Global utilities
window.DocumentApp = {
    // Show flash message
    showMessage(message, type = 'info', duration = 3000) {
        const container = document.querySelector('.container');
        if (!container) return;
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        container.insertBefore(alert, container.firstChild);
        
        // Auto-dismiss
        if (duration > 0) {
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.remove();
                }
            }, duration);
        }
    },
    
    // Get CSRF token
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    },
    
    // Loading overlay
    showLoading() {
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.id = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-spinner text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div class="mt-2">Loading...</div>
            </div>
        `;
        document.body.appendChild(overlay);
    },
    
    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.remove();
        }
    }
};

// Document Editor Component (for detail view)
function documentEditor() {
    return {
        content: '',
        originalContent: '',
        isDirty: false,

        init() {
            // Warn about unsaved changes on page unload
            window.addEventListener('beforeunload', (e) => {
                if (this.isDirty) {
                    e.preventDefault();
                    e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
                    return 'You have unsaved changes. Are you sure you want to leave?';
                }
            });
        },

        markDirty() {
            this.isDirty = (this.content !== this.originalContent);
        }
    };
}

// Document Card Component (for list view)
function documentCard() {
    return {
        deleting: false,
        
        async confirmDelete(documentTitle, deleteUrl) {
            if (confirm(`Are you sure you want to delete "${documentTitle}"?`)) {
                await this.deleteDocument(deleteUrl);
            }
        },
        
        async deleteDocument(deleteUrl) {
            this.deleting = true;
            
            try {
                const response = await fetch(deleteUrl, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': DocumentApp.getCSRFToken(),
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                if (response.ok) {
                    // Animate card removal
                    const card = this.$el;
                    card.style.transition = 'opacity 0.3s, transform 0.3s';
                    card.style.opacity = '0';
                    card.style.transform = 'scale(0.9)';
                    
                    setTimeout(() => {
                        card.remove();
                    }, 300);
                    
                    DocumentApp.showMessage('Document deleted successfully!', 'success');
                } else {
                    const errorData = await response.json();
                    DocumentApp.showMessage(
                        errorData.message || 'Failed to delete document. Please try again.',
                        'danger'
                    );
                }
            } catch (error) {
                console.error('Delete error:', error);
                DocumentApp.showMessage(
                    'Failed to delete document. Please check your connection.',
                    'danger'
                );
            } finally {
                this.deleting = false;
            }
        }
    };
}

// Search Box Component
function searchBox() {
    return {
        searchQuery: '',
        isSearching: false,
        resultCount: 0,
        searchTime: 0,
        
        init() {
            // Focus search input on page load if not on mobile
            if (!this.isMobile()) {
                this.$nextTick(() => {
                    const searchInput = this.$el.querySelector('#search-input');
                    if (searchInput) {
                        searchInput.focus();
                    }
                });
            }
            
            // Keyboard shortcuts
            document.addEventListener('keydown', (e) => {
                // Ctrl+K or Cmd+K to focus search
                if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                    e.preventDefault();
                    this.focusSearch();
                }
                
                // Escape to clear search
                if (e.key === 'Escape' && this.searchQuery) {
                    this.clearSearch();
                }
            });
        },
        
        focusSearch() {
            const searchInput = document.getElementById('search-input');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        },
        
        clearSearch() {
            this.searchQuery = '';
            
            // Trigger HTMX to reload normal document list
            const searchInput = document.getElementById('search-input');
            if (searchInput) {
                searchInput.dispatchEvent(new Event('input'));
            }
        },
        
        isMobile() {
            return window.innerWidth < 768;
        }
    };
}

// Document List Component
function documentList() {
    return {
        loading: false,
        searchQuery: '',
        
        init() {
            // Initialize any document list specific functionality
            this.setupInfiniteScroll();
        },
        
        setupInfiniteScroll() {
            // Future enhancement: infinite scroll for large document lists
            // For now, we use pagination
        }
    };
}

// Navigation Component
function navigationComponent() {
    return {
        userMenuOpen: false,
        
        toggleUserMenu() {
            this.userMenuOpen = !this.userMenuOpen;
        },
        
        closeUserMenu() {
            this.userMenuOpen = false;
        }
    };
}

// Form Enhancement Component
function formEnhancer() {
    return {
        submitting: false,
        
        async handleSubmit(event, successUrl) {
            if (this.submitting) {
                event.preventDefault();
                return;
            }
            
            this.submitting = true;
            
            // Let the form submit naturally, but show loading state
            setTimeout(() => {
                this.submitting = false;
            }, 2000); // Reset after 2 seconds as fallback
        }
    };
}

// Initialize HTMX event handlers
document.addEventListener('DOMContentLoaded', function() {
    // HTMX global configuration
    if (typeof htmx !== 'undefined') {
        // Show loading state for HTMX requests
        document.addEventListener('htmx:beforeRequest', function(event) {
            const target = event.target;
            const loadingText = target.getAttribute('data-loading-text');
            
            if (loadingText) {
                target.setAttribute('data-original-text', target.innerHTML);
                target.innerHTML = loadingText;
                target.disabled = true;
            }
        });
        
        // Hide loading state after HTMX requests
        document.addEventListener('htmx:afterRequest', function(event) {
            const target = event.target;
            const originalText = target.getAttribute('data-original-text');
            
            if (originalText) {
                target.innerHTML = originalText;
                target.disabled = false;
                target.removeAttribute('data-original-text');
            }
        });
        
        // Handle HTMX errors
        document.addEventListener('htmx:responseError', function(event) {
            DocumentApp.showMessage(
                'An error occurred. Please try again.',
                'danger'
            );
        });
    }
    
    // Initialize Bootstrap tooltips and popovers
    if (typeof bootstrap !== 'undefined') {
        // Initialize tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
        
        // Initialize popovers
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    }
    
    // Auto-focus first input on forms
    const firstInput = document.querySelector('form input:not([type="hidden"]):not([readonly]):not([disabled])');
    if (firstInput) {
        firstInput.focus();
    }
    
    // Add fade-in animation to main content
    const mainContent = document.querySelector('main');
    if (mainContent) {
        mainContent.classList.add('fade-in');
    }
});

// WebSocket Component for Document Collaboration
function documentWebSocket() {
    return {
        socket: null,
        connectionState: 'disconnected', // disconnected, connecting, connected, error
        activeUsers: [],
        typingUsers: [],
        reconnectAttempts: 0,
        maxReconnectAttempts: 5,
        reconnectInterval: 1000,
        pingInterval: null,
        documentId: '',

        init() {
            // Get document ID from the current URL or data attribute
            this.documentId = this.getDocumentId();
            if (this.documentId) {
                this.connect();
                
                // Setup ping interval
                this.pingInterval = setInterval(() => {
                    this.sendPing();
                }, 30000); // Ping every 30 seconds
                
                // Cleanup on page unload
                window.addEventListener('beforeunload', () => {
                    this.disconnect();
                });
            }
        },

        getDocumentId() {
            // Extract document ID from URL path like /documents/uuid/
            const path = window.location.pathname;
            const matches = path.match(/\/documents\/([0-9a-f-]+)\//);
            return matches ? matches[1] : null;
        },

        connect() {
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                return;
            }

            this.connectionState = 'connecting';
            
            // Determine WebSocket protocol and host
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            const wsUrl = `${protocol}//${host}/ws/documents/${this.documentId}/`;

            try {
                this.socket = new WebSocket(wsUrl);
                this.setupEventHandlers();
            } catch (error) {
                console.error('WebSocket connection error:', error);
                this.connectionState = 'error';
                this.scheduleReconnect();
            }
        },

        disconnect() {
            if (this.pingInterval) {
                clearInterval(this.pingInterval);
                this.pingInterval = null;
            }
            
            if (this.socket) {
                this.socket.close();
                this.socket = null;
            }
            
            this.connectionState = 'disconnected';
            this.activeUsers = [];
            this.typingUsers = [];
        },

        setupEventHandlers() {
            this.socket.onopen = () => {
                console.log('WebSocket connected');
                this.connectionState = 'connected';
                this.reconnectAttempts = 0;
            };

            this.socket.onclose = (event) => {
                console.log('WebSocket disconnected:', event.code, event.reason);
                this.connectionState = 'disconnected';
                this.activeUsers = [];
                this.typingUsers = [];
                
                if (event.code !== 1000) { // Not a normal closure
                    this.scheduleReconnect();
                }
            };

            this.socket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.connectionState = 'error';
            };

            this.socket.onmessage = (event) => {
                this.handleMessage(event.data);
            };
        },

        handleMessage(data) {
            try {
                const message = JSON.parse(data);
                
                switch (message.type) {
                    case 'pong':
                        // Handle ping response
                        break;
                        
                    case 'presence_update':
                        this.handlePresenceUpdate(message);
                        break;
                        
                    case 'user_typing':
                        this.handleUserTyping(message);
                        break;
                        
                    case 'cursor_position':
                        this.handleCursorPosition(message);
                        break;
                        
                    case 'error':
                        console.error('WebSocket server error:', message.message);
                        this.showNotification(message.message, 'danger');
                        break;
                        
                    default:
                        console.warn('Unknown message type:', message.type);
                }
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        },

        handlePresenceUpdate(message) {
            console.log('Presence update:', message);
            
            // Update active users list
            if (message.action === 'user_joined') {
                this.showNotification(`${message.username} joined the document`, 'info', 2000);
            } else if (message.action === 'user_left') {
                this.showNotification(`${message.username} left the document`, 'info', 2000);
            }
            
            // For now, we'll track users manually since the full presence system 
            // would require more complex Redis operations
            this.updateActiveUsersList(message);
        },

        updateActiveUsersList(message) {
            // Simple presence tracking - in production you'd get the full active user list
            if (message.action === 'user_joined') {
                if (!this.activeUsers.find(u => u.user_id === message.user_id)) {
                    this.activeUsers.push({
                        user_id: message.user_id,
                        username: message.username
                    });
                }
            } else if (message.action === 'user_left') {
                this.activeUsers = this.activeUsers.filter(u => u.user_id !== message.user_id);
            }
        },

        handleUserTyping(message) {
            const index = this.typingUsers.findIndex(u => u.user_id === message.user_id);
            
            if (message.is_typing) {
                if (index === -1) {
                    this.typingUsers.push({
                        user_id: message.user_id,
                        username: message.username
                    });
                }
            } else {
                if (index !== -1) {
                    this.typingUsers.splice(index, 1);
                }
            }
        },

        handleCursorPosition(message) {
            // Future enhancement: handle cursor position updates
            console.log('Cursor position update:', message);
        },

        sendMessage(type, data = {}) {
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                const message = { type, ...data };
                this.socket.send(JSON.stringify(message));
            } else {
                console.warn('WebSocket not connected, cannot send message:', type);
            }
        },

        sendPing() {
            this.sendMessage('ping', { timestamp: Date.now() });
        },

        sendTypingStatus(isTyping) {
            this.sendMessage('user_typing', { is_typing: isTyping });
        },

        sendCursorPosition(position) {
            this.sendMessage('cursor_position', { position });
        },

        scheduleReconnect() {
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                const delay = this.reconnectInterval * Math.pow(2, this.reconnectAttempts);
                console.log(`Scheduling reconnect in ${delay}ms (attempt ${this.reconnectAttempts + 1})`);
                
                setTimeout(() => {
                    this.reconnectAttempts++;
                    this.connect();
                }, delay);
            } else {
                console.error('Max reconnection attempts reached');
                this.connectionState = 'error';
            }
        },

        showNotification(message, type = 'info', duration = 3000) {
            // Use existing notification system
            if (window.DocumentApp && window.DocumentApp.showMessage) {
                window.DocumentApp.showMessage(message, type, duration);
            }
        },

        getConnectionStatusText() {
            switch (this.connectionState) {
                case 'connected':
                    return 'Connected';
                case 'connecting':
                    return 'Connecting...';
                case 'disconnected':
                    return 'Disconnected';
                case 'error':
                    return 'Connection Error';
                default:
                    return 'Unknown';
            }
        },

        getConnectionStatusClass() {
            switch (this.connectionState) {
                case 'connected':
                    return 'text-success';
                case 'connecting':
                    return 'text-warning';
                case 'disconnected':
                case 'error':
                    return 'text-danger';
                default:
                    return 'text-secondary';
            }
        },

        getActiveUsersText() {
            if (this.activeUsers.length === 0) {
                return 'You are the only one here';
            } else if (this.activeUsers.length === 1) {
                return `${this.activeUsers[0].username} is also here`;
            } else {
                return `${this.activeUsers.length} others are here`;
            }
        },

        getTypingUsersText() {
            if (this.typingUsers.length === 0) {
                return '';
            } else if (this.typingUsers.length === 1) {
                return `${this.typingUsers[0].username} is typing...`;
            } else {
                return `${this.typingUsers.length} people are typing...`;
            }
        }
    };
}

// Export components for use in templates
window.documentEditor = documentEditor;
window.documentCard = documentCard;
window.documentList = documentList;
window.searchBox = searchBox;
window.navigationComponent = navigationComponent;
window.formEnhancer = formEnhancer;
window.documentWebSocket = documentWebSocket;