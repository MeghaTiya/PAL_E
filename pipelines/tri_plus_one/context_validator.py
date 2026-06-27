try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    
import logging
import re
from typing import Dict, Any, Optional

try:
    import pytesseract  # type: ignore
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None

from core.llm.providers import LLMRouter

logger = logging.getLogger(__name__)

class ContextValidator:
    """
    Validates transcript segments by extracting and analyzing visual context
    (Frame extraction, OCR, VLM visual descriptions).
    """
    
    def __init__(self, use_vlm: bool = True):
        self.use_vlm = use_vlm
        self.tesseract_available = TESSERACT_AVAILABLE
        self.llm_router = LLMRouter() if use_vlm else None
        
        if not self.use_vlm and not self.tesseract_available:
            logger.warning("Neither VLM nor Tesseract OCR available.")

    def validate(self, video_path: str, snippet: dict) -> Optional[Dict[str, Any]]:
        """
        Validate visual context for a specific transcript snippet.
        """
        try:
            timestamp = snippet.get('time', snippet.get('timestamp', '00:00:00'))
            transcript_text = snippet.get('text', '')
            
            # Step 1: Extract frame
            frame = self._extract_frame(video_path, timestamp)
            if frame is None:
                return None
                
            # Step 2: Extract visual educational content
            if self.use_vlm:
                visual_content = self._extract_visual_content_vlm(frame, transcript_text)
            else:
                visual_content = self._extract_visual_content_ocr(frame)
                
            if not visual_content or not visual_content.get('educational_concepts'):
                # Fallback to transcript purely if visual fails
                concepts = self._extract_key_topics(transcript_text)
                return {
                    'timestamp': timestamp,
                    'slide_content': '',
                    'educational_concepts': concepts[:3] if concepts else ['General Topic'],
                    'transcript_text': transcript_text,
                    'confidence': 0.5,
                    'method': 'transcript_fallback'
                }
                
            # Build combined context
            context = {
                'timestamp': timestamp,
                'method': 'visual_first',
                'slide_content': visual_content.get('slide_text', ''),
                'educational_concepts': visual_content.get('educational_concepts', []),
                'transcript_text': transcript_text,
                'confidence': visual_content.get('confidence', 0.0)
            }
            return context
            
        except Exception as e:
            logger.error(f"Visual-first validation failed: {str(e)}")
            return None

    def _extract_frame(self, video_path: str, timestamp: str) -> Optional[Any]:
        if not CV2_AVAILABLE:
            return None
            
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None
                
            time_parts = str(timestamp).split(':')
            if len(time_parts) == 3:
                total_seconds = float(time_parts[0]) * 3600 + float(time_parts[1]) * 60 + float(time_parts[2])
            elif len(time_parts) == 2:
                total_seconds = float(time_parts[0]) * 60 + float(time_parts[1])
            else:
                total_seconds = float(time_parts[0])
                
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            
            # Cap the requested seconds to slightly before the end of the video if it exceeds
            if fps > 0 and frame_count > 0:
                duration = frame_count / fps
                if total_seconds >= duration:
                    total_seconds = max(0, duration - 0.5)
                    
            frame_number = int(total_seconds * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            ret, frame = cap.read()
            cap.release()
            return frame if ret else None
        except Exception:
            return None

    def _extract_visual_content_vlm(self, frame, transcript_context: str) -> dict:
        """
        Uses LLMRouter (Gemini/Ollama) to extract concepts from an image.
        In a full implementation, we'd pass base64 image data.
        For now, we simulate visual-to-text fallback via OCR first, then send to LLM for concept extraction.
        """
        ocr_result = self._extract_visual_content_ocr(frame)
        slide_text = ocr_result.get('slide_text', '')
        
        if not slide_text:
            return ocr_result

        prompt = f"Extract up to 5 key educational concepts from this slide text: '{slide_text}' and transcript: '{transcript_context}'. Return only a comma-separated list of concepts."
        
        try:
            response = self.llm_router.generate(prompt=prompt)
            concepts = [c.strip() for c in response.split(',') if c.strip()]
            return {
                'slide_text': slide_text,
                'educational_concepts': concepts,
                'confidence': 0.85
            }
        except Exception as e:
            logger.error(f"VLM concept extraction failed: {e}")
            return ocr_result

    def _extract_visual_content_ocr(self, frame) -> dict:
        if not self.tesseract_available or not CV2_AVAILABLE or frame is None:
            return {'slide_text': '', 'educational_concepts': [], 'confidence': 0.0}
            
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
            gray = cv2.GaussianBlur(gray, (1, 1), 0)
            
            extracted_text = pytesseract.image_to_string(gray, lang='eng').strip()
            extracted_text = re.sub(r'\s+', ' ', extracted_text)
            
            concepts = self._extract_key_topics(extracted_text)
            
            return {
                'slide_text': extracted_text,
                'educational_concepts': concepts[:5],
                'confidence': 0.7 if concepts else 0.3
            }
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return {'slide_text': '', 'educational_concepts': [], 'confidence': 0.0}

    def _extract_key_topics(self, text: str) -> list:
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'this', 'that', 'these', 'those'}
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        freq = {}
        for w in words:
            if w not in stop_words:
                freq[w] = freq.get(w, 0) + 1
                
        return sorted(freq.keys(), key=lambda x: freq[x], reverse=True)
