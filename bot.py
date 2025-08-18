#!/usr/bin/env python3
"""
Psychosonus - Discord Music Bot
Modular and improved version with proper async handling
"""

import asyncio
import json
import logging
import threading
import time
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Any

import discord
from discord.ext import commands
from flask import Flask, jsonify, request, send_from_directory
import yt_dlp
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Config:
    """Configuration manager"""
    
    def __init__(self, config_path: str = 'config.json'):
        self.config_path = config_path
        self.data = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Config file {self.config_path} not found!")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            raise
    
    def _validate_config(self):
        """Validate required configuration"""
        required_fields = ['discord_token']
        for field in required_fields:
            if not self.data.get(field) or self.data[field] == f"YOUR_{field.upper()}_HERE":
                logger.error(f"Missing or invalid {field} in config.json")
                raise ValueError(f"Please configure {field} in config.json")
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.data.get(key, default)

class Song:
    """Song data structure"""
    
    def __init__(self, id: str, title: str, artist: str, duration: str, url: str):
        self.id = id
        self.title = title
        self.artist = artist
        self.duration = duration
        self.url = url
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'title': self.title,
            'artist': self.artist,
            'duration': self.duration,
            'url': self.url
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'Song':
        """Create Song from dictionary"""
        return cls(
            id=data['id'],
            title=data['title'],
            artist=data['artist'],
            duration=data['duration'],
            url=data['url']
        )

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
                                title=entry.get('title', 'Unknown Title')[:100],  # Limit title length
                                artist=entry.get('uploader', 'Unknown Artist')[:50],  # Limit artist length
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
                'format': 'bestaudio[ext=webm]/bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True,
                'extractaudio': True,
                'audioformat': 'webm',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                return info.get('url')
                
        except Exception as e:
            logger.error(f"Error getting audio URL for {youtube_url}: {e}")
            return None

