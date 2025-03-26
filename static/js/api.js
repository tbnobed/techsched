// Utility functions for API calls with CSRF token handling
function getCSRFToken() {
    // Get CSRF token from meta tag
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

async function fetchWithCSRF(url, options = {}) {
    // Add CSRF token to headers
    const headers = {
        'X-CSRF-Token': getCSRFToken(),
        ...options.headers
    };

    try {
        const response = await fetch(url, {
            ...options,
            headers,
            credentials: 'same-origin' // Include cookies in request
        });

        if (!response.ok) {
            if (response.status === 401) {
                // Redirect to login page if unauthorized
                window.location.href = '/login';
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// Example API call functions
async function getActiveUsers() {
    return await fetchWithCSRF('/api/active_users');
}

// Export functions for use in other files
window.api = {
    getActiveUsers,
    fetchWithCSRF
};
