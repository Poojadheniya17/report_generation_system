"""
Scoring verification against the client's Excel workbook.

Fixtures in excel_fixtures.json are the 6 sample participants from
Copy_of_Work_Style_Report_Scoring_Logic.xlsx, with raw answers AND the Excel's
own computed facet/domain/TRIAD values. We assert our engine reproduces every
number to within 1e-4. This is the contract: scoring MUST match the workbook.
"""
import json
import os

from app.services.scoring import score_all, score_bfi2, score_triad
from app.services.scoring_key import LEVEL_THRESHOLD, NORMS

HERE = os.path.dirname(__file__)
CASES = json.load(open(os.path.join(HERE, "excel_fixtures.json")))
TOL = 1e-4


def _expected_level(score, norm):
    diff = score - norm
    if abs(diff) < LEVEL_THRESHOLD:
        return "Average"
    return "High" if diff > 0 else "Low"


def run():
    results = []
    for case in CASES:
        name = case["name"]
        triad = {int(k): v for k, v in case["triad"].items()}
        bfi = {int(k): v for k, v in case["bfi"].items()}

        bfi_out = score_bfi2(bfi)
        facet_scores = {
            f["name"]: f["score"] for d in bfi_out["domains"] for f in d["facets"]
        }
        domain_scores = {d["name"]: d["score"] for d in bfi_out["domains"]}

        # facets
        for fac, exp in case["exp_facets"].items():
            if not isinstance(exp, (int, float)):
                continue
            ok = abs(facet_scores[fac] - exp) < TOL
            results.append((f"{name} facet {fac}", ok))

        # domains
        for dom, exp in case["exp_domains"].items():
            if not isinstance(exp, (int, float)):
                continue
            ok = abs(domain_scores[dom] - exp) < TOL
            results.append((f"{name} domain {dom}", ok))

        # TRIAD
        triad_out = score_triad(triad)
        for dim, exp in case["exp_triad"].items():
            if not isinstance(exp, (int, float)):
                continue
            ok = abs(triad_out[dim]["score"] - exp) < TOL
            results.append((f"{name} triad {dim}", ok))

        # levels derive from score+norm — check internal consistency
        for d in bfi_out["domains"]:
            exp_lvl = _expected_level(d["score"], NORMS[d["name"]])
            results.append((f"{name} level {d['name']}", d["level"] == exp_lvl))

    passed = sum(ok for _, ok in results)
    total = len(results)
    print(f"\n  SCORING vs EXCEL — {len(CASES)} participants")
    print("  " + "=" * 50)
    fails = [(n, ok) for n, ok in results if not ok]
    if fails:
        for n, ok in fails:
            print(f"  [FAIL] {n}")
    else:
        print(f"  [PASS] all {total} checks (facets, domains, TRIAD, levels)")
    print("  " + "=" * 50)
    print(f"  {passed}/{total} assertions passed\n")
    return passed == total


if __name__ == "__main__":
    import sys
    sys.exit(0 if run() else 1)
