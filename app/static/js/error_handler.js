class ErrorHandler {
    constructor() {
        this.errorContainer = document.getElementById('error-container') || this._createErrorContainer();
        this.errorMessageElement = document.getElementById('error-message');
        this.errorDetailElement = document.getElementById('error-detail');
        this.closeButton = document.getElementById('close-error');
        
        if (this.closeButton) {
            this.closeButton.addEventListener('click', () => this.hideError());
        }
    }
    
    showError(message, details = null, type = 'error') {
        this.errorMessageElement.textContent = message;
        
        if (details) {
            this.errorDetailElement.textContent = details;
            this.errorDetailElement.style.display = 'block';
        } else {
            this.errorDetailElement.style.display = 'none';
        }
        
        // Set appropriate styling based on error type
        this.errorContainer.className = `error-container ${type}`;
        this.errorContainer.style.display = 'block';
        
        // Automatically hide non-critical errors after a delay
        if (type !== 'error') {
            setTimeout(() => this.hideError(), 5000);
        }
    }
    
    showApiError(response) {
        response.json().then(data => {
            let message = data.message || 'An error occurred';
            let details = data.details || JSON.stringify(data);
            this.showError(message, details, 'error');
        }).catch(() => {
            this.showError(`${response.status}: ${response.statusText}`);
        });
    }
    
    showWarning(message, details = null) {
        this.showError(message, details, 'warning');
    }
    
    showInfo(message) {
        this.showError(message, null, 'info');
    }
    
    hideError() {
        this.errorContainer.style.display = 'none';
    }
    
    _createErrorContainer() {
        const container = document.createElement('div');
        container.id = 'error-container';
        container.className = 'error-container';
        container.style.display = 'none';
        
        const message = document.createElement('div');
        message.id = 'error-message';
        container.appendChild(message);
        
        const detail = document.createElement('div');
        detail.id = 'error-detail';
        detail.style.display = 'none';
        container.appendChild(detail);
        
        const close = document.createElement('button');
        close.id = 'close-error';
        close.textContent = '×';
        close.className = 'close-button';
        container.appendChild(close);
        
        document.body.appendChild(container);
        
        return container;
    }
}

// Export for use in other modules
window.ErrorHandler = ErrorHandler;
