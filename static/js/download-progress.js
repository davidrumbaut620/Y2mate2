/**
 * YouTube Video Downloader - Download Progress Animation
 * Handles the sleek download progress animation
 */
class DownloadProgressAnimation {
    constructor() {
        // DOM Elements
        this.progressContainer = document.getElementById('download-progress-container');
        this.progressCirclePath = document.getElementById('progress-circle-path');
        this.progressPercent = document.getElementById('progress-percent');
        this.progressStatus = document.getElementById('progress-status');
        this.downloadTitle = document.getElementById('download-title');
        this.completeIcon = document.getElementById('download-complete-icon');
        this.cancelBtn = document.getElementById('cancel-download-btn');
        this.continueBtn = document.getElementById('continue-download-btn');
        
        // Circle properties
        this.radius = parseInt(this.progressCirclePath.getAttribute('r'));
        this.circumference = 2 * Math.PI * this.radius;
        
        // Initial setup
        this.progressCirclePath.style.strokeDasharray = `${this.circumference} ${this.circumference}`;
        this.progressCirclePath.style.strokeDashoffset = this.circumference;
        
        // Fix the circle stroke to match viewBox size exactly
        this.progressCirclePath.style.transformOrigin = 'center';
        this.progressCirclePath.setAttribute('stroke-dasharray', this.circumference);
        
        // Progress simulation properties
        this.currentProgress = 0;
        this.targetProgress = 0;
        this.animationSpeed = 0.5; // Speed of progress animation
        this.progressInterval = null;
        this.downloadStartTime = null;
        this.downloadTimeout = null;
        
        // Event listeners
        this.cancelBtn.addEventListener('click', () => this.hide());
        this.continueBtn.addEventListener('click', () => this.hide());
        
        // Simulated download stages and messages
        this.downloadStages = [
            { progress: 10, message: "Connecting to YouTube servers..." },
            { progress: 20, message: "Analyzing video streams..." },
            { progress: 30, message: "Extracting video information..." },
            { progress: 40, message: "Selecting best quality..." },
            { progress: 50, message: "Requesting direct CDN URL..." },
            { progress: 60, message: "Establishing secure connection..." },
            { progress: 70, message: "Starting download stream..." },
            { progress: 80, message: "Optimizing download speed..." },
            { progress: 90, message: "Finalizing download preparation..." },
            { progress: 100, message: "Download ready! Your file will begin downloading shortly." },
        ];
    }
    
    /**
     * Set the circle progress visually
     * @param {number} percent - Progress percentage (0-100)
     */
    setProgress(percent) {
        const progress = percent / 100;
        const dashoffset = this.circumference * (1 - progress);
        this.progressCirclePath.style.strokeDashoffset = dashoffset;
        this.progressPercent.textContent = `${Math.round(percent)}%`;
    }
    
    /**
     * Animate progress towards target
     */
    animateProgress() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }
        
        this.progressInterval = setInterval(() => {
            if (this.currentProgress < this.targetProgress) {
                this.currentProgress += this.animationSpeed;
                this.setProgress(this.currentProgress);
                
                // Find appropriate message for current progress
                for (let i = 0; i < this.downloadStages.length; i++) {
                    const stage = this.downloadStages[i];
                    if (this.currentProgress < stage.progress) {
                        this.progressStatus.textContent = stage.message;
                        break;
                    }
                }
                
                // If we've reached target, stop animation
                if (this.currentProgress >= this.targetProgress) {
                    clearInterval(this.progressInterval);
                    
                    // If we've reached 100%, show complete state
                    if (this.targetProgress >= 100) {
                        this.showCompleteState();
                    }
                }
            }
        }, 16); // ~60fps
    }
    
    /**
     * Show the download complete state
     */
    showCompleteState() {
        // Hide the progress percentage and show the checkmark
        this.progressPercent.style.display = 'none';
        this.completeIcon.style.display = 'block';
        
        // Update status message and show the continue button
        this.progressStatus.textContent = 'Download complete! Your file should begin downloading automatically.';
        this.continueBtn.classList.remove('d-none');
        this.cancelBtn.textContent = 'Close';
        
        // Add success style to progress circle
        this.progressCirclePath.style.stroke = '#4CAF50';
    }
    
    /**
     * Reset the animation state
     */
    reset() {
        // Reset progress and animation
        this.currentProgress = 0;
        this.targetProgress = 0;
        clearInterval(this.progressInterval);
        if (this.downloadTimeout) {
            clearTimeout(this.downloadTimeout);
        }
        
        // Reset UI elements
        this.setProgress(0);
        this.progressPercent.style.display = 'block';
        this.completeIcon.style.display = 'none';
        this.progressStatus.textContent = 'Initializing download...';
        this.progressCirclePath.style.stroke = '#FF0000';
        this.continueBtn.classList.add('d-none');
        this.cancelBtn.textContent = 'Cancel';
    }
    
    /**
     * Show the download progress animation
     * @param {Object} options - Configuration options
     * @param {string} options.title - Title to display
     * @param {Function} options.onComplete - Callback when download completes
     */
    show(options = {}) {
        this.reset();
        
        // Set title if provided
        if (options.title) {
            this.downloadTitle.textContent = options.title;
        }
        
        // Show the container
        this.progressContainer.classList.remove('d-none');
        
        // Start download simulation
        this.simulateDownloadProgress(options.onComplete);
        
        return this;
    }
    
    /**
     * Hide the download progress animation
     */
    hide() {
        this.progressContainer.classList.add('d-none');
        this.reset();
    }
    
    /**
     * Simulate realistic download progress
     * @param {Function} onComplete - Callback when download completes
     */
    simulateDownloadProgress(onComplete) {
        this.downloadStartTime = Date.now();
        
        // Simulate the stages of download progress
        this.downloadStages.forEach((stage, index) => {
            setTimeout(() => {
                this.targetProgress = stage.progress;
                this.animateProgress();
                
                // If this is the last stage (100%), call onComplete
                if (stage.progress === 100 && typeof onComplete === 'function') {
                    this.downloadTimeout = setTimeout(onComplete, 1000);
                }
            }, (index + 1) * 700); // Increase the timeout based on index for realistic progress
        });
    }
}

// Create global instance when document is ready
let downloadProgress;
document.addEventListener('DOMContentLoaded', function() {
    downloadProgress = new DownloadProgressAnimation();
});