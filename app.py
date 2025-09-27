from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables
load_dotenv()

# =========================================================
# ✅ Use ONLY your frontend Render URL
FRONTEND_URL = "https://lesson-plan-frontend.onrender.com"
# =========================================================

# Create app
app = Flask(__name__)
CORS(app, origins=[FRONTEND_URL])

# Root route – test with http://localhost:5000
@app.route("/")
def home():
    return jsonify({
        "status": "success",
        "message": "Backend is Running! Connect to /generate"
    })

# AI generation route
@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()

    # Collect all possible inputs from frontend
    class_level = data.get("class_level", "Basic 7")
    lesson = data.get("lesson", "1")
    strand = data.get("strand", "")
    content_standard = data.get("content_standard", "")
    performance_indicator = data.get("performance_indicator", "")
    exemplars = data.get("exemplars", [])
    tlrs = data.get("tlrs", "")
    keywords = data.get("keywords", [])

    # Ensure exemplars is a list
    if isinstance(exemplars, str):
        exemplars = [e.strip() for e in exemplars.split(",") if e.strip()]

    # Get API key securely
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return jsonify({"error": "API key not set in environment"}), 500

    try:
        # Strong structured prompt
        system_message = """
You are an expert Ghanaian lesson planner.
You MUST return output strictly in valid JSON with this structure:

{
  "starter": "Warm-up activity connected to the topic and class level.",
  "activities": [
    {
      "activity": "Teacher-learner activity based on exemplar 1 and TLRs",
      "note": "Supporting notes/explanation for this activity",
      "assessment": "Assessment question related to this activity"
    },
    {
      "activity": "Teacher-learner activity based on exemplar 2 and TLRs",
      "note": "Supporting notes/explanation",
      "assessment": "Assessment question"
    }
  ]
}

Rules:
- Starter must be an engaging warm-up activity related to the lesson and class level.
- The number of activities MUST equal the number of exemplars provided.
- Each activity MUST use the given exemplar and the TLRs.
- Each activity MUST include a supporting note AND one assessment question.
- Do not include any extra commentary outside the JSON.
"""

        user_message = f"""
Class level: {class_level}
Lesson: {lesson}
Strand: {strand}
Content Standard: {content_standard}
Performance Indicator: {performance_indicator}
Exemplars: {exemplars}
T/L Resources: {tlrs}
Keywords: {keywords}
"""

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
                "max_tokens": 1200,
                "top_p": 0.9,
                "frequency_penalty": 0.2,
                "presence_penalty": 0.2
            }
        )

        if response.status_code == 200:
            result = response.json()
            raw_output = result["choices"][0]["message"]["content"].strip()

            # Ensure JSON-safe return
            import json
            try:
                structured = json.loads(raw_output)
            except Exception:
                return jsonify({
                    "error": "AI returned invalid JSON",
                    "raw": raw_output
                }), 500

            return jsonify(structured)
        else:
            return jsonify({
                "error": f"AI Error: {response.status_code}",
                "details": response.text
            }), response.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
