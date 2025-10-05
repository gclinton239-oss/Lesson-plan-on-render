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
    print("WARNING: GEMINI_API_KEY environment variable not set.")

try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"Failed to initialize Gemini Client: {e}")
    client = None

GEMINI_MODEL = "gemini-2.5-flash"
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
    
    # --- UPDATED SYSTEM MESSAGE (Removed ASSESSMENT from the final structure list) ---
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
- CRITICAL FORMATTING: Structure notes precisely like the 'Ecosystem' example: Use clear headings (e.g., 'Ecosystem:', 'Biotic components', 'Abiotic components', 'Types of Ecosystems:'), followed by definitions/explanations.
- Include TLR references where necessary.

ASSESSMENT
- Generate 1–1 questions for each activity based on exemplars.
- CRITICAL FORMATTING: The value for the 'assessment' key MUST be a SINGLE STRING containing all the questions, separated by newlines.
- Organize as:
1. First question
2. Second question
...

PHASE 3: REFLECTION
- Generate reflective oral questions (≤ {phase3_duration} minutes) based on the lesson.

Rules:
- Display durations only at the top of each phase column.
- Use simple Ghanaian context examples.
- Return the result as structured JSON with keys: phase1, **phase2 (MUST contain the main content and notes)**, **assessment**, phase3.
- Return ONLY content, no extra formatting (no markdown blocks like ```json).
"""
    # ----------------------------------------------------

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                {"role": "user", "parts": [{"text": user_message.strip()}]}
            ],
            config=genai.types.GenerateContentConfig(
                temperature=0.5,
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
        
        print(f"RAW AI OUTPUT: {raw_output}")

        try:
            if raw_output.startswith("```json") and raw_output.endswith("```"):
                json_string = raw_output.strip("```json").strip("```").strip()
            else:
                json_string = raw_output
                
            ai_json = json.loads(json_string)
            
            # Safeguard for list outputs (from previous fix)
            for key in ['phase1', 'phase2', 'assessment', 'phase3']:
                if key in ai_json and isinstance(ai_json[key], list):
                    ai_json[key] = "\n".join(ai_json[key])

            # --- CRITICAL FIX: Merge Assessment into Phase 2 ---
            phase2_content = ai_json.get('phase2', '')
            assessment_content = ai_json.get('assessment', '')

            if assessment_content:
                # Append Assessment content to Phase 2 with a clear header
                ai_json['phase2'] = (
                    phase2_content.strip() + 
                    "\n\n\n**ASSESSMENT**\n\n" + 
                    assessment_content.strip()
                )
            
            # Remove the now redundant 'assessment' key from the final JSON
            if 'assessment' in ai_json:
                del ai_json['assessment']
            # -------------------------------------------------
            
            if not ai_json.get('phase2'):
                print("WARNING: Phase 2 content is empty despite successful generation.")
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