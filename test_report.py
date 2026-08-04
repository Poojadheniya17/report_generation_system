# test_report.py
import sys
sys.path.insert(0, r"C:\Users\Acer\OneDrive\Desktop\report_generation_system")

from app.services.pdf_generator import generate_pdf

report = {
    "executive_summary": {
        "text": "Jordan's most defining workplace characteristic is a natural pull toward connection: Sociability is the strongest tendency in the TRIAD profile, and it is reinforced by high Agreeableness in the personality results. Jordan builds trust quickly, keeps communication open, and tends to hold a team together through consistent, genuine engagement rather than authority. Open-Mindedness is Jordan's highest personality domain, pointing to someone who actively looks for better approaches instead of defaulting to convention.\n\nThe key tension to watch is the gap between Jordan's high Energy Level and only moderate Assertiveness: Jordan puts in visible effort and pushes work forward, but states personal positions more quietly than the work itself would suggest. Managers get the most from Jordan by creating explicit space for Jordan's input in higher-stakes discussions and by naming Jordan's contributions directly rather than assuming they will be self-evident."
    },
    "triad": {
        "task": {
            "score": 1.83, "direction_label": "Moderate tendency toward",
            "interpretation": "Jordan shows a moderate lean toward task focus, inclined to keep work moving toward a clear outcome and to follow through on commitments without needing rigid structure to stay on track.",
            "likely_contribution": "On a team, Jordan is likely to keep projects progressing and take ownership of assigned responsibilities. Jordan works best when priorities are clear and shared, rather than left entirely to Jordan to define.",
            "manager_considerations": "Give Jordan a clear outcome and check in on structure rather than micromanaging process. Because this tendency is moderate rather than strong, pairing Jordan with someone more process-driven on complex projects can add useful ballast.",
        },
        "sociability": {
            "score": 2.17, "direction_label": "Strong tendency toward",
            "interpretation": "This is the strongest tendency in Jordan's profile. Jordan is inclined to engage with people, read group dynamics, and keep relationships smooth, often without visible effort.",
            "likely_contribution": "Jordan is likely to strengthen cohesion and communication across the team, and colleagues tend to gravitate toward Jordan for informal problem-solving. This makes Jordan valuable in roles that depend on cross-functional coordination.",
            "manager_considerations": "Watch for Jordan absorbing more of the team's relational labor than is sustainable or visible in performance reviews. Make a habit of naming this contribution explicitly, since it is easy to under-credit.",
        },
        "dominance": {
            "score": 0.83, "direction_label": "Mild tendency toward",
            "interpretation": "Jordan shows a mild tendency toward assertiveness, stepping in when it genuinely matters but not seeking to lead every interaction.",
            "likely_contribution": "This makes Jordan adaptable: capable of taking the lead when a situation calls for it, and equally comfortable supporting someone else's lead. In louder rooms, Jordan's input may stay understated unless directly invited.",
            "manager_considerations": "In group settings with more assertive voices, proactively invite Jordan's perspective rather than waiting for it. Position Jordan for lead roles on initiatives that reward steady influence over forceful direction.",
        },
    },
    "domains": [
        {"name": "Extraversion", "score": 3.83, "norm": 3.27, "level": "High",
         "meaning": "Jordan's Extraversion sits above the norm, driven mainly by high Energy Level rather than high Assertiveness. This combination means Jordan brings visible drive and enthusiasm to work without needing to dominate discussions. Paired with strong Agreeableness, Jordan tends to raise a group's energy through warmth rather than pressure.",
         "preferences": "Jordan does best in roles with regular contact and visible collaboration, where energy has an audience and ideas get real engagement.",
         "potential_needs": "Because Jordan's energy outpaces assertiveness, effort can go unclaimed. Encourage Jordan to state contributions directly, not just deliver them, and provide regular interaction so energy has somewhere to go.",
         "facets": [
             {"name": "Sociability", "score": 3.75, "norm": 3.20, "level": "High",
              "meaning": "Jordan seeks out company rather than waiting for it, and is clearly above the norm here without needing constant social contact to stay effective.",
              "preferences": "Jordan performs well in roles built around regular, genuine interaction with others.",
              "potential_needs": "Give Jordan work that includes real conversation, not just transactional check-ins, to sustain engagement."},
             {"name": "Assertiveness", "score": 3.50, "norm": 3.35, "level": "Average",
              "meaning": "Jordan sits close to the norm here, the quieter half of the Extraversion story. Jordan will speak up when it matters but does not push to lead every exchange.",
              "preferences": "Jordan is comfortable contributing without needing to control the conversation.",
              "potential_needs": "In rooms with louder voices, prompt Jordan directly so input is not lost by default."},
             {"name": "Energy Level", "score": 4.25, "norm": 3.25, "level": "High",
              "meaning": "This is Jordan's highest Extraversion facet and a major driver of how colleagues experience Jordan day to day: visible pace, stamina, and enthusiasm.",
              "preferences": "Jordan thrives when there is real momentum and active movement in the work.",
              "potential_needs": "Slow, low-stimulation stretches will drain Jordan faster than most. Look for ways to keep pace and variety in Jordan's workload."},
         ]},
        {"name": "Agreeableness", "score": 4.08, "norm": 3.57, "level": "High",
         "meaning": "This is one of Jordan's strongest domains, with Compassion, Respectfulness, and Trust all elevated together. That consistency means cooperation is a default for Jordan, not a strategy, and colleagues generally find Jordan easy to work with.",
         "preferences": "Jordan thrives where collaboration is valued over competition and good faith is the norm rather than the exception.",
         "potential_needs": "Because trust is Jordan's starting point, Jordan may extend it before it has been earned in lower-trust environments. A little more early caution in unproven situations protects Jordan without costing the warmth that is a clear strength.",
         "facets": [
             {"name": "Compassion", "score": 4.00, "norm": 3.65, "level": "High",
              "meaning": "Jordan is strongly attuned to how others feel and is genuinely invested in colleagues' wellbeing, a defining part of how Jordan works with people.",
              "preferences": "Jordan does best in cultures that value care and mutual support.",
              "potential_needs": "Jordan stays balanced when that compassion is reciprocated rather than one-directional."},
             {"name": "Respectfulness", "score": 4.25, "norm": 3.60, "level": "High",
              "meaning": "Jordan treats people with courtesy and consideration as a default, regardless of position or seniority.",
              "preferences": "Jordan works well where mutual respect is the norm across the team.",
              "potential_needs": "Jordan is most comfortable, and most productive, when that respect is returned consistently."},
             {"name": "Trust", "score": 3.92, "norm": 3.65, "level": "High",
              "meaning": "Jordan extends good faith readily and tends to assume the best of people until shown otherwise.",
              "preferences": "Jordan thrives in high-trust, low-politics environments.",
              "potential_needs": "A little early caution in unproven settings protects Jordan without undermining the openness that is a real asset."},
         ]},
        {"name": "Conscientiousness", "score": 3.58, "norm": 3.52, "level": "Average",
         "meaning": "Jordan sits close to the norm here, making this the most flexible domain in the profile. Responsibility runs notably higher than Organization: Jordan reliably follows through on what matters even when the underlying system for getting there is looser than the sense of duty behind it.",
         "preferences": "Jordan works well with clear priorities and room to adapt as things shift, rather than rigid process for its own sake.",
         "potential_needs": "Because follow-through outpaces organization, lightweight structure such as a simple checklist or a firm deadline will catch details that commitment alone might miss.",
         "facets": [
             {"name": "Organization", "score": 3.40, "norm": 3.45, "level": "Average",
              "meaning": "Jordan sits around the norm here, and notably below Responsibility. Jordan can structure work when needed, but it is not the strongest natural instinct.",
              "preferences": "Jordan works best with clear priorities rather than rigid systems imposed from outside.",
              "potential_needs": "Lightweight tools such as a short list or a clear deadline will catch what follow-through alone might let slip."},
             {"name": "Productiveness", "score": 3.50, "norm": 3.48, "level": "Average",
              "meaning": "Jordan is reliably productive at a steady, sustainable pace without being driven to over-produce.",
              "preferences": "Jordan does well with realistic workloads and clearly defined outcomes.",
              "potential_needs": "Concrete goals help Jordan sustain output over longer stretches."},
             {"name": "Responsibility", "score": 3.83, "norm": 3.62, "level": "High",
              "meaning": "This is Jordan's strongest Conscientiousness facet. Jordan takes ownership seriously and follows through on commitments.",
              "preferences": "Jordan thrives when trusted with real accountability rather than close supervision.",
              "potential_needs": "Jordan stays effective when that sense of duty is matched with enough structure to support it."},
         ]},
        {"name": "Negative Emotionality", "score": 2.25, "norm": 2.77, "level": "Low",
         "meaning": "Jordan scores low across all three facets here, marking genuine emotional steadiness rather than a situational calm. Jordan recovers quickly from setbacks and stays even as pressure rises.",
         "preferences": "Jordan is at their best in fast-moving situations where a steady presence helps settle the people around them.",
         "potential_needs": "That steadiness can mask strain, both from others and from Jordan's own awareness of it. Build in regular, honest check-ins so pressure does not build unnoticed beneath the calm exterior.",
         "facets": [
             {"name": "Anxiety", "score": 2.33, "norm": 2.80, "level": "Low",
              "meaning": "Jordan stays relatively calm under uncertainty and worries less than most in ambiguous situations.",
              "preferences": "Jordan functions well in ambiguous or high-pressure conditions.",
              "potential_needs": "Encourage Jordan to name concerns early, before small worries compound unspoken."},
             {"name": "Depression", "score": 2.00, "norm": 2.70, "level": "Low",
              "meaning": "Jordan points to a generally stable, positive baseline mood at work.",
              "preferences": "Jordan brings a steadiness that colleagues can reliably lean on.",
              "potential_needs": "Jordan holds up best with regular positive connection and recognition of effort."},
             {"name": "Emotional Volatility", "score": 2.42, "norm": 2.80, "level": "Low",
              "meaning": "Jordan's reactions stay even and predictable to the people working alongside them.",
              "preferences": "Jordan functions as a calming presence on a team under pressure.",
              "potential_needs": "Jordan stays balanced with space to process before reacting to sudden changes."},
         ]},
        {"name": "Open-Mindedness", "score": 4.58, "norm": 3.50, "level": "High",
         "meaning": "This is Jordan's highest domain by a wide margin, with every facet near the top of the scale. Jordan is drawn to ideas, quality, and new ways of approaching a problem, and actively looks for the better approach rather than the established one. Combined with only mild Dominance, this suggests Jordan leads through ideas and persuasion more than positional authority.",
         "preferences": "Jordan is most engaged in roles that reward learning, experimentation, and fresh thinking, and tends to bring others into that exploration.",
         "potential_needs": "Routine, repetitive work with no room to explore will drain Jordan faster than most. Keep a genuine problem in front of Jordan to stay engaged.",
         "facets": [
             {"name": "Intellectual Curiosity", "score": 4.50, "norm": 3.55, "level": "High",
              "meaning": "Near the top of the scale, Jordan actively seeks out ideas, questions, and new understanding.",
              "preferences": "Jordan is most engaged in roles that reward learning and inquiry.",
              "potential_needs": "Jordan disengages quickly from work that offers nothing new to think about."},
             {"name": "Aesthetic Sensitivity", "score": 4.58, "norm": 3.40, "level": "High",
              "meaning": "Jordan notices and values quality, design, and craft more than most colleagues.",
              "preferences": "Jordan does well where attention to form and experience genuinely matters.",
              "potential_needs": "Jordan is most satisfied when quality is actually valued, not just tolerated."},
             {"name": "Creative Imagination", "score": 4.67, "norm": 3.55, "level": "High",
              "meaning": "Jordan generates ideas readily and enjoys exploring possibilities that others might overlook.",
              "preferences": "Jordan thrives where experimentation is encouraged rather than discouraged.",
              "potential_needs": "Jordan stays engaged with room to try new approaches rather than repeat set ones."},
         ]},
    ],
    "manager_action_guide": {
        "communication_style": {
            "narrative": "Jordan communicates through warmth and steady engagement rather than assertion. High Sociability and Agreeableness mean Jordan reads group dynamics well and works to keep exchanges smooth, while only moderate Assertiveness and mild Dominance mean Jordan's own positions can get lost in the mix if not directly invited. Feedback lands best when it is direct but delivered with the same warmth Jordan extends to others.",
            "recommendations": [
                "Ask for Jordan's view directly in meetings rather than waiting for it to surface",
                "Deliver feedback in a direct, specific, low-drama style; Jordan responds well to clarity",
                "Encourage Jordan to state positions as recommendations, not just observations",
                "Avoid conflict-avoidant framing when giving critical feedback; Jordan can handle directness",
                "Use one-on-ones to surface disagreements Jordan may be smoothing over in group settings",
            ],
        },
        "motivators_stressors": {
            "narrative": "Jordan is energized by momentum, genuine interaction, and problems worth solving, and is steady enough to hold that energy through pressure without losing composure. Stagnant, low-interaction, or purely repetitive work will wear on Jordan faster than it would most people, and unacknowledged effort is a quieter but real source of frustration.",
            "motivators": [
                "Fast-moving work with visible progress and real collaboration",
                "Novel problems that reward curiosity and creative thinking",
                "Public or direct recognition of contributions, not just outcomes",
                "Teams with a genuine, low-politics collaborative culture",
            ],
            "stressors": [
                "Long stretches of repetitive, low-interaction work",
                "Environments where trust has to be earned before collaboration starts",
                "Contributions going unnoticed or uncredited over time",
                "Rigid process imposed without room to adapt",
            ],
        },
        "delegation_guide": {
            "narrative": "Jordan is best suited for work that blends steady follow-through with room to bring people together. High Responsibility means delegated ownership will be honored, and high Sociability makes Jordan a natural fit for anything that depends on relationship-building or cross-team coordination. Because Organization is only average, complex multi-thread projects benefit from a lightweight structure supplied up front.",
            "best_suited_for": [
                "Cross-functional coordination and stakeholder-facing work",
                "Initiatives that benefit from building buy-in across a team",
                "Ownership of a clear outcome with flexibility in how to get there",
                "Mentoring or onboarding roles that draw on natural warmth and curiosity",
            ],
            "recommendations": [
                "Grant real autonomy on execution once the outcome is agreed",
                "Provide a simple structural scaffold, like milestones or a shared tracker, for multi-step work",
                "Check in on progress rather than process; Jordan will flag real blockers",
                "Pair with a more detail-oriented teammate for projects with many moving parts",
            ],
        },
        "leadership_summary": {
            "narrative": "Jordan is a connector: someone who builds trust quickly, brings steady energy to a team, and pushes work forward through relationships and curiosity rather than authority. The core risk in this profile is not underperformance but under-visibility: Jordan tends to give more than gets claimed, and that pattern compounds if a manager does not name it directly.",
            "strengths": [
                "Builds genuine trust quickly and holds a team together informally",
                "Brings consistent energy and follow-through to committed work",
                "Curious and open to better approaches rather than defaulting to convention",
                "Stays steady and composed under pressure, which settles those around Jordan",
            ],
            "watch_points": [
                "Effort and contribution can go unclaimed without direct prompting",
                "May extend trust in lower-trust settings before it has been earned",
                "Steadiness can mask real strain if not checked in on directly",
            ],
            "actions": [
                "Proactively invite Jordan's input in higher-stakes meetings",
                "Name Jordan's contributions explicitly in team and leadership updates",
                "Build regular, honest check-ins focused on workload and sustainability",
                "Brief Jordan ahead of politically complex stakeholder conversations",
            ],
        },
    },
    "role_cluster_proximity": {
        "business_interpretation": "Jordan's TRIAD profile combines a moderate task orientation with a distinctly strong pull toward sociability and only a mild dominance signal, a pattern that places Jordan closest to the Coordinator cluster and, more loosely, near the Social and Problem Solver profiles. This blend suggests someone who keeps work moving without needing to control it directly: task focus is present but not rigid, and the sociability score, well above the other two dimensions, means connection and coordination are the primary lever Jordan relies on to get things done. The mild dominance score points to influence through presence and consistency rather than assertion, consistent with a coordinator-style profile rather than a directive one.",
        "strengths": [
            {"title": "Natural Team Connector", "explanation": "Jordan's sociability score is the clear high point of the profile, well above both task orientation and dominance, making relationship-building Jordan's default mode of getting work done."},
            {"title": "Steady Task Follow-Through", "explanation": "A moderate but real task orientation means Jordan keeps commitments on track without needing to lead through control or urgency."},
            {"title": "Low-Friction Influence", "explanation": "With dominance only mildly elevated, Jordan tends to move people and plans forward through consistency and trust rather than direct assertion."},
            {"title": "Coordinator-Level Versatility", "explanation": "Jordan's closest match reflects an unusually balanced combination across all three dimensions rather than a narrow specialization in just one."},
            {"title": "Comfortable Across Adjacent Roles", "explanation": "Secondary proximity to both Social and Problem Solver profiles suggests Jordan can flex into relationship-first or resolution-first work depending on what a team needs."},
        ],
        "development_areas": [
            {"title": "Building Comfort with Direct Assertion", "explanation": "Because dominance sits well below sociability, Jordan may default to influence-through-relationship even in moments that call for a more direct stance, particularly in fast-moving or high-conflict discussions."},
            {"title": "Strengthening Structural Follow-Up", "explanation": "With task orientation only moderate rather than strong, Jordan's coordination style benefits from an explicit tracking system on complex, multi-owner projects, especially where relational check-ins alone may leave gaps."},
            {"title": "Leading Without Full Group Buy-In", "explanation": "Jordan's coordinator-style profile is well suited to consensus-building work; developing comfort making a call before full alignment is reached would round out this pattern, most likely to surface when timelines are tight."},
        ],
    },
}

participant = {"name": "Jordan Avery", "role": "Operations Manager"}

pdf_bytes = generate_pdf(participant, report)

output_path = r"C:\Users\Acer\OneDrive\Desktop\test_report.pdf"
with open(output_path, "wb") as f:
    f.write(pdf_bytes)

print(f"Done! PDF saved to {output_path}")
print(f"Size: {len(pdf_bytes):,} bytes")
