"""Composite influence scoring, tiering, and strategic flags.

Each component is converted to a 0-1 percentile rank (robust to outliers and
to the very skewed distributions typical of bibliometric data), then combined
with the transparent, adjustable weights in ``config.SCORE_WEIGHTS``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config
from . import geo
from .disambiguate import Expert


def _percentile_rank(s: pd.Series) -> pd.Series:
    """Map values to [0,1] by rank. Ties share the average rank."""
    if s.nunique() <= 1:
        return pd.Series(np.zeros(len(s)), index=s.index)
    return s.rank(method="average", pct=True)


def score_experts(experts: dict[str, Expert],
                  centrality: dict[str, float],
                  weights: dict | None = None,
                  min_pubs: int = 2) -> pd.DataFrame:
    weights = weights or config.SCORE_WEIGHTS
    rows = []
    for k, e in experts.items():
        if e.pub_count < min_pubs:
            continue
        rows.append({
            "key": k,
            "name": e.name or k,
            "affiliation": e.affiliation,
            "country": e.country,
            "publications": e.pub_count,
            "senior_authorships": e.senior_count,
            "recent_publications": e.recent_count,
            "recency_ratio": round(e.recency_ratio, 3),
            "trials_led": e.trial_count,
            "industry_trials": e.industry_trial_count,
            "centrality_raw": centrality.get(k, 0.0),
            "focus": ", ".join(e.focus_terms),
            "top_journals": ", ".join(j for j, _ in e.journals.most_common(3)),
            "active_years": f"{min(e.years)}-{max(e.years)}" if e.years else "",
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["region"] = df["country"].apply(geo.country_to_region)

    # Citation proxy: senior authorships are a defensible stand-in until a
    # citation source (OpenAlex / Semantic Scholar) is wired in (see roadmap).
    df["citation_proxy"] = df["senior_authorships"]

    comp = {
        "publications": _percentile_rank(df["publications"]),
        "seniority": _percentile_rank(df["senior_authorships"]),
        "recency": _percentile_rank(df["recent_publications"]),
        "trials": _percentile_rank(df["trials_led"]),
        "citations": _percentile_rank(df["citation_proxy"]),
        "centrality": _percentile_rank(df["centrality_raw"]),
    }
    for name, series in comp.items():
        df[f"c_{name}"] = (series * 100).round(1)

    total_w = sum(weights.values()) or 1.0
    df["influence_score"] = sum(
        comp[name] * (w / total_w) for name, w in weights.items()
    ) * 100
    df["influence_score"] = df["influence_score"].round(1)

    df = df.sort_values("influence_score", ascending=False).reset_index(drop=True)
    df.insert(0, "rank", df.index + 1)

    # ---- tiering (percentile of the composite score) ----
    s = df["influence_score"]
    t1 = s.quantile(config.TIER_PERCENTILES["Tier 1"])
    t2 = s.quantile(config.TIER_PERCENTILES["Tier 2"])
    df["tier"] = np.where(s >= t1, "Tier 1", np.where(s >= t2, "Tier 2", "Tier 3"))

    # ---- strategic flags ----
    df["rising_star"] = (
        (df["recency_ratio"] >= config.RISING_STAR_RECENCY_MIN)
        & (df["publications"] <= config.RISING_STAR_MAX_PUBS)
        & (df["recent_publications"] >= 3)
    )
    # White-space / under-engaged: high scientific influence, little or no
    # industry trial involvement (proxy for low industry engagement; swap in
    # CMS Open Payments for the production signal).
    ws_cut = s.quantile(config.WHITESPACE_SCORE_MIN_PERCENTILE)
    df["whitespace"] = (s >= ws_cut) & (df["industry_trials"] == 0)

    return df


def tier_summary(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"experts": 0}
    return {
        "experts": int(len(df)),
        "tier1": int((df["tier"] == "Tier 1").sum()),
        "tier2": int((df["tier"] == "Tier 2").sum()),
        "tier3": int((df["tier"] == "Tier 3").sum()),
        "rising_stars": int(df["rising_star"].sum()),
        "whitespace": int(df["whitespace"].sum()),
    }
