import os
import json
import datetime
import whisper

class VideoTranscriptGenerator:
    """
    Video Transcript Generator using OpenAI Whisper.
    """
    
    def __init__(self, model_size="base"):
        self.model_size = model_size
        self.model = None

    def _load_model(self):
        if self.model is None:
            print(f"Loading Whisper model '{self.model_size}'...")
            self.model = whisper.load_model(self.model_size)

    def _format_timestamp(self, seconds, separator=","):
        """
        Format a timestamp in seconds to HH:MM:SS,mmm format
        """
        td = datetime.timedelta(seconds=seconds)
        hours = td.seconds // 3600
        minutes = (td.seconds % 3600) // 60
        secs = td.seconds % 60
        millisecs = int(td.microseconds / 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millisecs:03d}"

    def transcribe_with_whisper(self, video_path):
        """
        Generate a transcript using OpenAI Whisper.
        """
        print(f"Transcribing {video_path} using Whisper...")
        self._load_model()
        result = self.model.transcribe(video_path)
        
        transcript_data = []
        for segment in result.get("segments", []):
            start_str = self._format_timestamp(segment["start"])
            end_str = self._format_timestamp(segment["end"])
            
            transcript_data.append({
                "start": start_str,
                "end": end_str,
                "text": segment["text"].strip()
            })
            
        return transcript_data

    def transcribe_with_speech_recognition(self, video_path):
        """
        Stub for generating a transcript using SpeechRecognition.
        Currently falling back to whisper.
        """
        print(f"SpeechRecognition requested, but falling back to Whisper...")
        return self.transcribe_with_whisper(video_path)

    def save_as_vtt(self, transcript_data, filepath):
        """
        Save transcript data as VTT format.
        """
        print(f"Saving transcript as VTT to {filepath}")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            for item in transcript_data:
                # VTT format expects a dot for milliseconds, e.g. 00:00:00.000
                start_time = item.get('start', '00:00:00,000').replace(',', '.')
                end_time = item.get('end', '00:00:00,000').replace(',', '.')
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{item['text']}\n\n")

    def save_as_srt(self, transcript_data, filepath):
        """
        Save transcript data as SRT format.
        """
        print(f"Saving transcript as SRT to {filepath}")
        with open(filepath, 'w', encoding='utf-8') as f:
            for i, item in enumerate(transcript_data, 1):
                f.write(f"{i}\n")
                # SRT expects comma for milliseconds, e.g. 00:00:00,000
                start_time = item.get('start', '00:00:00,000').replace('.', ',')
                end_time = item.get('end', '00:00:00,000').replace('.', ',')
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{item['text']}\n\n")

    def save_as_json(self, transcript_data, filepath):
        """
        Save transcript data as JSON format.
        """
        print(f"Saving transcript as JSON to {filepath}")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f, indent=4)
