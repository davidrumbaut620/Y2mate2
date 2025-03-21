/**
 * YouTube Video Downloader
 * Main JavaScript file handling UI interactions
 */
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements for URL Analysis
    const videoUrlInput = document.getElementById('videoUrl');
    const searchBtn = document.getElementById('searchBtn');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const errorMessage = document.getElementById('errorMessage');
    const videoInfo = document.getElementById('videoInfo');
    const videoThumbnail = document.getElementById('videoThumbnail');
    const videoTitle = document.getElementById('videoTitle');
    const videoDuration = document.getElementById('videoDuration');
    const formatsList = document.getElementById('formatsList');
    
    // DOM Elements for Video Search
    const searchQuery = document.getElementById('searchQuery');
    const videoSearchBtn = document.getElementById('videoSearchBtn');
    const searchResults = document.getElementById('searchResults');
    const resultsContainer = document.getElementById('resultsContainer');
    
    // Bootstrap Modal Elements
    const downloadModal = new bootstrap.Modal(document.getElementById('downloadModal'));
    const downloadProgress = document.getElementById('downloadProgress');
    const downloadStatus = document.getElementById('downloadStatus');

    /**
     * Shows an error message
     * @param {string} message - The error message to display
     */
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('d-none');
        setTimeout(() => {
            errorMessage.classList.add('d-none');
        }, 5000);
    }

    /**
     * Shows the loading indicator
     * @param {boolean} show - Whether to show or hide the loading indicator
     */
    function showLoading(show) {
        if (show) {
            loadingIndicator.classList.remove('d-none');
        } else {
            loadingIndicator.classList.add('d-none');
        }
    }

    /**
     * Reset the video info section
     */
    function resetVideoInfo() {
        videoInfo.classList.add('d-none');
        videoThumbnail.src = '';
        videoTitle.textContent = '';
        videoDuration.textContent = '';
        formatsList.innerHTML = '';
    }

    /**
     * Display video information and available formats
     * @param {Object} data - The video analysis data from Y2Mate API
     */
    function displayVideoInfo(data) {
        try {
            // Reset previous data
            resetVideoInfo();
            
            const videoData = data.result || data;
            
            if (!videoData) {
                showError('Invalid video data received');
                return;
            }
            
            // Set video details
            videoThumbnail.src = videoData.thumbnail || '';
            videoTitle.textContent = videoData.title || 'Unknown Title';
            
            // Format duration if available
            if (videoData.duration) {
                videoDuration.textContent = `Duration: ${y2mate.formatDuration(videoData.duration)}`;
            } else {
                videoDuration.textContent = '';
            }
            
            // Display available formats
            const formats = videoData.formats || [];
            if (formats.length === 0) {
                formatsList.innerHTML = '<tr><td colspan="4" class="text-center">No download options available</td></tr>';
            } else {
                // Sort formats by quality (highest first for video, then audio)
                const sortedFormats = [...formats].sort((a, b) => {
                    // First prioritize video formats
                    if (a.hasVideo && !b.hasVideo) return -1;
                    if (!a.hasVideo && b.hasVideo) return 1;
                    
                    // Then sort by quality
                    const aHeight = a.height || 0;
                    const bHeight = b.height || 0;
                    return bHeight - aHeight;
                });
                
                // Create format rows
                let formatsHtml = '';
                sortedFormats.forEach(format => {
                    const formatType = format.hasVideo ? 'video' : 'audio';
                    const formatLabel = format.hasVideo 
                        ? `${format.height}p` 
                        : 'Audio';
                    const formatDescription = format.hasVideo 
                        ? `${format.videoCodec || 'Video'} + ${format.audioCodec || 'Audio'}` 
                        : `${format.audioCodec || 'Audio only'}`;
                    const fileSize = y2mate.formatFileSize(format.fileSize);
                    
                    formatsHtml += `
                        <tr>
                            <td>
                                <span class="format-badge ${formatType === 'video' ? 'format-video' : 'format-audio'}">
                                    ${formatLabel}
                                </span>
                            </td>
                            <td>${format.extension || 'Unknown'}</td>
                            <td>${fileSize}</td>
                            <td>
                                <button class="btn btn-sm btn-success btn-download" 
                                        data-format-id="${format.formatId}" 
                                        data-format-name="${formatLabel} ${format.extension || ''}">
                                    <i class="fas fa-download"></i> Download
                                </button>
                            </td>
                        </tr>
                    `;
                });
                
                formatsList.innerHTML = formatsHtml;
                
                // Add event listeners to download buttons
                document.querySelectorAll('.btn-download').forEach(button => {
                    button.addEventListener('click', function() {
                        const formatId = this.getAttribute('data-format-id');
                        const formatName = this.getAttribute('data-format-name');
                        initiateDownload(formatId, formatName);
                    });
                });
            }
            
            // Show the video info section
            videoInfo.classList.remove('d-none');
            
        } catch (error) {
            console.error('Error displaying video info:', error);
            showError('Failed to display video information');
        }
    }

    /**
     * Analyze a YouTube video URL
     */
    async function analyzeVideo() {
        const url = videoUrlInput.value.trim();
        
        if (!url) {
            showError('Please enter a YouTube video URL');
            return;
        }
        
        // Basic URL validation
        if (!url.match(/^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/)) {
            showError('Please enter a valid YouTube URL');
            return;
        }
        
        try {
            resetVideoInfo();
            showLoading(true);
            errorMessage.classList.add('d-none');
            
            const data = await y2mate.analyzeVideo(url);
            showLoading(false);
            
            if (data.error) {
                showError(data.error);
                return;
            }
            
            displayVideoInfo(data);
            
        } catch (error) {
            showLoading(false);
            showError(error.message || 'Failed to analyze video');
            console.error('Error:', error);
        }
    }

    /**
     * Initiate the download process for a video format
     * @param {string} formatId - The format ID to download
     * @param {string} formatName - The display name of the format
     */
    async function initiateDownload(formatId, formatName) {
        const url = videoUrlInput.value.trim();
        
        try {
            // Show download modal
            downloadProgress.style.width = '10%';
            downloadStatus.textContent = `Preparing ${formatName} for download...`;
            downloadModal.show();
            
            // Update progress
            downloadProgress.style.width = '50%';
            downloadStatus.textContent = 'Processing download...';
            
            // Most reliable method: Direct form submission to server
            // Create a form and submit it directly
            const downloadForm = document.createElement('form');
            downloadForm.method = 'POST';
            downloadForm.action = '/api/download';
            
            // Create hidden inputs
            const urlInput = document.createElement('input');
            urlInput.type = 'hidden';
            urlInput.name = 'url';
            urlInput.value = url;
            
            const formatInput = document.createElement('input');
            formatInput.type = 'hidden';
            formatInput.name = 'format_id';
            formatInput.value = formatId;
            
            // Add inputs to form
            downloadForm.appendChild(urlInput);
            downloadForm.appendChild(formatInput);
            
            // Update progress
            downloadProgress.style.width = '80%';
            downloadStatus.textContent = 'Starting download...';
            
            // Add form to document and submit
            document.body.appendChild(downloadForm);
            downloadForm.submit();
            document.body.removeChild(downloadForm);
            
            // Complete the progress
            downloadProgress.style.width = '100%';
            downloadStatus.textContent = 'Download started!';
            
            // Close modal after a delay
            setTimeout(() => {
                downloadModal.hide();
                downloadProgress.style.width = '0%';
            }, 2000);
            
        } catch (error) {
            console.error('Download error:', error);
            downloadStatus.textContent = `Error: ${error.message || 'Failed to download video'}`;
            downloadProgress.style.width = '0%';
            
            // Keep the modal open so the user can see the error
        }
    }

    /**
     * Search for YouTube videos by query
     */
    async function searchYouTubeVideos() {
        const query = searchQuery.value.trim();
        
        if (!query) {
            showError('Please enter a search term');
            return;
        }
        
        try {
            showLoading(true);
            errorMessage.classList.add('d-none');
            searchResults.classList.add('d-none');
            resetVideoInfo();
            
            const data = await y2mate.searchVideos(query);
            showLoading(false);
            
            if (data.error) {
                showError(data.error);
                return;
            }
            
            displaySearchResults(data);
            
        } catch (error) {
            showLoading(false);
            showError(error.message || 'Failed to search videos');
            console.error('Search error:', error);
        }
    }
    
    /**
     * Display search results
     * @param {Object} data - The search results data
     */
    function displaySearchResults(data) {
        try {
            resultsContainer.innerHTML = '';
            
            const videos = data.result || [];
            if (!videos || videos.length === 0) {
                resultsContainer.innerHTML = '<div class="col-12 text-center">No videos found. Try a different search term.</div>';
                searchResults.classList.remove('d-none');
                return;
            }
            
            // Create video cards for each result
            videos.forEach(video => {
                const videoCard = document.createElement('div');
                videoCard.className = 'col-md-4 col-sm-6 mb-4';
                
                // Format duration if available
                const duration = video.duration ? y2mate.formatDuration(video.duration) : 'Unknown';
                
                videoCard.innerHTML = `
                    <div class="video-card">
                        <div class="video-card-thumbnail">
                            <img src="${video.thumbnail || ''}" alt="${video.title || 'Video thumbnail'}">
                            <span class="video-card-duration">${duration}</span>
                        </div>
                        <div class="video-card-body">
                            <h3 class="video-card-title">${video.title || 'Unknown Title'}</h3>
                            <p class="video-card-channel">${video.channel || ''}</p>
                            <div class="video-card-footer">
                                <button class="btn btn-sm btn-primary select-video-btn" data-video-url="${video.url}">
                                    <i class="fas fa-download"></i> Download Options
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                
                resultsContainer.appendChild(videoCard);
            });
            
            // Add event listeners to video selection buttons
            document.querySelectorAll('.select-video-btn').forEach(button => {
                button.addEventListener('click', function() {
                    const videoUrl = this.getAttribute('data-video-url');
                    if (videoUrl) {
                        videoUrlInput.value = videoUrl;
                        analyzeVideo();
                        // Scroll to video info section
                        window.scrollTo({
                            top: videoUrlInput.offsetTop - 100,
                            behavior: 'smooth'
                        });
                    }
                });
            });
            
            // Show the results section
            searchResults.classList.remove('d-none');
            
        } catch (error) {
            console.error('Error displaying search results:', error);
            showError('Failed to display search results');
        }
    }

    // Event Listeners for URL Analysis
    searchBtn.addEventListener('click', analyzeVideo);
    
    // Allow pressing Enter in the input field for URL
    videoUrlInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            analyzeVideo();
        }
    });
    
    // Event Listeners for Video Search
    videoSearchBtn.addEventListener('click', searchYouTubeVideos);
    
    // Allow pressing Enter in the search query field
    searchQuery.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchYouTubeVideos();
        }
    });
    
    // Check for YouTube URL in clipboard when focused
    videoUrlInput.addEventListener('focus', async function() {
        try {
            // Try to read from clipboard if it's empty
            if (!videoUrlInput.value && navigator.clipboard) {
                const clipboardText = await navigator.clipboard.readText();
                // Check if it's a YouTube URL
                if (clipboardText.match(/^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/)) {
                    videoUrlInput.value = clipboardText;
                }
            }
        } catch (error) {
            // Clipboard access might be denied, silently fail
            console.log('Clipboard access not available');
        }
    });
});
