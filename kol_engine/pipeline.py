"""Orchestration + cache I/O.

``process`` turns raw publications + trials into the full scored artefact set.
``run_live`` wires in the network ingestion. ``save_cache`` / ``load_cache``
persist a snapshot so the deployed app is instant and never rate-limited.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pandas as pd

import config
from . import briefs as briefs_mod
from . import network as network_mod
from . import scoring as scoring_mod
from .disambiguate import build_experts


def process(pubs, trials, indication: str, source_label: str = "live") -> dict:
    experts = build_experts(pubs, trials)
    graph = network_mod.build_graph(experts)
    centrality = network_mod.centrality_scores(graph)
    df = scoring_mod.score_experts(experts, centrality)
    briefs = briefs_mod.generate_all(df) if not df.empty else {}

    # Adjacency limited to scored experts, for a clean visualisation.
    scored_keys = set(df["key"]) if not df.empty else set()
    names = {k: (experts[k].name or k) for k in scored_keys}
    adjacency = {
        k: sorted(experts[k].coauthors & scored_keys)
        for k in scored_keys
    }

    # Per-expert evidence: their actual publications and trials (most recent first).
    details: dict = {}
    for k in scored_keys:
        e = experts[k]
        seen_pmids: set = set()
        pubs = []
        for r in sorted(e.pub_records, key=lambda r: (r.get("year") or 0), reverse=True):
            if r["pmid"] in seen_pmids:
                continue
            seen_pmids.add(r["pmid"])
            pubs.append(r)
            if len(pubs) >= 15:
                break
        trials = [{"nct": t[0], "role": t[1], "phase": t[2],
                   "sponsor_class": t[3], "title": t[4] if len(t) > 4 else ""}
                  for t in e.trials][:15]
        details[k] = {"publications": pubs, "trials": trials}

    meta = {
        "indication": indication,
        "built": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": source_label,
        "n_publications": len(pubs),
        "n_trials": len(trials),
        "weights": config.SCORE_WEIGHTS,
        "summary": scoring_mod.tier_summary(df),
        "sources": [
            "PubMed / MEDLINE (NCBI E-utilities)",
            "ClinicalTrials.gov API v2",
        ],
    }
    return {"experts": df, "adjacency": adjacency, "names": names,
            "briefs": briefs, "details": details, "meta": meta}


def run_live(pubmed_query: str | None = None, ct_condition: str | None = None,
             indication: str | None = None, max_results: int = 1500) -> dict:
    from . import ingest_pubmed, ingest_clinicaltrials  # imported here to keep core offline
    indication = indication or config.DEFAULT_INDICATION
    pubs = ingest_pubmed.ingest(pubmed_query, max_results=max_results)
    trials = ingest_clinicaltrials.ingest(ct_condition, max_results=max_results)
    return process(pubs, trials, indication=indication, source_label="live")


# ---------------------------------------------------------------------------
# Cache persistence
# ---------------------------------------------------------------------------
def save_cache(result: dict, out_dir: Path) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result["experts"].to_csv(out_dir / "experts.csv", index=False)
    (out_dir / "network.json").write_text(json.dumps(
        {"adjacency": result["adjacency"], "names": result["names"]}))
    (out_dir / "briefs.json").write_text(json.dumps(result["briefs"]))
    (out_dir / "details.json").write_text(json.dumps(result.get("details", {})))
    (out_dir / "meta.json").write_text(json.dumps(result["meta"], indent=2))


def load_cache(in_dir: Path) -> dict | None:
    in_dir = Path(in_dir)
    if not (in_dir / "experts.csv").exists():
        return None
    df = pd.read_csv(in_dir / "experts.csv")
    for col in ("rising_star", "whitespace"):
        if col in df.columns:
            df[col] = df[col].astype(bool)
    net = json.loads((in_dir / "network.json").read_text())
    briefs = json.loads((in_dir / "briefs.json").read_text())
    details_path = in_dir / "details.json"
    details = json.loads(details_path.read_text()) if details_path.exists() else {}
    meta = json.loads((in_dir / "meta.json").read_text())
    return {"experts": df, "adjacency": net["adjacency"], "names": net["names"],
            "briefs": briefs, "details": details, "meta": meta}


def load_best_available() -> tuple[dict | None, str]:
    """Prefer the live-built cache; fall back to the committed sample fixture."""
    live = load_cache(config.CACHE_DIR)
    if live is not None:
        return live, "live"
    sample = load_cache(config.SAMPLE_DIR)
    if sample is not None:
        return sample, "sample"
    return None, "none"
