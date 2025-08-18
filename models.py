#!/usr/bin/env python3
"""
Data models for Psychosonus
"""

from typing import Dict, Any, Optional

class Song:
    """Song data structure"""
    
    def __init__(self, id: str, title: str, artist: str, duration: str, url: str, 
                 source: str = 'youtube', youtube_url: Optional[str] = None):
        self.id = id
        self.title = title
        self.artist = artist
        self.duration = duration
        self.url = url  # Original URL (Spotify or YouTube)
        self.source = source  # 'spotify' or 'youtube'
        self.youtube_url = youtube_url  # YouTube URL for playback if source is Spotify
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'title': self.title,
            'artist': self.artist,
            'duration': self.duration,
            'url': self.url,
            'source': self.source,
            'youtube_url': self.youtube_url
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
            source=data.get('source', 'youtube'),
            youtube_url=data.get('youtube_url')
        )
    
    def get_playback_url(self) -> str:
        """Get the URL to use for playback"""
        if self.source == 'spotify' and self.youtube_url:
            return self.youtube_url
        return self.url