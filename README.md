# PAL — Personal Adaptive Learner

A comprehensive research and production toolkit for building automated, adaptive video learning experiences.

PAL unifies three primary capabilities:
1. **Agentic Question Generation ("Tri+1" Pipeline)**: Automatically ingests YouTube or local lecture videos, extracts transcripts via Whisper/yt-dlp, validates context using Vision-Language Models (VLMs), and generates high-quality, multi-difficulty, context-aware distractors using a Large Language Model.
2. **Hybrid Reinforcement Learning (RL) Engine**: Evaluates learner performance in real-time, blending traditional Item Response Theory (IRT) statistics with a pure Q-learning bandit algorithm to intelligently adjust question difficulty.
3. **Adaptive Delivery UI**: A React-based Single Page Application (SPA) that synchronizes video playback with seamlessly injected, adaptive questions.

---

## Repository Layout

```text
PAL---Personal-Adaptive-Learner/
├── demo_application/            # React SPA (Adaptive Video UI, Question Player)
├── engine_rl/                   # Core RL engine (Q-learning, Mixture Logic, State tracking)
├── pipelines/                   
│   └── tri_plus_one/            # Agentic "3+1" video-to-question generation pipeline
├── core/                        # Core schemas, LLM providers (Ollama routing), utilities
├── question_generator/          # Flask API backend connecting pipelines & UI
├── run_demo.py                  # CLI simulation script for testing the end-to-end backend
└── README.md
```

*(Note: Legacy `hybrid_rl_algorithm/` and `personalised_summariser/` directories have been migrated and unified into the new modular `engine_rl` and `pipelines` architecture).*

---

## What’s Inside

### 1. Agentic Question Generation (`pipelines/tri_plus_one`)
- **Transcript Analyzer**: Identifies candidate educational segments using transcript linguistic cues (definitions, emphasis).
- **Context Validator**: Aligns transcript timestamps with video frame OCR to ensure visual and textual congruence.
- **Question Generator**: LLM orchestrator that outputs exactly 3 questions per segment (1 factual, 1 conceptual, 1 applied) alongside dynamically generated, context-aware multiple-choice distractors.
- **Difficulty Rater**: Assigns true cognitive complexity scores to generated questions.

### 2. Hybrid Adaptive Engine (`engine_rl/`)
- **Statistical Base**: Implements IRT-style smoothing based on answering streaks, time spent, and confidence.
- **Q-Learning Head**: Epsilon-greedy reinforcement learning algorithm dynamically exploring `{Easy, Medium, Hard}` state spaces.
- **Mixture Logic**: Deterministically blends statistical predictions and RL rewards for optimal next-difficulty recommendations.

### 3. Adaptive Video Delivery (`demo_application/`)
- A React application that dynamically pulls generated lesson manifests.
- Pauses the video automatically at key timestamps.
- Communicates live with the Hybrid RL engine to present the optimal difficulty variant of the generated question.

---

## Prerequisites

- **Node.js 18+** and npm (for the React demo)
- **Python 3.9+** (for Flask backend and pipelines)
- **Ollama** installed and running locally with `llama3.2` and `llama3.2-vision` (or an equivalent LLM provider configured in `core/llm/providers.py`).
- macOS / Linux / WSL recommended.

---

## Quickstart Guide

To run the complete PAL experience, you need to spin up both the Flask backend and the React frontend.

### 1. Start the Flask Backend API
This server handles YouTube ingestion, the Tri+1 generation pipeline, and serves the generated JSONs to the UI.

```bash
cd question_generator
# (Optional) Create and activate a virtual environment
# python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
*The backend runs on `http://127.0.0.1:5005`.*

### 2. Start the React Adaptive UI
This is the main graphical interface where you can upload videos and take the adaptive lessons.

```bash
cd demo_application
npm install
npm start
```
*The application opens automatically at `http://localhost:3000`.*

### 3. Simulate Backend Workflows (CLI)
If you only want to test the LLM pipeline and the RL engine programmatically without spinning up the servers, you can run the provided demo script from the repository root:

```bash
python run_demo.py
```

---

## Architecture Flow

1. **Ingestion**: The user pastes a YouTube URL into the React UI.
2. **Pipeline Trigger**: React hits the Flask `/process-youtube` endpoint.
3. **Generation**: Flask downloads the `.mp4` and `.vtt`, feeding them into the `TriPlusOnePipeline`. The pipeline yields a timestamped JSON manifest containing the context-aware distractor array (`options`).
4. **Playback**: React (`DataLoader.js`) fetches the JSON, maps the distractors cleanly onto A/B/C/D option blocks, and launches the adaptive video player.
5. **Adaptation**: As the user answers questions, the React component dynamically signals the `engine_rl` logic to scale difficulty up or down.

---

## License

This project is licensed under the MIT License — see the `LICENSE` file for details.
