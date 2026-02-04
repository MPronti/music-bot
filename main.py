import os
import random
import asyncio
import logging
from typing import Optional, List, Dict
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ---------------------------------------------
# SETUP & CONFIG
# ---------------------------------------------
load_dotenv()
BOT_TOKEN = os.getenv('DISCORD_TOKEN')

logger = logging.getLogger('discord')

MUSIC_DIRECTORY = "[YOUR PATH HERE]"
ALLOWED_EXTENSIONS = {'.mp3', '.wav', '.flac', '.ogg', '.m4a'}

from youtube import create_youtube_audio_source, get_youtube_info

def create_normalized_audio_source(file_path: str) -> discord.FFmpegPCMAudio:
    """Create a normalized audio source using FFmpeg filters."""
    options = {
        'options': '-af "dynaudnorm=f=200:g=15:p=0.95"'
    }
    return discord.FFmpegPCMAudio(file_path, **options)

# ---------------------------------------------
# STATE MANAGEMENT
# ---------------------------------------------
class GuildState:
    def __init__(self):
        # DJ (local file) player state
        self.is_playing_dj = False
        self.is_paused_dj = False
        self.dj_queue: List[str] = []
        
        # YouTube player state
        self.yt_queue: List[Dict] = []
        self.yt_now_playing: Optional[Dict] = None 
        
        # Flag to prevent disconnects when switching between DJ and YT
        self.is_switching_sources = False

guild_states: Dict[int, GuildState] = {}

def get_guild_state(guild_id: int) -> GuildState:
    if guild_id not in guild_states:
        guild_states[guild_id] = GuildState()
    return guild_states[guild_id]

# ---------------------------------------------
# BOT SETUP
# ---------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print('------')
    print(f'Guilds: {[guild.name for guild in bot.guilds]}')
    print('------')
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s).")
    except Exception as e:
        logger.error("Error syncing commands:", exc_info=e)

@bot.tree.command(name="commands", description="Display bot commands")
async def commands_slash(interaction: discord.Interaction):
    response = (
        "```DJ Commands:\n"
        "!dj_play [song]:  Play specified song (name or path)\n"
        "!dj_play:         Shuffle play all local songs\n"
        "!dj_pause:        Pause current song\n"
        "!dj_resume:       Resume paused song\n"
        "!dj_skip:         Skip current song\n"
        "!dj_list:         List all available music\n"
        "!dj_stop:         Stop music and disconnect\n"
        "\nYouTube Commands:\n"
        "!yt_play [url]:   Play a YouTube video or playlist\n"
        "!yt_pause:        Pause current video\n"
        "!yt_resume:       Resume paused video\n"
        "!yt_skip:         Skip current video\n"
        "!yt_queue:        Show the YouTube queue\n"
        "!yt_clear:        Clear the YouTube queue\n"
        "!yt_stop:         Stop YouTube playback and disconnect```"
    )
    await interaction.response.send_message(response)

# ---------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------
def find_song_paths(target_name, search_path):
    """Recursively searches for allowed audio files matching 'target_name'."""
    matches = []
    target_lower = target_name.lower()
    for root, dirs, files in os.walk(search_path):
        for file in files:
            _, ext = os.path.splitext(file)
            if ext.lower() in ALLOWED_EXTENSIONS:
                fname_no_ext = os.path.splitext(file)[0]
                if fname_no_ext.lower() == target_lower:
                    matches.append(os.path.join(root, file))
    return matches

def get_all_songs(search_path):
    """Recursively gets all valid audio files."""
    all_songs = []
    for root, dirs, files in os.walk(search_path):
        for file in files:
            _, ext = os.path.splitext(file)
            if ext.lower() in ALLOWED_EXTENSIONS:
                all_songs.append(os.path.join(root, file))
    return all_songs

async def get_or_move_voice_client(ctx, voice_channel):
    if ctx.voice_client is None:
        return await voice_channel.connect()
    if ctx.voice_client.channel != voice_channel:
        await ctx.voice_client.move_to(voice_channel)
    return ctx.voice_client

# ---------------------------------------------
# DJ SYSTEM (LOCAL)
# ---------------------------------------------
async def after_dj_playback(ctx, vc, error):
    guild_state = get_guild_state(ctx.guild.id)
    if error:
        logger.error(f"Error in DJ playback: {error}")
        await ctx.send(f"An error occurred: {error}!")

    # Check for switching flag to prevent premature disconnect
    if guild_state.is_switching_sources:
        return

    if guild_state.dj_queue:
        await play_next_dj_song(ctx, vc)
    else:
        guild_state.is_playing_dj = False
        await ctx.send("DJ queue finished")
        if vc.is_connected():
            await vc.disconnect()

