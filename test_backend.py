import requests
import json

BACKEND_URL = "https://lesson-plan-on-render.onrender.com/generate"

payload = {
    "class_level": "BASIC 7",
    "lesson": "Introduction to Ecosystems",
    "strand": "Living Things and Their Environment",
    "content_standard": "Learners should be able to identify components of an ecosystem.",
    "performance_indicator": "Identify biotic and abiotic factors in a given ecosystem.",
    "exemplars": [
        "Explain electronic spreadsheet to the learners.",
        "Guide learners to identify 2 examples of electronic spreadsheet."
    ],
    "tlrs": "Computer with MS Excel, Projector",
    "duration": 40
}

try:
    print("📡 Sending request to live backend...")
    response = requests.post(BACKEND_URL, json=payload, timeout=30)
    
    if response.status_code == 200:
        result = response.json()
        print("\n✅ Success! AI Response:")
        print(json.dumps(result, indent=2))
        
        # Check required keys
        for key in ["phase1", "phase2", "assessment", "phase3"]:
            if key not in result:
                print(f"⚠️ Missing key: {key}")
            else:
                print(f"✔️ {key} found")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

except Exception as e:
    print(f"💥 Test failed: {str(e)}")