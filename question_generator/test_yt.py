import yt_dlp
import sys

ydl_opts = {
    'format': '18',
    'outtmpl': 'test.mp4',
    'extractor_args': {'youtube': {'player_client': ['android']}}
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(['https://youtu.be/ZfWDVO3rzeA'])
    print("SUCCESS")
except Exception as e:
    print("FAILED:", e)
