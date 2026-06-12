"""PubMed ingestion via NCBI E-utilities.

Two steps:
  1. esearch  -> list of PMIDs for the indication + date window
  2. efetch   -> full records (authors, affiliations, MeSH, year, journal)

No API key required, but supplying ``config.NCBI_API_KEY`` raises the rate
limit from 3 to 10 requests/second. All network access is isolated here so the
rest of the engine is pure data transformation and unit-testable offline.
"""
from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Iterable

import requests

import config

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@dataclass
class Author:
    last: str
    fore: str
    initials: str
    affiliation: str
    position: str  # "first" | "last" | "middle"

    @property
    def full_name(self) -> str:
        name = f"{self.fore} {self.last}".strip()
        return name or self.last or self.initials


@dataclass
class Publication:
    pmid: str
    year: int | None
    journal: str
    title: str
    authors: list[Author] = field(default_factory=list)
    mesh: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def _params(extra: dict) -> dict:
    p = {"tool": config.NCBI_TOOL, "email": config.NCBI_EMAIL}
    if config.NCBI_API_KEY:
        p["api_key"] = config.NCBI_API_KEY
    p.update(extra)
    return p


def _get(path: str, params: dict, timeout: int = 30) -> requests.Response:
    resp = requests.get(f"{EUTILS}/{path}", params=_params(params), timeout=timeout)
    resp.raise_for_status()
    time.sleep(config.REQUEST_PAUSE_SECONDS)  # be polite to NCBI
    return resp


# ---------------------------------------------------------------------------
# esearch
# ---------------------------------------------------------------------------
def search_pmids(query: str, max_results: int = 1500,
                 lookback_years: int | None = None) -> list[str]:
    """Return PMIDs for *query*, sampled EVENLY across each year in the window.

    Fetching simply the "most recent N" in a high-volume field (e.g. myeloma)
    returns almost only the current year, which collapses every author's date
    range and distorts the recency signal. Querying year-by-year guarantees
    multi-year coverage so 'active years' and recency are meaningful.
    """
    lookback_years = lookback_years or config.LOOKBACK_YEARS
    years = list(range(config.CURRENT_YEAR - lookback_years + 1, config.CURRENT_YEAR + 1))
    per_year = max(80, max_results // len(years))
    pmids: list[str] = []
    seen: set[str] = set()
    for yr in years:
        term = f"({query}) AND {yr}[pdat]"
        got, retstart = 0, 0
        while got < per_year:
            data = _get("esearch.fcgi", {
                "db": "pubmed", "term": term, "retmode": "json",
                "retstart": retstart, "retmax": min(500, per_year - got),
            }).json()
            res = data.get("esearchresult", {})
            batch = res.get("idlist", [])
            if not batch:
                break
            for p in batch:
                if p not in seen:
                    seen.add(p)
                    pmids.append(p)
            got += len(batch)
            retstart += len(batch)
            if retstart >= int(res.get("count", 0)):
                break
    return pmids[:max_results]


# ---------------------------------------------------------------------------
# efetch + parsing
# ---------------------------------------------------------------------------
def _text(node, path: str, default: str = "") -> str:
    el = node.find(path)
    return (el.text or default).strip() if el is not None and el.text else default


def _parse_article(art: ET.Element) -> Publication | None:
    medline = art.find("MedlineCitation")
    if medline is None:
        return None
    pmid = _text(medline, "PMID")
    article = medline.find("Article")
    if article is None:
        return None
    title = _text(article, "ArticleTitle")
    journal = _text(article, "Journal/Title") or _text(article, "Journal/ISOAbbreviation")

    # Year: prefer the article's publication year, fall back to MedlineDate.
    year = None
    y = article.find("Journal/JournalIssue/PubDate/Year")
    if y is not None and y.text and y.text.isdigit():
        year = int(y.text)
    else:
        md = article.find("Journal/JournalIssue/PubDate/MedlineDate")
        if md is not None and md.text:
            digits = "".join(c for c in md.text[:4] if c.isdigit())
            year = int(digits) if len(digits) == 4 else None

    # Authors with position (first / last / middle).
    authors: list[Author] = []
    alist = article.find("AuthorList")
    raw = alist.findall("Author") if alist is not None else []
    n = len(raw)
    for i, a in enumerate(raw):
        last = _text(a, "LastName")
        fore = _text(a, "ForeName")
        initials = _text(a, "Initials")
        if not (last or initials):
            continue  # skip collective/consortium authors
        aff = ""
        aff_el = a.find("AffiliationInfo/Affiliation")
        if aff_el is not None and aff_el.text:
            aff = aff_el.text.strip()
        position = "first" if i == 0 else ("last" if i == n - 1 and n > 1 else "middle")
        authors.append(Author(last=last, fore=fore, initials=initials,
                              affiliation=aff, position=position))

    mesh = [d.text.strip() for d in medline.findall("MeshHeadingList/MeshHeading/DescriptorName")
            if d.text]

    return Publication(pmid=pmid, year=year, journal=journal, title=title,
                       authors=authors, mesh=mesh)


def fetch_publications(pmids: Iterable[str], batch_size: int = 200) -> list[Publication]:
    pmids = list(pmids)
    pubs: list[Publication] = []
    for start in range(0, len(pmids), batch_size):
        chunk = pmids[start:start + batch_size]
        try:
            xml = _get("efetch.fcgi", {
                "db": "pubmed", "id": ",".join(chunk), "retmode": "xml",
            }).text
            root = ET.fromstring(xml)
        except (ET.ParseError, requests.RequestException):
            continue  # skip a flaky batch rather than fail the whole build
        for art in root.findall("PubmedArticle"):
            pub = _parse_article(art)
            if pub is not None:
                pubs.append(pub)
    return pubs


def ingest(query: str | None = None, max_results: int = 1500) -> list[Publication]:
    """Convenience: search + fetch in one call."""
    query = query or config.DEFAULT_PUBMED_QUERY
    pmids = search_pmids(query, max_results=max_results)
    return fetch_publications(pmids)
