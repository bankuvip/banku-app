// Main JavaScript for ConnectApp

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize form handlers
    initializeFormHandlers();
    
    // Initialize notification handlers
    initializeNotificationHandlers();
    
    // Initialize real-time updates
    initializeRealTimeUpdates();
    
    // Initialize search functionality
    initializeSearch();
    
    // Initialize dark mode
    initializeDarkMode();
}

// Tooltip initialization
function initializeTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Form handlers
function initializeFormHandlers() {
    // Auto-submit forms on change for filters
    const filterForms = document.querySelectorAll('.filter-form');
    filterForms.forEach(form => {
        form.addEventListener('change', function() {
            this.submit();
        });
    });
    
    // Confirm delete actions
    const deleteButtons = document.querySelectorAll('[data-confirm-delete]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm-message') || 'Are you sure you want to delete this item?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
    
    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

// Notification handlers
function initializeNotificationHandlers() {
    // Mark notification as read when clicked
    const notificationItems = document.querySelectorAll('.notification-item');
    notificationItems.forEach(item => {
        item.addEventListener('click', function() {
            const notificationId = this.getAttribute('data-notification-id');
            if (notificationId) {
                markNotificationAsRead(notificationId);
            }
        });
    });
    
    // Mark all notifications as read
    const markAllReadBtn = document.getElementById('markAllReadBtn');
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', function() {
            markAllNotificationsAsRead();
        });
    }
}

// Real-time updates
function initializeRealTimeUpdates() {
    // Real-time features can be added here in the future
    // For now, we'll use polling or other methods
}

// Search functionality
function initializeSearch() {
    const searchInputs = document.querySelectorAll('.search-input');
    searchInputs.forEach(input => {
        let timeout;
        input.addEventListener('input', function() {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                performSearch(this.value);
            }, 300);
        });
    });
}

// Dark mode functionality
function initializeDarkMode() {
    // Check for saved theme preference or default to light mode
    const currentTheme = localStorage.getItem('theme') || 'light';
    
    // Set theme immediately to prevent flash
    document.documentElement.setAttribute('data-theme', currentTheme);
    setTheme(currentTheme);
    
    // Add event listener to dark mode toggle button
    const darkModeToggle = document.getElementById('darkModeToggle');
    console.log('Dark mode toggle button found:', darkModeToggle);
    
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            console.log('Dark mode toggle clicked');
            toggleDarkMode();
            return false;
        });
    } else {
        console.log('Dark mode toggle button not found');
    }
    
    // Also add event delegation as backup
    document.addEventListener('click', function(e) {
        if (e.target.closest('.dark-mode-toggle') || e.target.closest('#darkModeToggle')) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            console.log('Dark mode toggle clicked via delegation');
            toggleDarkMode();
            return false;
        }
    });
    
    // Add event listener to any element with data-theme-toggle attribute
    const themeToggles = document.querySelectorAll('[data-theme-toggle]');
    themeToggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            toggleDarkMode();
        });
    });
}

function setTheme(theme) {
    console.log('Setting theme to:', theme);
    
    // Ensure documentElement exists
    if (!document.documentElement) {
        console.error('documentElement not found');
        return;
    }
    
    if (theme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        if (document.documentElement.className !== undefined) {
            document.documentElement.className = 'dark-theme';
        }
        localStorage.setItem('theme', 'dark');
        console.log('Applied dark theme');
        updateDarkModeToggle(true);
    } else {
        document.documentElement.setAttribute('data-theme', 'light');
        if (document.documentElement.className !== undefined) {
            document.documentElement.className = 'light-theme';
        }
        localStorage.setItem('theme', 'light');
        console.log('Applied light theme');
        updateDarkModeToggle(false);
    }
    console.log('Final data-theme attribute:', document.documentElement.getAttribute('data-theme'));
    console.log('Final className:', document.documentElement.className);
    
    // Force a style recalculation
    if (document.body) {
        document.body.style.display = 'none';
        document.body.offsetHeight; // Trigger reflow
        document.body.style.display = '';
    }
    
    // Check if CSS is working
    setTimeout(() => {
        if (document.body) {
            const computedStyle = window.getComputedStyle(document.body);
            console.log('Body background color:', computedStyle.backgroundColor);
            console.log('Body color:', computedStyle.color);
            console.log('HTML data-theme:', document.documentElement.getAttribute('data-theme'));
        }
    }, 100);
}

