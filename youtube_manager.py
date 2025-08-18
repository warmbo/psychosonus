#!/usr/bin/env python3
"""
YouTube search and audio extraction for Psychosonus
"""

import logging
from typing import List, Optional
import yt_dlp

from models import Song

logger = logging.getLogger(__name__)

class YouTubeManager:
    """YouTube search and audio extraction"""
    
    @staticmethod
    def search_tracks(query: str, limit: int = 5) -> List[Song]:
        """Search for tracks on YouTube"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'default_search': f'ytsearch{limit}:',
                'ignoreerrors': True,
                'source_address': '0.0.0.0',  # Bind to IPv4
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_results = ydl.extract_info(query, download=False)
                
                tracks = []
                if 'entries' in search_results:
                    for entry in search_results['entries']:
                        if entry and 'id' in entry:
                            duration = entry.get('duration', 0)
                            if duration:
                                minutes = duration // 60
                                seconds = duration % 60
                                duration_str = f"{minutes:02d}:{seconds:02d}"
                            else:
                                duration_str = "Unknown"
                            
                            song = Song(
                                id=entry['id'],
                                title=entry.get('title', 'Unknown Title')[:100],
                                artist=entry.get('uploader', 'Unknown Artist')[:50],
                                duration=duration_str,
                                url=f"https://www.youtube.com/watch?v={entry['id']}",
                                source='youtube'
                            )
                            tracks.append(song)
                
                return tracks
                
        except Exception as e:
            logger.error(f"YouTube search error: {e}")
            return []
    
    @staticmethod
    def get_audio_url(youtube_url: str) -> Optional[str]:
        """Extract audio URL from YouTube video"""
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True,
                'extractaudio': True,
                'audioformat': 'mp3',
                'source_address': '0.0.0.0',  # Bind to IPv4
                'cookiefile': None,  # Don't use cookies
                'age_limit': None,
                'geo_bypass': True,
                'extract_flat': False,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'referer': 'https://www.youtube.com/',
                'socket_timeout': 30,
                'retries': 3,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(youtube_url, download=False)
                    if info and 'url' in info:
                        logger.info(f"Successfully extracted audio URL for: {info.get('title', 'Unknown')}")
                        return info['url']
                    else:
                        # Try alternative format selection
                        logger.warning(f"No direct URL found, trying alternative formats for: {youtube_url}")
                        
                        # Fallback format options
                        fallback_formats = [
                            'bestaudio[ext=m4a]',
                            'bestaudio[ext=webm]', 
                            'best[height<=480]',
                            'worst'
                        ]
                        
                        for fmt in fallback_formats:
                            try:
                                ydl_opts['format'] = fmt
                                with yt_dlp.YoutubeDL(ydl_opts) as ydl_fallback:
                                    info = ydl_fallback.extract_info(youtube_url, download=False)
                                    if info and 'url' in info:
                                        logger.info(f"Fallback format {fmt} worked for: {info.get('title', 'Unknown')}")
                                        return info['url']
                            except Exception as fallback_error:
                                logger.debug(f"Fallback format {fmt} failed: {fallback_error}")
                                continue
                        
                        logger.error(f"All format options failed for: {youtube_url}")
                        return None
                        
                except yt_dlp.DownloadError as download_error:
                    logger.error(f"yt-dlp download error for {youtube_url}: {download_error}")
                    return None
                except Exception as extract_error:
                    logger.error(f"yt-dlp extraction error for {youtube_url}: {extract_error}")
                    return None
                
        except Exception as e:
            logger.error(f"General error getting audio URL for {youtube_url}: {e}")
            return None

    @staticmethod
    def search_youtube_for_spotify_track(spotify_song: Song) -> Optional[str]:
        """Search YouTube for a Spotify track and return the best match URL"""
        try:
            # Create search query combining artist and title
            search_query = f"{spotify_song.artist} {spotify_song.title}"
            
            # Search YouTube for the track
            youtube_tracks = YouTubeManager.search_tracks(search_query, limit=3)
            
            if youtube_tracks:
                # Return the first result's URL (usually most relevant)
                best_match = youtube_tracks[0]
                logger.info(f"Found YouTube match for Spotify track: {spotify_song.title}")
                return best_match.url
            else:
                logger.warning(f"No YouTube results for Spotify track: {spotify_song.title}")
                return None
                
        except Exception as e:
            logger.error(f"Error searching YouTube for Spotify track {spotify_song.title}: {e}")
            return None