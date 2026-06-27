import webvtt
import re
import sys

transcript_segments = []
last_lines = []
transcript_path = "uploads/yt_Ce1m3Y0OMKA_f5eef9.en.vtt"

for caption in webvtt.read(transcript_path):
    clean_text = re.sub(r'<[^>]+>', '', caption.text)
    lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
    
    unique_lines = []
    for line in lines:
        if line not in last_lines:
            unique_lines.append(line)
            
    last_lines = lines
    
    if unique_lines:
        transcript_segments.append({
            "time": caption.start.split(".")[0], 
            "text": " ".join(unique_lines)
        })

print(len(transcript_segments))
