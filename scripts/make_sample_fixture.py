"""Generate a realistic but SYNTHETIC sample fixture for multiple myeloma.

Purpose: let the app run end-to-end out of the box (for screenshots, local dev,
and CI) WITHOUT hitting the network. All names here are fictional and must not be
read as real people. Replace with real data by running scripts/build_cache.py.

    python scripts/make_sample_fixture.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from kol_engine import pipeline
from kol_engine.ingest_pubmed import Author, Publication
from kol_engine.ingest_clinicaltrials import Trial, TrialRole

RNG = random.Random(42)
CUR = config.CURRENT_YEAR

FIRST = ["Helena", "Marcus", "Priya", "Daniel", "Sofia", "Liam", "Yuki", "Omar",
         "Clara", "Tomas", "Aisha", "Niels", "Rosa", "Viktor", "Mei", "Andre",
         "Lena", "Carlos", "Ingrid", "Samir", "Nadia", "Paul", "Elif", "Jonas"]
LAST = ["Vantfield", "Okonkwo", "Saarinen", "Delacroix", "Romano", "Bjork",
        "Nakamura", "Haddad", "Esposito", "Lindqvist", "Moreau", "Petrov",
        "Sorensen", "Kapoor", "Navarro", "Holmberg", "Dubois", "Costa",
        "Vermeer", "Ferreira", "Alvarez", "Brandt", "Yilmaz", "Larsen"]

INSTITUTIONS = [
    ("Northgate Cancer Institute, Boston, MA, USA", "USA"),
    ("Université Lyon Hématologie, Lyon, France", "France"),
    ("Heidelberg Myeloma Center, Heidelberg, Germany", "Germany"),
    ("Karolinska Hematology Unit, Stockholm, Sweden", "Sweden"),
    ("St. Aldwyn Hospital, London, UK", "UK"),
    ("Verona Translational Oncology, Verona, Italy", "Italy"),
    ("Kyoto Hematologic Malignancy Center, Kyoto, Japan", "Japan"),
    ("Toronto Plasma Cell Program, Toronto, Canada", "Canada"),
    ("Barcelona Myeloma Group, Barcelona, Spain", "Spain"),
    ("Rotterdam Cancer Centre, Rotterdam, Netherlands", "Netherlands"),
]
JOURNALS = ["Blood", "Journal of Clinical Oncology", "The Lancet Oncology",
            "Leukemia", "Blood Cancer Journal", "Haematologica",
            "New England Journal of Medicine", "Clinical Cancer Research"]
MESH = ["Bortezomib", "Lenalidomide", "Daratumumab", "Immunotherapy",
        "Antibodies, Monoclonal", "Stem Cell Transplantation",
        "Receptors, Chimeric Antigen", "Carfilzomib", "Drug Resistance, Neoplasm",
        "Minimal Residual Disease", "Bispecific Antibodies", "Pomalidomide"]


def _unique_names(n):
    combos = [(f, l) for f in FIRST for l in LAST]
    RNG.shuffle(combos)
    return [f"{f} {l}" for f, l in combos[:n]]


def make_experts(n=46):
    names = _unique_names(n)
    experts = []
    for i in range(n):
        inst, country = RNG.choice(INSTITUTIONS)
        # archetypes drive realistic distributions
        r = RNG.random()
        if r < 0.13:                      # established heavy hitter
            arche, prod, recency, trials, industry = "heavy", RNG.randint(45, 80), 0.45, RNG.randint(6, 14), 0.6
        elif r < 0.30:                    # rising star: lower volume, very recent
            arche, prod, recency, trials, industry = "rising", RNG.randint(6, 11), 0.92, RNG.randint(0, 2), 0.1
        elif r < 0.45:                    # academic white-space: strong, low industry
            arche, prod, recency, trials, industry = "whitespace", RNG.randint(25, 45), 0.5, RNG.randint(2, 6), 0.0
        else:                             # mid / general
            arche, prod, recency, trials, industry = "mid", RNG.randint(3, 25), 0.5, RNG.randint(0, 3), 0.3
        experts.append({
            "name": names[i], "arche": arche,
            "aff": inst, "country": country, "prod": prod,
            "recency": recency, "trials": trials, "industry": industry,
            "focus": RNG.sample(MESH, k=RNG.randint(2, 4)),
        })
    return experts


def year_for(recency_bias):
    # higher recency_bias -> more weight on the last 3 years
    if RNG.random() < recency_bias:
        return RNG.randint(CUR - 2, CUR)
    return RNG.randint(CUR - config.LOOKBACK_YEARS + 1, CUR - 3)


def build():
    experts = make_experts()
    pubs: list[Publication] = []
    pmid = 40000000

    for e in experts:
        for _ in range(e["prod"]):
            pmid += 1
            senior = RNG.random() < 0.55       # this expert is senior on this paper
            n_co = RNG.randint(2, 7)
            # Rising stars keep a small footprint: they aren't pulled onto others' papers.
            pool = [x for x in experts if x is not e and x["arche"] != "rising"]
            others = RNG.sample(pool, k=min(n_co, len(pool)))
            authors = []
            lead = e if senior else RNG.choice(others)
            members = [lead] + [x for x in ([e] + others) if x is not lead]
            members = members[:RNG.randint(3, 8)]
            m = len(members)
            for idx, person in enumerate(members):
                fn = person["name"].split()[0]
                ln = person["name"].split()[1]
                pos = "first" if idx == 0 else ("last" if idx == m - 1 else "middle")
                authors.append(Author(last=ln, fore=fn, initials=fn[0],
                                       affiliation=person["aff"], position=pos))
            pubs.append(Publication(
                pmid=str(pmid), year=year_for(e["recency"]),
                journal=RNG.choice(JOURNALS),
                title="Synthetic record for multiple myeloma demo fixture",
                authors=authors,
                mesh=["Multiple Myeloma", "Humans"] + RNG.sample(e["focus"], k=min(2, len(e["focus"]))),
            ))

    trials: list[Trial] = []
    nct = 5000000
    for e in experts:
        for _ in range(e["trials"]):
            nct += 1
            cls = "INDUSTRY" if RNG.random() < e["industry"] else RNG.choice(["NIH", "OTHER"])
            ln = e["name"].split()[1]
            fn = e["name"].split()[0]
            trials.append(Trial(
                nct_id=f"NCT{nct:08d}",
                title="Synthetic myeloma trial (demo fixture)",
                phase=RNG.choice(["Phase 1", "Phase 1, Phase 2", "Phase 2", "Phase 3"]),
                status=RNG.choice(["RECRUITING", "ACTIVE_NOT_RECRUITING", "COMPLETED"]),
                start_year=RNG.randint(CUR - 4, CUR),
                lead_sponsor="Synthetic Sponsor" if cls == "INDUSTRY" else e["aff"],
                sponsor_class=cls,
                leaders=[TrialRole(name=f"{fn} {ln}, MD", affiliation=e["aff"],
                                   role=RNG.choice(["PRINCIPAL_INVESTIGATOR", "STUDY_CHAIR",
                                                    "STUDY_DIRECTOR"]))],
            ))

    result = pipeline.process(pubs, trials, indication=config.DEFAULT_INDICATION,
                              source_label="sample")
    result["meta"]["note"] = "SYNTHETIC sample fixture — fictional names. Run build_cache.py for live data."
    pipeline.save_cache(result, config.SAMPLE_DIR)
    s = result["meta"]["summary"]
    print(f"Sample fixture built: {len(pubs)} pubs, {len(trials)} trials, "
          f"{s['experts']} experts (T1 {s['tier1']}, T2 {s['tier2']}, "
          f"rising {s['rising_stars']}, whitespace {s['whitespace']}).")


if __name__ == "__main__":
    build()
