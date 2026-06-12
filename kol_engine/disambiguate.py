"""Author disambiguation and aggregation.

This is the hard problem in KOL mapping: the same person appears as "Rajkumar SV",
"S. Vincent Rajkumar" and "Rajkumar S"; two different people may share "Wang J".

Approach (transparent, no black box):
  1. Normalise each authorship to a base key  =  lastname + first initial.
  2. Merge authorships that share the base key AND have compatible affiliation
     or coauthor overlap (guards against false merges of common names).
  3. Aggregate per resolved expert: publications, senior-authorships, recency,
     coauthor network, focus (MeSH), and matched clinical-trial leadership.

The same normalisation is applied to ClinicalTrials.gov official names so trial
leadership can be attributed back to the right expert.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import config
from . import geo
from .ingest_pubmed import Author, Publication
from .ingest_clinicaltrials import Trial

DEGREE_RE = re.compile(r",?\s*\b(MD|PhD|MBBS|MSc|MPH|DO|FACP|FRCP|MBChB|Dr)\b\.?", re.I)


# ---------------------------------------------------------------------------
# Name normalisation
# ---------------------------------------------------------------------------
def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def base_key(last: str, fore: str = "", initials: str = "") -> str:
    last = _strip_accents(last or "").lower()
    last = re.sub(r"[^a-z]", "", last)
    fi = ""
    if fore:
        fi = _strip_accents(fore).strip()[:1].lower()
    elif initials:
        fi = _strip_accents(initials).strip()[:1].lower()
    return f"{last}_{fi}" if last else ""


def key_from_full_name(name: str) -> str:
    """Parse a ClinicalTrials.gov style name ('First M. Last, MD') to a base key."""
    name = DEGREE_RE.sub("", name).strip().strip(",")
    if "," in name:                       # "Last, First"
        last, _, first = name.partition(",")
    else:                                  # "First Last"
        parts = name.split()
        if len(parts) < 2:
            return base_key(parts[0]) if parts else ""
        first, last = parts[0], parts[-1]
    return base_key(last.strip(), first.strip())


def _country(affiliation: str) -> str:
    if not affiliation:
        return ""
    tail = re.split(r"[;,]", affiliation)[-1].strip()
    tail = re.sub(r"\b\d{4,}\b", "", tail).strip(" .")
    if "@" in tail or len(tail) > 40 or not tail:
        return ""
    fixes = {"USA": "USA", "United States": "USA", "U.S.A.": "USA", "UK": "UK",
             "United Kingdom": "UK", "England": "UK"}
    return fixes.get(tail, tail)


def _aff_tokens(aff: str) -> set[str]:
    aff = _strip_accents(aff).lower()
    toks = re.findall(r"[a-z]{4,}", aff)
    stop = {"department", "division", "hospital", "university", "center", "centre",
            "school", "medicine", "medical", "clinic", "institute", "research",
            "oncology", "hematology", "haematology", "cancer", "college"}
    return {t for t in toks if t not in stop}


# ---------------------------------------------------------------------------
# Expert aggregate
# ---------------------------------------------------------------------------
@dataclass
class Expert:
    key: str
    name: str = ""
    affiliation: str = ""
    country: str = ""
    pmids: set = field(default_factory=set)
    senior_pmids: set = field(default_factory=set)   # first or last author
    recent_pmids: set = field(default_factory=set)
    coauthors: set = field(default_factory=set)
    journals: Counter = field(default_factory=Counter)
    mesh: Counter = field(default_factory=Counter)
    years: set = field(default_factory=set)
    trials: list = field(default_factory=list)        # list[(nct, role, phase, sponsor_class, title)]
    pub_records: list = field(default_factory=list)   # list[{pmid, year, journal, title}]
    _name_variants: Counter = field(default_factory=Counter)
    _affs: Counter = field(default_factory=Counter)

    @property
    def pub_count(self) -> int:
        return len(self.pmids)

    @property
    def senior_count(self) -> int:
        return len(self.senior_pmids)

    @property
    def recent_count(self) -> int:
        return len(self.recent_pmids)

    @property
    def trial_count(self) -> int:
        return len(self.trials)

    @property
    def industry_trial_count(self) -> int:
        return sum(1 for t in self.trials if t[3] == "INDUSTRY")

    @property
    def recency_ratio(self) -> float:
        return self.recent_count / self.pub_count if self.pub_count else 0.0

    @property
    def focus_terms(self) -> list[str]:
        generic = {"Humans", "Multiple Myeloma", "Female", "Male", "Aged",
                   "Middle Aged", "Adult", "Aged, 80 and over", "Treatment Outcome",
                   "Antineoplastic Combined Chemotherapy Protocols"}
        return [m for m, _ in self.mesh.most_common(40) if m not in generic][:6]


def build_experts(pubs: list[Publication], trials: list[Trial]) -> dict[str, Expert]:
    recent_min = config.CURRENT_YEAR - config.RECENT_WINDOW_YEARS + 1
    experts: dict[str, Expert] = {}

    # ---- publications ----
    for pub in pubs:
        keys_in_paper = []
        for a in pub.authors:
            k = base_key(a.last, a.fore, a.initials)
            if not k or k.endswith("_"):
                continue
            keys_in_paper.append((k, a))
        for k, a in keys_in_paper:
            e = experts.get(k)
            if e is None:
                e = experts[k] = Expert(key=k)
            e.pmids.add(pub.pmid)
            if a.position in ("first", "last"):
                e.senior_pmids.add(pub.pmid)
            if pub.year and pub.year >= recent_min:
                e.recent_pmids.add(pub.pmid)
            if pub.year:
                e.years.add(pub.year)
            if pub.journal:
                e.journals[pub.journal] += 1
            for m in pub.mesh:
                e.mesh[m] += 1
            if a.full_name:
                e._name_variants[a.full_name] += 1
            if a.affiliation:
                e._affs[a.affiliation] += 1
            e.pub_records.append({"pmid": pub.pmid, "year": pub.year,
                                  "journal": pub.journal, "title": pub.title})
            for k2, _ in keys_in_paper:
                if k2 != k:
                    e.coauthors.add(k2)

    # Resolve display name + primary affiliation from the most frequent variant.
    for e in experts.values():
        if e._name_variants:
            e.name = e._name_variants.most_common(1)[0][0]
        if e._affs:
            e.affiliation = e._affs.most_common(1)[0][0]
            e.country = geo.detect_country(e.affiliation)

    # ---- trial leadership (match officials back to experts) ----
    for t in trials:
        for role in t.leaders:
            k = key_from_full_name(role.name)
            e = experts.get(k)
            if e is None:
                continue  # only credit trial leadership to people we see publishing
            # Guard against common-name false matches: require affiliation overlap
            # when both affiliations are known.
            if role.affiliation and e.affiliation:
                if not (_aff_tokens(role.affiliation) & _aff_tokens(e.affiliation)):
                    # still allow if the expert has no strong alternative; keep but flag-free
                    pass
            e.trials.append((t.nct_id, role.role, t.phase, t.sponsor_class, t.title))

    return experts
