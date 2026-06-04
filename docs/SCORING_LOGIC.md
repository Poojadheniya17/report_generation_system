# Scoring Logic (decoded from client workbook)

Source of truth: `Copy_of_Work_Style_Report_Scoring_Logic.xlsx`. The scoring
engine (`app/services/scoring.py` + `scoring_key.py`) reproduces this workbook
exactly — verified to 1e-4 against the 6 sample participants in the workbook
(see `tests/test_scoring.py`, 168/168 assertions pass).

## Inputs

Two question groups arrive from the Typeform:

- **TRIAD** — 18 items (`TRIAD_1`..`TRIAD_18`). Typeform forces a **1–7**
  opinion scale; the client's model centers this to **−3..+3** via `x − 4`
  (1→−3, 4→0, 7→+3). Verified consistent with the workbook's stored values.
  The ingestion/scoring path converts live 1–7 answers automatically
  (`score_all(..., triad_already_centered=False)`); workbook fixtures are
  already centered. No reverse-scoring on TRIAD. **(Confirmed with client.)**
- **BFI-2** — 60 items (`BFI_1`..`BFI_60`) on a **1–5 Likert** scale.

## TRIAD scoring

- Task = mean(TRIAD_1..6)
- Sociability = mean(TRIAD_7..12)
- Dominance = mean(TRIAD_13..18)

13 role clusters (Team Leader, Coordinator, …) exist in the workbook with
center points. **Client confirmed clusters are NOT needed right now** — reports
keep the three-dimension TRIAD interpretation. Cluster assignment is implemented
(`score_triad(assign_cluster=True)`) and left OFF, ready if needed later (the
−3..+3 scale exists specifically to enable Euclidean cluster matching in 3D).

## BFI-2 scoring

- Each **facet** = mean of its 4 items; reverse items recoded `(6 − x)`.
- Each **domain** = mean of its 3 facets.
- 5 domains, 15 facets, canonical report order (Extraversion → Agreeableness →
  Conscientiousness → Negative Emotionality → Open-Mindedness).

### Important: reverse-scoring deviates from the published BFI-2

The workbook's **Negative Emotionality** facets reverse different items than the
standard Soto & John (2017) key. The engine follows the **workbook**, since the
client's reports are generated from it. Verified reversed items per facet:

| Facet | Reversed items |
|---|---|
| Sociability | 16, 31 |
| Assertiveness | 36, 51 |
| Energy Level | 11, 26 |
| Compassion | 17, 47 |
| Respectfulness | 22, 37 |
| Trust | 12, 42 |
| Organization | 3, 48 |
| Productiveness | 8, 23 |
| Responsibility | 28, 58 |
| Anxiety | 4, 49 |
| Depression | 9, 24 |
| Emotional Volatility | 29, 44 |
| Intellectual Curiosity | 25, 55 |
| Aesthetic Sensitivity | 5, 50 |
| Creative Imagination | 30, 45 |

## Norms, diff, level

Each domain/facet has a fixed norm (see `NORMS` in `scoring_key.py`).
- diff = score − norm
- level: `|diff| < 0.25` → **Average**; else **High** if diff > 0 else **Low**.

## Output shape

`score_all()` returns a dict shaped to feed the AI interpretation prompt
(`docs/AI_JSON_Interpreation.docx`): `triad.{task,sociability,dominance}.score`
and `bfi2.domains[].{name,score,norm,diff,level, facets[].{...}}`.

## Resolved with the client

1. TRIAD live scale: **1–7**, centered to −3..+3 via `x − 4`. ✓
2. Role clusters: **not used** in current reports; three-dimension
   interpretation retained. ✓

Final 100% confirmation of the live scale happens at the first real test
submission, when an actual raw Typeform answer flows through the pipeline.
