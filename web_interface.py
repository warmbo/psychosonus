#!/usr/bin/env python3
"""
Flask web interface for Psychosonus with Discord OAuth2
"""

import asyncio
import logging
import secrets
from functools import wraps
from flask import Flask, jsonify, request, send_from_directory, redirect, session, url_for, render_template_string

from config import Config
from models import Song
from youtube_manager import YouTubeManager
from discord_auth import DiscordAuth, ServerPermissions

logger = logging.getLogger(__name__)

# Import SearchManager if available
try:
    from search import SearchManager
    SPOTIFY_AVAILABLE = True
except ImportError:
    logger.warning("Spotify search not available - using YouTube only")
    SPOTIFY_AVAILABLE = False

class WebInterface:
    """Flask web interface with Discord OAuth2"""
    
    def __init__(self, bot, config: Config):
        self.bot = bot
        self.config = config
        self.app = Flask(__name__)
        
        # Set up session secret
        self.app.secret_key = config.get('session_secret', secrets.token_hex(32))
        
        # Use config's redirect_uri without port
        self.discord_auth = DiscordAuth(
            client_id=config.get('discord_client_id'),
            client_secret=config.get('discord_client_secret'),
            redirect_uri=config.get('redirect_uri')  # Port-less URI from config
        )
        
        # Initialize server permissions
        self.server_permissions = ServerPermissions(bot)
        
        # Initialize search manager if Spotify is available
        if SPOTIFY_AVAILABLE:
            self.search_manager = SearchManager(config.data)
        else:
            self.search_manager = None
        
        self.setup_routes()
    
    def require_auth(self, f):
        """Decorator to require authentication"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                return jsonify({'success': False, 'error': 'Authentication required', 'auth_url': '/auth'}), 401
            return f(*args, **kwargs)
        return decorated_function
    
    def require_guild_access(self, f):
        """Decorator to require guild access"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                return jsonify({'success': False, 'error': 'Authentication required', 'auth_url': '/auth'}), 401
            
            current_guild_id = self.bot.get_current_guild_id()
            if not current_guild_id:
                return jsonify({'success': False, 'error': 'Bot not connected to any server'}), 403
            
            user_id = session['user']['user_id']
            if not self.server_permissions.user_has_access(user_id, str(current_guild_id)):
                return jsonify({'success': False, 'error': 'You do not have access to this server'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def dashboard():
            """Serve dashboard HTML file or redirect to auth"""
            if 'user' not in session:
                return redirect('/auth')
            return send_from_directory('static', 'dashboard.html')
        
        @self.app.route('/auth')
        def auth_page():
            """Discord OAuth2 authorization page"""
            auth_url = self.discord_auth.get_authorization_url()
            
            auth_page_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Psychosonus - Discord Authorization</title>
                <style>
                    body { 
                        font-family: 'Consolas', monospace; 
                        background: #000; 
                        color: #fff; 
                        text-align: center; 
                        padding: 50px;
                    }
                    .auth-container {
                        max-width: 500px;
                        margin: 0 auto;
                        padding: 40px;
                        background: #111;
                        border: 2px solid #333;
                        border-radius: 10px;
                    }
                    .title { 
                        font-size: 3rem; 
                        color: #fff;
                        text-shadow: 0 0 10px rgba(255, 0, 0, 0.8);
                        margin-bottom: 20px;
                    }
                    .subtitle { 
                        color: #aaa; 
                        margin-bottom: 30px; 
                    }
                    .discord-btn {
                        background: #5865F2;
                        color: white;
                        padding: 15px 30px;
                        border: none;
                        border-radius: 8px;
                        font-size: 18px;
                        text-decoration: none;
                        display: inline-block;
                        margin: 20px 0;
                        transition: background 0.3s;
                    }
                    .discord-btn:hover { background: #4752C4; }
                    .info { color: #888; font-size: 14px; margin-top: 20px; }
                </style>
            </head>
            <body>
                <div class="auth-container">
                    <h1 class="title">🎵 Psychosonus</h1>
                    <p class="subtitle">Discord Music Bot Dashboard</p>
                    <p>Sign in with your Discord account to access the web dashboard.</p>
                    <a href="{{ auth_url }}" class="discord-btn">
                        🔗 Authorize with Discord
                    </a>
                    <div class="info">
                        <p>You need to be a member of a server where Psychosonus is installed.</p>
                        <p>Only server members can control the bot's queue.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            return render_template_string(auth_page_html, auth_url=auth_url)
        
        @self.app.route('/auth/callback')
        def auth_callback():
            """Handle Discord OAuth2 callback"""
            code = request.args.get('code')
            error = request.args.get('error')
            
            if error:
                return f"Authorization error: {error}", 400
            
            if not code:
                return "Missing authorization code", 400
            
            # Exchange code for token
            token_data = self.discord_auth.exchange_code(code)
            if not token_data:
                logger.error("Failed to exchange authorization code. Redirecting to error page.")
                return redirect(url_for('auth_page', error='token_exchange_failed'))
            
            access_token = token_data['access_token']
            
            # Get user info
            user_info = self.discord_auth.get_user_info(access_token)
            if not user_info:
                return "Failed to get user information", 400
            
            # Get user guilds
            user_guilds = self.discord_auth.get_user_guilds(access_token)
            
            # Filter to only guilds where bot is present
            accessible_guilds = self.server_permissions.get_user_accessible_guilds(user_guilds)
            
            if not accessible_guilds:
                return render_template_string("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Access Denied - Psychosonus</title>
                    <style>
                        body { 
                            font-family: 'Consolas', monospace; 
                            background: #000; 
                            color: #fff; 
                            text-align: center; 
                            padding: 50px;
                        }
                        .error-container {
                            max-width: 500px;
                            margin: 0 auto;
                            padding: 40px;
                            background: #111;
                            border: 2px solid #f44;
                            border-radius: 10px;
                        }
                        .title { color: #f44; font-size: 2rem; margin-bottom: 20px; }
                        .message { color: #ccc; margin-bottom: 20px; }
                        .retry-btn {
                            background: #333;
                            color: white;
                            padding: 10px 20px;
                            border: none;
                            border-radius: 5px;
                            text-decoration: none;
                            display: inline-block;
                        }
                    </style>
                </head>
                <body>
                    <div class="error-container">
                        <h1 class="title">❌ Access Denied</h1>
                        <p class="message">You are not a member of any servers where Psychosonus is installed.</p>
                        <p class="message">Ask a server admin to invite the bot first!</p>
                        <a href="/auth" class="retry-btn">Try Again</a>
                    </div>
                </body>
                </html>
                """)
            
            # Create session
            session['user'] = {
                'user_id': user_info['id'],
                'username': user_info['username'],
                'discriminator': user_info.get('discriminator', '0'),
                'avatar': user_info.get('avatar'),
                'guilds': accessible_guilds
            }
            
            logger.info(f"User {user_info['username']} authenticated with access to {len(accessible_guilds)} guilds")
            
            return redirect('/')
        
        @self.app.route('/auth/logout')
        def logout():
            """Logout user"""
            session.clear()
            return redirect('/auth')
        
        @self.app.route('/static/<path:filename>')
        def static_files(filename):
            """Serve static files"""
            return send_from_directory('static', filename)
        
        @self.app.route('/api/user')
        @self.require_auth
        def get_user():
            """Get current user information"""
            return jsonify({
                'success': True,
                'user': session['user']
            })
        
        @self.app.route('/api/search', methods=['POST'])
        @self.require_guild_access
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
        @self.require_auth
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
        @self.require_guild_access
        def add_to_queue():
            """Add song to queue"""
            try:
                data = request.json
                song_data = data.get('song')
                
                if not song_data:
                    return jsonify({'success': False, 'error': 'No song data'})
                
                song = Song.from_dict(song_data)
                logger.info(f"User {session['user']['username']} adding song: {song.title} by {song.artist}")
                
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
                    
                    return jsonify({'success': True})
                else:
                    return jsonify({'success': False, 'error': 'Queue is full'})
                
            except Exception as e:
                logger.error(f"Add to queue error: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/queue/remove', methods=['POST'])
        @self.require_guild_access
        def remove_from_queue():
            """Remove song from queue"""
            try:
                data = request.json
                index = data.get('index')
                
                if index is None:
                    return jsonify({'success': False, 'error': 'No index provided'})
                
                if self.bot.music_queue.remove_at_index(index):
                    logger.info(f"User {session['user']['username']} removed song at index {index}")
                    return jsonify({'success': True})
                else:
                    return jsonify({'success': False, 'error': 'Invalid index'})
                
            except Exception as e:
                logger.error(f"Remove from queue error: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/queue/clear', methods=['POST'])
        @self.require_guild_access
        def clear_queue():
            """Clear queue"""
            try:
                self.bot.music_queue.clear()
                logger.info(f"User {session['user']['username']} cleared the queue")
                return jsonify({'success': True})
            except Exception as e:
                logger.error(f"Clear queue error: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/control/pause', methods=['POST'])
        @self.require_guild_access
        def pause_song():
            """Pause current song"""
            try:
                if not self.bot.voice_client:
                    return jsonify({'success': False, 'error': 'Bot not connected to voice channel'})
                
                if self.bot.voice_client.is_playing():
                    self.bot.voice_client.pause()
                    logger.info(f"User {session['user']['username']} paused playback")
                    return jsonify({'success': True, 'message': 'Paused'})
                else:
                    return jsonify({'success': False, 'error': 'Nothing is playing'})
            except Exception as e:
                logger.error(f"Pause error: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/control/resume', methods=['POST'])
        @self.require_guild_access
        def resume_song():
            """Resume current song"""
            try:
                if not self.bot.voice_client:
                    return jsonify({'success': False, 'error': 'Bot not connected to voice channel'})
                
                if self.bot.voice_client.is_paused():
                    self.bot.voice_client.resume()
                    logger.info(f"User {session['user']['username']} resumed playback")
                    return jsonify({'success': True, 'message': 'Resumed'})
                else:
                    return jsonify({'success': False, 'error': 'Nothing is paused'})
            except Exception as e:
                logger.error(f"Resume error: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/control/skip', methods=['POST'])
        @self.require_guild_access
        def skip_song():
            """Skip current song"""
            try:
                if self.bot.voice_client and self.bot.voice_client.is_playing():
                    self.bot.voice_client.stop()
                    logger.info(f"User {session['user']['username']} skipped song")
                    return jsonify({'success': True})
                else:
                    return jsonify({'success': False, 'error': 'Nothing is playing'})
            except Exception as e:
                logger.error(f"Skip error: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/control/stop', methods=['POST'])
        @self.require_guild_access
        def stop_song():
            """Stop current song and clear current track"""
            try:
                if not self.bot.voice_client:
                    return jsonify({'success': False, 'error': 'Bot not connected to voice channel'})
                
                if self.bot.voice_client.is_playing() or self.bot.voice_client.is_paused():
                    self.bot.voice_client.stop()
                    self.bot.is_playing = False
                    self.bot.music_queue.current_track = None
                    logger.info(f"User {session['user']['username']} stopped playback")
                    return jsonify({'success': True, 'message': 'Stopped'})
                else:
                    return jsonify({'success': False, 'error': 'Nothing is playing'})
            except Exception as e:
                logger.error(f"Stop error: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/control/play', methods=['POST'])
        @self.require_guild_access
        def force_play():
            """Force start playing next song in queue"""
            try:
                if not self.bot.voice_client:
                    return jsonify({'success': False, 'error': 'Bot not connected to voice channel'})
                
                if self.bot.is_playing:
                    return jsonify({'success': False, 'error': 'Already playing'})
                
                if self.bot.music_queue.size() == 0:
                    return jsonify({'success': False, 'error': 'Queue is empty'})
                
                logger.info(f"User {session['user']['username']} force starting playback")
                future = asyncio.run_coroutine_threadsafe(self.bot.play_next(), self.bot.loop)
                future.result(timeout=10)
                
                return jsonify({'success': True})
            except Exception as e:
                logger.error(f"Force play error: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/queue/shuffle', methods=['POST'])
        @self.require_guild_access
        def shuffle_queue():
            """Shuffle the queue"""
            try:
                import random
                with self.bot.music_queue._lock:
                    queue_list = list(self.bot.music_queue.queue)
                    random.shuffle(queue_list)
                    self.bot.music_queue.queue = type(self.bot.music_queue.queue)(queue_list)
                
                logger.info(f"User {session['user']['username']} shuffled the queue")
                return jsonify({'success': True, 'message': 'Queue shuffled'})
            except Exception as e:
                logger.error(f"Shuffle error: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/control/leave', methods=['POST'])
        @self.require_guild_access
        def leave_channel():
            """Leave voice channel"""
            try:
                if self.bot.voice_client:
                    future = asyncio.run_coroutine_threadsafe(
                        self.bot.voice_client.disconnect(), 
                        self.bot.loop
                    )
                    future.result(timeout=5)
                    self.bot.voice_client = None
                    self.bot.is_playing = False
                    self.bot.current_channel = None
                    self.bot.current_guild_id = None
                    logger.info(f"User {session['user']['username']} made bot leave voice channel")
                    return jsonify({'success': True, 'message': 'Left voice channel'})
                else:
                    return jsonify({'success': False, 'error': 'Not connected to voice channel'})
            except Exception as e:
                logger.error(f"Leave error: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/status')
        @self.require_auth
        def get_status():
            """Get bot status"""
            try:
                voice_connected = self.bot.voice_client is not None
                voice_playing = self.bot.voice_client.is_playing() if self.bot.voice_client else False
                voice_paused = self.bot.voice_client.is_paused() if self.bot.voice_client else False
                current_guild_id = self.bot.get_current_guild_id()
                
                # Check if user has access to current guild
                user_has_access = False
                if current_guild_id:
                    user_id = session['user']['user_id']
                    user_has_access = self.server_permissions.user_has_access(user_id, str(current_guild_id))
                
                return jsonify({
                    'success': True,
                    'connected': voice_connected,
                    'playing': voice_playing,
                    'paused': voice_paused,
                    'bot_is_playing': self.bot.is_playing,
                    'queue_size': self.bot.music_queue.size(),
                    'current_track': self.bot.music_queue.current_track.to_dict() if self.bot.music_queue.current_track else None,
                    'voice_channel': self.bot.voice_client.channel.name if self.bot.voice_client else None,
                    'guild_name': self.bot.voice_client.guild.name if self.bot.voice_client else None,
                    'user_has_access': user_has_access
                })
            except Exception as e:
                logger.error(f"Status error: {e}")
                return jsonify({'success': False, 'error': str(e)})
    
    def run(self):
        """Run Flask app"""
        port = self.config.get('port', 8888)
        domain = self.config.get('domain', 'localhost')
        logger.info(f"Starting web interface on port {port}")
        domain = self.config.get("domain", "localhost")
        logger.info(f"Discord OAuth2 redirect URI: https://{self.config.get('domain', 'localhost')}/auth/callback")
        self.app.run(host='0.0.0.0', port=port, debug=False, threaded=True)