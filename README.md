# music-bot
A Discord bot for local and online (YouTube) audio playback!

Programmed in conjunction with Gemini

## Dependencies
```
discord.py
python-dotenv
yt-dlp
PyNaCl
ffmpeg
davey (for discord.py 2.7.x and up)
```

## Setup
Create a `.env` file in your directory with:
```
DISCORD_TOKEN=[your_discord_bot_token]
```

### DJ Commands (Local)

| Command | Description |
| :--- | :--- |
| `!dj_play [song]` | Play a specified local song (name or subdirectory path) |
| `!dj_play` | Shuffle play all local songs |
| `!dj_pause` | Pause current song |
| `!dj_resume` | Resume paused song |
| `!dj_skip` | Skip current song |
| `!dj_list` | List all available music |
| `!dj_stop` | Stop music playback and disconnect |

### YouTube Commands

| Command | Description |
| :--- | :--- |
| `!yt_play [song]` | Play a specified YouTube video or playlist (name or URL) |
| `!yt_pause` | Pause current video |
| `!yt_resume` | Resume paused video |
| `!yt_skip` | Skip current video |
| `!yt_queue` | Show the YouTube queue |
| `!yt_clear` | Clear the YouTube queue |
| `!yt_stop` | Stop YouTube playback and disconnect |

#### Notes
!dj_play: If no song name is specified, the entirety of the audio source directory will be shuffle played. If a subdirectory is specified, that directory will be shuffle played.

!yt_play: If a name is specified, the video which appears first in a YouTube search of that name will be played
