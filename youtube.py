import re
import discord
import yt_dlp
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Regex to check if a string is a valid YouTube URL
YOUTUBE_URL_REGEX = re.compile(
    r'(https?://)?(www\.)?'
    r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
    r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

# --- yt-dlp Configuration ---
YDL_OPTS = {
    'format': 'bestaudio/best',     # Select best quality audio available
    'quiet': True,
    'noplaylist': False,
    'extract_flat': 'in_playlist',  # Fast extraction for playlists
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

# --- FFmpeg Configuration ---
# 1. reconnect flags: Fix choppiness/network dropouts
# 2. -ac 2: Force Stereo (2 channels)
# 3. -ar 48000: Force 48kHz sample rate (Discord Native). Prevents bad resampling artifacts.
FFMPEG_OPTS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -reconnect_on_network_error 1',
    'options': '-vn -ac 2 -ar 48000'
}

def is_youtube_url(url: str) -> bool:
    """Checks if the given string is a valid YouTube URL."""
    return YOUTUBE_URL_REGEX.match(url) is not None

def get_youtube_info(url: str) -> Optional[List[Dict]]:
    """
    Retrieves video metadata using 'flat' extraction for playlists.
    Returns dictionaries containing title and valid webpage URL.
    """
    with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
        try:
            logger.info(f"Extracting info for URL: {url}")
            info = ydl.extract_info(url, download=False)
            
            if not info:
                logger.warning(f"yt-dlp returned no info for {url}")
                return None

            if 'entries' in info:
                # Playlist: entries are flat (partial info)
                entries = []
                for entry in info['entries']:
                    if entry:
                        video_url = entry.get('url')
                        # Ensure we have a valid URL 
                        if video_url and not video_url.startswith('http'):
                            video_url = f"https://www.youtube.com/watch?v={video_url}"
                        
                        entries.append({
                            'title': entry.get('title', 'Unknown'),
                            'url': video_url,
                            'duration': entry.get('duration')
                        })
                logger.info(f"Successfully extracted {len(entries)} videos from playlist.")
                return entries
            else:
                # Single video
                return [info]
            
        except Exception as e:
            logger.error(f"Error in get_youtube_info: {e}", exc_info=True)
            return None

def get_stream_url(video_url: str) -> Optional[str]:
    """
    Resolves the specific audio stream URL for a single video just before playback.
    """
    stream_opts = dict(YDL_OPTS)
    stream_opts['extract_flat'] = False
    
    with yt_dlp.YoutubeDL(stream_opts) as ydl:
        try:
            info = ydl.extract_info(video_url, download=False)
            return info.get('url') 
        except Exception as e:
            logger.error(f"Error resolving stream URL for {video_url}: {e}")
            return None

def create_youtube_audio_source(stream_url: str) -> discord.FFmpegPCMAudio:
    """Creates a discord.FFmpegPCMAudio source from a direct stream URL."""
    return discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTS)