class MusicBot(commands.Bot):
    """Main Discord bot class"""
    
    def __init__(self, config: Config):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix=config.get('command_prefix', '!'),
            intents=intents,
            help_command=None
        )
        
        self.config = config
        self.music_queue = MusicQueue(config.get('max_queue_size', 100))
        self.voice_client: Optional[discord.VoiceClient] = None
        self.is_playing = False
        self.current_channel = None
        
        # Add commands
        self.add_commands()
    
    def add_commands(self):
        """Add bot commands"""
        
        @self.command(name='join', aliases=['j'])
        async def join_voice(ctx):
            """Join voice channel"""
            if not ctx.author.voice:
                await ctx.send("❌ You need to be in a voice channel!")
                return
            
            channel = ctx.author.voice.channel
            
            try:
                if self.voice_client:
                    await self.voice_client.move_to(channel)
                else:
                    self.voice_client = await channel.connect()
                
                self.current_channel = ctx.channel
                web_port = self.config.get('web_port', 8888)
                await ctx.send(f"🎵 Joined **{channel.name}**\n🌐 Dashboard: http://localhost:{web_port}")
                
                if not self.is_playing:
                    await self.play_next()
                    
            except Exception as e:
                logger.error(f"Failed to join voice channel: {e}")
                await ctx.send(f"❌ Failed to join: {str(e)}")
        
        @self.command(name='leave', aliases=['l', 'disconnect'])
        async def leave_voice(ctx):
            """Leave voice channel"""
            if self.voice_client:
                await self.voice_client.disconnect()
                self.voice_client = None
                self.is_playing = False
                self.current_channel = None
                await ctx.send("👋 Left voice channel")
            else:
                await ctx.send("❌ Not in a voice channel")
        
        @self.command(name='queue', aliases=['q'])
        async def show_queue(ctx):
            """Show current queue"""
            queue_list = self.music_queue.get_queue_list()
            if not queue_list:
                await ctx.send("📭 Queue is empty")
                return
            
            queue_text = []
            for i, item in enumerate(queue_list[:10]):  # Show first 10
                song = item['song']
                if item['current']:
                    prefix = "▶️ "
                else:
                    prefix = f"{i}. "
                queue_text.append(f"{prefix}**{song['title']}** - {song['artist']} `{song['duration']}`")
            
            remaining = len(queue_list) - 10
            if remaining > 0:
                queue_text.append(f"... and {remaining} more songs")
            
            embed = discord.Embed(title="🎼 Music Queue", description="\n".join(queue_text), color=0x00ff00)
            await ctx.send(embed=embed)
        
        @self.command(name='skip', aliases=['s'])
        async def skip_song(ctx):
            """Skip current song"""
            if self.voice_client and self.voice_client.is_playing():
                self.voice_client.stop()
                await ctx.send("⏭️ Skipped!")
            else:
                await ctx.send("❌ Nothing is playing")
        
        @self.command(name='stop')
        async def stop_music(ctx):
            """Stop music and clear queue"""
            if self.voice_client:
                self.voice_client.stop()
                self.music_queue.clear()
                self.is_playing = False
                await ctx.send("⏹️ Stopped and cleared queue")
            else:
                await ctx.send("❌ Not playing anything")
        
        @self.command(name='play', aliases=['p'])
        async def play_music(ctx, *, query: str):
            """Search and play music"""
            if not ctx.author.voice:
                await ctx.send("❌ You need to be in a voice channel!")
                return
            
            # Join voice channel if not already connected
            if not self.voice_client:
                await join_voice(ctx)
            
            # Search for the song
            await ctx.send(f"🔍 Searching for: **{query}**")
            tracks = YouTubeManager.search_tracks(query, limit=1)
            
            if not tracks:
                await ctx.send("❌ No results found")
                return
            
            song = tracks[0]
            if self.music_queue.add_song(song):
                await ctx.send(f"✅ Added to queue: **{song.title}** - {song.artist}")
                
                if not self.is_playing:
                    await self.play_next()
            else:
                await ctx.send("❌ Queue is full")
    
    async def on_ready(self):
        """Bot ready event"""
        logger.info(f'🎵 {self.user} is online!')
        web_port = self.config.get('web_port', 8888)
        logger.info(f'🌐 Web dashboard: http://localhost:{web_port}')
    
    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            return
        
        logger.error(f"Command error: {error}")
        await ctx.send(f"❌ An error occurred: {str(error)}")
    
    async def play_next(self):
        """Play next song in queue"""
        if not self.voice_client:
            self.is_playing = False
            return
        
        next_song = self.music_queue.get_next()
        if not next_song:
            self.is_playing = False
            if self.current_channel:
                await self.current_channel.send("📭 Queue is empty")
            return
        
        self.is_playing = True
        
        try:
            audio_url = YouTubeManager.get_audio_url(next_song.url)
            if not audio_url:
                logger.error(f"Failed to get audio URL for: {next_song.title}")
                if self.current_channel:
                    await self.current_channel.send(f"❌ Failed to play: **{next_song.title}**")
                await self.play_next()
                return
            
            FFMPEG_OPTIONS = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn -filter:a "volume=0.5"'
            }
            
            source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
            
            def after_playing(error):
                if error:
                    logger.error(f'Player error: {error}')
                
                # Schedule next track
                future = asyncio.run_coroutine_threadsafe(self.play_next(), self.loop)
                try:
                    future.result(timeout=5)
                except Exception as e:
                    logger.error(f"Error scheduling next track: {e}")
            
            self.voice_client.play(source, after=after_playing)
            logger.info(f"🎵 Now playing: {next_song.title}")
            
            if self.current_channel:
                embed = discord.Embed(
                    title="🎵 Now Playing",
                    description=f"**{next_song.title}**\n{next_song.artist} • {next_song.duration}",
                    color=0x00ff00
                )
                await self.current_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error playing track: {e}")
            if self.current_channel:
                await self.current_channel.send(f"❌ Error playing: **{next_song.title}**")
            await self.play_next()

class WebInterface:
    """Flask web interface"""
    
    def __init__(self, bot: MusicBot, config: Config):
        self.bot = bot
        self.config = config
        self.app = Flask(__name__)
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
                
                tracks = YouTubeManager.search_tracks(query, limit=8)
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

def main():
    """Main function"""
    try:
        # Load configuration
        config = Config()
        
        # Create bot instance
        bot = MusicBot(config)
        
        # Create web interface
        web_interface = WebInterface(bot, config)
        
        # Start Flask in separate thread
        flask_thread = threading.Thread(target=web_interface.run, daemon=True)
        flask_thread.start()
        
        # Start Discord bot
        bot.run(config.get('discord_token'))
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()