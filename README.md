# AI Gym & Fitness Assistant

Unified system: workout detection (pose estimation), diet planning, behavior tracking,
simulated IoT smart-gym feed, and a conversational assistant — all in one Streamlit app.

## Setup
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Modules
- `modules/diet.py` — BMR/TDEE calc, macro split, rule-based meal plan generator.
- `modules/tracker.py` — SQLite-backed logging for meals/workouts/water/sleep/weight, streaks, weekly summary.
- `modules/workout_detect.py` — Tap-based rep/set counter with session timer (pure Python, no camera/CV libs — mediapipe/opencv don't support Python 3.14 yet).
- `modules/iot_sim.py` — Simulated smart-gym sensors (heart rate, scale, bottle, treadmill) with safety alerts. Swap for real MQTT/BLE later.
- `modules/chatbot.py` — Rule-based fitness Q&A; auto-upgrades to Claude if `ANTHROPIC_API_KEY` is set in env.

## Notes
- Data persists locally in `data/gym_assistant.db` (SQLite).
- Requirements are pure Python (streamlit, pandas, numpy) — runs fine on Python 3.14.
- Want live webcam pose detection instead of the tap counter? That needs `mediapipe` + `opencv-python-headless` + `streamlit-webrtc`, which currently only support Python 3.9-3.12 — run that version in a separate venv and swap `workout_detect.py` for a pose-estimation version.
- Calorie-burn estimates in `workout_detect.py` and meal calories in `diet.py` are approximations — swap in a real food/exercise database for production accuracy.
