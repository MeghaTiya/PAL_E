"""
Flask Application for Agentic Video Question Generation Pipeline
Converts video + transcript into validated educational questions
Supports automatic transcript generation from video files
"""

import os
import sys
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory

# Add parent directory to path so 'pipelines' and 'core' can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from werkzeug.utils import secure_filename
from pipelines.tri_plus_one.pipeline import TriPlusOnePipeline
import logging
import logging
from flask_cors import CORS
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['THUMBNAIL_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

# Allowed file extensions
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'wmv'}
ALLOWED_TRANSCRIPT_EXTENSIONS = {'json', 'txt', 'srt', 'vtt'}

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['THUMBNAIL_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

def allowed_file(filename, allowed_extensions):
    """Check if uploaded file has allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/')
def index():
    """Home page with upload form"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle video and optional transcript file uploads"""
    try:
        # Check if video file is present
        if 'video' not in request.files:
            return jsonify({'error': 'Video file is required'}), 400
        
        video_file = request.files['video']
        transcript_file = request.files.get('transcript')  # Optional now
        
        if video_file.filename == '':
            return jsonify({'error': 'No video file selected'}), 400
        
        # Validate video file extension
        if not allowed_file(video_file.filename, ALLOWED_VIDEO_EXTENSIONS):
            return jsonify({'error': 'Invalid video file format'}), 400
        
        # Validate transcript file if provided
        if transcript_file and transcript_file.filename != '':
            if not allowed_file(transcript_file.filename, ALLOWED_TRANSCRIPT_EXTENSIONS):
                return jsonify({'error': 'Invalid transcript file format'}), 400
        
        # Save files securely
        video_filename = secure_filename(video_file.filename)
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)
        video_file.save(video_path)
        
        transcript_filename = None
        if transcript_file and transcript_file.filename != '':
            transcript_filename = secure_filename(transcript_file.filename)
            transcript_path = os.path.join(app.config['UPLOAD_FOLDER'], transcript_filename)
            transcript_file.save(transcript_path)
        
        logger.info(f"Video uploaded: {video_filename}")
        if transcript_filename:
            logger.info(f"Transcript uploaded: {transcript_filename}")
        
        return jsonify({
            'message': 'Files uploaded successfully',
            'video_file': video_filename,
            'transcript_file': transcript_filename,
            'has_transcript': transcript_filename is not None
        })
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/process', methods=['POST'])
def process_video():
    """Process video and generate questions with optional transcript generation"""
    try:
        data = request.get_json()
        
        if not data or 'video_file' not in data:
            return jsonify({'error': 'Video file name is required'}), 400
        
        video_filename = data['video_file']
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)
        
        if not os.path.exists(video_path):
            return jsonify({'error': 'Video file not found'}), 404
        
        # Check for transcript file or generation options
        transcript_filename = data.get('transcript_file')
        generate_transcript = data.get('generate_transcript', False)
        transcript_method = data.get('transcript_method', 'whisper')
        output_format = data.get('output_format', 'vtt')
        
        transcript_path = None
        
        # Handle transcript generation or existing file
        if generate_transcript:
            try:
                # Generate transcript using VideoTranscriptGenerator
                from agents.transcript_generator import VideoTranscriptGenerator
                
                transcript_gen = VideoTranscriptGenerator()
                
                # Generate transcript and save it
                base_name = os.path.splitext(video_filename)[0]
                transcript_filename = f"{base_name}_transcript.{output_format}"
                transcript_path = os.path.join(app.config['UPLOAD_FOLDER'], transcript_filename)
                
                # Generate transcript based on method
                if transcript_method == 'whisper':
                    transcript_data = transcript_gen.transcribe_with_whisper(video_path)
                else:
                    transcript_data = transcript_gen.transcribe_with_speech_recognition(video_path)
                
                # Save in requested format
                if output_format == 'vtt':
                    transcript_gen.save_as_vtt(transcript_data, transcript_path)
                elif output_format == 'srt':
                    transcript_gen.save_as_srt(transcript_data, transcript_path)
                else:
                    transcript_gen.save_as_json(transcript_data, transcript_path)
                
                logger.info(f"Transcript generated: {transcript_filename}")
                
            except Exception as e:
                logger.error(f"Transcript generation error: {str(e)}")
                return jsonify({'error': f'Transcript generation failed: {str(e)}'}), 500
        
        elif transcript_filename:
            # Use existing transcript file
            transcript_path = os.path.join(app.config['UPLOAD_FOLDER'], transcript_filename)
            if not os.path.exists(transcript_path):
                return jsonify({'error': 'Transcript file not found'}), 404
        else:
            return jsonify({'error': 'Either provide transcript file or enable transcript generation'}), 400
        
        # Get processing options
        num_questions = int(data.get('num_questions', 5))
        include_mcq = data.get('include_mcq', True)  # Enabled by default for enhanced types
        use_vlm = data.get('use_vlm', True)
        analysis_mode = data.get('analysis_mode', 'visual_first')  # NEW: Visual first as default
        
        logger.info(f"Processing request: {num_questions} questions, analysis_mode={analysis_mode}")
        
        # Initialize processors - Use proper pipeline approach
        try:
            from pipelines.tri_plus_one.pipeline import TriPlusOnePipeline
            pipeline = TriPlusOnePipeline(use_vlm=use_vlm)
            
            # Read actual VTT transcript
            import webvtt
            import re
            transcript_segments = []
            last_lines = []
            try:
                for caption in webvtt.read(transcript_path):
                    # Clean up YouTube's word-by-word formatting tags
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
            except Exception as e:
                logger.error(f"Failed to parse VTT transcript: {e}")
                return jsonify({'error': f"Failed to parse VTT transcript: {e}"}), 500
            
            logger.info(f"Using Tri+1 pipeline with {len(transcript_segments)} segments")
            
            # Run Visual-First pipeline
            questions = pipeline.run(video_path, transcript_segments)
            
            validated_questions = []
            
            for question in questions:
                try:
                    q_data = question.get('question_data', {})
                    segment_context = question.get('context_metadata', {})
                    
                    # Convert QuestionSchema output to frontend expected format
                    score = 5 # Mock score since LLMJudge is deprecated
                    difficulty = q_data.get('d', 'medium')
                    tags = [q_data.get('t', 'factual')]
                    
                    if score >= 2:
                        validated_questions.append({
                            'question': q_data,
                            'timestamp': question.get('timestamp', '00:00:00'),
                            'segment_text': segment_context.get('transcript_text', ''),
                            'quality_score': score,
                            'difficulty': difficulty,
                            'tags': tags,
                            'question_type': q_data.get('t', 'factual'),
                            
                            'vlm_analysis': 'Pipeline execution successful',
                            'transcript_analysis': segment_context.get('transcript_analysis', {}),
                            'educational_indicators': segment_context.get('educational_concepts', []),
                            'visual_elements': ', '.join(segment_context.get('visual_elements', [])),
                            'analysis_mode': segment_context.get('method', 'unknown')
                        })
                        
                except Exception as e:
                    logger.error(f"Error evaluating question: {e}")
                    continue
              
            # Generate output filename
            base_name = os.path.splitext(video_filename)[0]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"{base_name}_questions_{timestamp}.json"
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
            
            # Save results
            results = {
                'video_file': video_filename,
                'transcript_file': transcript_filename,
                'generated_transcript': generate_transcript,
                'processing_options': {
                    'num_questions': num_questions,
                    'include_mcq': include_mcq,
                    'use_vlm': use_vlm,
                    'analysis_mode': analysis_mode
                },
                'context_summary': f'Visual-first pipeline processed {len(questions)} questions',
                'questions': validated_questions,
                'total_questions': len(validated_questions),
                'timestamp': timestamp
            }
            
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            
            # Update lessons_index.json
            thumbnail_filename = data.get('thumbnail_file')
            lessons_index_path = os.path.join(app.config['OUTPUT_FOLDER'], 'lessons_index.json')
            lessons_list = []
            if os.path.exists(lessons_index_path):
                try:
                    with open(lessons_index_path, 'r') as f:
                        lessons_list = json.load(f)
                except Exception as e:
                    logger.error(f"Error reading lessons index: {e}")
            
            new_lesson_id = str(len(lessons_list) + 1)
            lesson_metadata = {
                "id": new_lesson_id,
                "title": os.path.splitext(video_filename)[0],
                "thumbnailFileName": f"http://localhost:5005/video/{thumbnail_filename}" if thumbnail_filename else "https://via.placeholder.com/320x180?text=Custom+Lesson",
                "vidFidName": f"http://localhost:5005/video/{video_filename}",
                "questions_file": output_filename
            }
            lessons_list.append(lesson_metadata)
            
            with open(lessons_index_path, 'w') as f:
                json.dump(lessons_list, f, indent=2)
            
            logger.info(f"Questions generated and saved: {output_filename}")
            
            return jsonify({
                'message': 'Video processed successfully',
                'results_file': output_filename,
                'questions_generated': len(validated_questions),
                'transcript_generated': generate_transcript,
                'download_url': f'/download/{output_filename}'
            })
            
        except Exception as e:
            logger.error(f"Processing error: {str(e)}")
            return jsonify({'error': f'Processing failed: {str(e)}'}), 500
        
    except Exception as e:
        logger.error(f"Process endpoint error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/questions')
def view_questions():
    """View generated questions"""
    return render_template('questions.html')

@app.route('/api/questions/<filename>')
def get_questions(filename):
    """API endpoint to get questions from a file"""
    try:
        # Questions are saved in OUTPUTS_FOLDER
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'Questions file not found'}), 404
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Extract just the questions array if it's wrapped in an object
        if isinstance(data, dict) and 'questions' in data:
            questions = data['questions']
        else:
            questions = data
        
        return jsonify(questions)
        
    except Exception as e:
        logger.error(f"Error loading questions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard-stats')
def dashboard_stats():
    """Get dashboard statistics"""
    try:
        # Count files in upload and output folders
        upload_files = len([f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                           if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], f))])
        
        output_files = len([f for f in os.listdir(app.config['OUTPUT_FOLDER']) 
                           if f.endswith('.json')])
        
        # Count different file types
        video_files = len([f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                          if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm'))])
        
        transcript_files = len([f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                               if f.lower().endswith(('.txt', '.vtt', '.srt', '.json'))])
        
        stats = {
            'total_uploads': upload_files,
            'video_files': video_files,
            'transcript_files': transcript_files,
            'generated_questions': output_files,
            'last_processed': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Dashboard stats error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/favicon.ico')
def favicon():
    """Handle favicon requests"""
    return '', 204

@app.route('/api/generate_transcript', methods=['POST'])
def generate_transcript():
    """Generate transcript from video file only"""
    try:
        data = request.get_json()
        
        if not data or 'video_file' not in data:
            return jsonify({'error': 'Video file name is required'}), 400
        
        video_filename = data['video_file']
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)
        
        if not os.path.exists(video_path):
            return jsonify({'error': 'Video file not found'}), 404
        
        transcript_method = data.get('transcript_method', 'whisper')
        output_format = data.get('output_format', 'vtt')
        
        try:
            # Generate transcript using VideoTranscriptGenerator
            from agents.transcript_generator import VideoTranscriptGenerator
            
            transcript_gen = VideoTranscriptGenerator()
            
            # Generate transcript and save it
            base_name = os.path.splitext(video_filename)[0]
            transcript_filename = f"{base_name}_transcript.{output_format}"
            transcript_path = os.path.join(app.config['UPLOAD_FOLDER'], transcript_filename)
            
            # Generate transcript based on method
            if transcript_method == 'whisper':
                transcript_data = transcript_gen.transcribe_with_whisper(video_path)
            else:
                transcript_data = transcript_gen.transcribe_with_speech_recognition(video_path)
            
            # Save in requested format
            if output_format == 'vtt':
                transcript_gen.save_as_vtt(transcript_data, transcript_path)
            elif output_format == 'srt':
                transcript_gen.save_as_srt(transcript_data, transcript_path)
            else:
                transcript_gen.save_as_json(transcript_data, transcript_path)
            
            logger.info(f"Transcript generated: {transcript_filename}")
            
            return jsonify({
                'message': 'Transcript generated successfully',
                'transcript_file': transcript_filename,
                'method': transcript_method,
                'format': output_format
            })
            
        except Exception as e:
            logger.error(f"Transcript generation error: {str(e)}")
            return jsonify({'error': f'Transcript generation failed: {str(e)}'}), 500
        
    except Exception as e:
        logger.error(f"Generate transcript endpoint error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/files')
def list_files():
    """List available question files"""
    try:
        # Questions are saved in UPLOAD_FOLDER, so look there
        question_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                         if '_questions_' in f and f.endswith('.json')]
        return jsonify({'files': question_files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/lessons_index')
def get_lessons_index():
    """Get the dynamically generated lessons index"""
    try:
        lessons_index_path = os.path.join(app.config['OUTPUT_FOLDER'], 'lessons_index.json')
        if not os.path.exists(lessons_index_path):
            return jsonify([])
        with open(lessons_index_path, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error loading lessons index: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/download/<filename>')
def download_file(filename):
    """Download generated questions file"""
    try:
        return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/video/<filename>')
def serve_video(filename):
    """Serve uploaded/downloaded video files for the frontend player"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

@app.route('/process-youtube', methods=['POST'])
def process_youtube():
    try:
        data = request.get_json()
        youtube_url = data.get('youtube_url')
        if not youtube_url:
            return jsonify({'error': 'YouTube URL is required'}), 400
        
        video_id = extract_video_id(youtube_url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
            
        base_name = f"yt_{video_id}_{uuid.uuid4().hex[:6]}"
        video_filename = f"{base_name}.mp4"
        transcript_filename = f"{base_name}_transcript.json"
        
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)
        transcript_path = os.path.join(app.config['UPLOAD_FOLDER'], transcript_filename)
        
        # 1. Download YouTube Video and Subtitles
        logger.info(f"Downloading YouTube video and subtitles for {video_id}")
        ydl_cmd = [
            "yt-dlp",
            "--extractor-args", "youtube:player_client=android",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "-o", video_path,
            "--merge-output-format", "mp4",
            "--write-sub",
            "--write-auto-sub",
            "--sub-format", "vtt",
            "--sub-lang", "en",
            "--write-thumbnail",
            "--convert-thumbnails", "png",
            youtube_url
        ]
        try:
            import subprocess
            subprocess.run(ydl_cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as yt_err:
            error_output = yt_err.stderr or ""
            if "Video unavailable" in error_output:
                return jsonify({'error': 'This YouTube video is unavailable, private, or the URL is incorrect. Please check the link.'}), 400
            if "HTTP Error 403" in error_output or "Sign in to confirm you’re not a bot" in error_output:
                return jsonify({'error': 'YouTube is blocking requests right now (403 Forbidden). Please upload a local file instead.'}), 400
            raise Exception(f"yt-dlp failed: {error_output}")
            
        # yt-dlp saves subtitles as <video_basename>.en.vtt because of our outtmpl
        base_video_path = os.path.splitext(video_path)[0]
        vtt_path = f"{base_video_path}.en.vtt"
        
        final_transcript_filename = None
        if os.path.exists(vtt_path):
            final_transcript_filename = f"{base_name}.en.vtt"
            logger.info(f"Successfully downloaded VTT subtitles: {final_transcript_filename}")
        else:
            logger.warning("No subtitles found or downloaded. Falling back to Whisper generation.")
            try:
                from agents.transcript_generator import VideoTranscriptGenerator
                transcript_gen = VideoTranscriptGenerator()
                transcript_data = transcript_gen.transcribe_with_whisper(video_path)
                
                final_transcript_filename = f"{base_name}.en.vtt"
                generated_vtt_path = os.path.join(app.config['UPLOAD_FOLDER'], final_transcript_filename)
                
                transcript_gen.save_as_vtt(transcript_data, generated_vtt_path)
                logger.info(f"Successfully generated VTT using Whisper: {final_transcript_filename}")
            except Exception as e:
                logger.error(f"Whisper generation failed: {str(e)}")
                return jsonify({'error': 'Failed to get subtitles from YouTube and Whisper generation also failed.'}), 500
            
        # Check for downloaded thumbnail
        final_thumbnail_filename = None
        import shutil
        for ext in ['.png', '.webp', '.jpg', '.jpeg']:
            thumb_path = f"{base_video_path}{ext}"
            if os.path.exists(thumb_path):
                final_thumbnail_filename = f"{base_name}.png"
                new_thumb_path = os.path.join(app.config['THUMBNAIL_FOLDER'], final_thumbnail_filename)
                
                # If not png, we should ideally convert, but we asked FFmpeg to convert to png
                # Just in case, move it and rename to .png
                shutil.move(thumb_path, new_thumb_path)
                break
            
        return jsonify({
            'message': 'YouTube video processed successfully',
            'video_file': video_filename,
            'transcript_file': final_transcript_filename,
            'thumbnail_file': final_thumbnail_filename
        })
        
    except Exception as e:
        logger.error(f"Process YouTube endpoint error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 500MB.'}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5005)
