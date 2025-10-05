from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from flask_cors import CORS
import json
import google.generativeai as genai  # Gemini SDK

# -------------------------------
# Load environment variables
# -------------------------------
load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("⚠️ WARNING: GEMINI_API_KEY not found in environment")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# -------------------------------
# Flask Setup
# -------------------------------
FRONTEND_URL = "https://lesson-plan-frontend.onrender.com"

app = Flask(__name__)
CORS(CORS(app, origins=[FRONTEND_URL])
)

# -------------------------------
# Routes
# -------------------------------
@app.route("/")
def home():
    return jsonify({
        "status": "success",
        "message": "Backend is Running! Connect to /generate"
    })


@app.route("/generate", methods=["POST"])
def generate():
    try:
        data = request.get_json()

        # Extract user input safely
        class_level = data.get("class_level", "Basic 7")
        lesson = data.get("lesson", "1")
        strand = data.get("strand", "")
        content_standard = data.get("content_standard", "")
        performance_indicator = data.get("performance_indicator", "")
        exemplars = data.get("exemplars", [])
        tlrs = data.get("tlrs", "")
        total_duration = int(data.get("duration", 70))

        # Ensure exemplars is a list
        if isinstance(exemplars, str):
            exemplars = [e.strip() for e in exemplars.split(",") if e.strip()]

        # Compute phase durations
        phase1_duration = min(10, int(total_duration * 0.15))
        phase3_duration = min(10, int(total_duration * 0.15))
        phase2_duration = total_duration - (phase1_duration + phase3_duration)

        # Compose prompt
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

        system_instruction = """
You are an expert Ghanaian lesson planner. Generate a lesson plan in strict JSON format with these keys:
{
  "phase1": "starter activity using only TLRs",
  "phase2": "step-by-step teaching activities based on exemplars and TLRs",
  "assessment": "numbered questions for learners",
  "phase3": "reflective oral questions for learners"
}

Rules:
- Use simple Ghanaian classroom examples.
- Keep activities realistic, not robotic.
- Return ONLY valid JSON — no markdown, no explanations.
- Do not include any extra text or formatting.
"""

        # -------------------------------
        # Gemini Model Setup
        # -------------------------------
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",  # Use "gemini-1.5-pro" if you have billing
            system_instruction=system_instruction.strip()
        )

        # Generate response
        response = model.generate_content(
            user_message.strip(),
            generation_config=genai.types.GenerationConfig(
                temperature=0.6,
                max_output_tokens=1500,
                response_mime_type="application/json"
            )
        )

        # -------------------------------
        # Handle Gemini Output (FIXED)
        # -------------------------------
        result_text = (
            response.candidates[0].content.parts[0].text
            if response.candidates
            and response.candidates[0].content
            and response.candidates[0].content.parts
            else ""
        ).strip()

        if not result_text:
            raise ValueError("Gemini returned an empty response")

        try:
            ai_json = json.loads(result_text)
            return jsonify(ai_json)
        except json.JSONDecodeError:
            # Fallback if Gemini didn’t return valid JSON
            print("⚠️ Gemini returned non-JSON response:\n", result_text)
            return jsonify({"content": result_text})

    except Exception as e:
        print("❌ Gemini Error:", str(e))
        return jsonify({
            "error": "AI generation failed",
            "details": str(e)
        }), 500


# -------------------------------
# Run the Flask App
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
