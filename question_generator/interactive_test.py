import streamlit as st
import os
import sys
import json
import uuid
import yt_dlp
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import shutil

# Setup path so modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from pipelines.tri_plus_one.transcript_analyzer import TranscriptAnalyzer
from pipelines.tri_plus_one.context_validator import ContextValidator
from pipelines.tri_plus_one.question_generator import QuestionGenerator
from pipelines.tri_plus_one.difficulty_rater import DifficultyRater
import webvtt

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

st.set_page_config(page_title="PAL Interactive Demo", layout="wide")

def extract_video_id(url):
    parsed = urlparse(url)
    if parsed.hostname == 'youtu.be':
        return parsed.path[1:]
    if parsed.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed.path == '/watch':
            return parse_qs(parsed.query)['v'][0]
        if parsed.path.startswith('/embed/'):
            return parsed.path.split('/')[2]
        if parsed.path.startswith('/v/'):
            return parsed.path.split('/')[2]
    return None

def main():
    st.title("PAL Tri+1 Pipeline Interactive Demo")
    
    tab1, tab2 = st.tabs(["🎥 Library / Home", "⚙️ Generate Questions"])
    
    with tab1:
        st.header("Library")
        # Find all videos in uploads folder
        videos = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.mp4')]
        if not videos:
            st.info("No videos in library yet. Go to Generate Questions tab to add some!")
        else:
            cols = st.columns(3)
            for idx, vid in enumerate(videos):
                base = os.path.splitext(vid)[0]
                thumb_path = os.path.join(UPLOAD_FOLDER, f"{base}.png")
                if not os.path.exists(thumb_path):
                    thumb_path = "https://via.placeholder.com/320x180?text=No+Thumbnail"
                
                with cols[idx % 3]:
                    play_key = f"play_state_{vid}"
                    is_playing = st.session_state.get(play_key, False)
                    
                    if is_playing:
                        st.video(os.path.join(UPLOAD_FOLDER, vid))
                        if st.button("Close Video", key=f"close_{vid}"):
                            st.session_state[play_key] = False
                            if hasattr(st, 'rerun'): st.rerun()
                            else: st.experimental_rerun()
                    else:
                        st.image(thumb_path, use_container_width=True)
                        if st.button("▶ Play Video", key=f"play_{vid}"):
                            st.session_state[play_key] = True
                            if hasattr(st, 'rerun'): st.rerun()
                            else: st.experimental_rerun()
                            
                    st.write(f"**{vid}**")
                    json_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.startswith(base) and f.endswith('.json') and '_questions_' in f]
                    if json_files:
                        with st.expander("View Questions JSON"):
                            try:
                                with open(os.path.join(UPLOAD_FOLDER, json_files[-1]), 'r') as f:
                                    st.json(json.load(f))
                            except Exception as e:
                                st.error(f"Error loading JSON: {e}")
    
    with tab2:
        st.header("Generate Questions from YouTube")
        with st.form("youtube_form"):
            url = st.text_input("Enter YouTube URL (e.g., https://www.youtube.com/watch?v=dQw4w9WgXcQ):")
            submit_button = st.form_submit_button("Start Pipeline")
        
        if submit_button:
            if not url:
                st.error("Please enter a valid URL.")
                return
            
            video_id = extract_video_id(url)
            if not video_id:
                st.error("Invalid YouTube URL.")
                return
                
            base_name = f"yt_{video_id}_{uuid.uuid4().hex[:6]}"
            video_filename = f"{base_name}.mp4"
            video_path = os.path.join(UPLOAD_FOLDER, video_filename)
            
            st.write(f"### 📥 Step 1: Downloading Video & Transcript...")
            
            # Use columns to show progress
            status_placeholder = st.empty()
            with status_placeholder.container():
                with st.spinner("Downloading from YouTube..."):
                    ydl_opts = {
                        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                        'outtmpl': video_path,
                        'quiet': True,
                        'no_warnings': True,
                        'merge_output_format': 'mp4',
                        'extractor_args': {'youtube': {'player_client': ['android']}},
                        'writesubtitles': True,
                        'writeautomaticsub': True,
                        'subtitlesformat': 'vtt',
                        'subtitleslangs': ['en'],
                        'writethumbnail': True,
                        'postprocessors': [{'key': 'FFmpegThumbnailsConvertor', 'format': 'png'}]
                    }
                    try:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([url])
                    except Exception as e:
                        st.error(f"Download failed: {e}")
                        return
                    
                st.success("✅ Download complete!")
            
            # Subtitle and Thumbnail handling
            base_video_path = os.path.splitext(video_path)[0]
            vtt_path = f"{base_video_path}.en.vtt"
            final_transcript_filename = None
            if os.path.exists(vtt_path):
                final_transcript_filename = f"{base_name}.en.vtt"
                # rename it to match standard
                shutil.move(vtt_path, os.path.join(UPLOAD_FOLDER, final_transcript_filename))
                st.write(f"Found transcript: {final_transcript_filename}")
            else:
                st.warning("No subtitles found. Make sure the video has closed captions.")
                return
                
            # Move thumbnail
            for ext in ['.png', '.webp', '.jpg', '.jpeg']:
                thumb_path = f"{base_video_path}{ext}"
                if os.path.exists(thumb_path):
                    new_thumb_path = os.path.join(UPLOAD_FOLDER, f"{base_name}.png")
                    shutil.move(thumb_path, new_thumb_path)
                    st.image(new_thumb_path, width=300)
                    break
            
            st.markdown("---")
            st.write("### 🧠 Step 2: Running Tri+1 Pipeline...")
            
            # Load Transcript
            vtt_path_to_load = os.path.join(UPLOAD_FOLDER, final_transcript_filename)
            transcript_segments = []
            try:
                for caption in webvtt.read(vtt_path_to_load):
                    transcript_segments.append({"time": caption.start.split(".")[0], "text": caption.text.replace("\n", " ")})
            except Exception as e:
                st.error(f"Failed to parse VTT: {e}")
                return
            
            # Initialize Pipeline Components
            st.write("Initializing Agents...")
            try:
                analyzer = TranscriptAnalyzer()
                validator = ContextValidator(use_vlm=True)
                generator = QuestionGenerator()
                rater = DifficultyRater()
            except Exception as e:
                st.error(f"Initialization failed: {e}")
                return
                
            # Stage 1: Transcript Analyzer
            st.subheader("1. Transcript Analyzer")
            with st.spinner("Analyzing transcript..."):
                candidates = analyzer.find_candidates(transcript_segments)
            st.success(f"Found {len(candidates)} candidate segments.")
            with st.expander("View Candidates"):
                st.json(candidates)
                
            final_questions = []
            
            progress_bar = st.progress(0)
            
            for i, segment in enumerate(candidates):
                st.markdown(f"#### Processing Segment {i+1} / {len(candidates)} (Time: {segment.get('time')})")
                
                # Stage 2: Context Validator
                with st.expander(f"Stage 2: Context Validator Output"):
                    context = validator.validate(video_path, segment)
                    if not context:
                        st.warning("Validation failed for this segment.")
                        continue
                    st.write("**Transcript snippet:**", segment.get('text'))
                    st.write("**Slide Text (OCR):**", context.get('slide_content'))
                    st.write("**Extracted Educational Concepts:**", context.get('educational_concepts'))
                    st.write("**Confidence:**", context.get('confidence'))
                
                # Stage 3: Question Generator
                with st.expander(f"Stage 3: Question Generator Output"):
                    question_output = generator.generate_questions(context, timestamp=segment.get('time'))
                    if not question_output or not question_output.questions:
                        st.warning("Question generation failed.")
                        continue
                    
                    for idx, q in enumerate(question_output.questions):
                        st.markdown(f"**Generated Question {idx+1}:** {q.q}")
                        st.markdown(f"**Answer:** {q.a}")
                        st.markdown(f"**Type:** {q.t} | **Base Difficulty:** {q.d}")
                
                # Stage 4: Difficulty Rater
                with st.expander(f"Stage 4: Difficulty Rater Output"):
                    for idx, q in enumerate(question_output.questions):
                        actual_difficulty = rater.rate_difficulty(q, context)
                        st.write(f"Question '{q.q}' rated as **{actual_difficulty}** (was {q.d})")
                        q.d = actual_difficulty
                        
                        final_questions.append({
                            "timestamp": segment.get('time'),
                            "question_data": q.model_dump(),
                            "context_metadata": context
                        })
                
                progress_bar.progress((i + 1) / len(candidates))
                
            st.success("Pipeline Execution Complete!")
            
            st.markdown("---")
            st.write("### 📄 Final Pipeline JSON Output")
            st.json(final_questions)
            
            # Save to JSON
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"{base_name}_questions_{timestamp_str}.json"
            output_path = os.path.join(UPLOAD_FOLDER, output_filename)
            
            results = {
                'video_file': video_filename,
                'transcript_file': final_transcript_filename,
                'questions': final_questions,
                'total_questions': len(final_questions),
                'timestamp': timestamp_str
            }
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            
            st.info(f"Saved results to {output_filename}")

if __name__ == "__main__":
    main()
