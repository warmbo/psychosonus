#!/usr/bin/env python3
"""
Search module for Psychosonus - Spotify Integration
Handles music search and metadata extraction
"""

import logging
import requests
import base64
import time
from typing import Dict, List, Optional, Any
import yt_dlp # Import yt-dlp here

from common import Song # Import Song from common.py

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
                                url=f"https://www.youtube.com/watch?v={entry['id']}"
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


class SpotifyManager:
    """Spotify API integration for music search"""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expires_at = 0
        
    def _get_access_token(self) -> bool:
        """Get Spotify access token using client credentials flow"""
        try:
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {'grant_type': 'client_credentials'}
            
            response = requests.post(
                'https://accounts.spotify.com/api/token',
                headers=headers,
                data=data,
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                self.token_expires_at = time.time() + token_data['expires_in'] - 60
                logger.info("Successfully obtained Spotify access token")
                return True
            else:
                logger.error(f"Failed to get Spotify token: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error getting Spotify access token: {e}")
            return False
    
    def _ensure_valid_token(self) -> bool:
        """Ensure we have a valid access token"""
        if not self.access_token or time.time() >= self.token_expires_at:
            return self._get_access_token()
        return True
    
    def search_tracks(self, query: str, limit: int = 5) -> List[Song]:
        """Search for tracks on Spotify"""
        if not self._ensure_valid_token():
            logger.error("Failed to get valid Spotify token")
            return []
        
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            params = {
                'q': query,
                'type': 'track',
                'limit': limit,
                'market': 'US'
            }
            
            response = requests.get(
                'https://api.spotify.com/v1/search',
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                tracks = []
                
                for track in data.get('tracks', {}).get('items', []):
                    duration_ms = track.get('duration_ms', 0)
                    minutes = duration_ms // 60000
                    seconds = (duration_ms % 60000) // 1000
                    duration_str = f"{minutes:02d}:{seconds:02d}"
                    
                    artists = [artist['name'] for artist in track.get('artists', [])]
                    artist_str = ', '.join(artists) if artists else 'Unknown Artist'
                    
                    song = Song(
                        id=track['id'],
                        title=track.get('name', 'Unknown Title')[:100],
                        artist=artist_str[:50],
                        duration=duration_str,
                        url=track.get('external_urls', {}).get('spotify', ''),
                        preview_url=track.get('preview_url')
                    )
                    tracks.append(song)
                
                logger.info(f"Found {len(tracks)} tracks for query: {query}")
                return tracks
            
            elif response.status_code == 401:
                logger.warning("Spotify token expired, refreshing...")
                if self._get_access_token():
                    return self.search_tracks(query, limit)
                else:
                    logger.error("Failed to refresh Spotify token")
                    return []
            else:
                logger.error(f"Spotify search failed: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Spotify search error: {e}")
            return []
    
    def get_track_info(self, track_id: str) -> Optional[Song]:
        """Get detailed track information"""
        if not self._ensure_valid_token():
            return None
        
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f'https://api.spotify.com/v1/tracks/{track_id}',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                track = response.json()
                
                duration_ms = track.get('duration_ms', 0)
                minutes = duration_ms // 60000
                seconds = (duration_ms % 60000) // 1000
                duration_str = f"{minutes:02d}:{seconds:02d}"
                
                artists = [artist['name'] for artist in track.get('artists', [])]
                artist_str = ', '.join(artists) if artists else 'Unknown Artist'
                
                return Song(
                    id=track['id'],
                    title=track.get('name', 'Unknown Title'),
                    artist=artist_str,
                    duration=duration_str,
                    url=track.get('external_urls', {}).get('spotify', ''),
                    preview_url=track.get('preview_url')
                )
            else:
                logger.error(f"Failed to get track info: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting track info: {e}")
            return None

class SearchManager:
    """Main search manager that handles different music services"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.spotify = None
        self.youtube = YouTubeManager()
        
        spotify_client_id = config.get('spotify_client_id')
        spotify_client_secret = config.get('spotify_client_secret')
        
        if spotify_client_id and spotify_client_secret:
            if (spotify_client_id != "SPOTIFY_CLIENT_ID_GOES_HERE" and 
                spotify_client_secret != "SPOTIFY_CLIENT_SECRET_GOES_HERE"):
                self.spotify = SpotifyManager(spotify_client_id, spotify_client_secret)
                logger.info("Spotify integration initialized")
            else:
                logger.warning("Spotify credentials not configured")
        else:
            logger.warning("Spotify credentials missing from config")
    
    def search_tracks(self, query: str, limit: int = 5) -> List[Song]:
        """Search for tracks using available services (prioritize Spotify)"""
        if self.spotify:
            return self.spotify.search_tracks(query, limit)
        elif self.youtube:
            return self.youtube.search_tracks(query, limit)
        else:
            logger.error("No search services available")
            return []
    
    def get_audio_url(self, song: Song) -> Optional[str]:
        """Get the audio URL for a song, searching YouTube if needed"""
        if 'youtube' in song.url:
            return self.youtube.get_audio_url(song.url)
        else:
            # Fallback to YouTube search for songs from other services (e.g., Spotify)
            search_query = f"{song.title} {song.artist}"
            tracks = self.youtube.search_tracks(search_query, limit=1)
            if tracks:
                return self.youtube.get_audio_url(tracks[0].url)
            return None
    
    def is_service_available(self, service: str) -> bool:
        """Check if a service is available"""
        if service == 'spotify':
            return self.spotify is not None
        elif service == 'youtube':
            return self.youtube is not None
        return False