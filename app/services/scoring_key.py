"""
BFI-2 scoring key and TRIAD/Norms reference data.

This is a faithful, code-form transcription of the client's scoring workbook
(Copy_of_Work_Style_Report_Scoring_Logic.xlsx), sheets: BFI2_Key, Norms,
TRIAD_Clusters. Keeping it as data (not hardcoded formulas) means the scoring
engine is a small, testable function and any future change to the key is a
one-line edit here.

Verified against the published BFI-2 (Soto & John, 2017) item key.

Scale: respondents answer each item 1–5. Reverse-scored items are recoded as
(6 - x) before averaging. Each FACET = mean of its 4 items. Each DOMAIN =
mean of its 3 facets. (Equivalently the mean of its 12 items — same result.)
"""
from __future__ import annotations

# --- BFI-2: item -> (domain, facet, reverse?) -----------------------------
# Item numbers are 1..60, matching survey refs BFI_1..BFI_60.
DOMAINS = [
    "Extraversion",
    "Agreeableness",
    "Conscientiousness",
    "Negative_Emotionality",
    "Open_Mindedness",
]

# facet -> parent domain, in the canonical report order
FACET_TO_DOMAIN = {
    "Sociability": "Extraversion",
    "Assertiveness": "Extraversion",
    "Energy_Level": "Extraversion",
    "Compassion": "Agreeableness",
    "Respectfulness": "Agreeableness",
    "Trust": "Agreeableness",
    "Organization": "Conscientiousness",
    "Productiveness": "Conscientiousness",
    "Responsibility": "Conscientiousness",
    "Anxiety": "Negative_Emotionality",
    "Depression": "Negative_Emotionality",
    "Emotional_Volatility": "Negative_Emotionality",
    "Intellectual_Curiosity": "Open_Mindedness",
    "Aesthetic_Sensitivity": "Open_Mindedness",
    "Creative_Imagination": "Open_Mindedness",
}

DOMAIN_TO_FACETS = {
    "Extraversion": ["Sociability", "Assertiveness", "Energy_Level"],
    "Agreeableness": ["Compassion", "Respectfulness", "Trust"],
    "Conscientiousness": ["Organization", "Productiveness", "Responsibility"],
    "Negative_Emotionality": ["Anxiety", "Depression", "Emotional_Volatility"],
    "Open_Mindedness": [
        "Intellectual_Curiosity",
        "Aesthetic_Sensitivity",
        "Creative_Imagination",
    ],
}

# (item_number, facet, reverse) — transcribed from BFI2_Key sheet.
BFI2_KEY: list[tuple[int, str, bool]] = [
    (1, "Sociability", False),
    (2, "Compassion", False),
    (3, "Organization", True),
    (4, "Anxiety", True),
    (5, "Aesthetic_Sensitivity", True),
    (6, "Assertiveness", False),
    (7, "Respectfulness", False),
    (8, "Productiveness", True),
    (9, "Depression", True),
    (10, "Intellectual_Curiosity", False),
    (11, "Energy_Level", True),
    (12, "Trust", True),
    (13, "Responsibility", False),
    (14, "Emotional_Volatility", False),  # NOT reversed (client's Excel; differs from published BFI-2)
    (15, "Creative_Imagination", False),
    (16, "Sociability", True),
    (17, "Compassion", True),
    (18, "Organization", False),
    (19, "Anxiety", False),
    (20, "Aesthetic_Sensitivity", False),
    (21, "Assertiveness", False),
    (22, "Respectfulness", True),
    (23, "Productiveness", True),
    (24, "Depression", True),
    (25, "Intellectual_Curiosity", True),
    (26, "Energy_Level", True),
    (27, "Trust", False),
    (28, "Responsibility", True),
    (29, "Emotional_Volatility", True),
    (30, "Creative_Imagination", True),
    (31, "Sociability", True),
    (32, "Compassion", False),
    (33, "Organization", False),
    (34, "Anxiety", False),
    (35, "Aesthetic_Sensitivity", False),
    (36, "Assertiveness", True),
    (37, "Respectfulness", True),
    (38, "Productiveness", False),
    (39, "Depression", False),
    (40, "Intellectual_Curiosity", False),
    (41, "Energy_Level", False),
    (42, "Trust", True),
    (43, "Responsibility", False),
    (44, "Emotional_Volatility", True),
    (45, "Creative_Imagination", True),
    (46, "Sociability", False),
    (47, "Compassion", True),
    (48, "Organization", True),
    (49, "Anxiety", True),
    (50, "Aesthetic_Sensitivity", True),
    (51, "Assertiveness", True),
    (52, "Respectfulness", False),
    (53, "Productiveness", False),
    (54, "Depression", False),
    (55, "Intellectual_Curiosity", True),
    (56, "Energy_Level", False),
    (57, "Trust", False),
    (58, "Responsibility", True),
    (59, "Emotional_Volatility", False),  # NOT reversed (client's Excel; differs from published BFI-2)
    (60, "Creative_Imagination", False),
]

