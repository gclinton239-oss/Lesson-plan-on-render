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

if not GEMINI_API_KEY:
    # Changed from raise ValueError to return an error if deploying without the key
    print("WARNING: GEMINI_API_KEY environment variable not set.")
    # Client will still be initialized, but calls will fail unless the environment is corrected.

# Initialize the Gemini Client
# It's safer to initialize inside the request handler or verify API key presence
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"Failed to initialize Gemini Client: {e}")
    client = None

# UPGRADED MODEL: Use Pro for better complex structured output adherence
GEMINI_MODEL = "gemini-2.5-pro" 
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
        "message": f"Backend is Running! Using {GEMINI_MODEL}."
    })

@app.route("/generate", methods=["POST"])
def generate():
    if not client:
         return jsonify({"error": "AI client not initialized. Check GEMINI_API_KEY."}), 500
         
    data = request.get_json()

    # ... (Data extraction and duration calculation remain the same) ...
    class_level = data.get("class_level", "Basic 7")
    lesson = data.get("lesson", "1")
    strand = data.get("strand", "")
    content_standard = data.get("content_standard", "")
    performance_indicator = data.get("performance_indicator", "")
    exemplars = data.get("exemplars", [])
    tlrs = data.get("tlrs", "")
    total_duration = int(data.get("duration", 70)) 

    if isinstance(exemplars, str):
        exemplars = [e.strip() for e in exemplars.split(",") if e.strip()]

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
    
    # --- STRENGTHENED SYSTEM MESSAGE ---
    system_message = f"""
You are an expert Ghanaian lesson planner. Generate a lesson exactly in this structure:

PHASE 1: STARTER
- Generate a short warm-up (≤ {phase1_duration} minutes) using only the teacher-provided TLRs.

PHASE 2: MAIN
- **CRITICAL**: This is the core of the lesson. Generate detailed, step-by-step, actionable, learner-centered activities based ONLY on the exemplars and TLRs.
- This section MUST NOT be empty.
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
- Return the result as structured JSON with keys: phase1, **phase2 (MUST be the main content)**, assessment, phase3.
- Return ONLY content, no extra formatting (no markdown blocks like ```json).
"""
    # ----------------------------------

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                {"role": "user", "parts": [{"text": user_message.strip()}]}
            ],
            config=genai.types.GenerateContentConfig(
                temperature=0.5,
                # Using the system_instruction parameter is more reliable for system prompts
                system_instruction=system_message.strip() 
            )
        )

        if not response.text:
            finish_reason = response.candidates[0].finish_reason.name if response.candidates else "UNKNOWN"
            return jsonify({
                "error": "AI generation blocked or empty.",
                "details": f"Content was blocked due to finish reason: {finish_reason}."
            }), 400

        raw_output = response.text.strip()
        
        # LOGGING: Print the raw output here to inspect the JSON payload
        print(f"RAW AI OUTPUT: {raw_output}")
        
        # Attempt to parse JSON from AI
        try:
            # Simple cleanup for common markdown wrapper
            if raw_output.startswith("```json") and raw_output.endswith("```"):
                json_string = raw_output.strip("```json").strip("```").strip()
            else:
                json_string = raw_output
                
            ai_json = json.loads(json_string)
            
            # --- FINAL CHECK FOR EMPTY PHASE 2 ---
            if not ai_json.get('phase2'):
                 print("WARNING: Phase 2 content is empty despite successful generation.")
                 # Fallback: Return an error that indicates the AI failed on the content
                 return jsonify({"error": "AI generated structure but Phase 2 content is empty. Try a different prompt."}), 500

            return jsonify(ai_json) 
            
        except json.JSONDecodeError:
            return jsonify({
                "error": "AI returned content, but it was not valid JSON.", 
                "content": raw_output
            }), 500

    except APIError as e:
        return jsonify({"error": f"Gemini API Error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)