#!/usr/bin/env python3
"""
Thread-safe music queue manager for Psychosonus
"""

import threading
from collections import deque
from typing import List, Dict, Any, Optional

from models import Song

class MusicQueue:
    """Thread-safe music queue manager"""
    
    def __init__(self, max_size: int = 100):
        self.queue = deque()
        self.current_track: Optional[Song] = None
        self.max_size = max_size
        self._lock = threading.Lock()
    
    def add_song(self, song: Song) -> bool:
        """Add song to queue"""
        with self._lock:
            if len(self.queue) >= self.max_size:
                return False
            self.queue.append(song)
            return True
    
    def get_next(self) -> Optional[Song]:
        """Get next song from queue"""
        with self._lock:
            if self.queue:
                self.current_track = self.queue.popleft()
                return self.current_track
            return None
    
    def remove_at_index(self, index: int) -> bool:
        """Remove song at specific index (0-based, excluding current track)"""
        with self._lock:
            if 0 <= index < len(self.queue):
                queue_list = list(self.queue)
                queue_list.pop(index)
                self.queue = deque(queue_list)
                return True
            return False
    
    def clear(self):
        """Clear the entire queue"""
        with self._lock:
            self.queue.clear()
    
    def get_queue_list(self) -> List[Dict[str, Any]]:
        """Get current queue as list including current track"""
        with self._lock:
            queue_list = []
            if self.current_track:
                queue_list.append({
                    'song': self.current_track.to_dict(),
                    'current': True
                })
            
            for song in self.queue:
                queue_list.append({
                    'song': song.to_dict(),
                    'current': False
                })
            
            return queue_list
    
    def size(self) -> int:
        """Get queue size (excluding current track)"""
        with self._lock:
            return len(self.queue)