# Portfolio pack — KOL Influence Mapping Engine

Everything you need to present this project to recruiters and Medical Affairs hiring managers.

---

## One-line value statement

> Tiers and maps the scientific opinion-leader landscape for a therapeutic area from public data, and generates a per-expert engagement brief — turning weeks of manual KOL list-building into a reproducible, defensible decision.

## The 30-second pitch

"KOL identification is core MSL work, but it's usually manual and hard to defend. I built an engine that ingests PubMed and ClinicalTrials.gov, disambiguates authors, and scores every expert on a transparent, adjustable composite — then tiers them and flags two things teams usually miss: rising stars and high-influence experts with no industry engagement. It's a live web app; a Medical Director can re-weight the model and watch the tiers re-form. I validated it against known myeloma KOLs before trusting it."

---

## Resume bullets (lift directly)

- Built a **KOL influence-mapping web app** that ingests PubMed and ClinicalTrials.gov, disambiguates authors, and tiers experts on a transparent, re-weightable composite score — replacing manual KOL list-building with a reproducible, auditable workflow.
- Engineered an **author-disambiguation pipeline** (name normalisation + affiliation + coauthor-overlap) and a coauthorship-network centrality model to identify strategically-positioned and **under-engaged ("white-space") opinion leaders**.
- Surfaced **rising-star KOLs** (high recent output, low total volume) to enable earlier scientific engagement than competitors, and shipped a **CRM-ready export** for Field Medical.
- Deployed a public Streamlit app (multiple myeloma) with per-expert, **evidence-grounded engagement briefs** — demonstrating Medical Affairs strategy plus practical AI/data engineering.

## Interview talking points

- **"I rebuilt the KOL-mapping workflow that agencies charge six figures for, on public data."**
- **The hard problem was author disambiguation** — name collisions (`Wang J`) and affiliation drift. I normalise to a lastname+initial key, then guard merges with affiliation tokens and coauthor overlap. *(senior signal)*
- **Scoring is transparent and adjustable** — a Medical Director must defend why someone is Tier 1, not point at a black box. The sidebar re-weights the model live. *(MA judgment)*
- **I added a white-space flag** — high influence, low industry engagement — where Medical and Commercial both find value. *(cross-functional)*
- **I validated against a known-KOL set before trusting the output.** *(scientific rigour)*
- **I stated the limitations honestly** — initial-based disambiguation, PubMed affiliation gaps — each with a roadmap fix. *(maturity)*

---

## LinkedIn post (draft)

> **Who should a Medical Science Liaison engage first — and why?**
>
> KOL identification is core Medical Affairs work, but it's often manual, inconsistent, and hard to justify. So I built a **KOL Influence Mapping Engine**.
>
> It ingests public data (PubMed + ClinicalTrials.gov), disambiguates authors, and scores every expert in a therapeutic area on a **transparent, adjustable** composite — publication volume, senior authorship, recent activity, trial leadership, and coauthorship-network centrality.
>
> Then it does the part teams usually miss:
> ⭐ flags **rising stars** — high recent output, modest total volume — so you engage before competitors do
> 🎯 flags **white-space leaders** — high influence, low industry engagement — a priority for new scientific relationships
>
> A Medical Director can re-weight the model and watch the tiers re-form live. It exports a CRM-ready list and writes an evidence-grounded engagement brief for each expert.
>
> Worked example: multiple myeloma. Built with Python, NetworkX, and Streamlit. Live demo + code below.
>
> #MedicalAffairs #MSL #KOL #Pharma #HealthcareAnalytics #AI

*(Replace links, add 2–3 screenshots: the tiered list, the network map, an expert brief.)*

---

## Validation guide (do this before sharing live data)

**Automated:** after building the live cache, run:
```
python scripts/validate.py
```
It checks a starter list of widely-recognised myeloma investigators against your
data and prints a **top-tier recall** figure plus a slide-ready sentence. Edit the
`KNOWN_KOLS` list in that file to reflect your own judgement.

**What to check / report:**
1. How many known names were **found** in the dataset (coverage).
2. How many landed in **Tier 1 / Tier 2** (top-tier recall) — the headline number.
3. For any misses, check whether it's a true gap or a disambiguation artefact
   (e.g., a name split across initials). Note that very common surnames may match
   the highest-scoring person of that name, so eyeball the "matched in data" column.
4. Put it on a slide: *"Validated against N known KOLs; X% surfaced in the top two
   tiers."* This single line answers "how do you know it works?"

---

## Screenshots to capture (for README + LinkedIn + portfolio site)

1. **Overview tab** — metrics row + tier distribution (the "it works" hero shot).
2. **Tiered list** — with the influence progress bars and ⭐/🎯 flags visible.
3. **Network map** — an expert's coauthorship ego-network.
4. **KOL brief** — profile + talking points + score breakdown.

Save them to `docs/img/` and embed in `README.md`.
