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

// Document List Component
function documentList() {
    return {
        loading: false,
        searchQuery: '',
        
        init() {
            // Initialize search functionality
            this.initSearch();
        },
        
        initSearch() {
            // Debounced search
            let searchTimeout;
            this.$watch('searchQuery', (value) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.performSearch(value);
                }, 300);
            });
        },
        
        async performSearch(query) {
            // This would be implemented if we add search functionality
            console.log('Searching for:', query);
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

// Export components for use in templates
window.documentEditor = documentEditor;
window.documentCard = documentCard;
window.documentList = documentList;
window.navigationComponent = navigationComponent;
window.formEnhancer = formEnhancer;