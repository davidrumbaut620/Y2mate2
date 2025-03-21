/**
 * Y2Mate API Client
 * This module manages the communication with the Y2Mate API through our backend proxy.
 */
class Y2MateClient {
    constructor() {
        this.apiBase = '/api';
    }

    /**
     * Searches for videos on YouTube through Y2Mate
     * @param {string} query - The search query
     * @returns {Promise} - Promise resolving to search results
     */
    async searchVideos(query) {
        try {
            const response = await fetch(`${this.apiBase}/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Search failed');
            }

            return await response.json();
        } catch (error) {
            console.error('Error searching videos:', error);
            throw error;
        }
    }

    /**
     * Analyzes a YouTube video URL to get available download options
     * @param {string} url - The YouTube video URL
     * @returns {Promise} - Promise resolving to the video analysis result
     */
    async analyzeVideo(url) {
        try {
            const response = await fetch(`${this.apiBase}/analyze`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to analyze video');
            }

            return await response.json();
        } catch (error) {
            console.error('Error analyzing video:', error);
            throw error;
        }
    }

    /**
     * Converts a YouTube video to prepare it for download
     * @param {string} url - The YouTube video URL
     * @param {string} formatId - The format ID to convert
     * @returns {Promise} - Promise resolving to the conversion result
     */
    async convertVideo(url, formatId) {
        try {
            const response = await fetch(`${this.apiBase}/convert`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url, format_id: formatId })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to convert video');
            }

            return await response.json();
        } catch (error) {
            console.error('Error converting video:', error);
            throw error;
        }
    }

    /**
     * Initiates the download of a converted video
     * @param {string} url - The direct download URL
     * @returns {string} - The URL to redirect to for download
     */
    getDownloadUrl(url) {
        return `${this.apiBase}/direct-download?url=${encodeURIComponent(url)}`;
    }

    /**
     * Helper function to format file size
     * @param {number} bytes - The size in bytes
     * @returns {string} - Formatted file size string
     */
    formatFileSize(bytes) {
        if (!bytes || bytes === 0) return 'Unknown';
        
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`;
    }

    /**
     * Helper function to format duration
     * @param {string|number} duration - Duration in seconds or time string
     * @returns {string} - Formatted duration string
     */
    formatDuration(duration) {
        if (!duration) return 'Unknown';
        
        // If it's already a formatted string (like "10:30")
        if (typeof duration === 'string' && duration.includes(':')) {
            return duration;
        }
        
        // Convert to number if it's a string
        const seconds = typeof duration === 'string' ? parseInt(duration, 10) : duration;
        
        if (isNaN(seconds)) return 'Unknown';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            return `${minutes}:${secs.toString().padStart(2, '0')}`;
        }
    }
}

// Create global instance
const y2mate = new Y2MateClient();
