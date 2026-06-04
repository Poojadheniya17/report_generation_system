"""
Interpretation tests — no API key needed. A fake model_call returns a
well-formed (and deliberately malformed) report so we verify:
  - validation accepts a correct report
  - validation rejects each kind of structural violation
  - number injection overwrites model numbers with our verified scores
  - the happy path round-trips from real scores
"""
import json

from app.services.interpretation import (
    InterpretationError,
    build_user_message,
    inject_verified_numbers,
    interpret,
    parse_model_json,
    validate_report,
)
from app.services.interpretation_prompt import DISPLAY_NAMES
from app.services.scoring import score_all

# Build real scores from a simple synthetic respondent.
TRIAD = {i: (3 if i <= 6 else 5 if i <= 12 else 1) for i in range(1, 19)}  # centered scale
BFI = {i: ((i % 5) + 1) for i in range(1, 61)}
SCORES = score_all(TRIAD, BFI)


def _well_formed_report(scores: dict) -> dict:
    """Construct a structurally-valid report (numbers intentionally 'wrong')."""
    domains = []
    for d in scores["bfi2"]["domains"]:
        domains.append({
            "name": DISPLAY_NAMES[d["name"]],
            "score": 0.0, "norm": 0.0, "diff": 0.0, "level": "WRONG",
            "meaning": "m", "preferences": "p", "potential_needs": "n",
            "facets": [
                {
                    "name": DISPLAY_NAMES[f["name"]],
                    "score": 0.0, "norm": 0.0, "diff": 0.0, "level": "WRONG",
                    "meaning": "m", "preferences": "p", "potential_needs": "n",
                }
                for f in d["facets"]
            ],
        })
    return {
        "executive_summary": {"text": "A supportive summary of your work style."},
        "triad": {
            dim: {"score": 0.0, "interpretation": "i", "workplace_implications": "w"}
            for dim in ("task", "sociability", "dominance")
        },
        "domains": domains,
        "recommendations": {
            "strengths": ["a", "b", "c"],
            "blind_spots": ["x", "y"],
            "development_suggestions": ["p", "q", "r"],
        },
    }


def run():
    results = []

    # 1. user message builds and contains display names
    msg = build_user_message({"name": "Test", "role": "Engineer"}, SCORES)
    results.append(("user message includes Negative Emotionality",
                    "Negative Emotionality" in msg))

    # 2. valid report passes validation
    good = _well_formed_report(SCORES)
    try:
        validate_report(good); ok = True
    except InterpretationError:
        ok = False
    results.append(("validation accepts well-formed report", ok))

    # 3. wrong domain count rejected
    bad = _well_formed_report(SCORES); bad["domains"].pop()
    results.append(("rejects != 5 domains",
                    _raises(lambda: validate_report(bad))))

    # 4. wrong domain order rejected
    bad = _well_formed_report(SCORES)
    bad["domains"][0]["name"] = "Open-Mindedness"
    results.append(("rejects wrong domain order",
                    _raises(lambda: validate_report(bad))))

    # 5. too few strengths rejected
    bad = _well_formed_report(SCORES); bad["recommendations"]["strengths"] = ["only-one"]
    results.append(("rejects <3 strengths",
                    _raises(lambda: validate_report(bad))))

    # 6. fences tolerated by parser
    fenced = "```json\n" + json.dumps(good) + "\n```"
    try:
        parse_model_json(fenced); ok = True
    except InterpretationError:
        ok = False
    results.append(("parser tolerates code fences", ok))

    # 7. number injection overwrites WRONG with verified values
    injected = inject_verified_numbers(_well_formed_report(SCORES), SCORES)
    ne = next(d for d in injected["domains"] if d["name"] == "Negative Emotionality")
    expected_ne = next(d for d in SCORES["bfi2"]["domains"]
                       if d["name"] == "Negative_Emotionality")
    results.append(("injects verified domain score",
                    abs(ne["score"] - round(expected_ne["score"], 2)) < 1e-9))
    results.append(("injects verified level (not WRONG)",
                    ne["level"] == expected_ne["level"]))

    # 8. full interpret() round-trip with a fake model
    def fake_model(system_prompt, user_message):
        assert "Work Style Report" in system_prompt
        return json.dumps(_well_formed_report(SCORES))
    report = interpret({"name": "Test", "role": "Eng"}, SCORES, fake_model)
    task_ok = abs(report["triad"]["task"]["score"]
                  - round(SCORES["triad"]["task"]["score"], 2)) < 1e-9
    results.append(("interpret() returns verified TRIAD score", task_ok))
    results.append(("interpret() keeps narrative prose",
                    report["executive_summary"]["text"].startswith("A supportive")))

    print("\n  INTERPRETATION — TEST RESULTS")
    print("  " + "=" * 46)
    passed = 0
    for name, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        passed += bool(ok)
    print("  " + "=" * 46)
    print(f"  {passed}/{len(results)} passed\n")
    return passed == len(results)


def _raises(fn) -> bool:
    try:
        fn(); return False
    except InterpretationError:
        return True


if __name__ == "__main__":
    import sys
    sys.exit(0 if run() else 1)
