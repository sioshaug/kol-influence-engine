"""Smoke + logic tests. Run: python -m pytest -q  (or python tests/test_scoring.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kol_engine.disambiguate import base_key, key_from_full_name, build_experts
from kol_engine.ingest_pubmed import Author, Publication
from kol_engine.ingest_clinicaltrials import Trial, TrialRole
from kol_engine import network, scoring


def test_base_key_normalises_variants():
    assert base_key("Rajkumar", "S. Vincent") == base_key("Rajkumar", "Shaji") == "rajkumar_s"
    assert base_key("O'Brien", "Mary") == "obrien_m"
    assert key_from_full_name("Shaji Kumar, MD") == "kumar_s"
    assert key_from_full_name("Kumar, Shaji") == "kumar_s"


def _toy():
    a = Author("Smith", "Alice", "A", "Northgate Cancer Institute, Boston", "first")
    b = Author("Jones", "Bob", "B", "Northgate Cancer Institute, Boston", "last")
    pubs = [Publication(str(i), 2024, "Blood", "t", [a, b], ["Multiple Myeloma"]) for i in range(5)]
    trials = [Trial("NCT1", "t", "Phase 2", "RECRUITING", 2024, "Sponsor", "INDUSTRY",
                    [TrialRole("Alice Smith, MD", "Northgate Cancer Institute", "PRINCIPAL_INVESTIGATOR")])]
    return pubs, trials


def test_pipeline_scores_and_tiers():
    pubs, trials = _toy()
    experts = build_experts(pubs, trials)
    assert "smith_a" in experts and "jones_b" in experts
    assert experts["smith_a"].trial_count == 1          # trial attributed via name match
    g = network.build_graph(experts)
    cent = network.centrality_scores(g)
    df = scoring.score_experts(experts, cent, min_pubs=1)
    assert not df.empty
    assert {"influence_score", "tier", "rising_star", "whitespace"} <= set(df.columns)
    assert df["influence_score"].between(0, 100).all()


if __name__ == "__main__":
    test_base_key_normalises_variants()
    test_pipeline_scores_and_tiers()
    print("All tests passed.")
