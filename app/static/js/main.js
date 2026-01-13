// Main JavaScript for Expense Manager

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    if (typeof bootstrap !== 'undefined') {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Auto-dismiss success alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-success, .alert-info');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const closeBtn = alert.querySelector('.btn-close');
            if (closeBtn) {
                closeBtn.click();
            }
        }, 5000);
    });

    // Add loading state to forms
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('input[type="submit"], button[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                submitBtn.disabled = true;
                const originalText = submitBtn.textContent;
                submitBtn.innerHTML = '<span class="loading"></span> ' + originalText;
                
                // Re-enable after 10 seconds as fallback
                setTimeout(function() {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                }, 10000);
            }
        });
    });

    // Initialize live search for expenses
    initializeExpenseSearch();
    
    // Initialize budget progress animations
    initializeBudgetProgress();
    
    // Initialize category color previews
    initializeCategoryColorPreviews();
});

// Expense search functionality
function initializeExpenseSearch() {
    const searchInput = document.querySelector('input[name="search"]');
    if (!searchInput) return;

    let searchTimeout;
    const searchContainer = searchInput.parentElement;
    
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();
        
        if (query.length < 2) {
            hideSearchResults();
            return;
        }
        
        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 300);
    });
    
    // Hide search results when clicking outside
    document.addEventListener('click', function(e) {
        if (!searchContainer.contains(e.target)) {
            hideSearchResults();
        }
    });
}

function performSearch(query) {
    fetch(`/search_expenses?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            showSearchResults(data);
        })
        .catch(error => {
            console.error('Search error:', error);
        });
}

function showSearchResults(results) {
    hideSearchResults(); // Remove existing results
    
    if (results.length === 0) return;
    
    const searchInput = document.querySelector('input[name="search"]');
    const searchContainer = searchInput.parentElement;
    
    const resultsDiv = document.createElement('div');
    resultsDiv.className = 'search-results';
    
    results.forEach(result => {
        const item = document.createElement('div');
        item.className = 'search-result-item';
        item.innerHTML = `
            <div class="d-flex justify-content-between">
                <div>
                    <strong>${result.title}</strong><br>
                    <small class="text-muted">${result.category} • ${result.date}</small>
                </div>
                <strong>$${result.amount.toFixed(2)}</strong>
            </div>
        `;
        
        item.addEventListener('click', function() {
            window.location.href = `/expenses/edit/${result.id}`;
        });
        
        resultsDiv.appendChild(item);
    });
    
    searchContainer.style.position = 'relative';
    searchContainer.appendChild(resultsDiv);
}

function hideSearchResults() {
    const existingResults = document.querySelector('.search-results');
    if (existingResults) {
        existingResults.remove();
    }
}

// Budget progress animations
function initializeBudgetProgress() {
    const progressBars = document.querySelectorAll('.progress-bar');
    
    progressBars.forEach(bar => {
        const targetWidth = bar.style.width;
        bar.style.width = '0%';
        
        setTimeout(() => {
            bar.style.transition = 'width 1s ease-in-out';
            bar.style.width = targetWidth;
        }, 500);
    });
}

// Category color previews in forms
function initializeCategoryColorPreviews() {
    const colorSelect = document.querySelector('select[name="color"]');
    const iconSelect = document.querySelector('select[name="icon"]');
    
    if (colorSelect || iconSelect) {
        updateCategoryPreview();
        
        if (colorSelect) {
            colorSelect.addEventListener('change', updateCategoryPreview);
        }
        if (iconSelect) {
            iconSelect.addEventListener('change', updateCategoryPreview);
        }
    }
}

function updateCategoryPreview() {
    const colorSelect = document.querySelector('select[name="color"]');
    const iconSelect = document.querySelector('select[name="icon"]');
    
    if (!colorSelect || !iconSelect) return;
    
    const color = colorSelect.value;
    const icon = iconSelect.value;
    
    // Create or update preview
    let preview = document.querySelector('.category-preview');
    if (!preview) {
        preview = document.createElement('div');
        preview.className = 'category-preview mt-2';
        colorSelect.parentElement.appendChild(preview);
    }
    
    preview.innerHTML = `
        <span class="badge bg-${color}">
            <i class="${icon}"></i> Preview
        </span>
    `;
}

// Utility functions
function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2
    }).format(amount);
}

function showNotification(message, type = 'success') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'danger' ? 'exclamation-triangle' : 'info-circle'}"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto-dismiss after 4 seconds
    setTimeout(() => {
        if (alertDiv && alertDiv.parentNode) {
            const closeBtn = alertDiv.querySelector('.btn-close');
            if (closeBtn) {
                closeBtn.click();
            }
        }
    }, 4000);
}

// Confirmation dialogs for delete actions
function confirmDelete(message = 'Are you sure you want to delete this item?') {
    return confirm(message);
}

// File upload preview
function previewFile(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        const fileSize = (file.size / 1024 / 1024).toFixed(2); // MB
        
        if (fileSize > 16) {
            showNotification('File size must be less than 16MB', 'danger');
            input.value = '';
            return;
        }
        
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'application/pdf'];
        if (!allowedTypes.includes(file.type)) {
            showNotification('Please select a valid image or PDF file', 'danger');
            input.value = '';
            return;
        }
        
        // Show file info
        const fileInfo = document.createElement('div');
        fileInfo.className = 'mt-2 text-muted small';
        fileInfo.textContent = `Selected: ${file.name} (${fileSize} MB)`;
        
        // Remove existing file info
        const existingInfo = input.parentElement.querySelector('.file-info');
        if (existingInfo) {
            existingInfo.remove();
        }
        
        fileInfo.className += ' file-info';
        input.parentElement.appendChild(fileInfo);
    }
}

// Initialize file upload previews
document.addEventListener('change', function(e) {
    if (e.target.type === 'file') {
        previewFile(e.target);
    }
});

// Export functions for global use
window.ExpenseManager = {
    showNotification: showNotification,
    formatCurrency: formatCurrency,
    confirmDelete: confirmDelete
};