"""ClinicalTrials.gov ingestion via the public API v2 (JSON).

We care about *trial leadership* — overall officials / principal investigators
and the responsible-party PI — because leading a trial is one of the strongest
public signals of clinical influence in a therapeutic area.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import requests

import config

CT_API = "https://clinicaltrials.gov/api/v2/studies"


@dataclass
class TrialRole:
    name: str
    affiliation: str
    role: str          # e.g. "PRINCIPAL_INVESTIGATOR", "STUDY_CHAIR", "STUDY_DIRECTOR"


@dataclass
class Trial:
    nct_id: str
    title: str
    phase: str
    status: str
    start_year: int | None
    lead_sponsor: str
    sponsor_class: str  # INDUSTRY / NIH / OTHER ...
    leaders: list[TrialRole] = field(default_factory=list)


def _start_year(study: dict) -> int | None:
    sd = (study.get("protocolSection", {})
                .get("statusModule", {})
                .get("startDateStruct", {})
                .get("date"))
    if sd and len(sd) >= 4 and sd[:4].isdigit():
        return int(sd[:4])
    return None


def _parse_study(study: dict) -> Trial | None:
    ps = study.get("protocolSection", {})
    ident = ps.get("identificationModule", {})
    nct = ident.get("nctId")
    if not nct:
        return None
    design = ps.get("designModule", {})
    phases = design.get("phases", []) or []
    phase = ", ".join(p.replace("PHASE", "Phase ") for p in phases) or "N/A"

    status = ps.get("statusModule", {}).get("overallStatus", "")
    sponsor_mod = ps.get("sponsorCollaboratorsModule", {})
    lead = sponsor_mod.get("leadSponsor", {})
    lead_sponsor = lead.get("name", "")
    sponsor_class = lead.get("class", "")

    leaders: list[TrialRole] = []
    contacts = ps.get("contactsLocationsModule", {})
    for off in contacts.get("overallOfficials", []) or []:
        name = (off.get("name") or "").strip()
        if not name:
            continue
        leaders.append(TrialRole(
            name=name,
            affiliation=(off.get("affiliation") or "").strip(),
            role=off.get("role", "OFFICIAL"),
        ))
    # Responsible-party investigator (often the academic PI).
    rp = sponsor_mod.get("responsibleParty", {})
    if rp.get("type") in {"PRINCIPAL_INVESTIGATOR", "SPONSOR_INVESTIGATOR"} and rp.get("investigatorFullName"):
        leaders.append(TrialRole(
            name=rp["investigatorFullName"].strip(),
            affiliation=(rp.get("investigatorAffiliation") or "").strip(),
            role="RESPONSIBLE_PARTY_PI",
        ))

    return Trial(
        nct_id=nct,
        title=ident.get("briefTitle", ""),
        phase=phase,
        status=status,
        start_year=_start_year(study),
        lead_sponsor=lead_sponsor,
        sponsor_class=sponsor_class,
        leaders=leaders,
    )


def ingest(condition: str | None = None, max_results: int = 1500) -> list[Trial]:
    condition = condition or config.DEFAULT_CT_CONDITION
    trials: list[Trial] = []
    page_token = None
    while len(trials) < max_results:
        params = {"query.cond": condition, "pageSize": 100}
        if page_token:
            params["pageToken"] = page_token
        resp = requests.get(CT_API, params=params, timeout=45)
        resp.raise_for_status()
        data = resp.json()
        for study in data.get("studies", []):
            try:
                t = _parse_study(study)
            except Exception:
                continue  # skip a malformed record rather than fail the whole build
            if t is not None:
                trials.append(t)
        page_token = data.get("nextPageToken")
        time.sleep(config.REQUEST_PAUSE_SECONDS)
        if not page_token:
            break
    return trials[:max_results]