async def play_next_dj_song(ctx, vc):
    guild_state = get_guild_state(ctx.guild.id)
    if not guild_state.dj_queue:
        return await after_dj_playback(ctx, vc, None)

    file_path = guild_state.dj_queue.pop(0)
    
    if not os.path.exists(file_path):
        await ctx.send(f"File not found: {file_path}, skipping!")
        return await after_dj_playback(ctx, vc, None)

    try:
        audio_source = create_normalized_audio_source(file_path)
        display_name = os.path.basename(file_path)
        
        vc.play(
            audio_source,
            after=lambda e: asyncio.run_coroutine_threadsafe(after_dj_playback(ctx, vc, e), bot.loop)
        )
        guild_state.is_playing_dj = True
        guild_state.is_paused_dj = False
        await ctx.send(f"Now playing: **{display_name}**")
        
    except Exception as e:
        await ctx.send(f"Error playing file: {e}!")
        await after_dj_playback(ctx, vc, e)

@bot.command()
async def dj_play(ctx, *, filename: Optional[str] = None):
    if not ctx.author.voice:
        return await ctx.send("You need to be in a voice channel!")

    guild_state = get_guild_state(ctx.guild.id)
    voice_channel = ctx.author.voice.channel
    vc = await get_or_move_voice_client(ctx, voice_channel)

    found_path = None
    display_name = None

    if filename:
        matches = find_song_paths(filename, MUSIC_DIRECTORY)
        if not matches:
            return await ctx.send(f"Could not find **'{filename}'**!")
        elif len(matches) > 1:
            msg = f"Found **{len(matches)}** songs named '{filename}':\n```"
            for match in matches:
                msg += f"- {os.path.relpath(match, MUSIC_DIRECTORY)}\n"
            msg += "```\nPlease use a specific path"
            return await ctx.send(msg)
        else:
            found_path = matches[0]
            display_name = os.path.basename(found_path)

    # Prepare transition
    guild_state.yt_queue.clear()
    guild_state.yt_now_playing = None
    guild_state.dj_queue.clear()

    if found_path:
        guild_state.dj_queue.append(found_path)
        await ctx.send(f"Queued up: **{display_name}**")
    else:
        # Shuffle
        audio_files = get_all_songs(MUSIC_DIRECTORY)
        if not audio_files:
            return await ctx.send(f"No audio files found in {MUSIC_DIRECTORY}!")
        random.shuffle(audio_files)
        guild_state.dj_queue.extend(audio_files)
        await ctx.send(f"Queued {len(audio_files)} songs from the playlist")

    # Trigger playback
    if vc.is_playing() or vc.is_paused():
        # Set switching flag so the 'after' callback doesn't disconnect or play wrong thing
        guild_state.is_switching_sources = True 
        vc.stop()
        # Allow a brief moment for cleanup/callback
        await asyncio.sleep(0.1)
        guild_state.is_switching_sources = False
        
    if guild_state.dj_queue:
        await play_next_dj_song(ctx, vc)

@bot.command()
async def dj_list(ctx):
    if not os.path.exists(MUSIC_DIRECTORY):
        return await ctx.send(f"Error: Directory `{MUSIC_DIRECTORY}` does not exist!")

    await ctx.send(f"**Listing files in:** `{MUSIC_DIRECTORY}`")
    lines = []
    for root, dirs, files in os.walk(MUSIC_DIRECTORY):
        level = root.replace(MUSIC_DIRECTORY, '').count(os.sep)
        indent = ' ' * 4 * level
        folder_name = os.path.basename(root)
        if level == 0: lines.append(f"{folder_name}/")
        else: lines.append(f"{indent}{folder_name}/")
        
        sub_indent = ' ' * 4 * (level + 1)
        for f in files:
            _, ext = os.path.splitext(f)
            if ext.lower() in ALLOWED_EXTENSIONS:
                lines.append(f"{sub_indent}- {f}")

    if not lines: return await ctx.send("Directory is empty!")

    messages = []
    chunk = "```text\n"
    for line in lines:
        if len(chunk) + len(line) + 10 > 1900:
            chunk += "```"
            messages.append(chunk)
            chunk = "```text\n"
        chunk += line + "\n"
    chunk += "```"
    messages.append(chunk)

    for msg in messages: await ctx.send(msg)

@bot.command()
async def dj_skip(ctx):
    if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
        await ctx.send("Skipping song...")
        ctx.voice_client.stop()
    else:
        await ctx.send("Nothing is playing!")

@bot.command()
async def dj_stop(ctx):
    guild_state = get_guild_state(ctx.guild.id)
    if ctx.voice_client:
        guild_state.dj_queue.clear()
        guild_state.is_playing_dj = False
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected")

@bot.command()
async def dj_pause(ctx):
    guild_state = get_guild_state(ctx.guild.id)
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        guild_state.is_paused_dj = True
        await ctx.send("Paused")

