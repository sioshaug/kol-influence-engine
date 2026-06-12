"""Validate the engine against a list of widely-recognised multiple myeloma experts.

This answers the inevitable interview question: *"how do you know it's right?"*
It checks how many known KOLs the engine surfaces, and in which tier, then prints
a "top-tier recall" figure you can put on a slide.

    python scripts/validate.py

NOTE: edit KNOWN_KOLS below to match your own indication / judgement. Matching is
by surname (robust to first-initial differences), so for very common surnames it
may match the highest-scoring person of that name — eyeball the matched name.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kol_engine import pipeline
from kol_engine.disambiguate import base_key

# A STARTER list of widely-published multiple myeloma investigators (public
# academic figures). Edit freely — this is your validation yardstick, not a
# definitive ranking. Format: display name used only for the report.
KNOWN_KOLS = [
    "S. Vincent Rajkumar", "Shaji Kumar", "Robert Kyle", "Paul Richardson",
    "Kenneth Anderson", "Nikhil Munshi", "Irene Ghobrial", "Sagar Lonial",
    "Maria-Victoria Mateos", "Jesus San-Miguel", "Pieter Sonneveld",
    "Philippe Moreau", "Thierry Facon", "Meletios Dimopoulos",
    "Herve Avet-Loiseau", "Gareth Morgan", "Faith Davies", "Saad Usmani",
    "Ola Landgren", "Noopur Raje", "Ajai Chari", "Philip McCarthy",
]


def surname_candidates(full_name: str) -> list[str]:
    """Possible normalised surname keys for a name.

    Handles compound surnames (San-Miguel -> 'sanmiguel', Avet-Loiseau ->
    'avetloiseau') by trying the last token AND the last two tokens joined.
    """
    tokens = full_name.replace("-", " ").split()
    cands = set()
    if tokens:
        cands.add(base_key(tokens[-1]).rstrip("_"))
    if len(tokens) >= 2:
        cands.add(base_key(tokens[-2] + tokens[-1]).rstrip("_"))
    return [c for c in cands if c]


def main() -> None:
    data, source = pipeline.load_best_available()
    if data is None:
        print("No cache found. Run scripts/build_cache.py first.")
        return
    if source == "sample":
        print("WARNING: running on the SYNTHETIC sample (fictional names). Build the "
              "live cache first (scripts/build_cache.py) for a meaningful result.\n")

    df = data["experts"]
    # Map surname-prefix -> best (highest score) expert row of that surname.
    df = df.copy()
    df["surname"] = df["key"].str.split("_").str[0]
    best_by_surname = (df.sort_values("influence_score", ascending=False)
                         .drop_duplicates("surname").set_index("surname"))

    found = top_tier = 0
    rows = []
    for name in KNOWN_KOLS:
        match_key = next((c for c in surname_candidates(name)
                          if c in best_by_surname.index), None)
        if match_key is not None:
            r = best_by_surname.loc[match_key]
            found += 1
            is_top = r["tier"] in ("Tier 1", "Tier 2")
            top_tier += int(is_top)
            rows.append((name, "yes", r["name"], r["tier"],
                         int(r["rank"]), round(float(r["influence_score"]), 1)))
        else:
            rows.append((name, "no", "-", "-", "-", "-"))

    n = len(KNOWN_KOLS)
    print(f"Validation against {n} known multiple myeloma experts")
    print("-" * 86)
    print(f"{'Known KOL':24} {'found':6} {'matched in data':24} {'tier':8} {'rank':>5} {'score':>6}")
    print("-" * 86)
    for name, f, matched, tier, rank, score in rows:
        print(f"{name:24} {f:6} {str(matched)[:24]:24} {str(tier):8} {str(rank):>5} {str(score):>6}")
    print("-" * 86)
    print(f"Found in dataset:        {found}/{n}  ({found/n*100:.0f}%)")
    print(f"In Tier 1 or Tier 2:     {top_tier}/{n}  ({top_tier/n*100:.0f}%)   <-- top-tier recall")
    print("\nSlide-ready: \"Validated against {} known KOLs; {:.0f}% surfaced in the top "
          "two tiers.\"".format(n, top_tier / n * 100))


if __name__ == "__main__":
    main()
