import { Lesson } from "../model/Lesson";
import { Question } from "../model/Question";
import { useEffect, useState } from "react";
import { useLearningAppFascade } from "../useSingleton/useLearningAppFascade";
import { useLessonList } from "../useSingleton/useLessonList";

function DataLoader() {
  const [isInitializedReady, setIsInitializedReady] = useState(false);
  const { resumeLesson, currentLesson } = useLearningAppFascade();
  const { addLesson, lessons } = useLessonList();

  function timestampToSeconds(timestamp) {
    if (!timestamp || typeof timestamp !== "string") {
      return 0; // fallback if missing
    }

    const parts = timestamp.split(":").map(Number);

    if (parts.length === 3) {
      const [hours, minutes, seconds] = parts;
      return hours * 3600 + minutes * 60 + seconds;
    } else if (parts.length === 2) {
      const [minutes, seconds] = parts;
      return minutes * 60 + seconds;
    }

    return 0;
  }
  // Run to Initialize data in App
  useEffect(() => {
    // Flag to prevent state update after component unmounts
    let ignore = false;

        const initializeData = async () => {
      try {
        let indexData = null;
        try {
          const indexRes = await fetch("http://localhost:5005/api/lessons_index");
          if (indexRes.ok) {
            indexData = await indexRes.json();
          }
        } catch (e) {
          console.log("No custom lessons index found or server offline, loading default data...");
        }

        if (!ignore && lessons.length === 0) {
          if (indexData && indexData.length > 0) {
            // Load custom dynamic lessons
            for (const item of indexData) {
              const qRes = await fetch(`http://localhost:5005/api/questions/${item.questions_file}`);
              if (!qRes.ok) continue;
              const qDataRaw = await qRes.json();
              const questionsData = qDataRaw.questions || qDataRaw;
              
              var questions = [];
              let lastTimestamp = -1;
              questionsData.forEach((jsonquestion) => {
                 const seconds = timestampToSeconds(jsonquestion.timestamp);
                 if (questions.length === 0 || lastTimestamp !== seconds) {
                   questions.push(new Question(seconds));
                   lastTimestamp = seconds;
                 }
                 const currentQ = questions[questions.length - 1];
                 let answerText = jsonquestion.question.answer || jsonquestion.question.a || "A";
                 let options_raw = jsonquestion.question.options || [];
                 let options = [];
                 if (options_raw && typeof options_raw === "object" && !Array.isArray(options_raw)) {
                     options = [
                         options_raw.a || options_raw.A || "", 
                         options_raw.b || options_raw.B || "", 
                         options_raw.c || options_raw.C || "", 
                         options_raw.d || options_raw.D || ""
                     ].filter(x => x !== "");
                 } else if (Array.isArray(options_raw)) {
                     options = options_raw;
                 }
                 
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
                   jsonquestion.question.text || jsonquestion.question.q || "Generated Question",
                   options,
                   correctAnswerLetter,
                   jsonquestion.question.detailed_answer || jsonquestion.question.explanation || answerText || "No answer",
                   jsonquestion.difficulty || jsonquestion.question.d || "medium"
                 );
              });

              const lessonInstance = new Lesson(
                item.id,
                item.title,
                questions,
                item.thumbnailFileName,
                item.vidFidName
              );
              addLesson(lessonInstance);
            }
          } else {
            let res;
            try {
              res = await fetch("data/custom_lesson.json");
              if (!res.ok) throw new Error("Not found");
            } catch (err) {
              // Fallback to original hardcoded default lesson
              res = await fetch("data/D2-S1_Corln.v.Causn_questions_20250829_081747.json");
            }
            const data = await res.json();
            data.forEach((item) => {
              var questions = [];
              item.questions.forEach((jsonquestion, index) => {
                if (
                  index === 0 ||
                  item.questions[index - 1].timestamp !== jsonquestion.timestamp
                ) {
                  questions.push(new Question(timestampToSeconds(jsonquestion.timestamp)))
                }
                questions[questions.length - 1].addDifficulty(
                    jsonquestion.question.text,
                    jsonquestion.question.options,
                    jsonquestion.question.answer,
                    jsonquestion.question.detailed_answer,
                    jsonquestion.question.difficulty
                  );
              });
              const lessonInstance = new Lesson(
                item.id,
                item.title,
                questions,
                item.thumbnailFileName,
                item.video_file
              );
              addLesson(lessonInstance);
            });
          }
          setIsInitializedReady(true);
        }
      } catch (err) {
        console.error("Failed to load lessons:", err);
        if (!ignore) {
          setIsInitializedReady(true); // Still signal readiness on error
        }
      }
    };

    initializeData();

    // Cleanup function: runs when the component unmounts
    return () => {
      ignore = true;
    };
  }, [addLesson, lessons.length]);

  // Load saved lesson from localStorage on mount
  useEffect(() => {
    if (isInitializedReady) {
      const saved = localStorage.getItem("currentLesson");
      if (saved && saved !== "undefined") {
        resumeLesson(saved);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isInitializedReady]);

  // Save current lesson to localStorage on unload
  useEffect(() => {
    if (isInitializedReady) {
      const handleBeforeUnload = () => {
        if (currentLesson) {
          const id = currentLesson.getId();
          localStorage.setItem("currentLesson", id);
        }
      };

      window.addEventListener("beforeunload", handleBeforeUnload);
      return () => {
        window.removeEventListener("beforeunload", handleBeforeUnload);
      };
    }
  }, [isInitializedReady, currentLesson]);

  return null;
}

export default DataLoader;
