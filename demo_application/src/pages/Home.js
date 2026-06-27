import { useNavigate } from "react-router-dom";
import { useLessonList } from "../useSingleton/useLessonList";
import { useLearningAppFascade } from "../useSingleton/useLearningAppFascade";
import sidebarStyles from "../stylesheets/sidebar.module.css";
import videoGridStyles from "../stylesheets/videoGrid.module.css";

function Home() {
  const { lessons } = useLessonList();
  const { logout, startNewLesson } = useLearningAppFascade();
  const navigate = useNavigate();

  // Logout button is pressed
  const LogOut = () => {
    logout();
    navigate("/");
  };

  // Video is pressed
  const MoveToVideo = (lesson) => {
    startNewLesson(lesson);
    navigate("/video");
  };

  // Account button is pressed
  const AccessAccount = () => { };

  // Upload button is pressed
  const MoveToUpload = () => {
    navigate("/upload");
  };

  return (
    <div className={videoGridStyles.body}>
      <div className={sidebarStyles.sidebar}>
        <button name="signout_button" type="button" onClick={LogOut}>
          Sign Out
        </button>
        <button name="account_button" type="button" onClick={AccessAccount}>
          Account
        </button>
        <button name="upload_button" type="button" onClick={MoveToUpload}>
          Create Custom Lesson
        </button>
      </div>
      <div className={videoGridStyles.videoGrid}>
        {lessons.map((lesson) => (
          <img
            src={lesson.getThumbnailFileName()}
            alt="D1S1thumbnail"
            onClick={() => MoveToVideo(lesson)}
            style={{ cursor: "pointer", width: "320px", height: "180px", objectFit: "cover", margin: "10px", borderRadius: "8px" }}
            draggable="false"
            key={lesson.getId()}
          />
        ))}
      </div>
    </div>
  );
}

export default Home;