# --- TRIAD: 18 items, 6 per dimension (Raw_Responses cols F..W) ------------
# TRIAD_1..6 -> Task, TRIAD_7..12 -> Sociability, TRIAD_13..18 -> Dominance.
# Each dimension score = mean of its 6 items. (No reverse-scoring in TRIAD.)
TRIAD_ITEMS = {
    "Task": [1, 2, 3, 4, 5, 6],
    "Sociability": [7, 8, 9, 10, 11, 12],
    "Dominance": [13, 14, 15, 16, 17, 18],
}

# --- Norms (Norms sheet) ---------------------------------------------------
NORMS: dict[str, float] = {
    "Extraversion": 3.27,
    "Agreeableness": 3.57,
    "Conscientiousness": 3.52,
    "Negative_Emotionality": 2.77,
    "Open_Mindedness": 3.50,
    "Sociability": 3.20,
    "Assertiveness": 3.35,
    "Energy_Level": 3.25,
    "Compassion": 3.55,
    "Respectfulness": 3.65,
    "Trust": 3.50,
    "Organization": 3.40,
    "Productiveness": 3.55,
    "Responsibility": 3.60,
    "Anxiety": 2.85,
    "Depression": 2.70,
    "Emotional_Volatility": 2.75,
    "Intellectual_Curiosity": 3.55,
    "Aesthetic_Sensitivity": 3.35,
    "Creative_Imagination": 3.60,
}

# Level cut-off (BFI2_Scoring *_Level formula): |diff| < 0.25 -> Average,
# else High if diff > 0 else Low.
LEVEL_THRESHOLD = 0.25

# --- TRIAD role clusters (TRIAD_Clusters sheet) ----------------------------
# Each role has a center in (Task, Sociability, Dominance) space. A participant
# is assigned the role whose center is nearest (Euclidean distance).
# NOTE: cluster centers are on a centered scale (negative values present),
# while raw TRIAD means are 1..5. See score_triad() for the centering step.
TRIAD_CLUSTERS: list[tuple[str, float, float, float]] = [
    ("Team Leader", 2.58, 0.04, 2.35),
    ("Task Motivator", 0.64, -0.04, 1.96),
    ("Power Seeker", -0.43, -2.43, 2.13),
    ("Critic", -0.92, -1.31, -0.30),
    ("Attention Seeker", -2.46, 0.00, 0.50),
    ("Negative", -2.75, -2.22, -2.22),
    ("Social", -0.03, 2.84, -0.45),
    ("Coordinator", 1.69, 2.15, 0.56),
    ("Follower", 0.56, 1.24, -2.39),
    ("Teamwork Support", 2.24, 0.11, -2.15),
    ("Evaluator", 2.30, -2.23, -0.10),
    ("Problem Solver", 1.28, 0.02, -0.25),
    ("Task Completer", 2.64, -0.08, -0.56),
]
