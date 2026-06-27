import yt_dlp
import os

ydl_opts = {
    'format': '18',
    'outtmpl': 'test_video.mp4',
    'quiet': False,
    'no_warnings': False,
    'merge_output_format': 'mp4',
    'extractor_args': {'youtube': {'player_client': ['android']}},
    'writethumbnail': True
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download(['https://youtu.be/ZfWDVO3rzeA'])

print("Files in current dir:")
print([f for f in os.listdir('.') if f.startswith('test_video')])
