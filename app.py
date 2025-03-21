import os
import logging
import json
import requests
import subprocess
import re
from urllib.parse import urlparse, parse_qs
from flask import Flask, render_template, request, jsonify, send_file, Response, stream_with_context
from flask_cors import CORS
import io
import yt_dlp
import trafilatura

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "youtube-dl-secret-key")
CORS(app)

def extract_video_id(url):
    """Extract the YouTube video ID from a URL."""
    parsed_url = urlparse(url)
    
    if parsed_url.netloc == 'youtu.be':
        return parsed_url.path[1:]
    
    if parsed_url.netloc in ('www.youtube.com', 'youtube.com'):
        if parsed_url.path == '/watch':
            query = parse_qs(parsed_url.query)
            return query.get('v', [None])[0]
        elif parsed_url.path.startswith('/embed/'):
            return parsed_url.path.split('/')[2]
        elif parsed_url.path.startswith('/v/'):
            return parsed_url.path.split('/')[2]
    
    return None

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search_videos():
    """Search for YouTube videos and return direct CDN URLs using yt-dlp."""
    try:
        data = request.get_json()
        query = data.get('query')
        
        if not query:
            return jsonify({'error': 'No search query provided'}), 400
        
        # Set up yt-dlp options for searching YouTube
        search_opts = {
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'noplaylist': True,
            'extract_flat': True,
            'default_search': 'ytsearch5',  # Search for 5 videos on YouTube
        }
        
        search_query = f"ytsearch5:{query}"  # Format for searching 5 videos
        
        # Perform the search on YouTube
        try:
            with yt_dlp.YoutubeDL(search_opts) as ydl:
                search_results = ydl.extract_info(search_query, download=False)
                
                if not search_results or 'entries' not in search_results:
                    return jsonify({'error': 'No videos found for your search query'}), 404
                
                # We got search results, now get detailed info for each video
                entries = search_results.get('entries', [])
                
                if not entries:
                    return jsonify({'error': 'No videos found for your search query'}), 404
        except Exception as e:
            logger.exception(f"Error searching YouTube: {e}")
            return jsonify({'error': f'Error searching YouTube: {str(e)}'}), 500
        
        # Process search results
        formatted_results = []
        
        for entry in entries:
            if not entry or not entry.get('id'):
                continue
                
            video_id = entry.get('id')
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Get detailed info for each video including format options
            format_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'noplaylist': True,
                'youtube_include_dash_manifest': True,  # Include DASH formats
            }
            
            try:
                # Get detailed video info
                with yt_dlp.YoutubeDL(format_opts) as ydl:
                    info = ydl.extract_info(youtube_url, download=False)
                    
                    if not info:
                        continue  # Skip to next video if we can't get info
                    
                    # Get video details
                    title = info.get('title', 'Unknown Title')
                    author = info.get('uploader', 'Unknown Uploader')
                    duration = info.get('duration', 0)
                    
                    # Format duration
                    minutes, seconds = divmod(int(duration) if duration else 0, 60)
                    formatted_duration = f"{minutes}:{seconds:02d}"
                    
                    # Get thumbnail
                    thumbnail = info.get('thumbnail', f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg")
                    
                    # Get all available formats
                    formats = info.get('formats', [])
                    available_qualities = []
                    
                    # Define the quality levels we're interested in
                    quality_targets = {
                        '360p': {'height': 360, 'found': False},
                        '480p': {'height': 480, 'found': False},
                        '720p': {'height': 720, 'found': False},
                        '1080p': {'height': 1080, 'found': False},
                        '1440p': {'height': 1440, 'found': False},  # 2K
                        '2160p': {'height': 2160, 'found': False},  # 4K
                    }
                    
                    # Find the best format for each quality level
                    for fmt in formats:
                        # Only consider formats with both audio and video
                        if fmt.get('acodec') != 'none' and fmt.get('vcodec') != 'none':
                            height = fmt.get('height', 0)
                            
                            # Match to our target qualities
                            for quality, target in quality_targets.items():
                                if height == target['height'] and not target['found']:
                                    # We found this quality
                                    target['found'] = True
                                    filesize = fmt.get('filesize', 0)
                                    if filesize:
                                        filesize_mb = round(filesize / (1024 * 1024), 2)
                                        size_str = f"{filesize_mb} MB"
                                    else:
                                        size_str = "Unknown size"
                                        
                                    available_qualities.append({
                                        'quality': quality,
                                        'url': fmt.get('url'),
                                        'ext': fmt.get('ext', 'mp4'),
                                        'size': size_str,
                                        'format_id': fmt.get('format_id')
                                    })
                    
                    # If we don't have specific qualities, use the best available
                    if not available_qualities:
                        # Find the best quality format with both audio and video
                        best_format = None
                        best_height = 0
                        
                        for fmt in formats:
                            if fmt.get('acodec') != 'none' and fmt.get('vcodec') != 'none':
                                height = fmt.get('height', 0)
                                if height > best_height:
                                    best_height = height
                                    best_format = fmt
                        
                        if best_format:
                            quality_name = f"{best_height}p" if best_height else "Best"
                            filesize = best_format.get('filesize', 0)
                            if filesize:
                                filesize_mb = round(filesize / (1024 * 1024), 2)
                                size_str = f"{filesize_mb} MB"
                            else:
                                size_str = "Unknown size"
                                
                            available_qualities.append({
                                'quality': quality_name,
                                'url': best_format.get('url'),
                                'ext': best_format.get('ext', 'mp4'),
                                'size': size_str,
                                'format_id': best_format.get('format_id')
                            })
                    
                    # Get the best available quality for direct link
                    best_direct_url = None
                    if available_qualities:
                        # Sort by quality (highest first)
                        sorted_qualities = sorted(available_qualities, 
                                                 key=lambda q: int(q['quality'].replace('p', '')) if q['quality'].replace('p', '').isdigit() else 0, 
                                                 reverse=True)
                        best_direct_url = sorted_qualities[0]['url']
                        
                    # Make sure we have at least one quality option
                    if not best_direct_url and formats:
                        # Fallback to any format with a valid URL
                        for fmt in formats:
                            if fmt.get('url'):
                                best_direct_url = fmt.get('url')
                                if fmt.get('acodec') != 'none' and fmt.get('vcodec') != 'none':
                                    break  # Prefer formats with both audio and video
                    
                    # Add to results if we have a valid URL
                    if best_direct_url:
                        video_result = {
                            'id': video_id,
                            'title': title,
                            'thumbnail': thumbnail,
                            'duration': formatted_duration,
                            'channel': author,
                            'url': youtube_url,
                            'direct_url': best_direct_url,  # Best quality direct URL
                            'resolution': 'Multiple formats available',
                            'file_type': 'mp4',
                            'formats': available_qualities  # All available quality options
                        }
                        formatted_results.append(video_result)
                
            except Exception as e:
                logger.warning(f"Error getting detailed info for video {video_id}: {e}")
                # Skip this video on error
                continue
        
        # Return the results
        return jsonify({'result': formatted_results})
    
    except Exception as e:
        logger.exception("Error in search_videos endpoint")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_video():
    """Analyze a YouTube video and get direct CDN URL for the best quality using yt-dlp."""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        
        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        # Set up yt-dlp options
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'noplaylist': True,
            'youtube_include_dash_manifest': True,  # Include DASH formats
        }
        
        try:
            # Get video info using yt-dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return jsonify({'error': 'Failed to get video information'}), 500
                
                # Get video details
                title = info.get('title', 'Unknown Title')
                author = info.get('uploader', 'Unknown Uploader')
                duration = info.get('duration', 0)
                
                # Format duration
                minutes, seconds = divmod(int(duration) if duration else 0, 60)
                formatted_duration = f"{minutes}:{seconds:02d}"
                
                # Get thumbnail
                thumbnail = info.get('thumbnail', f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg")
                
                # Get all available formats
                formats = info.get('formats', [])
                available_qualities = []
                
                # Define the quality levels we're interested in
                quality_targets = {
                    '360p': {'height': 360, 'found': False},
                    '480p': {'height': 480, 'found': False},
                    '720p': {'height': 720, 'found': False},
                    '1080p': {'height': 1080, 'found': False},
                    '1440p': {'height': 1440, 'found': False},  # 2K
                    '2160p': {'height': 2160, 'found': False},  # 4K
                }
                
                # Find the best format for each quality level
                for fmt in formats:
                    # Only consider formats with both audio and video
                    if fmt.get('acodec') != 'none' and fmt.get('vcodec') != 'none':
                        height = fmt.get('height', 0)
                        
                        # Match to our target qualities
                        for quality, target in quality_targets.items():
                            if height == target['height'] and not target['found']:
                                # We found this quality
                                target['found'] = True
                                filesize = fmt.get('filesize', 0)
                                if filesize:
                                    filesize_mb = round(filesize / (1024 * 1024), 2)
                                    size_str = f"{filesize_mb} MB"
                                else:
                                    size_str = "Unknown size"
                                    
                                available_qualities.append({
                                    'quality': quality,
                                    'url': fmt.get('url'),
                                    'ext': fmt.get('ext', 'mp4'),
                                    'size': size_str,
                                    'format_id': fmt.get('format_id')
                                })
                
                # If we don't have specific qualities, use the best available
                if not available_qualities:
                    # Find the best quality format with both audio and video
                    best_format = None
                    best_height = 0
                    
                    for fmt in formats:
                        if fmt.get('acodec') != 'none' and fmt.get('vcodec') != 'none':
                            height = fmt.get('height', 0)
                            if height > best_height:
                                best_height = height
                                best_format = fmt
                    
                    if best_format:
                        quality_name = f"{best_height}p" if best_height else "Best"
                        filesize = best_format.get('filesize', 0)
                        if filesize:
                            filesize_mb = round(filesize / (1024 * 1024), 2)
                            size_str = f"{filesize_mb} MB"
                        else:
                            size_str = "Unknown size"
                            
                        available_qualities.append({
                            'quality': quality_name,
                            'url': best_format.get('url'),
                            'ext': best_format.get('ext', 'mp4'),
                            'size': size_str,
                            'format_id': best_format.get('format_id')
                        })
                
                # Get the best available quality for direct link
                best_direct_url = None
                if available_qualities:
                    # Sort by quality (highest first)
                    sorted_qualities = sorted(available_qualities, 
                                             key=lambda q: int(q['quality'].replace('p', '')) if q['quality'].replace('p', '').isdigit() else 0, 
                                             reverse=True)
                    best_direct_url = sorted_qualities[0]['url']
                    
                # Make sure we have at least one quality option
                if not best_direct_url and formats:
                    # Fallback to any format with a valid URL
                    for fmt in formats:
                        if fmt.get('url'):
                            best_direct_url = fmt.get('url')
                            if fmt.get('acodec') != 'none' and fmt.get('vcodec') != 'none':
                                break  # Prefer formats with both audio and video
                
                if not best_direct_url:
                    return jsonify({'error': 'No suitable stream found for this video'}), 404
                
                # Return the info including direct CDN URL
                result = {
                    "result": {
                        "id": video_id,
                        "title": title,
                        "author": author,
                        "thumbnail": thumbnail,
                        "duration": formatted_duration,
                        "resolution": "Multiple formats available",
                        "file_type": "mp4",
                        "direct_url": best_direct_url,
                        "formats": available_qualities  # All available quality options
                    }
                }
                
                return jsonify(result)
            
        except Exception as e:
            logger.exception(f"Error analyzing video with yt-dlp: {e}")
            return jsonify({'error': f'Error processing video: {str(e)}'}), 500
    
    except Exception as e:
        logger.exception("Error in analyze_video endpoint")
        return jsonify({'error': str(e)}), 500

# Fallback method using a direct download link
@app.route('/api/direct-url', methods=['GET'])
def get_direct_url():
    """Get direct CDN URL from a YouTube URL using yt-dlp."""
    try:
        youtube_url = request.args.get('url')
        
        if not youtube_url:
            return jsonify({'error': 'YouTube URL is required'}), 400
        
        # Extract video_id from URL
        video_id = extract_video_id(youtube_url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        # Set up yt-dlp options to get all formats
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,  # Don't download, just get info
            'noplaylist': True,
            'youtube_include_dash_manifest': True,  # Include DASH formats
        }
        
        try:
            # Get video info and URL using yt-dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                
                if not info:
                    return jsonify({'error': 'Failed to get video information'}), 500
                
                # Get video details
                title = info.get('title', 'Unknown Title')
                author = info.get('uploader', 'Unknown Uploader')
                duration = info.get('duration', 0)
                
                # Format duration
                minutes, seconds = divmod(int(duration) if duration else 0, 60)
                formatted_duration = f"{minutes}:{seconds:02d}"
                
                # Get thumbnail
                thumbnail = info.get('thumbnail', f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg")
                
                # Get all available formats
                formats = info.get('formats', [])
                available_qualities = []
                
                # Define the quality levels we're interested in
                quality_targets = {
                    '360p': {'height': 360, 'found': False},
                    '480p': {'height': 480, 'found': False},
                    '720p': {'height': 720, 'found': False},
                    '1080p': {'height': 1080, 'found': False},
                    '1440p': {'height': 1440, 'found': False},  # 2K
                    '2160p': {'height': 2160, 'found': False},  # 4K
                }
                
                # Find the best format for each quality level
                for fmt in formats:
                    # Only consider formats with both audio and video
                    if fmt.get('acodec') != 'none' and fmt.get('vcodec') != 'none':
                        height = fmt.get('height', 0)
                        
                        # Match to our target qualities
                        for quality, target in quality_targets.items():
                            if height == target['height'] and not target['found']:
                                # We found this quality
                                target['found'] = True
                                filesize = fmt.get('filesize', 0)
                                if filesize:
                                    filesize_mb = round(filesize / (1024 * 1024), 2)
                                    size_str = f"{filesize_mb} MB"
                                else:
                                    size_str = "Unknown size"
                                    
                                available_qualities.append({
                                    'quality': quality,
                                    'url': fmt.get('url'),
                                    'ext': fmt.get('ext', 'mp4'),
                                    'size': size_str,
                                    'format_id': fmt.get('format_id')
                                })
                
                # If we don't have specific qualities, use the best available
                if not available_qualities:
                    # Find the best quality format with both audio and video
                    best_format = None
                    best_height = 0
                    
                    for fmt in formats:
                        if fmt.get('acodec') != 'none' and fmt.get('vcodec') != 'none':
                            height = fmt.get('height', 0)
                            if height > best_height:
                                best_height = height
                                best_format = fmt
                    
                    if best_format:
                        quality_name = f"{best_height}p" if best_height else "Best"
                        filesize = best_format.get('filesize', 0)
                        if filesize:
                            filesize_mb = round(filesize / (1024 * 1024), 2)
                            size_str = f"{filesize_mb} MB"
                        else:
                            size_str = "Unknown size"
                            
                        available_qualities.append({
                            'quality': quality_name,
                            'url': best_format.get('url'),
                            'ext': best_format.get('ext', 'mp4'),
                            'size': size_str,
                            'format_id': best_format.get('format_id')
                        })
                
                # Get the best available quality for direct link
                best_direct_url = None
                if available_qualities:
                    # Sort by quality (highest first)
                    sorted_qualities = sorted(available_qualities, 
                                             key=lambda q: int(q['quality'].replace('p', '')) if q['quality'].replace('p', '').isdigit() else 0, 
                                             reverse=True)
                    best_direct_url = sorted_qualities[0]['url']
                    
                # Make sure we have at least one quality option
                if not best_direct_url and formats:
                    # Fallback to any format with a valid URL
                    for fmt in formats:
                        if fmt.get('url'):
                            best_direct_url = fmt.get('url')
                            if fmt.get('acodec') != 'none' and fmt.get('vcodec') != 'none':
                                break  # Prefer formats with both audio and video
                
                if not best_direct_url:
                    return jsonify({'error': 'No suitable stream found for this video'}), 404
                
                # Return the info including direct CDN URL
                return jsonify({
                    'result': {
                        'id': video_id,
                        'title': title,
                        'author': author,
                        'duration': formatted_duration,
                        'resolution': 'Multiple formats available',
                        'file_type': 'mp4',
                        'thumbnail': thumbnail,
                        'direct_url': best_direct_url,
                        'formats': available_qualities  # All available quality options
                    }
                })
                
        except Exception as e:
            logger.exception(f"Error getting direct URL with yt-dlp: {e}")
            return jsonify({'error': f'Error processing video: {str(e)}'}), 500
    
    except Exception as e:
        logger.exception("Error in get_direct_url endpoint")
        return jsonify({'error': str(e)}), 500
        
@app.route('/api/direct-download', methods=['GET'])
def direct_download():
    """Direct download using the provided URL with yt-dlp."""
    try:
        url = request.args.get('url')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Check if it's a direct URL or a YouTube URL
        is_youtube_url = extract_video_id(url) is not None
        
        # If it's already a direct CDN URL (not a YouTube URL), use it directly
        if not is_youtube_url and (url.startswith('http://') or url.startswith('https://')):
            # It's already a direct URL, use it as is
            download_url = url
            filename = 'video.mp4'
            content_type = 'video/mp4'
            
            # Initiate the download request
            response = requests.get(download_url, stream=True)
            
            if response.status_code != 200:
                logger.error(f"Direct download error: {response.status_code}")
                return jsonify({'error': 'Failed to download video'}), 500
            
            # Try to determine the content type
            content_type = response.headers.get('Content-Type', 'video/mp4')
            
            # Stream the file to the client
            return Response(
                response.iter_content(chunk_size=4096),
                content_type=content_type,
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
        
        # If it's a YouTube URL, get the direct URL using yt-dlp
        else:
            # Set up yt-dlp options
            ydl_opts = {
                'format': 'best',  # Get best quality with video+audio
                'quiet': True,
                'no_warnings': True,
            }
            
            try:
                # Get video info and URL
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    if not info:
                        return jsonify({'error': 'Failed to get video information'}), 500
                    
                    # Get direct CDN URL
                    direct_url = info.get('url')
                    
                    if not direct_url:
                        # If no direct URL, try to get it from formats
                        formats = info.get('formats', [])
                        if formats:
                            # Get the best format with both video and audio
                            for fmt in formats:
                                if fmt.get('acodec') != 'none' and fmt.get('vcodec') != 'none':
                                    direct_url = fmt.get('url')
                                    break
                    
                    if not direct_url:
                        return jsonify({'error': 'No suitable stream found for this video'}), 404
                    
                    # Get video details
                    title = info.get('title', 'video')
                    extension = info.get('ext', 'mp4')
                    filename = f"{title}.{extension}"
                    content_type = f"video/{extension}"
                    
                    # Initiate the download request
                    response = requests.get(direct_url, stream=True)
                    
                    if response.status_code != 200:
                        logger.error(f"Download error: {response.status_code}")
                        return jsonify({'error': 'Failed to download video'}), 500
                    
                    # Stream the response directly to the user
                    return Response(
                        response.iter_content(chunk_size=4096),
                        content_type=content_type,
                        headers={
                            'Content-Disposition': f'attachment; filename="{filename}"'
                        }
                    )
                
            except Exception as e:
                logger.exception(f"Error in direct download with yt-dlp: {e}")
                return jsonify({'error': f'Error downloading video: {str(e)}'}), 500
    
    except Exception as e:
        logger.exception("Error in direct_download endpoint")
        return jsonify({'error': str(e)}), 500

# Web Scraper functionality
@app.route('/api/extract-text', methods=['POST'])
def extract_website_text():
    """Extract the main text content from a website using Trafilatura."""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
            
        # Validate URL
        try:
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return jsonify({'error': 'Invalid URL format'}), 400
        except:
            return jsonify({'error': 'Invalid URL'}), 400
        
        # Fetch and extract text from the URL
        try:
            # Download the content
            downloaded = trafilatura.fetch_url(url)
            
            if not downloaded:
                return jsonify({'error': 'Failed to download content from URL'}), 500
                
            # Extract the text content
            text_content = trafilatura.extract(downloaded)
            
            if not text_content:
                return jsonify({'error': 'No text content found on the page'}), 404
                
            # Return the result
            return jsonify({
                'result': {
                    'url': url,
                    'text_content': text_content
                }
            })
            
        except Exception as e:
            logger.exception(f"Error extracting text from URL: {e}")
            return jsonify({'error': f'Error processing website: {str(e)}'}), 500
    
    except Exception as e:
        logger.exception("Error in extract_website_text endpoint")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
