"""Per-expert engagement briefs.

By default briefs are composed deterministically from the structured evidence
(no hallucination, fully traceable). An optional LLM path can enrich the prose
when an API key is supplied — the demo ships the cached deterministic version so
the public app needs no key and no live spend.
"""
from __future__ import annotations

import pandas as pd

ROLE_LABEL = {
    "PRINCIPAL_INVESTIGATOR": "Principal Investigator",
    "STUDY_CHAIR": "Study Chair",
    "STUDY_DIRECTOR": "Study Director",
    "RESPONSIBLE_PARTY_PI": "Responsible-party PI",
    "OFFICIAL": "Trial official",
}


def _profile(row: pd.Series) -> str:
    name = row["name"]
    aff = row["affiliation"] or "an undisclosed institution"
    bits = [f"{name} is a {row['tier']} expert in the multiple myeloma landscape"]
    if row["affiliation"]:
        bits.append(f", affiliated with {aff}")
    bits.append(
        f". They appear on {int(row['publications'])} relevant publications "
        f"({int(row['senior_authorships'])} as first/last author) over {row['active_years']}, "
        f"with {int(row['recent_publications'])} in the recent window."
    )
    if row["trials_led"]:
        bits.append(
            f" They hold leadership roles on {int(row['trials_led'])} registered clinical "
            f"trial(s), {int(row['industry_trials'])} industry-sponsored."
        )
    if row["focus"]:
        bits.append(f" Apparent research focus: {row['focus']}.")
    return "".join(bits)


def _talking_points(row: pd.Series) -> list[str]:
    points: list[str] = []
    focus = [f.strip() for f in (row["focus"] or "").split(",") if f.strip()]
    if focus:
        points.append(
            f"Open on their published focus areas ({', '.join(focus[:2])}) to ground the "
            f"exchange in their own evidence."
        )
    if row["trials_led"] and row["industry_trials"] == 0:
        points.append(
            "Strong academic trial leadership but no industry-sponsored trials on record — "
            "explore interest in collaborative or investigator-initiated studies."
        )
    elif row["trials_led"]:
        points.append(
            "Active trialist — discuss emerging data readouts and evidence-generation gaps "
            "relevant to your asset."
        )
    if row["rising_star"]:
        points.append(
            "Rising-star trajectory (high recent output) — early scientific engagement now "
            "builds a durable relationship ahead of peers."
        )
    if row["whitespace"]:
        points.append(
            "High influence yet low industry engagement (white space) — a priority for new "
            "scientific relationship-building."
        )
    if len(points) < 3:
        points.append(
            "Validate the engagement priority against territory alignment and recent congress "
            "activity before outreach."
        )
    return points[:3]


def generate_brief(row: pd.Series) -> dict:
    """Return a structured brief for one expert (a row of the scored DataFrame)."""
    return {
        "profile": _profile(row),
        "talking_points": _talking_points(row),
    }


def generate_all(df: pd.DataFrame, top_n: int = 60) -> dict[str, dict]:
    briefs: dict[str, dict] = {}
    for _, row in df.head(top_n).iterrows():
        briefs[row["key"]] = generate_brief(row)
    return briefs
