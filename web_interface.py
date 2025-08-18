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

logger = logging.getLogger(__name__)

# Import SearchManager if available
try:
    from search import SearchManager
    SPOTIFY_AVAILABLE = True
except ImportError:
    logger.warning("Spotify search not available - using YouTube only")
    SPOTIFY_AVAILABLE = False

class WebInterface:
    """Flask web interface"""
    
    def __init__(self, bot, config: Config):
        self.bot = bot
        self.config = config
        self.app = Flask(__name__)
        
        # Initialize search manager if Spotify is available
        if SPOTIFY_AVAILABLE:
            self.search_manager = SearchManager(config.data)
        else:
            self.search_manager = None
        
        self.setup_routes()
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def dashboard():
            """Serve dashboard HTML file"""
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
                
                tracks = []
                
                # Try Spotify first if available and configured
                if (self.search_manager and 
                    self.search_manager.is_service_available('spotify')):
                    try:
                        spotify_tracks = self.search_manager.search_tracks(query, limit=5)
                        for track in spotify_tracks:
                            track.source = 'spotify'
                            tracks.append(track)
                        logger.info(f"Found {len(spotify_tracks)} Spotify tracks for: {query}")
                    except Exception as e:
                        logger.error(f"Spotify search failed: {e}")
                
                # Add YouTube results (always available)
                try:
                    youtube_tracks = YouTubeManager.search_tracks(query, limit=8)
                    for track in youtube_tracks:
                        track.source = 'youtube'
                        tracks.append(track)
                    logger.info(f"Found {len(youtube_tracks)} YouTube tracks for: {query}")
                except Exception as e:
                    logger.error(f"YouTube search failed: {e}")
                
                # Limit total results
                tracks = tracks[:10]
                
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
                logger.info(f"Adding song to queue: {song.title} by {song.artist} (source: {song.source})")
                
                if self.bot.music_queue.add_song(song):
                    # Start playing if not already playing and bot is connected
                    if self.bot.voice_client and not self.bot.is_playing:
                        logger.info("Bot is connected but not playing, starting playback...")
                        try:
                            future = asyncio.run_coroutine_threadsafe(self.bot.play_next(), self.bot.loop)
                            future.result(timeout=10)
                            logger.info("Successfully started playback")
                        except Exception as e:
                            logger.error(f"Error starting playback: {e}")
                    elif not self.bot.voice_client:
                        logger.warning("Bot not connected to voice channel - song added to queue but won't play")
                    else:
                        logger.info("Bot is already playing - song added to queue")
                    
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
        
        @self.app.route('/api/control/pause', methods=['POST'])
        def pause_song():
            """Pause/resume current song"""
            try:
                if not self.bot.voice_client:
                    return jsonify({'success': False, 'error': 'Bot not connected to voice channel'})
                
                if self.bot.voice_client.is_playing():
                    self.bot.voice_client.pause()
                    return jsonify({'success': True, 'message': 'Paused'})
                elif self.bot.voice_client.is_paused():
                    self.bot.voice_client.resume()
                    return jsonify({'success': True, 'message': 'Resumed'})
                else:
                    return jsonify({'success': False, 'error': 'Nothing to pause/resume'})
            except Exception as e:
                logger.error(f"Pause error: {e}")
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
        
        @self.app.route('/api/control/play', methods=['POST'])
        def force_play():
            """Force start playing next song in queue"""
            try:
                if not self.bot.voice_client:
                    return jsonify({'success': False, 'error': 'Bot not connected to voice channel'})
                
                if self.bot.is_playing:
                    return jsonify({'success': False, 'error': 'Already playing'})
                
                if self.bot.music_queue.size() == 0:
                    return jsonify({'success': False, 'error': 'Queue is empty'})
                
                logger.info("Force starting playback...")
                future = asyncio.run_coroutine_threadsafe(self.bot.play_next(), self.bot.loop)
                future.result(timeout=10)
                
                return jsonify({'success': True})
            except Exception as e:
                logger.error(f"Force play error: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/status')
        def get_status():
            """Get bot status"""
            try:
                voice_connected = self.bot.voice_client is not None
                voice_playing = self.bot.voice_client.is_playing() if self.bot.voice_client else False
                voice_paused = self.bot.voice_client.is_paused() if self.bot.voice_client else False
                
                return jsonify({
                    'success': True,
                    'connected': voice_connected,
                    'playing': voice_playing,
                    'paused': voice_paused,
                    'bot_is_playing': self.bot.is_playing,
                    'queue_size': self.bot.music_queue.size(),
                    'current_track': self.bot.music_queue.current_track.to_dict() if self.bot.music_queue.current_track else None,
                    'voice_channel': self.bot.voice_client.channel.name if self.bot.voice_client else None
                })
            except Exception as e:
                logger.error(f"Status error: {e}")
                return jsonify({'success': False, 'error': str(e)})
    
    def run(self):
        """Run Flask app"""
        port = self.config.get('web_port', 8888)
        logger.info(f"Starting web interface on port {port}")
        self.app.run(host='0.0.0.0', port=port, debug=False, threaded=True)