@bot.command()
async def dj_resume(ctx):
    guild_state = get_guild_state(ctx.guild.id)
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        guild_state.is_paused_dj = False
        await ctx.send("Resumed")

# ---------------------------------------------
# YOUTUBE SYSTEM
# ---------------------------------------------
async def after_youtube_playback(ctx, vc, error):
    guild_state = get_guild_state(ctx.guild.id)
    guild_state.yt_now_playing = None 
    if error:
        logger.error(f"Error during YouTube playback: {error}")
        await ctx.send(f"An error occurred: {error}!")

    if guild_state.is_switching_sources:
        return

    if guild_state.yt_queue:
        await play_next_youtube(ctx, vc)
    else:
        await ctx.send("YouTube queue finished")
        if vc.is_connected():
            await vc.disconnect()

async def play_next_youtube(ctx, vc):
    guild_state = get_guild_state(ctx.guild.id)
    if not guild_state.yt_queue:
        return await after_youtube_playback(ctx, vc, None)

    current_song = guild_state.yt_queue.pop(0)
    guild_state.yt_now_playing = current_song

    try:
        stream_url = current_song.get('url')
        if not stream_url: raise ValueError("Missing stream URL!")

        audio_source = create_youtube_audio_source(stream_url)
        vc.play(
            audio_source,
            after=lambda e: asyncio.run_coroutine_threadsafe(after_youtube_playback(ctx, vc, e), bot.loop)
        )
        await ctx.send(f"Now playing: **{current_song['title']}**")
    except Exception as e:
        logger.error(f"Error playing YouTube video: {e}")
        await ctx.send(f"Failed to play **{current_song.get('title')}**, skipping!")
        await after_youtube_playback(ctx, vc, e)

@bot.command()
async def yt_play(ctx, *, url: str):
    if not ctx.author.voice:
        return await ctx.send("You need to be in a voice channel!")
    
    guild_state = get_guild_state(ctx.guild.id)
    vc = await get_or_move_voice_client(ctx, ctx.author.voice.channel)

    # Prepare transition: Prevent disconnects if DJ is running
    if guild_state.is_playing_dj or guild_state.is_paused_dj or guild_state.dj_queue:
        guild_state.is_switching_sources = True
        guild_state.dj_queue.clear()
        guild_state.is_playing_dj = False
        vc.stop() 
        await ctx.send("Switching to YouTube")

    async def process_and_play():
        msg = await ctx.send(f"Processing request")
        try:
            loop = asyncio.get_event_loop()
            video_list = await loop.run_in_executor(None, get_youtube_info, url)
            
            if not video_list:
                return await msg.edit(content="Failed to get video information!")

            items_added = 0
            for v in video_list:
                if v and v.get('url'):
                    guild_state.yt_queue.append({
                        'title': v.get('title', 'Unknown'),
                        'url': v.get('url'),
                        'duration': v.get('duration')
                    })
                    items_added += 1

            if items_added == 0:
                return await msg.edit(content="No playable videos found!")
            
            txt = f"Added **{video_list[0]['title']}**" if items_added == 1 else f"Added **{items_added}** videos"
            await msg.edit(content=txt)

            # Reset flag now that queue is ready
            guild_state.is_switching_sources = False

            if not vc.is_playing() and not vc.is_paused():
                await play_next_youtube(ctx, vc)

        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            await msg.edit(content=f"Error: {e}!")
            guild_state.is_switching_sources = False

    bot.loop.create_task(process_and_play())

@bot.command()
async def yt_skip(ctx):
    if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
        await ctx.send("Skipping...")
        ctx.voice_client.stop()
    else:
        await ctx.send("Nothing is playing!")

@bot.command()
async def yt_stop(ctx):
    guild_state = get_guild_state(ctx.guild.id)
    if ctx.voice_client:
        guild_state.yt_queue.clear()
        guild_state.yt_now_playing = None
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected")

@bot.command()
async def yt_queue(ctx):
    guild_state = get_guild_state(ctx.guild.id)
    if not guild_state.yt_queue:
        return await ctx.send("YouTube queue is empty!")
    
    lines = [f"{i+1}. {v['title']}" for i, v in enumerate(guild_state.yt_queue[:10])]
    resp = "**YouTube Queue:**\n" + "\n".join(lines)
    if len(guild_state.yt_queue) > 10: resp += f"\n...and {len(guild_state.yt_queue)-10} more"
    await ctx.send(resp)

@bot.command()
async def yt_clear(ctx):
    get_guild_state(ctx.guild.id).yt_queue.clear()
    await ctx.send("YouTube queue cleared")

@bot.command()
async def yt_pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("YouTube paused")

@bot.command()
async def yt_resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("YouTube resumed")

bot.run(BOT_TOKEN)