function toggleDarkMode() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    console.log('Current theme:', currentTheme);
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    console.log('Switching to theme:', newTheme);
    setTheme(newTheme);
    console.log('Theme after switch:', document.documentElement.getAttribute('data-theme'));
}

function updateDarkModeToggle(isDark) {
    const darkModeToggle = document.querySelector('.dark-mode-toggle') || document.querySelector('#darkModeToggle');
    if (darkModeToggle) {
        const icon = darkModeToggle.querySelector('i') || document.querySelector('#darkModeIcon');
        if (icon) {
            if (isDark) {
                icon.className = 'fas fa-sun';
                if (darkModeToggle.title !== undefined) {
                    darkModeToggle.title = 'Switch to light mode';
                }
            } else {
                icon.className = 'fas fa-moon';
                if (darkModeToggle.title !== undefined) {
                    darkModeToggle.title = 'Switch to dark mode';
                }
            }
        } else {
            console.log('Dark mode icon not found');
        }
    } else {
        console.log('Dark mode toggle button not found');
    }
}

// API Helper Functions
async function apiRequest(url, options = {}) {
    // Get CSRF token from multiple sources
    let csrfToken = '';
    
    // Try to get from meta tag first
    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    if (csrfTokenMeta) {
        csrfToken = csrfTokenMeta.getAttribute('content');
        console.log('CSRF token from meta tag:', csrfToken ? 'Found' : 'Not found');
    }
    
    // Fallback: try to get from form if available
    if (!csrfToken) {
        const csrfInput = document.querySelector('input[name="csrf_token"]');
        if (csrfInput) {
            csrfToken = csrfInput.value;
            console.log('CSRF token from form input:', csrfToken ? 'Found' : 'Not found');
        }
    }
    
    // Final fallback: try to get from cookies (Flask-WTF might use this)
    if (!csrfToken) {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrf_token') {
                csrfToken = value;
                console.log('CSRF token from cookies:', csrfToken ? 'Found' : 'Not found');
                break;
            }
        }
    }
    
    console.log('Final CSRF token:', csrfToken ? 'Present' : 'Missing');
    
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    // Add CSRF token if available
    if (csrfToken) {
        defaultOptions.headers['X-CSRF-Token'] = csrfToken;
        console.log('Added CSRF token to headers');
    } else {
        console.warn('No CSRF token found - request may fail');
    }
    
    const mergedOptions = { ...defaultOptions, ...options };
    console.log('Request headers:', mergedOptions.headers);
    
    try {
        const response = await fetch(url, mergedOptions);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'An error occurred');
        }
        
        return data;
    } catch (error) {
        console.error('API Request Error:', error);
        showAlert('error', error.message);
        throw error;
    }
}

// Notification functions
async function markNotificationAsRead(notificationId) {
    try {
        // Get CSRF token
        let csrfToken = '';
        const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
        if (csrfTokenMeta) {
            csrfToken = csrfTokenMeta.getAttribute('content');
        }
        
        // Send as form data (Flask-WTF requirement)
        const formData = new FormData();
        if (csrfToken) {
            formData.append('csrf_token', csrfToken);
        }
        
        const response = await fetch(`/dashboard/notifications/${notificationId}/read`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'An unexpected error occurred');
        }
        
        // Update UI
        const notificationElement = document.querySelector(`[data-notification-id="${notificationId}"]`);
        if (notificationElement) {
            notificationElement.classList.remove('unread');
            notificationElement.classList.add('read');
        }
        
        updateNotificationCount();
        
        return data;
    } catch (error) {
        console.error('Error marking notification as read:', error);
        throw error;
    }
}

async function markAllNotificationsAsRead() {
    try {
        // Get CSRF token
        let csrfToken = '';
        const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
        if (csrfTokenMeta) {
            csrfToken = csrfTokenMeta.getAttribute('content');
        }
        
        // Send as form data (Flask-WTF requirement)
        const formData = new FormData();
        if (csrfToken) {
            formData.append('csrf_token', csrfToken);
        }
        
        const response = await fetch('/dashboard/notifications/mark-all-read', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'An unexpected error occurred');
        }
        
        // Update UI
        const notificationItems = document.querySelectorAll('.notification-item.unread');
        notificationItems.forEach(item => {
            item.classList.remove('unread');
            item.classList.add('read');
        });
        
        updateNotificationCount();
        
        return data;
    } catch (error) {
        console.error('Error marking all notifications as read:', error);
        throw error;
    }
}

