class ProgressiveVideoPlayer {
    constructor(videoElementId) {
        this.videoElement = document.getElementById(videoElementId);
        this.mediaSource = new MediaSource();
        this.sourceBuffer = null;
        this.chunks = [];
        this.isLoading = false;
    }
    
    init() {
        this.videoElement.src = URL.createObjectURL(this.mediaSource);
        
        this.mediaSource.addEventListener('sourceopen', () => {
            this.sourceBuffer = this.mediaSource.addSourceBuffer('video/mp4; codecs="avc1.42E01E, mp4a.40.2"');
            this.sourceBuffer.addEventListener('updateend', () => {
                this._appendNextChunk();
            });
        });
        
        return this;
    }
    
    loadVideo(videoId) {
        this.isLoading = true;
        this._fetchVideoChunks(videoId);
    }
    
    _fetchVideoChunks(videoId, offset = 0, chunkSize = 1024 * 1024) {
        fetch(`/api/video/${videoId}/chunk?offset=${offset}&size=${chunkSize}`)
            .then(response => response.arrayBuffer())
            .then(data => {
                if (data.byteLength > 0) {
                    this.chunks.push(data);
                    if (this.sourceBuffer && !this.sourceBuffer.updating) {
                        this._appendNextChunk();
                    }
                    
                    // Continue fetching if more chunks available
                    this._fetchVideoChunks(videoId, offset + chunkSize, chunkSize);
                } else {
                    this.isLoading = false;
                    if (this.mediaSource.readyState === 'open') {
                        this.mediaSource.endOfStream();
                    }
                }
            })
            .catch(error => {
                console.error('Error loading video chunk:', error);
                this.isLoading = false;
            });
    }
    
    _appendNextChunk() {
        if (this.chunks.length > 0 && !this.sourceBuffer.updating) {
            const chunk = this.chunks.shift();
            this.sourceBuffer.appendBuffer(chunk);
        }
    }
}

// Export for use in other modules
window.ProgressiveVideoPlayer = ProgressiveVideoPlayer;
