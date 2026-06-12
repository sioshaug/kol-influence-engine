# 🧬 KOL Influence Mapping Engine

**Tiers and maps the scientific opinion-leader landscape for a therapeutic area from public data — and generates a per-expert engagement brief.**

A Medical Affairs decision-support tool, built as a portfolio demonstration. It replaces weeks of manual KOL list-building with a reproducible engine that ranks experts, flags rising stars and under-engaged "white-space" leaders, visualises the coauthorship network, and exports a CRM-ready tiered list. Worked example: **multiple myeloma**.

> **The decision it changes:** *who should Field Medical engage first, and with what scientific narrative.*

---

## Why this matters to Medical Affairs

Identifying and prioritising Key Opinion Leaders is core MSL and Medical Affairs work, but it is usually done manually, inconsistently, and without a defensible rationale. This engine makes the process **transparent, reproducible, and strategic**:

- **MSL** — a ranked list of who to engage in their territory, plus a talking-point brief per expert.
- **Medical Director** — national/global tiering with adjustable, defensible scoring logic (no black box).
- **Commercial / Launch lead** — alignment between medical KOL tiers and target accounts.

It also surfaces two strategic signals most manual approaches miss:

- ⭐ **Rising stars** — high recent output, modest total volume. Engaging early builds durable relationships ahead of competitors.
- 🎯 **White-space (under-engaged)** — high scientific influence but little industry interaction. A priority for new scientific relationship-building.

---

## What it does

| Capability | Detail |
| --- | --- |
| **Ingests public evidence** | PubMed/MEDLINE (NCBI E-utilities) + ClinicalTrials.gov API v2 |
| **Disambiguates authors** | Name normalisation + affiliation + coauthor-overlap matching; trial leaders matched back to authors |
| **Scores influence** | Transparent composite: publication volume, senior authorship, recent activity, trial leadership, citation proxy, network centrality — **weights adjustable live** |
| **Tiers & flags** | Tier 1 / 2 / 3 + Rising Star + White-space |
| **Maps the network** | Interactive coauthorship graph (centrality = strategic position) |
| **Briefs each expert** | Data-grounded scientific profile + 3 suggested scientific-exchange talking points |
| **Exports** | CRM-ready CSV of the tiered list |

---

## Quickstart

```bash
# 1. install
pip install -r requirements.txt

# 2a. run immediately on the bundled SAMPLE fixture (synthetic, fictional names)
python scripts/make_sample_fixture.py
streamlit run app.py

# 2b. OR build the LIVE multiple-myeloma cache from real data (needs internet, a few minutes)
python scripts/build_cache.py
streamlit run app.py
```

The app prefers the live cache (`data/cache/`) and falls back to the committed sample (`data/sample/`). A banner clearly marks when sample data is in use.

### Build a different therapeutic area

```bash
python scripts/build_cache.py --indication "Atopic Dermatitis" \
    --pubmed '"dermatitis, atopic"[MeSH Terms] OR "atopic dermatitis"[Title/Abstract]' \
    --condition "atopic dermatitis"
```

---

## Methodology & rigour

**Influence score.** Each component (publications, seniority, recency, trial leadership, citation proxy, network centrality) is converted to a **percentile rank within the field** — robust to the heavily skewed distributions typical of bibliometric data — then combined with the open weights in `config.py`. The sidebar lets you re-weight live and watch the tiers re-form, because *a Medical Director must be able to defend why someone is Tier 1.*

**Author disambiguation** is the hard problem here. The same person appears as `Rajkumar SV`, `S. Vincent Rajkumar`, `Rajkumar S`; different people share `Wang J`. The engine normalises each authorship to a `lastname + first-initial` key, then guards against false merges using affiliation tokens and coauthor overlap. ClinicalTrials.gov official names are normalised the same way so trial leadership is attributed to the right expert.

**Citation proxy.** The MVP uses senior-authorship as a transparent stand-in for citation impact. The roadmap wires in OpenAlex / Semantic Scholar for true citation and h-index signals.

**Validation.** Before trusting the output, hand-curate 15–20 known experts for your indication and confirm the engine tiers them correctly (precision/recall). See `docs/PORTFOLIO.md`.

**Limitations (stated honestly).** Initial-based disambiguation can still merge or split a minority of names; PubMed affiliation coverage is incomplete on older records; trial-leadership matching is conservative (only credited to people who also publish). None of these undermine the tiering at the field level, and each has a roadmap fix.

---

## Architecture

```
PubMed E-utilities ─┐
                    ├─► disambiguate ─► score & tier ─► network ─► briefs ─► cache ─► Streamlit app
ClinicalTrials.gov ─┘
```

```
kol_engine/
  ingest_pubmed.py          # esearch + efetch, author/affiliation/MeSH parsing
  ingest_clinicaltrials.py  # API v2, trial-leadership extraction
  disambiguate.py           # name resolution + per-expert aggregation
  network.py                # coauthorship graph + centrality
  scoring.py                # percentile composite, tiering, flags
  briefs.py                 # data-grounded engagement briefs (optional LLM path)
  pipeline.py               # orchestration + cache I/O
scripts/
  build_cache.py            # build the live data snapshot
  make_sample_fixture.py    # synthetic fixture so the app runs offline
app.py                      # Streamlit UI (Overview · List · Network · Brief)
```

**Stack:** Python · pandas · NetworkX · pyvis · Streamlit. Zero-infra (file-based cache). Deploys free on Streamlit Community Cloud.

---

## Deploy (free, shareable link)

1. Push this folder to a **public GitHub repo**.
2. (Recommended) build the live cache first — `python scripts/build_cache.py` — and commit `data/cache/` so the public demo is instant. *(Remove `data/cache/` from `.gitignore` if you want to commit it.)*
3. Go to **share.streamlit.io** → *New app* → pick the repo → main file `app.py` → **Deploy**.
4. You get a public URL like `https://your-app.streamlit.app` to put on LinkedIn and your CV.

See `docs/DEPLOY.md` for the step-by-step and `docs/PORTFOLIO.md` for LinkedIn copy, resume bullets, and interview talking points.

---

## Roadmap

Longitudinal rising-star trajectories · real citation/h-index via OpenAlex · CMS Open Payments white-space signal (replacing the trial proxy) · congress-abstract ingestion (ASH/ASCO) · multi-TA switching · LLM-enriched briefs · auto-generated MSL pre-call brief.

---

*Built as a Medical Affairs portfolio project. Uses only public data. Not for clinical or promotional use.*