function updateNotificationCount() {
    const unreadCount = document.querySelectorAll('.notification-item.unread').length;
    const badge = document.querySelector('.notification-badge');
    if (badge) {
        badge.textContent = unreadCount;
        badge.style.display = unreadCount > 0 ? 'inline' : 'none';
    }
}

function showNotification(data) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = 'alert alert-info alert-dismissible fade show';
    notification.innerHTML = `
        <strong>${data.title}</strong><br>
        ${data.message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert at top of notifications container
    const container = document.querySelector('.notifications-container');
    if (container) {
        container.insertBefore(notification, container.firstChild);
    }
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Deal management functions
async function updateDealStatus(dealId, status) {
    try {
        await apiRequest(`/deals/${dealId}/update-status`, {
            method: 'POST',
            body: JSON.stringify({ status: status })
        });
        
        // Update UI
        const dealElement = document.querySelector(`[data-deal-id="${dealId}"]`);
        if (dealElement) {
            const statusBadge = dealElement.querySelector('.status-badge');
            if (statusBadge) {
                statusBadge.textContent = status.replace('_', ' ').toUpperCase();
                statusBadge.className = `badge status-${status}`;
            }
        }
    } catch (error) {
        console.error('Error updating deal status:', error);
    }
}

// Chat functions
function addMessageToChat(data) {
    const chatContainer = document.querySelector('.chat-messages');
    if (chatContainer) {
        const messageElement = document.createElement('div');
        messageElement.className = 'message mb-2';
        messageElement.innerHTML = `
            <div class="d-flex justify-content-between">
                <strong>${data.sender_name}</strong>
                <small class="text-muted">${new Date(data.timestamp).toLocaleTimeString()}</small>
            </div>
            <div>${data.message}</div>
        `;
        
        chatContainer.appendChild(messageElement);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}

// Search functions
async function performSearch(query) {
    if (query.length < 2) return;
    
    try {
        const response = await apiRequest(`/banks/search?q=${encodeURIComponent(query)}`);
        displaySearchResults(response.items);
    } catch (error) {
        console.error('Search error:', error);
    }
}

function displaySearchResults(items) {
    const resultsContainer = document.querySelector('.search-results');
    if (!resultsContainer) return;
    
    if (items.length === 0) {
        resultsContainer.innerHTML = '<p class="text-muted">No results found</p>';
        return;
    }
    
    const resultsHTML = items.map(item => `
        <div class="search-result-item p-3 border rounded mb-2">
            <h6 class="mb-1">${item.title}</h6>
            <p class="text-muted small mb-1">${item.description}</p>
            <div class="d-flex justify-content-between align-items-center">
                <span class="badge bg-secondary">${item.type}</span>
                <div>
                    ${item.price ? `<span class="fw-bold">$${item.price}</span>` : ''}
                    <span class="text-muted small ms-2">by ${item.profile_name}</span>
                </div>
            </div>
        </div>
    `).join('');
    
    resultsContainer.innerHTML = resultsHTML;
}

// Utility functions
function showAlert(type, message) {
    const alertContainer = document.querySelector('.alert-container') || createAlertContainer();
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertContainer.appendChild(alert);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

function createAlertContainer() {
    const container = document.createElement('div');
    container.className = 'alert-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
    return container;
}

function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Loading states
function showLoading(element) {
    element.classList.add('loading');
    const spinner = document.createElement('div');
    spinner.className = 'spinner-border spinner-border-sm me-2';
    element.insertBefore(spinner, element.firstChild);
}

function hideLoading(element) {
    element.classList.remove('loading');
    const spinner = element.querySelector('.spinner-border');
    if (spinner) {
        spinner.remove();
    }
}

// Export functions for global use
window.ConnectApp = {
    apiRequest,
    showAlert,
    formatCurrency,
    formatDate,
    formatDateTime,
    showLoading,
    hideLoading,
    markNotificationAsRead,
    markAllNotificationsAsRead,
    updateDealStatus,
    performSearch,
    setTheme,
    toggleDarkMode
};

// Global functions for testing
window.toggleDarkMode = toggleDarkMode;
window.setTheme = setTheme;
