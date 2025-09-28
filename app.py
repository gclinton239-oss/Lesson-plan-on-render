from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
from flask_cors import CORS
import json

# Load environment variables
load_dotenv()

# Frontend URL
FRONTEND_URL = "https://lesson-plan-frontend.onrender.com"

# Create app
app = Flask(__name__)
CORS(app, origins=[FRONTEND_URL])

@app.route("/")
def home():
    return jsonify({
        "status": "success",
        "message": "Backend is Running! Connect to /generate"
    })

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()

    # Extract fields safely
    class_level = data.get("class_level", "Basic 7")
    lesson = data.get("lesson", "1")
    strand = data.get("strand", "")
    content_standard = data.get("content_standard", "")
    performance_indicator = data.get("performance_indicator", "")
    exemplars = data.get("exemplars", [])
    tlrs = data.get("tlrs", "")
    total_duration = int(data.get("duration", 70))  # Ensure integer

    # Ensure exemplars is a list
    if isinstance(exemplars, str):
        exemplars = [e.strip() for e in exemplars.split(",") if e.strip()]

    # Phase durations
    phase1_duration = min(10, int(total_duration * 0.15))
    phase3_duration = min(10, int(total_duration * 0.15))
    phase2_duration = total_duration - (phase1_duration + phase3_duration)

    user_message = f"""
Class level: {class_level}
Lesson: {lesson}
Strand: {strand}
Content Standard: {content_standard}
Performance Indicator: {performance_indicator}
Exemplars: {exemplars}
T/L Resources: {tlrs}
Phase Durations: Phase 1 = {phase1_duration}, Phase 2 = {phase2_duration}, Phase 3 = {phase3_duration}
"""

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return jsonify({"error": "API key not set in environment"}), 500

    system_message = f"""
You are an expert Ghanaian lesson planner. Generate a lesson exactly in this structure:

PHASE 1: STARTER
- Generate a short warm-up (≤ {phase1_duration} minutes) using only the teacher-provided TLRs.

PHASE 2: MAIN
- Generate step-by-step, actionable, learner-centered activities based ONLY on the exemplars and TLRs.
- Organize activities like this:
1. First actionable activity
2. Second actionable activity
...
- Do NOT display the exemplars themselves.

NOTES
- For each Phase 2 activity, generate concise notes capturing the core content of the activity (students can copy for later learning).
- Structure notes like the Ecosystem example (with headings for Biotic, Abiotic, Types of Ecosystems, etc.).
- Include TLR references where necessary.

ASSESSMENT
- Generate 1–1 questions for each activity based on exemplars.
- Organize as:
1. First question
2. Second question
...

PHASE 3: REFLECTION
- Generate reflective oral questions (≤ {phase3_duration} minutes) based on the lesson.

Rules:
- Display durations only at the top of each phase column.
- Use simple Ghanaian context examples.
- Return the result as structured JSON with keys: phase1, phase2, assessment, phase3.
- Return ONLY content, no extra formatting.
"""

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek/deepseek-r1:free",
                "messages": [
                    {"role": "system", "content": system_message.strip()},
                    {"role": "user", "content": user_message.strip()}
                ],
                "temperature": 0.5,
                "max_tokens": 2000,
                "top_p": 0.9,
                "frequency_penalty": 0.2,
                "presence_penalty": 0.2
            }
        )

        if response.status_code == 200:
            result = response.json()
            choices = result.get("choices", [])
            if choices and "message" in choices[0] and "content" in choices[0]["message"]:
                raw_output = choices[0]["message"]["content"].strip()
                # Attempt to parse JSON from AI
                try:
                    ai_json = json.loads(raw_output)
                    return jsonify(ai_json)  # Returns phase1, phase2, assessment, phase3 separately
                except json.JSONDecodeError:
                    # Fallback: return raw content if AI didn't produce valid JSON
                    return jsonify({"content": raw_output})
            else:
                return jsonify({"error": "No content returned from AI"}), 500
        else:
            return jsonify({"error": f"AI Error: {response.status_code}", "details": response.text}), response.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
