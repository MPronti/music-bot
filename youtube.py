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
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': False,            # Explicitly allow playlists
    'default_search': 'auto',
    'source_address': '0.0.0.0',    # Force ipv4
}

# --- FFmpeg Configuration ---
FFMPEG_OPTS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

def is_youtube_url(url: str) -> bool:
    """Checks if the given string is a valid YouTube URL."""
    return YOUTUBE_URL_REGEX.match(url) is not None

def get_youtube_info(url: str) -> Optional[List[Dict]]:
    """
    SIMPLIFIED AND MORE ROBUST.
    Uses yt-dlp to extract full information for a URL in a single call.
    Handles both single videos and playlists directly.
    """
    with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
        try:
            logger.info(f"Extracting full info for URL: {url}")
            # This single call gets all the data we need.
            info = ydl.extract_info(url, download=False)
            
            if not info:
                logger.warning(f"yt-dlp returned no info for {url}")
                return None

            # Check if the result is a playlist.
            if 'entries' in info:
                # It's a playlist. The entries already contain full video info.
                # Filter out any failed entries which yt-dlp might return as None.
                entries = [entry for entry in info['entries'] if entry]
                logger.info(f"Successfully extracted {len(entries)} videos from playlist.")
                return entries
            else:
                # It's a single video. Wrap it in a list to keep the return type consistent.
                logger.info(f"Successfully extracted single video: {info.get('title')}")
                return [info]
            
        except yt_dlp.utils.DownloadError as e:
            # Provide more helpful log messages for debugging.
            logger.error(f"yt-dlp DownloadError for {url}: {e}")
            if "age restricted" in str(e).lower():
                logger.error("This content is age-restricted and cannot be accessed.")
            elif "private video" in str(e).lower():
                logger.error("This is a private video.")
            elif "unavailable" in str(e).lower():
                 logger.error("This video is unavailable.")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred in get_youtube_info: {e}", exc_info=True)
            return None

def create_youtube_audio_source(stream_url: str) -> discord.FFmpegPCMAudio:
    """Creates a discord.FFmpegPCMAudio source from a direct stream URL."""
    return discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTS)
