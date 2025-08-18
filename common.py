#!/usr/bin/env python3
"""
Common data structures for Psychosonus
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

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