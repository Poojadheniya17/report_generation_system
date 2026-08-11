# debug_ai_call.py
# Same as test_ai_interpretation.py, but saves the RAW model response to a
# file before validation runs, so we can see exactly what came back even
# if validation fails.

import sys
sys.path.insert(0, r"C:\Users\Acer\OneDrive\Desktop\report_generation_system")

from dotenv import load_dotenv
load_dotenv()

import json
from app.services.interpretation import build_user_message, parse_model_json
from app.services.interpretation_prompt import SYSTEM_PROMPT
from app.services.model_client import make_anthropic_model_call

scores = {
    "triad": {
        "task":        {"score": 2.35},
        "sociability": {"score": -0.60},
        "dominance":   {"score": 1.90},
    },
    "bfi2": {
        "domains": [
            {"name": "Extraversion", "score": 2.90, "norm": 3.27, "diff": -0.37, "level": "Low",
             "facets": [
                 {"name": "Sociability",   "score": 2.40, "norm": 3.20, "diff": -0.80, "level": "Low"},
                 {"name": "Assertiveness", "score": 3.80, "norm": 3.35, "diff": 0.45,  "level": "High"},
                 {"name": "Energy_Level",  "score": 2.50, "norm": 3.25, "diff": -0.75, "level": "Low"},
             ]},
            {"name": "Agreeableness", "score": 3.10, "norm": 3.57, "diff": -0.47, "level": "Average",
             "facets": [
                 {"name": "Compassion",     "score": 3.20, "norm": 3.65, "diff": -0.45, "level": "Average"},
                 {"name": "Respectfulness", "score": 3.30, "norm": 3.60, "diff": -0.30, "level": "Average"},
                 {"name": "Trust",          "score": 2.80, "norm": 3.65, "diff": -0.85, "level": "Low"},
             ]},
            {"name": "Conscientiousness", "score": 4.20, "norm": 3.52, "diff": 0.68, "level": "High",
             "facets": [
                 {"name": "Organization",    "score": 4.30, "norm": 3.45, "diff": 0.85, "level": "High"},
                 {"name": "Productiveness",  "score": 4.35, "norm": 3.48, "diff": 0.87, "level": "High"},
                 {"name": "Responsibility",  "score": 3.95, "norm": 3.62, "diff": 0.33, "level": "High"},
             ]},
            {"name": "Negative_Emotionality", "score": 2.95, "norm": 2.77, "diff": 0.18, "level": "Average",
             "facets": [
                 {"name": "Anxiety",              "score": 3.10, "norm": 2.80, "diff": 0.30, "level": "Average"},
                 {"name": "Depression",           "score": 2.60, "norm": 2.70, "diff": -0.10, "level": "Low"},
                 {"name": "Emotional_Volatility", "score": 3.15, "norm": 2.80, "diff": 0.35, "level": "Average"},
             ]},
            {"name": "Open_Mindedness", "score": 3.40, "norm": 3.50, "diff": -0.10, "level": "Average",
             "facets": [
                 {"name": "Intellectual_Curiosity", "score": 3.55, "norm": 3.55, "diff": 0.00,  "level": "Average"},
                 {"name": "Aesthetic_Sensitivity",  "score": 3.00, "norm": 3.40, "diff": -0.40, "level": "Average"},
                 {"name": "Creative_Imagination",   "score": 3.65, "norm": 3.55, "diff": 0.10,  "level": "Average"},
             ]},
        ]
    }
}

participant = {"name": "Alex Rivera", "role": "Project Lead"}

model_call = make_anthropic_model_call()
user_message = build_user_message(participant, scores)

print("Calling the model directly (no validation yet)...")
raw = model_call(SYSTEM_PROMPT, user_message)

# Save the completely raw text no matter what
with open(r"C:\Users\Acer\OneDrive\Desktop\raw_model_response.txt", "w", encoding="utf-8") as f:
    f.write(raw)
print("Raw response saved to raw_model_response.txt")

# Try to parse it as JSON and inspect the Extraversion domain specifically
try:
    report = parse_model_json(raw)
    print("\nJSON parsed successfully.")
    domains = report.get("domains", [])
    print(f"Number of domains returned: {len(domains)}")
    for d in domains:
        if d.get("name") == "Extraversion":
            print("\n--- Extraversion domain object, as returned ---")
            print(json.dumps(d, indent=2))
            required = {"name","score","norm","diff","level","meaning","preferences","potential_needs","facets"}
            present = set(d.keys())
            print("\nMissing fields:", required - present)
except Exception as e:
    print("Could not parse as JSON:", e)
