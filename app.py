# app.py
from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables
load_dotenv()

# Create app
app = Flask(__name__)
CORS(app)  # Allow frontend to connect

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
    prompt = data.get("prompt", "").strip()

    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    # Get API key securely
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return jsonify({"error": "API key not set in environment"}), 500

    try:
        # Enhanced prompt with strict formatting instructions
        system_message = """
You are an expert Ghanaian lesson planner for ICT, Science, or other subjects.
You must generate responses in the following strict format:

Teacher-Learner Activities:
1. [Specific activity related to first exemplar, using the T/L Resources].
2. [Specific activity related to second exemplar, using the T/L Resources].
...

[KEY CONCEPT 1 IN ALL CAPS]
Explanation of the concept in simple, clear language. Use real-life examples relevant to Ghanaian learners.

[KEY CONCEPT 2 IN ALL CAPS]
Explanation of the next concept...

Exercise;
1. Question based on first concept.<br>
2. Question based on second concept.<br>
...

Rules:
- Start with "Teacher-Learner Activities:" followed by numbered activities (1., 2., etc.).
- DO NOT use "Using T/LR," at the beginning of activities.
- Write activities in clear, instructional language (e.g., "Guide learners to discuss...").
- Each activity must match one exemplar.
- Use ALL CAPS for concept headings (e.g., ELECTRONIC SPREADSHEET).
- Provide one explanation per concept.
- End with "Exercise;" followed by numbered questions with <br> tags.
- Do not add extra sections or commentary.
- Use only the information provided.
"""

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",  # ✅ Fixed: no trailing spaces
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek/deepseek-r1:free",
                "messages": [
                    {"role": "system", "content": system_message.strip()},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.5,
                "max_tokens": 1024,
                "top_p": 0.9,
                "frequency_penalty": 0.2,
                "presence_penalty": 0.2
            }
        )

        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()

            # Optional: Add post-processing to fix common formatting issues
            if "Exercise;" not in content and "exercise;" not in content:
                if "Assessment;" in content:
                    content = content.replace("Assessment;", "Exercise;")
                else:
                    if content.count("<br>") >= 2:
                        last_br = content.rfind("<br>")
                        if last_br != -1:
                            end = content[last_br+6:].strip()
                            if end.isdigit() or end == "":
                                content += "\nExercise;\n1. What did you learn today?<br>\n2. How can you apply this?<br>\n3. Any questions?"

            return jsonify({"content": content})
        else:
            return jsonify({
                "error": f"AI Error: {response.status_code}",
                "details": response.text
            }), response.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # ✅ Use 8080 for Cloud Run
    app.run(host="0.0.0.0", port=port, debug=False)