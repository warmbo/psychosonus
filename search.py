#!/usr/bin/env python3
"""
Search module for Psychosonus - Spotify Integration
Handles music search and metadata extraction
"""

import logging
import requests
import base64
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Song:
    """Song data structure"""
    id: str
    title: str
    artist: str
    duration: str
    url: str
    preview_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'title': self.title,
            'artist': self.artist,
            'duration': self.duration,
            'url': self.url,
            'preview_url': self.preview_url
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Song':
        """Create Song from dictionary"""
        return cls(
            id=data['id'],
            title=data['title'],
            artist=data['artist'],
            duration=data['duration'],
            url=data['url'],
            preview_url=data.get('preview_url')
        )

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
            # Encode credentials
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            # Request token
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
                # Set expiration time (subtract 60 seconds for safety)
                import time
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
        import time
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
                'market': 'US'  # You can make this configurable
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
                    # Format duration
                    duration_ms = track.get('duration_ms', 0)
                    minutes = duration_ms // 60000
                    seconds = (duration_ms % 60000) // 1000
                    duration_str = f"{minutes:02d}:{seconds:02d}"
                    
                    # Get artist names
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
                # Token expired, try to refresh
                logger.warning("Spotify token expired, refreshing...")
                if self._get_access_token():
                    return self.search_tracks(query, limit)  # Retry once
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
                
                # Format duration
                duration_ms = track.get('duration_ms', 0)
                minutes = duration_ms // 60000
                seconds = (duration_ms % 60000) // 1000
                duration_str = f"{minutes:02d}:{seconds:02d}"
                
                # Get artist names
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
        
        # Initialize Spotify if credentials are provided
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
        """Search for tracks using available services"""
        if self.spotify:
            return self.spotify.search_tracks(query, limit)
        else:
            logger.error("No search services available")
            return []
    
    def get_track_info(self, track_id: str, service: str = 'spotify') -> Optional[Song]:
        """Get track information from specific service"""
        if service == 'spotify' and self.spotify:
            return self.spotify.get_track_info(track_id)
        else:
            logger.error(f"Service '{service}' not available")
            return None
    
    def is_service_available(self, service: str = 'spotify') -> bool:
        """Check if a service is available"""
        if service == 'spotify':
            return self.spotify is not None
        return False