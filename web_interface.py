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
            """Serve dashboard"""
            return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Psychosonus Dashboard</title>
    <style>
        body {
            font-family: monospace;
            background-color: #f0f0f0;
            color: #333;
            padding: 20px;
            line-height: 1.6;
        }
        .container {
            max-width: 800px;
            margin: auto;
            background-color: #fff;
            padding: 20px;
            border: 1px solid #ccc;
        }
        input, button {
            padding: 8px;
            margin: 5px 0;
            border: 1px solid #ccc;
            font-family: monospace;
        }
        button {
            cursor: pointer;
            background-color: #eee;
        }
        button:hover {
            background-color: #ddd;
        }
        button.play { background-color: #90EE90; }
        button.skip { background-color: #FFB6C1; }
        button.clear { background-color: #FFA07A; }
        
        #searchResults {
            margin-top: 20px;
            list-style-type: none;
            padding: 0;
        }
        .searchResultItem {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            border-bottom: 1px solid #eee;
        }
        .queueItem {
            padding: 10px;
            border-bottom: 1px solid #eee;
        }
        .status-detail {
            font-size: 0.9em;
            color: #666;
        }
    </style>
</head>
<body>

    <div class="container">
        <h1>Psychosonus Dashboard</h1>
        <p>A simple control panel for your Discord music bot.</p>

        <hr>

        <h2>Status</h2>
        <div id="status">
            <p><strong>Connected to Voice:</strong> <span id="connectedStatus">No</span> <span id="voiceChannel" class="status-detail"></span></p>
            <p><strong>Voice Playing:</strong> <span id="voicePlayingStatus">No</span></p>
            <p><strong>Bot Playing Flag:</strong> <span id="botPlayingStatus">No</span></p>
            <p><strong>Current Track:</strong> <span id="currentTrack">-</span></p>
            <p><strong>Queue Size:</strong> <span id="queueSize">0</span></p>
        </div>

        <hr>

        <h2>Search</h2>
        <div>
            <input type="text" id="searchQuery" placeholder="Search for a song or artist...">
            <button id="searchButton">Search</button>
        </div>
        <div id="searchMessage"></div>
        <ul id="searchResults"></ul>

        <hr>

        <h2>Queue Controls</h2>
        <div>
            <button id="playButton" class="play">▶️ Play</button>
            <button id="skipButton" class="skip">⏭️ Skip</button>
            <button id="clearQueueButton" class="clear">🗑️ Clear Queue</button>
        </div>
        <div id="queueMessage"></div>
        <ul id="queueList"></ul>
    </div>

    <script>
        const API_URL = '/api';

        document.addEventListener('DOMContentLoaded', () => {
            fetchStatus();
            fetchQueue();
            setInterval(fetchStatus, 3000); // Poll status every 3 seconds
            setInterval(fetchQueue, 5000); // Poll queue every 5 seconds

            document.getElementById('searchButton').addEventListener('click', searchMusic);
            document.getElementById('searchQuery').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    searchMusic();
                }
            });
            document.getElementById('playButton').addEventListener('click', forcePlay);
            document.getElementById('skipButton').addEventListener('click', skipSong);
            document.getElementById('clearQueueButton').addEventListener('click', clearQueue);
        });

        async function fetchStatus() {
            try {
                const response = await fetch(`${API_URL}/status`);
                const data = await response.json();
                if (data.success) {
                    document.getElementById('connectedStatus').textContent = data.connected ? 'Yes' : 'No';
                    document.getElementById('voicePlayingStatus').textContent = data.playing ? 'Yes' : 'No';
                    document.getElementById('botPlayingStatus').textContent = data.bot_is_playing ? 'Yes' : 'No';
                    document.getElementById('queueSize').textContent = data.queue_size;
                    document.getElementById('currentTrack').textContent = data.current_track ? `${data.current_track.title} by ${data.current_track.artist}` : '-';
                    document.getElementById('voiceChannel').textContent = data.voice_channel ? `(${data.voice_channel})` : '';
                }
            } catch (error) {
                console.error('Error fetching status:', error);
            }
        }

        async function searchMusic() {
            const query = document.getElementById('searchQuery').value.trim();
            const searchMessageEl = document.getElementById('searchMessage');
            const searchResultsEl = document.getElementById('searchResults');
            searchResultsEl.innerHTML = '';
            searchMessageEl.textContent = 'Searching...';

            if (!query) {
                searchMessageEl.textContent = 'Please enter a search query.';
                return;
            }

            try {
                const response = await fetch(`${API_URL}/search`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query })
                });
                const data = await response.json();
                if (data.success) {
                    searchMessageEl.textContent = `${data.results.length} results found.`;
                    data.results.forEach(track => {
                        const li = document.createElement('li');
                        li.className = 'searchResultItem';
                        const sourceIcon = track.source === 'spotify' ? '🎵' : '🎥';
                        li.innerHTML = `
                            <span>${sourceIcon} <strong>${track.title}</strong> by ${track.artist} (${track.duration})</span>
                            <button data-song='${JSON.stringify(track)}'>Add to Queue</button>
                        `;
                        li.querySelector('button').addEventListener('click', (e) => {
                            const songData = JSON.parse(e.target.getAttribute('data-song'));
                            addSongToQueue(songData);
                        });
                        searchResultsEl.appendChild(li);
                    });
                } else {
                    searchMessageEl.textContent = `Error: ${data.error}`;
                }
            } catch (error) {
                console.error('Search request failed:', error);
                searchMessageEl.textContent = 'Search failed. Please check the server connection.';
            }
        }

        async function fetchQueue() {
            try {
                const response = await fetch(`${API_URL}/queue`);
                const data = await response.json();
                const queueListEl = document.getElementById('queueList');
                queueListEl.innerHTML = '';
                if (data.success && data.queue.length > 0) {
                    data.queue.forEach((item, index) => {
                        const li = document.createElement('li');
                        li.className = 'queueItem';
                        const song = item.song;
                        const sourceIcon = song.source === 'spotify' ? '🎵' : '🎥';
                        li.innerHTML = `
                            <span>${item.current ? '▶️ ' : `${index}. `}${sourceIcon} <strong>${song.title}</strong> by ${song.artist} (${song.duration})</span>
                        `;
                        if (!item.current) {
                            const removeButton = document.createElement('button');
                            removeButton.textContent = 'Remove';
                            removeButton.style.marginLeft = '10px';
                            removeButton.addEventListener('click', () => removeSongFromQueue(index - (data.queue.length - data.queue.filter(q => !q.current).length)));
                            li.appendChild(removeButton);
                        }
                        queueListEl.appendChild(li);
                    });
                } else {
                    queueListEl.innerHTML = '<li>The queue is empty.</li>';
                }
            } catch (error) {
                console.error('Error fetching queue:', error);
            }
        }

        async function addSongToQueue(song) {
            try {
                const response = await fetch(`${API_URL}/queue/add`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ song: song })
                });
                const data = await response.json();
                const queueMessageEl = document.getElementById('queueMessage');
                if (data.success) {
                    queueMessageEl.textContent = `Added "${song.title}" to queue.`;
                    fetchQueue();
                    fetchStatus();
                } else {
                    queueMessageEl.textContent = `Error adding song: ${data.error}`;
                }
            } catch (error) {
                console.error('Add to queue request failed:', error);
                queueMessageEl.textContent = 'Failed to add song. Check server.';
            }
        }

        async function removeSongFromQueue(index) {
            try {
                const response = await fetch(`${API_URL}/queue/remove`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ index: index })
                });
                const data = await response.json();
                const queueMessageEl = document.getElementById('queueMessage');
                if (data.success) {
                    queueMessageEl.textContent = `Removed song at index ${index + 1} from queue.`;
                    fetchQueue();
                } else {
                    queueMessageEl.textContent = `Error removing song: ${data.error}`;
                }
            } catch (error) {
                console.error('Remove from queue request failed:', error);
                queueMessageEl.textContent = 'Failed to remove song. Check server.';
            }
        }

        async function forcePlay() {
            try {
                const response = await fetch(`${API_URL}/control/play`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                const queueMessageEl = document.getElementById('queueMessage');
                if (data.success) {
                    queueMessageEl.textContent = 'Started playing.';
                    fetchQueue();
                    fetchStatus();
                } else {
                    queueMessageEl.textContent = `Error starting playback: ${data.error}`;
                }
            } catch (error) {
                console.error('Play request failed:', error);
                queueMessageEl.textContent = 'Failed to start playback. Check server.';
            }
        }

        async function skipSong() {
            try {
                const response = await fetch(`${API_URL}/control/skip`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                const queueMessageEl = document.getElementById('queueMessage');
                if (data.success) {
                    queueMessageEl.textContent = 'Skipped current song.';
                    fetchQueue();
                    fetchStatus();
                } else {
                    queueMessageEl.textContent = `Error skipping song: ${data.error}`;
                }
            } catch (error) {
                console.error('Skip request failed:', error);
                queueMessageEl.textContent = 'Failed to skip. Check server.';
            }
        }

        async function clearQueue() {
            try {
                const response = await fetch(`${API_URL}/queue/clear`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                const queueMessageEl = document.getElementById('queueMessage');
                if (data.success) {
                    queueMessageEl.textContent = 'Queue cleared.';
                    fetchQueue();
                    fetchStatus();
                } else {
                    queueMessageEl.textContent = `Error clearing queue: ${data.error}`;
                }
            } catch (error) {
                console.error('Clear queue request failed:', error);
                queueMessageEl.textContent = 'Failed to clear queue. Check server.';
            }
        }
    </script>
</body>
</html>"""
        
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
                
                return jsonify({
                    'success': True,
                    'connected': voice_connected,
                    'playing': voice_playing,
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