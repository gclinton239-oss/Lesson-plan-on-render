from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from flask_cors import CORS
import json
import google.generativeai as genai  # <-- NEW IMPORT

# Load environment variables
load_dotenv()

# Configure Gemini once at startup
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("⚠️ WARNING: GEMINI_API_KEY not found in environment")

genai.configure(api_key=GEMINI_API_KEY)

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
Phase Durations: Phase 1 = {phase1_duration} minutes, Phase 2 = {phase2_duration} minutes, Phase 3 = {phase3_duration} minutes
"""

    system_instruction = f"""
You are an expert Ghanaian lesson planner. Generate a lesson plan in strict JSON format with these keys:
- "phase1": string (starter activity, ≤{phase1_duration} minutes, using only TLRs)
- "phase2": string (step-by-step, learner-centered activities based ONLY on exemplars and TLRs; do NOT list exemplars)
- "assessment": string (1–3 numbered assessment questions based on activities, e.g., "1. ...\n2. ...")
- "phase3": string (reflective oral questions for ≤{phase3_duration} minutes)

Rules:
- Use simple Ghanaian context examples.
- Include concise "Notes" section within phase2 if needed (e.g., under headings like "Biotic Factors").
- Return ONLY valid JSON — no markdown, no extra text.
"""

    try:
        # Define JSON schema for structured output
        schema = {
            "type": "OBJECT",
            "properties": {
                "phase1": {"type": "STRING"},
                "phase2": {"type": "STRING"},
                "assessment": {"type": "STRING"},
                "phase3": {"type": "STRING"}
            },
            "required": ["phase1", "phase2", "assessment", "phase3"]
        }

        model = genai.GenerativeModel(
            model_name="Gemini 2.5-flash",
            system_instruction=system_instruction.strip()
        )

        response = model.generate_content(
            user_message.strip(),
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.5,
                max_output_tokens=2000
            )
        )

        # Parse and return JSON
        ai_json = json.loads(response.text)
        return jsonify(ai_json)

    except Exception as e:
        error_msg = str(e)
        print("Gemini Error:", error_msg)
        return jsonify({
            "error": "AI generation failed",
            "details": error_msg
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)