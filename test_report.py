# test_report.py
import sys
sys.path.insert(0, r"C:\Users\Acer\OneDrive\Desktop\report_generation_system")

from app.services.pdf_generator import generate_pdf

# Minimal test report
report = {
    "executive_summary": {"text": "Your profile reflects strong warmth and intellectual curiosity. You build trust naturally and bring genuine energy to collaborative work. Your Open-Mindedness is your standout strength — you actively seek better approaches rather than defaulting to established ones. The pattern to watch is between your high sociability and moderate assertiveness: you invest heavily in relationships but may understate your own position in the process."},
    "triad": {
        "task":        {"score": 1.83, "direction_label": "Moderate tendency toward", "interpretation": "You engage with the work itself and value clarity around goals, though you do not require rigid structure to stay effective.", "workplace_implications": "You tend to keep work progressing and take ownership of responsibilities. You work best when priorities are shared and expectations are clear."},
        "sociability": {"score": 2.17, "direction_label": "Strong tendency toward",   "interpretation": "This is the most prominent tendency in your profile. You are strongly inclined to engage with people and keep relationships smooth.", "workplace_implications": "You are likely to strengthen cohesion and communication on any team you join. People tend to gravitate toward you naturally."},
        "dominance":   {"score": 0.83, "direction_label": "Mild tendency toward",     "interpretation": "Your score shows a mild tendency toward assertiveness. You step in when it genuinely matters, but leading every interaction is not something you naturally seek out.", "workplace_implications": "This leaves you adaptable. You can take the lead when needed and just as comfortably support someone else."},
    },
    "domains": [
        {"name":"Extraversion","score":3.83,"norm":3.27,"diff":0.56,"level":"High","meaning":"Your Extraversion sits above the norm. You bring visible drive and enthusiasm without needing to dominate the room.","preferences":"You do your best work in roles with regular contact and visible collaboration.","potential_needs":"You stay sharp when there is real interaction in your day.",
         "facets":[
             {"name":"Sociability","score":3.75,"norm":3.20,"diff":0.55,"level":"High","meaning":"You enjoy being around people and seek out company.","preferences":"You do well in roles with regular interaction.","potential_needs":"You stay energized when your day includes real conversation."},
             {"name":"Assertiveness","score":3.50,"norm":3.35,"diff":0.15,"level":"Average","meaning":"Your assertiveness sits around the norm. You speak up when it matters.","preferences":"You prefer environments where ideas are exchanged openly.","potential_needs":"You benefit from settings that value input without requiring you to compete."},
             {"name":"Energy Level","score":4.25,"norm":3.25,"diff":1.00,"level":"High","meaning":"Your energy level runs well above the norm.","preferences":"You maintain high effort in roles with varied work.","potential_needs":"You work best when your energy has somewhere useful to go."},
         ]},
        {"name":"Agreeableness","score":4.08,"norm":3.67,"diff":0.41,"level":"High","meaning":"Your Agreeableness is above the norm, reflecting genuine warmth and a cooperative orientation.","preferences":"You do well in collaborative environments where relationships matter.","potential_needs":"You stay effective when the environment is respectful.",
         "facets":[
             {"name":"Compassion","score":4.00,"norm":3.75,"diff":0.25,"level":"High","meaning":"You are attuned to others emotional states and respond with care.","preferences":"You prefer environments where people support each other.","potential_needs":"Emotionally safe environments help you bring your best."},
             {"name":"Respectfulness","score":4.25,"norm":3.60,"diff":0.65,"level":"High","meaning":"You treat others with consistent consideration, even under pressure.","preferences":"You work best where mutual respect is the norm.","potential_needs":"You thrive where courtesy is genuinely valued."},
             {"name":"Trust","score":3.92,"norm":3.65,"diff":0.27,"level":"High","meaning":"Your trust in others runs above the norm. You extend good faith readily.","preferences":"You prefer transparent working relationships.","potential_needs":"Consistent honesty from colleagues supports your effectiveness."},
         ]},
        {"name":"Conscientiousness","score":3.58,"norm":3.50,"diff":0.08,"level":"Average","meaning":"Your Conscientiousness sits right at the norm, suggesting solid organization and follow through without over reliance on structure.","preferences":"You work well in environments with clear goals and reasonable structure.","potential_needs":"Clarity around priorities helps you allocate effort effectively.",
         "facets":[
             {"name":"Organization","score":3.50,"norm":3.40,"diff":0.10,"level":"Average","meaning":"You maintain enough structure to stay on track without rigidity.","preferences":"You appreciate organized environments but adapt readily.","potential_needs":"Clear systems and shared processes support your effectiveness."},
             {"name":"Productiveness","score":3.75,"norm":3.50,"diff":0.25,"level":"Average","meaning":"You maintain consistent effort and follow through on commitments.","preferences":"You prefer roles where effort leads to visible outcomes.","potential_needs":"Clear goals and feedback keep your motivation high."},
             {"name":"Responsibility","score":3.50,"norm":3.60,"diff":-0.10,"level":"Average","meaning":"You take your commitments seriously and can be counted on.","preferences":"You prefer environments where accountability is shared.","potential_needs":"Shared ownership supports your sense of fairness."},
         ]},
        {"name":"Negative Emotionality","score":2.25,"norm":2.58,"diff":-0.33,"level":"Low","meaning":"Your Negative Emotionality sits below the norm, reflecting strong emotional stability and composure.","preferences":"You work well in demanding environments because your composure is authentic.","potential_needs":"You benefit from acknowledging strain when it exists rather than absorbing it silently.",
         "facets":[
             {"name":"Anxiety","score":2.25,"norm":2.60,"diff":-0.35,"level":"Low","meaning":"You experience worry at a manageable level, supporting clear thinking under pressure.","preferences":"You prefer environments with clear information.","potential_needs":"Reasonable clarity reduces unnecessary cognitive load."},
             {"name":"Depression","score":2.00,"norm":2.45,"diff":-0.45,"level":"Low","meaning":"You maintain positive affect and motivation even through difficult periods.","preferences":"You stay engaged when work feels meaningful.","potential_needs":"Purpose driven work supports your long term effectiveness."},
             {"name":"Emotional Volatility","score":2.50,"norm":2.70,"diff":-0.20,"level":"Low","meaning":"Your emotional responses are measured and consistent.","preferences":"You prefer steady, respectful working environments.","potential_needs":"Stability in team dynamics allows you to perform at your best."},
         ]},
        {"name":"Open-Mindedness","score":4.58,"norm":3.50,"diff":1.08,"level":"High","meaning":"Your Open-Mindedness is your highest domain and stands clearly above the norm. You are drawn to ideas, new perspectives, and intellectual exploration.","preferences":"You thrive in roles that reward curiosity, experimentation, and fresh thinking.","potential_needs":"Routine work without intellectual engagement will drain you faster than most.",
         "facets":[
             {"name":"Intellectual Curiosity","score":4.75,"norm":3.55,"diff":1.20,"level":"High","meaning":"Your intellectual curiosity is near the top of the scale.","preferences":"You are most engaged in roles that reward learning and inquiry.","potential_needs":"You disengage quickly from work that offers nothing new."},
             {"name":"Aesthetic Sensitivity","score":4.25,"norm":3.35,"diff":0.90,"level":"High","meaning":"You notice and value quality, design, and craft more than most.","preferences":"You do well where attention to quality genuinely matters.","potential_needs":"You are most satisfied when quality is genuinely valued."},
             {"name":"Creative Imagination","score":4.75,"norm":3.60,"diff":1.15,"level":"High","meaning":"You generate ideas readily and enjoy exploring possibilities others might not consider.","preferences":"You thrive where experimentation is encouraged.","potential_needs":"You stay engaged when there is room to try new approaches."},
         ]},
    ],
    "recommendations": {
        "strengths": [
            "You build trust quickly and genuinely, making you someone a team naturally relies on.",
            "Your curiosity drives you to look for better approaches rather than settling for the familiar one.",
            "You stay steady under pressure, and that calm settles the people around you.",
            "You follow through on what matters, and your warmth makes the effort feel effortless to others.",
        ],
        "blind_spots": [
            "Your energy outpaces your assertiveness, so you may carry effort quietly and end up undercredited for it.",
            "Your steadiness can mask strain, keeping pressure hidden from others and sometimes from yourself.",
            "Your default toward trust can lead you to extend it before it has been fully earned.",
        ],
        "development_suggestions": [
            "State your position, not just your effort — when you have done the work, make the contribution visible.",
            "Add lightweight structure to your follow through so your reliability is not the only thing holding the details.",
            "In lower trust environments, hold a little caution early without losing the warmth that is clearly your strength.",
            "Build in honest check-ins so the strain your calm hides has somewhere to surface.",
        ],
        "focus_paragraph": "Your profile shows someone who gives a great deal — in energy, in warmth, in follow through — and the single risk running through it is that you give more than you claim. Your Open-Mindedness and Sociability make you the person teams lean on and look to, and your composure makes it look effortless. The one shift that compounds everything else: make your contribution as visible as it is real. State your position early, name your effort clearly, and let the quieter strengths you carry be seen."
    }
}

participant = {"name": "Jordan Avery", "role": "Operations Manager"}

pdf_bytes = generate_pdf(participant, report)

output_path = r"C:\Users\Acer\OneDrive\Desktop\test_report.pdf"
with open(output_path, "wb") as f:
    f.write(pdf_bytes)

print(f"Done! PDF saved to {output_path}")
print(f"Size: {len(pdf_bytes):,} bytes")