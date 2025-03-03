import os
import random
import asyncio
import discord
from discord.ext import commands

# Set up Discord intents
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

BOT_TOKEN = YOUR_BOT_TOKEN_HERE

# Create the bot instance
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

# Initialize the state variables for dj
is_playing = False
is_paused  = False
source     = None

@bot.command()
async def dj_start(ctx, filename: str = None):
    """
    Plays a local audio file.
    Expects the file to be in the 'audio/' directory.
    Usage: !dj [song] - leave out song name for shuffle play of entire audio folder
    """
    global is_playing, is_paused, source

    if not ctx.author.voice:
        await ctx.send("You need to be in a voice channel to play audio")
        return

    voice_channel = ctx.author.voice.channel

    # Connect to the voice channel if the bot isn't already connected
    if ctx.voice_client is None:
        vc = await voice_channel.connect()
    else:
        vc = ctx.voice_client

    # Specific song
    if filename:
        # Construct the file path; adjust this as necessary for your file structure
        file_path = f"./audio/{filename}.mp3"

        # Check if the file exists before trying to play it
        if not os.path.isfile(file_path):
            await ctx.send(f"File **{filename}.mp3** not found in `audio/`")
            return

        # Create an FFmpeg audio source from the local file
        audio_source = discord.FFmpegPCMAudio(file_path)
        
        # Play the audio source
        vc.play(audio_source, after=lambda e: print(f"Finished playing {filename}"))
        source = audio_source
        is_playing = True
        is_paused  = False
        display_name = filename.replace('_', ' ').replace('.mp3', '')
        await ctx.send(f"Now playing: **{display_name}**")

    # Shuffle
    else:
        # Get all mp3 files in the 'audio/' directory
        audio_folder = './audio/'
        audio_files = [f for f in os.listdir(audio_folder) if f.endswith('.mp3')]

        if not audio_files:
            await ctx.send("No audio files found in the 'audio/' folder!")
            return

        # Shuffle the list of audio files
        random.shuffle(audio_files)

        # Play each song in the shuffled list
        for file in audio_files:
            file_path = os.path.join(audio_folder, file)
            
            if os.path.exists(file_path):
                audio_source = discord.FFmpegPCMAudio(file_path)
                
                # Play the audio
                display_name = file.replace('_', ' ').replace('.mp3', '')
                vc.play(audio_source, after=lambda e: print(f"Finished playing {display_name}"))
                await ctx.send(f"Now playing: **{display_name}**")
                source = audio_source
                is_playing = True
                is_paused  = False

                # Wait until the audio finishes before playing the next one
                while vc.is_playing() or vc.is_paused():
                    await asyncio.sleep(1)
        await ctx.send("All songs have been played!")

@bot.command()
async def dj_pause(ctx):
    """Pauses the current song"""
    global is_playing, is_paused
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        is_paused  = True
        is_playing = False
        await ctx.send("The audio has been paused")
    else:
        await ctx.send("No audio is currently playing")

@bot.command()
async def dj_resume(ctx):
    """Resumes paused song"""
    global is_playing, is_paused
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        is_paused  = False
        is_playing = True
        await ctx.send("The audio has been resumed")
    else:
        await ctx.send("No audio is currently paused")

@bot.command()
async def dj_skip(ctx):
    """Skips the current song"""
    global is_playing, is_paused, source
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()  # Stop the current track
        is_playing = False
        is_paused  = False
        await ctx.send("The song has been skipped")
    else:
        await ctx.send("No audio is currently playing")

@bot.command()
async def dj_stop(ctx):
    """Stops the audio and disconnects the bot from the voice channel"""
    global is_playing, is_paused, source
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        is_playing = False
        is_paused = False
        source = None
        await ctx.send("Disconnected from the voice channel")

# Start the bot
bot.run(BOT_TOKEN)
