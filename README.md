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
```

## Setup
Create a `.env` file in your directory with:
```
DISCORD_TOKEN=[your_discord_bot_token]
```

### DJ Commands (Local)

| Command | Description |
| :--- | :--- |
| `!dj_play [song]` | Play specified song (name or path) |
| `!dj_play` | Shuffle play all local songs |
| `!dj_pause` | Pause current song |
| `!dj_resume` | Resume paused song |
| `!dj_skip` | Skip current song |
| `!dj_list` | List all available music |
| `!dj_stop` | Stop music playback and disconnect |

### YouTube Commands

| Command | Description |
| :--- | :--- |
| `!yt_play [url]` | Play a YouTube video or playlist |
| `!yt_pause` | Pause current video |
| `!yt_resume` | Resume paused video |
| `!yt_skip` | Skip current video |
| `!yt_queue` | Show the YouTube queue |
| `!yt_clear` | Clear the YouTube queue |
| `!yt_stop` | Stop YouTube playback and disconnect |
