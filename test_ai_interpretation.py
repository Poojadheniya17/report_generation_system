# test_ai_interpretation.py
# Actually runs raw scores through the live AI interpretation step,
# then renders the result with the real PDF layout.

import sys
sys.path.insert(0, r"C:\Users\Acer\OneDrive\Desktop\report_generation_system")

from dotenv import load_dotenv
load_dotenv()

import os
from app.services.interpretation import interpret
from app.services.model_client import make_anthropic_model_call
from app.services.pdf_generator import generate_pdf

# --- 1. Sample scores (deliberately a DIFFERENT profile than Jordan Avery,
#         so this proves the AI writes fresh content, not a template) ---
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

# --- 2. Actually call the live model, saving the raw response FIRST so we
#         never lose diagnostic info if validation fails ---
from app.services.interpretation import build_user_message, parse_model_json, validate_report, inject_verified_numbers
from app.services.interpretation_prompt import SYSTEM_PROMPT

model_call = make_anthropic_model_call()  # reads ANTHROPIC_API_KEY from environment
user_message = build_user_message(participant, scores)
print("Calling the model, this may take a bit...")
raw = model_call(SYSTEM_PROMPT, user_message)

with open(r"C:\Users\Acer\OneDrive\Desktop\last_raw_response.txt", "w", encoding="utf-8") as f:
    f.write(raw)
print("Raw response saved to last_raw_response.txt (overwritten each run)")

report = parse_model_json(raw)
from app.services.interpretation import InterpretationError
try:
    validate_report(report)
except InterpretationError:
    raise
except Exception as e:
    raise InterpretationError(
        f"Unexpected problem validating the model's response ({type(e).__name__}: {e}). "
        f"Check last_raw_response.txt to see the actual structure returned."
    )
report = inject_verified_numbers(report, scores)
print("Got a validated report back from the model.")

# --- 3. Render it with the real PDF layout ---
pdf_bytes = generate_pdf(participant, report)

output_path = r"C:\Users\Acer\OneDrive\Desktop\ai_test_report.pdf"
with open(output_path, "wb") as f:
    f.write(pdf_bytes)

print(f"Done! PDF saved to {output_path}")
print(f"Size: {len(pdf_bytes):,} bytes")
