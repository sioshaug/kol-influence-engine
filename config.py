"""Central configuration for the KOL Influence Mapping Engine.

Everything that controls *how* an expert's influence is scored lives here, in the
open, so the logic is transparent and defensible — a Medical Director must be
able to explain why someone is Tier 1, not point at a black box.
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"      # live-built snapshot (gitignored)
SAMPLE_DIR = DATA_DIR / "sample"    # committed fixture so the app runs out-of-box

# ---------------------------------------------------------------------------
# Default indication for the showcase build
# ---------------------------------------------------------------------------
DEFAULT_INDICATION = "Multiple Myeloma"
# PubMed query for the showcase. Tightened to therapy/clinical literature.
DEFAULT_PUBMED_QUERY = (
    '"multiple myeloma"[MeSH Terms] OR "multiple myeloma"[Title/Abstract]'
)
DEFAULT_CT_CONDITION = "multiple myeloma"

# Recency window (years). "Recent" activity is weighted more heavily because
# Medical Affairs cares about who is influential *now*, not a decade ago.
CURRENT_YEAR = _dt.date.today().year
RECENT_WINDOW_YEARS = 3            # last N years count as "recent"
LOOKBACK_YEARS = 6                 # how far back ingestion reaches

# ---------------------------------------------------------------------------
# Scoring weights  (must sum to 1.0)  — fully adjustable & exposed in the UI
# ---------------------------------------------------------------------------
SCORE_WEIGHTS = {
    "publications": 0.25,   # volume of relevant publications
    "seniority": 0.20,      # first/last (senior) authorship share
    "recency": 0.15,        # share of output in the recent window
    "trials": 0.20,         # clinical-trial leadership (PI / official roles)
    "citations": 0.10,      # citation impact (proxy when available)
    "centrality": 0.10,     # position in the coauthorship network
}

# Tier thresholds applied to the 0-100 composite score (percentile-based at runtime).
TIER_PERCENTILES = {"Tier 1": 0.90, "Tier 2": 0.70}  # else Tier 3

# Rising Star: high recent velocity but lower absolute volume.
RISING_STAR_RECENCY_MIN = 0.70     # >=70% of output is recent
RISING_STAR_MAX_PUBS = 20          # but modest total volume

# White-space / under-engaged flag: high influence yet low industry interaction.
# (Industry-payment signal, e.g. CMS Open Payments, plugs in here.)
WHITESPACE_SCORE_MIN_PERCENTILE = 0.70

# ---------------------------------------------------------------------------
# Ingestion politeness (NCBI asks for <=3 req/s without an API key)
# ---------------------------------------------------------------------------
NCBI_TOOL = "kol-influence-engine"
NCBI_EMAIL = "portfolio-demo@example.com"   # replace with your email for higher limits
NCBI_API_KEY = None                          # optional: raises rate limit to 10 req/s
REQUEST_PAUSE_SECONDS = 0.34
