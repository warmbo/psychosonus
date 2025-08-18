#!/usr/bin/env python3
"""
Discord bot functionality for Psychosonus
"""

import asyncio
import logging
from typing import Optional

import discord
from discord.ext import commands

from config import Config
from models import Song
from queue_manager import MusicQueue
from youtube_manager import YouTubeManager

logger = logging.getLogger(__name__)

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
            
            # Search for the song on YouTube only (avoid Spotify DRM issues)
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
            # Handle Spotify tracks by searching YouTube
            if next_song.source == 'spotify':
                if self.current_channel:
                    await self.current_channel.send(f"🔍 Finding YouTube source for: **{next_song.title}** by {next_song.artist}")
                
                # Try multiple search variations
                search_queries = [
                    f"{next_song.artist} {next_song.title}",
                    f"{next_song.title} {next_song.artist}",
                    f"{next_song.title}",
                    f"{next_song.artist} - {next_song.title}"
                ]
                
                youtube_tracks = []
                for query in search_queries:
                    logger.info(f"Trying YouTube search: {query}")
                    youtube_tracks = YouTubeManager.search_tracks(query, limit=3)
                    if youtube_tracks:
                        logger.info(f"Found {len(youtube_tracks)} results for: {query}")
                        break
                
                if not youtube_tracks:
                    logger.error(f"Could not find YouTube equivalent for: {next_song.title} by {next_song.artist}")
                    if self.current_channel:
                        await self.current_channel.send(f"❌ Could not find playable source for: **{next_song.title}**")
                    await self.play_next()
                    return
                
                # Use the YouTube version
                youtube_song = youtube_tracks[0]
                playback_url = youtube_song.url
                # Update the song object for display
                next_song.youtube_url = playback_url
                logger.info(f"Found YouTube equivalent: {youtube_song.title} - {youtube_song.url}")
            else:
                # Direct YouTube URL
                playback_url = next_song.url
            
            # Extract audio URL
            audio_url = YouTubeManager.get_audio_url(playback_url)
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
                if next_song.source == 'spotify':
                    embed.add_field(name="Source", value="🎵 Spotify → YouTube", inline=True)
                else:
                    embed.add_field(name="Source", value="🎥 YouTube", inline=True)
                await self.current_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error playing track: {e}")
            if self.current_channel:
                await self.current_channel.send(f"❌ Error playing: **{next_song.title}**")
            await self.play_next()