from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from flask_cors import CORS
import json
from google import genai
from google.genai.errors import APIError

# Load environment variables
load_dotenv()

# --- Gemini Setup ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Check for API key immediately on startup
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

# Initialize the Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-2.5-flash" # Use a fast model for generation tasks
# --------------------

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
    total_duration = int(data.get("duration", 70)) # Ensure integer

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
    
    # System message is crucial for high-quality, structured output
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
        # Use the Gemini client to generate content
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                {"role": "user", "parts": [{"text": user_message.strip()}]}
            ],
            config=genai.types.GenerateContentConfig(
                temperature=0.5,
                system_instruction=system_message.strip() # System message can also go here
            )
        )
        # Check for blocked or empty response (handles the original 500 error scenario)
        if not response.text:
            # Check for specific finish reasons (e.g., SAFETY, RECITATION)
            finish_reason = response.candidates[0].finish_reason.name if response.candidates else "UNKNOWN"
            
            return jsonify({
                "error": "AI generation blocked or empty.",
                "details": f"Content was blocked due to finish reason: {finish_reason}. Review your prompt for policy violations."
            }), 400

        raw_output = response.text.strip()
        
        # Attempt to parse JSON from AI, which is required by the system message
        try:
            # Clean up the output to ensure it starts with { and ends with }
            # Some models may wrap the JSON in markdown blocks
            if raw_output.startswith("```json") and raw_output.endswith("```"):
                json_string = raw_output.strip("```json").strip("```").strip()
            else:
                json_string = raw_output
                
            ai_json = json.loads(json_string)
            return jsonify(ai_json) 
            
        except json.JSONDecodeError:
            # Fallback: if JSON parsing fails, return the raw text as a content field
            return jsonify({
                "error": "AI returned content, but it was not valid JSON.", 
                "content": raw_output
            }), 500

    except APIError as e:
        # Catch specific API errors (e.g., network, key invalid)
        return jsonify({"error": f"Gemini API Error: {str(e)}"}), 500
    except Exception as e:
        # Catch all other exceptions (e.g., connection issues)
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # Note: debug=False is recommended for production environments like Render
    app.run(host="0.0.0.0", port=port, debug=False)