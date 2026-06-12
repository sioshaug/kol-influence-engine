"""Build the live data cache for the showcase indication.

Run this ONCE on a machine with internet access (your laptop, or it runs
automatically the first time the app is deployed). It pulls live PubMed +
ClinicalTrials.gov data, runs the full pipeline, and writes the snapshot to
``data/cache/`` which the app then serves instantly.

    python scripts/build_cache.py
    python scripts/build_cache.py --max 800      # smaller / faster build
    python scripts/build_cache.py --indication "Atopic Dermatitis" \
        --pubmed '"dermatitis, atopic"[MeSH Terms]' --condition "atopic dermatitis"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from kol_engine import pipeline


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--indication", default=config.DEFAULT_INDICATION)
    ap.add_argument("--pubmed", default=config.DEFAULT_PUBMED_QUERY)
    ap.add_argument("--condition", default=config.DEFAULT_CT_CONDITION)
    ap.add_argument("--max", type=int, default=1500, help="max records per source")
    args = ap.parse_args()

    print(f"Building cache for: {args.indication}")
    # Clean any previous snapshot so files can never be mixed across runs.
    if config.CACHE_DIR.exists():
        for f in config.CACHE_DIR.glob("*"):
            try:
                f.unlink()
            except OSError:
                pass
    print("  -> querying PubMed + ClinicalTrials.gov (this can take a few minutes)…")
    result = pipeline.run_live(
        pubmed_query=args.pubmed,
        ct_condition=args.condition,
        indication=args.indication,
        max_results=args.max,
    )
    pipeline.save_cache(result, config.CACHE_DIR)
    s = result["meta"]["summary"]
    print(f"  -> {result['meta']['n_publications']} publications, "
          f"{result['meta']['n_trials']} trials ingested")
    print(f"  -> {s.get('experts', 0)} experts scored "
          f"(Tier 1: {s.get('tier1', 0)}, Tier 2: {s.get('tier2', 0)})")
    print(f"  -> cache written to {config.CACHE_DIR}")


if __name__ == "__main__":
    main()
