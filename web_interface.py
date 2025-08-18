#!/usr/bin/env python3
"""
Flask web interface for Psychosonus
"""

import asyncio
import logging
from flask import Flask, jsonify, request, send_from_directory

from config import Config
from models import Song
from youtube_manager import YouTubeManager
from search import SearchManager

logger = logging.getLogger(__name__)

class WebInterface:
    """Flask web interface"""
    
    def __init__(self, bot, config: Config):
        self.bot = bot
        self.config = config
        self.app = Flask(__name__)
        
        # Initialize search manager
        self.search_manager = SearchManager(config.data)
        
        self.setup_routes()
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def dashboard():
            """Serve dashboard"""
            return send_from_directory('static', 'dashboard.html')
        
        @self.app.route('/static/<path:filename>')
        def static_files(filename):
            """Serve static files"""
            return send_from_directory('static', filename)
        
        @self.app.route('/api/search', methods=['POST'])
        def search_music():
            """Search for music"""
            try:
                data = request.json
                query = data.get('query', '').strip()
                
                if not query:
                    return jsonify({'success': False, 'error': 'No query provided'})
                
                # First try Spotify search for better metadata
                tracks = []
                if self.search_manager.is_service_available('spotify'):
                    spotify_tracks = self.search_manager.search_tracks(query, limit=5)
                    for track in spotify_tracks:
                        # Mark as Spotify source
                        track.source = 'spotify'
                        tracks.append(track)
                
                # If no Spotify results or Spotify not available, fall back to YouTube
                if not tracks:
                    youtube_tracks = YouTubeManager.search_tracks(query, limit=8)
                    for track in youtube_tracks:
                        track.source = 'youtube'
                        tracks.append(track)
                
                return jsonify({
                    'success': True,
                    'results': [track.to_dict() for track in tracks]
                })
                
            except Exception as e:
                logger.error(f"Search error: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/queue')
        def get_queue():
            """Get current queue"""
            try:
                return jsonify({
                    'success': True,
                    'queue': self.bot.music_queue.get_queue_list()
                })
            except Exception as e:
                logger.error(f"Queue get error: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/queue/add', methods=['POST'])
        def add_to_queue():
            """Add song to queue"""
            try:
                data = request.json
                song_data = data.get('song')
                
                if not song_data:
                    return jsonify({'success': False, 'error': 'No song data'})
                
                song = Song.from_dict(song_data)
                
                if self.bot.music_queue.add_song(song):
                    # Start playing if not already playing
                    if self.bot.voice_client and not self.bot.is_playing:
                        future = asyncio.run_coroutine_threadsafe(self.bot.play_next(), self.bot.loop)
                        future.result(timeout=5)
                    
                    return jsonify({'success': True})
                else:
                    return jsonify({'success': False, 'error': 'Queue is full'})
                
            except Exception as e:
                logger.error(f"Add to queue error: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/queue/remove', methods=['POST'])
        def remove_from_queue():
            """Remove song from queue"""
            try:
                data = request.json
                index = data.get('index')
                
                if index is None:
                    return jsonify({'success': False, 'error': 'No index provided'})
                
                if self.bot.music_queue.remove_at_index(index):
                    return jsonify({'success': True})
                else:
                    return jsonify({'success': False, 'error': 'Invalid index'})
                
            except Exception as e:
                logger.error(f"Remove from queue error: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/queue/clear', methods=['POST'])
        def clear_queue():
            """Clear queue"""
            try:
                self.bot.music_queue.clear()
                return jsonify({'success': True})
            except Exception as e:
                logger.error(f"Clear queue error: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/control/skip', methods=['POST'])
        def skip_song():
            """Skip current song"""
            try:
                if self.bot.voice_client and self.bot.voice_client.is_playing():
                    self.bot.voice_client.stop()
                    return jsonify({'success': True})
                else:
                    return jsonify({'success': False, 'error': 'Nothing is playing'})
            except Exception as e:
                logger.error(f"Skip error: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/status')
        def get_status():
            """Get bot status"""
            try:
                return jsonify({
                    'success': True,
                    'connected': self.bot.voice_client is not None,
                    'playing': self.bot.is_playing,
                    'queue_size': self.bot.music_queue.size(),
                    'current_track': self.bot.music_queue.current_track.to_dict() if self.bot.music_queue.current_track else None
                })
            except Exception as e:
                logger.error(f"Status error: {e}")
                return jsonify({'success': False, 'error': str(e)})
    
    def run(self):
        """Run Flask app"""
        port = self.config.get('web_port', 8888)
        self.app.run(host='0.0.0.0', port=port, debug=False, threaded=True)