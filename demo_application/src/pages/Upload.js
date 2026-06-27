import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useLearningAppFascade } from "../useSingleton/useLearningAppFascade";
import { useLessonList } from "../useSingleton/useLessonList";
import { Lesson } from "../model/Lesson";
import { Question } from "../model/Question";
import loginStyle from "../stylesheets/login.module.css";
import sidebarStyles from "../stylesheets/sidebar.module.css";
import videoGridStyles from "../stylesheets/videoGrid.module.css";

function Upload() {
  const navigate = useNavigate();
  const { startNewLesson } = useLearningAppFascade();
  const { addLesson } = useLessonList();
  
  const [uploadMode, setUploadMode] = useState("local"); // "local" or "youtube"
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [videoFile, setVideoFile] = useState(null);
  const [transcriptFile, setTranscriptFile] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");

  const handleVideoChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setVideoFile(e.target.files[0]);
    }
  };

  const handleTranscriptChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setTranscriptFile(e.target.files[0]);
    }
  };

  // Helper to convert timestamp strings like "00:01:23" to seconds
  const timestampToSeconds = (timestamp) => {
    if (!timestamp || typeof timestamp !== "string") {
      return 0;
    }
    const parts = timestamp.split(":").map(Number);
    if (parts.length === 3) {
      return parts[0] * 3600 + parts[1] * 60 + parts[2];
    } else if (parts.length === 2) {
      return parts[0] * 60 + parts[1];
    }
    return 0;
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (uploadMode === "local" && !videoFile) {
      setStatusMessage("Please select a video file first.");
      return;
    }
    if (uploadMode === "youtube" && !youtubeUrl) {
      setStatusMessage("Please enter a YouTube URL.");
      return;
    }

    setIsLoading(true);
    setStatusMessage(uploadMode === "local" ? "Uploading files..." : "Downloading YouTube video and extracting transcript...");

    try {
      let uploadedVideoName = null;
      let uploadedTranscriptName = null;
      let uploadedThumbnailName = null;
      let videoObjectUrl = "";

      if (uploadMode === "local") {
        // 1. Upload local files
        const formData = new FormData();
        formData.append("video", videoFile);
        if (transcriptFile) {
          formData.append("transcript", transcriptFile);
        }

        const uploadRes = await fetch("http://localhost:5005/upload", {
          method: "POST",
          body: formData,
        });

        if (!uploadRes.ok) {
          const errorData = await uploadRes.json();
          throw new Error(errorData.error || "Upload failed");
        }

        const uploadData = await uploadRes.json();
        uploadedVideoName = uploadData.video_file;
        uploadedTranscriptName = uploadData.transcript_file;
        videoObjectUrl = URL.createObjectURL(videoFile);
        
      } else {
        // 1. Process YouTube link
        const ytRes = await fetch("http://localhost:5005/process-youtube", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ youtube_url: youtubeUrl }),
        });

        if (!ytRes.ok) {
          const errorData = await ytRes.json();
          throw new Error(errorData.error || "YouTube processing failed");
        }

        const ytData = await ytRes.json();
        uploadedVideoName = ytData.video_file;
        uploadedTranscriptName = ytData.transcript_file;
        uploadedThumbnailName = ytData.thumbnail_file;
        videoObjectUrl = `http://localhost:5005/video/${uploadedVideoName}`;
      }

      // 2. Process to generate questions
      setStatusMessage("Analyzing content and generating questions...");
      
      const processPayload = {
        video_file: uploadedVideoName,
        generate_transcript: !uploadedTranscriptName, // generate if no transcript provided
      };
      
      if (uploadedTranscriptName) {
        processPayload.transcript_file = uploadedTranscriptName;
      }
      if (uploadedThumbnailName) {
        processPayload.thumbnail_file = uploadedThumbnailName;
      }

      const processRes = await fetch("http://localhost:5005/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(processPayload),
      });

      if (!processRes.ok) {
        const errorData = await processRes.json();
        throw new Error(errorData.error || "Processing failed");
      }

      const processData = await processRes.json();
      const resultsFile = processData.results_file;

      // 3. Fetch questions
      setStatusMessage("Fetching generated questions...");
      const questionsRes = await fetch(`http://localhost:5005/api/questions/${resultsFile}`);
      if (!questionsRes.ok) throw new Error("Failed to fetch questions");
      
      let questionsData = await questionsRes.json();
      if (questionsData.questions) {
         questionsData = questionsData.questions;
      }

      // 4. Parse questions and create Lesson
      setStatusMessage("Preparing your custom lesson...");
      
      const parsedQuestions = [];
      let lastTimestamp = -1;

      questionsData.forEach((jsonQuestion) => {
        const seconds = timestampToSeconds(jsonQuestion.timestamp);
        
        // Group by timestamp like DataLoader does
        if (parsedQuestions.length === 0 || lastTimestamp !== seconds) {
          parsedQuestions.push(new Question(seconds));
          lastTimestamp = seconds;
        }

        const currentQ = parsedQuestions[parsedQuestions.length - 1];
        
        let answerText = jsonQuestion.question.answer || jsonQuestion.question.a || "A";
        let options = jsonQuestion.question.options || [];
        
        let correctAnswerLetter = "A";
        
        // If the answer is just a letter "A", "B", "C", "D"
        if (["A", "B", "C", "D"].includes(answerText.trim().toUpperCase())) {
            correctAnswerLetter = answerText.trim().toUpperCase();
        } else {
            // The answer is actual text!
            if (options.length === 0) {
                options = [answerText, "False option 1", "False option 2", "False option 3"];
                correctAnswerLetter = "A";
            } else {
                let idx = options.indexOf(answerText);
                if (idx === -1) {
                    options[0] = answerText;
                    correctAnswerLetter = "A";
                } else {
                    correctAnswerLetter = ["A", "B", "C", "D"][idx] || "A";
                }
            }
        }
        
        if (options.length < 4) {
          options = [...options, ...Array(4 - options.length).fill("N/A")];
        }

        currentQ.addDifficulty(
          jsonQuestion.question.text || jsonQuestion.question.q || "Generated Question",
          options,
          correctAnswerLetter,
          jsonQuestion.question.detailed_answer || jsonQuestion.question.explanation || answerText || "No detailed answer provided.",
          jsonQuestion.difficulty || jsonQuestion.question.d || "medium"
        );
      });

      const lessonTitle = uploadMode === "local" ? videoFile.name : "YouTube Lesson";
      
      const thumbUrl = uploadedThumbnailName 
        ? `http://localhost:5005/video/${uploadedThumbnailName}` 
        : "https://via.placeholder.com/320x180?text=Custom+Lesson";
      
      const newLesson = new Lesson(
        Date.now(),
        "Custom Lesson: " + lessonTitle,
        parsedQuestions,
        thumbUrl,
        videoObjectUrl
      );

      // Add to global lesson list so it appears on Home
      addLesson(newLesson);
      
      setIsLoading(false);
      navigate("/home");

    } catch (error) {
      console.error(error);
      setStatusMessage(`Error: ${error.message}`);
      setIsLoading(false);
    }
  };

  const GoHome = () => {
    navigate("/home");
  };

  return (
    <div className={videoGridStyles.body}>
      <div className={sidebarStyles.sidebar}>
        <button name="home_button" type="button" onClick={GoHome}>
          Home
        </button>
      </div>
      
      <div className={videoGridStyles.videoGrid} style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <div className={loginStyle.formContainer}>
          <h2 style={{ color: 'white', marginBottom: '20px', textAlign: 'center' }}>Create Custom Lesson</h2>
          
          <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', marginBottom: '20px' }}>
            <button 
              type="button" 
              onClick={() => setUploadMode("local")}
              style={{
                padding: '8px 16px',
                backgroundColor: uploadMode === "local" ? '#4f46e5' : '#374151',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Local File
            </button>
            <button 
              type="button" 
              onClick={() => setUploadMode("youtube")}
              style={{
                padding: '8px 16px',
                backgroundColor: uploadMode === "youtube" ? '#4f46e5' : '#374151',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              YouTube Link
            </button>
          </div>

          <form onSubmit={handleUpload} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            {uploadMode === "local" ? (
              <>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <label style={{ color: 'white', marginBottom: '5px' }}>Video File (.mp4)</label>
                  <input 
                    type="file" 
                    accept="video/mp4,video/x-m4v,video/*" 
                    onChange={handleVideoChange} 
                    style={{ color: 'white' }}
                    disabled={isLoading}
                  />
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <label style={{ color: 'white', marginBottom: '5px' }}>Transcript (Optional)</label>
                  <input 
                    type="file" 
                    accept=".txt,.json,.srt,.vtt,.docx" 
                    onChange={handleTranscriptChange} 
                    style={{ color: 'white' }}
                    disabled={isLoading}
                  />
                </div>
              </>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <label style={{ color: 'white', marginBottom: '5px' }}>YouTube URL</label>
                <input 
                  type="url" 
                  placeholder="https://www.youtube.com/watch?v=..."
                  value={youtubeUrl}
                  onChange={(e) => setYoutubeUrl(e.target.value)} 
                  style={{ 
                    padding: '10px', 
                    borderRadius: '4px',
                    border: '1px solid #4b5563',
                    backgroundColor: '#374151',
                    color: 'white'
                  }}
                  disabled={isLoading}
                />
              </div>
            )}
            
            <button 
              type="submit" 
              className={loginStyle.formContainerLinkButton} 
              style={{ marginTop: '15px', border: 'none', cursor: 'pointer', textAlign: 'center', backgroundColor: isLoading ? '#6b7280' : '#4f46e5' }}
              disabled={isLoading || (uploadMode === "local" ? !videoFile : !youtubeUrl)}
            >
              {isLoading ? "Processing..." : "Generate Lesson"}
            </button>
          </form>
          
          {statusMessage && (
            <p style={{ color: 'lightblue', marginTop: '20px', textAlign: 'center', fontSize: '14px' }}>
              {statusMessage}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default Upload;
