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
            logger.info(f"Searching YouTube for: '{query}' (limit: {limit})")
            
            # More permissive yt-dlp options
            ydl_opts = {
                'quiet': False,  # Enable output for debugging
                'no_warnings': False,
                'extract_flat': True,
                'default_search': f'ytsearch{limit}:',
                'ignoreerrors': True,
                'source_address': '0.0.0.0',
                'socket_timeout': 60,
                'retries': 5,
                'fragment_retries': 5,
                'http_chunk_size': 10485760,
                'geo_bypass': True,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            }
            
            tracks = []
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    logger.info(f"Extracting info for search: {query}")
                    search_results = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
                    
                    logger.info(f"Raw search results type: {type(search_results)}")
                    if search_results:
                        logger.info(f"Search results keys: {list(search_results.keys()) if isinstance(search_results, dict) else 'Not a dict'}")
                    
                    if not search_results:
                        logger.warning(f"yt-dlp returned None for query: {query}")
                        return []
                    
                    if 'entries' not in search_results:
                        logger.warning(f"No 'entries' key in search results for: {query}")
                        logger.debug(f"Available keys: {list(search_results.keys()) if isinstance(search_results, dict) else 'Not a dict'}")
                        return []
                    
                    entries = search_results['entries']
                    logger.info(f"Found {len(entries)} raw entries")
                    
                    for i, entry in enumerate(entries):
                        logger.debug(f"Processing entry {i+1}: {type(entry)}")
                        
                        if not entry:
                            logger.debug(f"Entry {i+1} is None, skipping")
                            continue
                            
                        if 'id' not in entry:
                            logger.debug(f"Entry {i+1} has no 'id', skipping")
                            continue
                        
                        # Extract information
                        video_id = entry['id']
                        title = entry.get('title', 'Unknown Title')
                        uploader = entry.get('uploader', 'Unknown Artist')
                        duration = entry.get('duration', 0)
                        
                        logger.debug(f"Entry {i+1}: id={video_id}, title={title}, uploader={uploader}, duration={duration} (type: {type(duration)})")
                        
                        # Format duration - FIXED: Handle float durations
                        if duration and duration > 0:
                            try:
                                # Convert to int in case it's a float
                                duration = int(float(duration))
                                minutes = duration // 60
                                seconds = duration % 60
                                duration_str = f"{minutes:02d}:{seconds:02d}"
                            except (ValueError, TypeError):
                                duration_str = "Unknown"
                        else:
                            duration_str = "Unknown"
                        
                        # Try to extract artist from title if it contains " - "
                        if ' - ' in title and uploader in ['Various Artists', 'Unknown Artist', title]:
                            parts = title.split(' - ', 1)
                            if len(parts) == 2:
                                uploader = parts[0].strip()
                                title = parts[1].strip()
                        
                        song = Song(
                            id=video_id,
                            title=title[:100],
                            artist=uploader[:50],
                            duration=duration_str,
                            url=f"https://www.youtube.com/watch?v={video_id}",
                            source='youtube'
                        )
                        tracks.append(song)
                        logger.info(f"Added track: {song.title} by {song.artist} ({song.url})")
                    
                    logger.info(f"Successfully processed {len(tracks)} tracks for query: {query}")
                    return tracks
                    
                except Exception as extract_error:
                    logger.error(f"Error during yt-dlp extraction for '{query}': {extract_error}")
                    logger.error(f"Error type: {type(extract_error)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    return []
                
        except Exception as e:
            logger.error(f"YouTube search error for '{query}': {e}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    @staticmethod
    def get_audio_url(youtube_url: str) -> Optional[str]:
        """Extract audio URL from YouTube video"""
        logger.info(f"Extracting audio URL from: {youtube_url}")
        
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': False,  # Enable output for debugging
                'no_warnings': False,
                'ignoreerrors': True,
                'extractaudio': True,
                'audioformat': 'mp3',
                'source_address': '0.0.0.0',
                'cookiefile': None,
                'age_limit': None,
                'geo_bypass': True,
                'extract_flat': False,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'socket_timeout': 60,
                'retries': 5,
                'fragment_retries': 5,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(youtube_url, download=False)
                    if info and 'url' in info:
                        logger.info(f"Successfully extracted audio URL for: {info.get('title', 'Unknown')}")
                        return info['url']
                    else:
                        logger.warning(f"No direct URL in info for: {youtube_url}")
                        if info:
                            logger.debug(f"Available info keys: {list(info.keys())}")
                        
                        # Try alternative format selection
                        logger.warning(f"Trying alternative formats for: {youtube_url}")
                        
                        fallback_formats = [
                            'bestaudio[ext=m4a]',
                            'bestaudio[ext=webm]', 
                            'best[height<=480]',
                            'worst'
                        ]
                        
                        for fmt in fallback_formats:
                            try:
                                logger.debug(f"Trying format: {fmt}")
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