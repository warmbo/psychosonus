#!/usr/bin/env python3
"""
Minimal Discord Music Bot with Web Interface
"""

import asyncio
import json
import threading
from collections import deque
from pathlib import Path

import discord
from discord.ext import commands
from flask import Flask, render_template_string, request, jsonify
import yt_dlp
import requests

# Load config
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    print("❌ config.json not found!")
    exit(1)

# Simple HTML template
WEB_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>🎵 Music Bot</title>
    <style>
        body { font-family: Arial, sans-serif; background: #1a1a1a; color: white; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .card { background: #2a2a2a; padding: 20px; margin: 10px 0; border-radius: 10px; }
        .search-box { width: 70%; padding: 10px; margin-right: 10px; border: none; border-radius: 5px; }
        .btn { background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
        .btn:hover { background: #45a049; }
        .song-item { background: #333; padding: 15px; margin: 5px 0; border-radius: 5px; }
        .queue-item { display: flex; justify-content: space-between; align-items: center; }
        .now-playing { border-left: 4px solid #FFD700; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 Music Bot Dashboard</h1>
        
        <div class="card">
            <h3>🔍 Search Music</h3>
            <input type="text" id="searchInput" class="search-box" placeholder="Search YouTube...">
            <button class="btn" onclick="searchMusic()">Search</button>
            <div id="searchResults"></div>
        </div>
        
        <div class="card">
            <h3>🎼 Queue</h3>
            <button class="btn" onclick="refreshQueue()">Refresh</button>
            <button class="btn" onclick="clearQueue()" style="background: #f44336;">Clear</button>
            <div id="queueList"></div>
        </div>
    </div>
    
    <script>
        async function searchMusic() {
            const query = document.getElementById('searchInput').value;
            if (!query) return;
            
            document.getElementById('searchResults').innerHTML = 'Searching...';
            
            try {
                const response = await fetch('/api/search', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({query: query})
                });
                
                const data = await response.json();
                displayResults(data.results || []);
            } catch (error) {
                document.getElementById('searchResults').innerHTML = 'Search failed';
            }
        }
        
        function displayResults(results) {
            const html = results.map(song => `
                <div class="song-item">
                    <div><strong>${song.title}</strong></div>
                    <div>${song.artist} - ${song.duration}</div>
                    <button class="btn" onclick="addToQueue('${JSON.stringify(song).replace(/'/g, "\\'")}')">Add to Queue</button>
                </div>
            `).join('');
            
            document.getElementById('searchResults').innerHTML = html;
        }
        
        async function addToQueue(songJson) {
            const song = JSON.parse(songJson);
            
            try {
                const response = await fetch('/api/queue/add', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({song: song})
                });
                
                if (response.ok) {
                    alert('Added to queue!');
                    refreshQueue();
                }
            } catch (error) {
                alert('Failed to add to queue');
            }
        }
        
        async function refreshQueue() {
            try {
                const response = await fetch('/api/queue');
                const data = await response.json();
                
                const html = data.queue.map((item, index) => `
                    <div class="song-item queue-item ${index === 0 ? 'now-playing' : ''}">
                        <div>
                            <strong>${index === 0 ? '▶️ ' : ''}${item.song.title}</strong><br>
                            ${item.song.artist}
                        </div>
                        ${index > 0 ? `<button class="btn" onclick="removeFromQueue(${index})" style="background: #f44336;">Remove</button>` : ''}
                    </div>
                `).join('');
                
                document.getElementById('queueList').innerHTML = html || 'Queue is empty';
            } catch (error) {
                document.getElementById('queueList').innerHTML = 'Failed to load queue';
            }
        }
        
        async function removeFromQueue(index) {
            try {
                await fetch('/api/queue/remove', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({index: index})
                });
                refreshQueue();
            } catch (error) {
                alert('Failed to remove from queue');
            }
        }
        
        async function clearQueue() {
            if (confirm('Clear entire queue?')) {
                try {
                    await fetch('/api/queue/clear', {method: 'POST'});
                    refreshQueue();
                } catch (error) {
                    alert('Failed to clear queue');
                }
            }
        }
        
        // Auto-refresh queue every 5 seconds
        setInterval(refreshQueue, 5000);
        refreshQueue();
    </script>
</body>
</html>
'''

class MusicQueue:
    def __init__(self):
        self.queue = deque()
        self.current_track = None
    
    def add_song(self, song_data):
        self.queue.append({'song': song_data})
        return True
    
    def get_next(self):
        if self.queue:
            self.current_track = self.queue.popleft()
            return self.current_track
        return None
    
    def remove_at_index(self, index):
        if 0 <= index - 1 < len(self.queue):
            queue_list = list(self.queue)
            queue_list.pop(index - 1)
            self.queue = deque(queue_list)
            return True
        return False
    
    def clear(self):
        self.queue.clear()
    
    def get_queue_list(self):
        queue_list = []
        if self.current_track:
            queue_list.append(self.current_track)
        queue_list.extend(list(self.queue))
        return queue_list

class YouTubeManager:
    @staticmethod
    def search_tracks(query, limit=5):
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'default_search': f'ytsearch{limit}:',
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
                            
                            tracks.append({
                                'id': entry['id'],
                                'title': entry.get('title', 'Unknown Title'),
                                'artist': entry.get('uploader', 'Unknown Artist'),
                                'duration': duration_str,
                                'url': f"https://www.youtube.com/watch?v={entry['id']}"
                            })
                
                return tracks
        except Exception as e:
            print(f"YouTube search error: {e}")
            return []
    
    @staticmethod
    def get_audio_url(youtube_url):
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                return info.get('url')
        except Exception as e:
            print(f"Error getting audio URL: {e}")
            return None

class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        
        self.music_queue = MusicQueue()
        self.voice_client = None
        self.is_playing = False
        
    async def on_ready(self):
        print(f'🎵 {self.user} is online!')
        print('🌐 Web dashboard: http://localhost:8888')
    
    @commands.command(name='join')
    async def join_voice(self, ctx):
        if not ctx.author.voice:
            await ctx.send("❌ You need to be in a voice channel!")
            return
        
        channel = ctx.author.voice.channel
        
        try:
            if self.voice_client:
                await self.voice_client.move_to(channel)
            else:
                self.voice_client = await channel.connect()
            
            await ctx.send(f"🎵 Joined **{channel.name}**\n🌐 Dashboard: http://localhost:8888")
            
            if not self.is_playing:
                await self.play_next()
                
        except Exception as e:
            await ctx.send(f"❌ Failed to join: {str(e)}")
    
    @commands.command(name='leave')
    async def leave_voice(self, ctx):
        if self.voice_client:
            await self.voice_client.disconnect()
            self.voice_client = None
            self.is_playing = False
            await ctx.send("👋 Left voice channel")
        else:
            await ctx.send("❌ Not in a voice channel")
    
    @commands.command(name='queue')
    async def show_queue(self, ctx):
        queue_list = self.music_queue.get_queue_list()
        if not queue_list:
            await ctx.send("📭 Queue is empty")
            return
        
        queue_text = []
        for i, item in enumerate(queue_list[:10]):  # Show first 10
            prefix = "▶️ " if i == 0 else f"{i}. "
            queue_text.append(f"{prefix}**{item['song']['title']}** - {item['song']['artist']}")
        
        await ctx.send("🎼 **Queue:**\n" + "\n".join(queue_text))
    
    async def play_next(self):
        if not self.voice_client:
            return
        
        next_track = self.music_queue.get_next()
        if not next_track:
            self.is_playing = False
            return
        
        self.is_playing = True
        song = next_track['song']
        
        try:
            audio_url = YouTubeManager.get_audio_url(song['url'])
            if not audio_url:
                print(f"Failed to get audio URL for: {song['title']}")
                await self.play_next()
                return
            
            FFMPEG_OPTIONS = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn'
            }
            
            source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
            
            def after_playing(error):
                if error:
                    print(f'Player error: {error}')
                
                # Schedule next track
                asyncio.run_coroutine_threadsafe(self.play_next(), self.loop)
            
            self.voice_client.play(source, after=after_playing)
            print(f"🎵 Now playing: {song['title']}")
            
        except Exception as e:
            print(f"Error playing track: {e}")
            await self.play_next()

# Global instances
music_queue = MusicQueue()
bot = MusicBot()
bot.music_queue = music_queue

# Flask web interface
app = Flask(__name__)

@app.route('/')
def dashboard():
    return render_template_string(WEB_TEMPLATE)

@app.route('/api/search', methods=['POST'])
def search_music():
    data = request.json
    query = data.get('query', '')
    
    if not query:
        return jsonify({'results': []})
    
    results = YouTubeManager.search_tracks(query)
    return jsonify({'results': results})

@app.route('/api/queue')
def get_queue():
    return jsonify({'queue': music_queue.get_queue_list()})

@app.route('/api/queue/add', methods=['POST'])
def add_to_queue():
    data = request.json
    song = data.get('song')
    
    if not song:
        return jsonify({'success': False, 'error': 'No song data'})
    
    music_queue.add_song(song)
    
    # Start playing if not already playing
    if bot.voice_client and not bot.is_playing:
        asyncio.run_coroutine_threadsafe(bot.play_next(), bot.loop)
    
    return jsonify({'success': True})

@app.route('/api/queue/remove', methods=['POST'])
def remove_from_queue():
    data = request.json
    index = data.get('index')
    
    if music_queue.remove_at_index(index):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Invalid index'})

@app.route('/api/queue/clear', methods=['POST'])
def clear_queue():
    music_queue.clear()
    return jsonify({'success': True})

def run_flask():
    app.run(host='0.0.0.0', port=8888, debug=False)

def main():
    # Start Flask in separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Start Discord bot
    bot.run(config['discord_token'])

if __name__ == "__main__":
    main()