class AutoManimSocket {
    constructor(taskId) {
        this.taskId = taskId;
        this.socket = null;
        this.callbacks = {
            progress: () => {},
            complete: () => {},
            error: () => {}
        };
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/task/${this.taskId}`;
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            console.log('WebSocket connection established');
        };
        
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            switch (data.type) {
                case 'progress':
                    this.callbacks.progress(data.progress, data.message);
                    break;
                case 'complete':
                    this.callbacks.complete(data.result);
                    break;
                case 'error':
                    this.callbacks.error(data.error);
                    break;
            }
        };
        
        this.socket.onclose = () => {
            console.log('WebSocket connection closed');
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.callbacks.error('WebSocket connection error');
        };
    }
    
    onProgress(callback) {
        this.callbacks.progress = callback;
        return this;
    }
    
    onComplete(callback) {
        this.callbacks.complete = callback;
        return this;
    }
    
    onError(callback) {
        this.callbacks.error = callback;
        return this;
    }
    
    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
    }
}

// Export for use in other modules
window.AutoManimSocket = AutoManimSocket;
