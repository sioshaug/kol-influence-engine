"""KOL Influence Mapping Engine — Streamlit app.

Tiers and maps the scientific opinion-leader landscape for a therapeutic area
from public data (PubMed + ClinicalTrials.gov), and generates a per-expert
engagement brief. Built as a Medical Affairs portfolio demonstration.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

import config
from kol_engine import geo, pipeline

st.set_page_config(page_title="KOL Influence Mapping Engine",
                   page_icon="🧬", layout="wide")

COMPONENTS = ["publications", "seniority", "recency", "trials", "citations", "centrality"]
COMPONENT_LABEL = {
    "publications": "Publication volume", "seniority": "Senior authorship",
    "recency": "Recent activity", "trials": "Trial leadership",
    "citations": "Citation impact (proxy)", "centrality": "Network centrality",
}


# ---------------------------------------------------------------------------
# Data loading + interactive re-scoring
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_data():
    data, source = pipeline.load_best_available()
    return data, source


def rescore(df: pd.DataFrame, weights: dict) -> pd.DataFrame:
    """Recompute the composite from stored component percentiles + live weights."""
    df = df.copy()
    total = sum(weights.values()) or 1.0
    df["influence_score"] = sum(
        df[f"c_{c}"] / 100 * (weights[c] / total) for c in COMPONENTS
    ) * 100
    df["influence_score"] = df["influence_score"].round(1)
    df = df.sort_values("influence_score", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1
    s = df["influence_score"]
    t1, t2 = s.quantile(config.TIER_PERCENTILES["Tier 1"]), s.quantile(config.TIER_PERCENTILES["Tier 2"])
    df["tier"] = np.where(s >= t1, "Tier 1", np.where(s >= t2, "Tier 2", "Tier 3"))
    ws = s.quantile(config.WHITESPACE_SCORE_MIN_PERCENTILE)
    df["whitespace"] = (s >= ws) & (df["industry_trials"] == 0)
    return df


TIER_COLORS = {"Tier 1": "#1F3864", "Tier 2": "#2E75B6", "Tier 3": "#9DC3E6"}


def tier_badge(tier: str) -> str:
    return f"<span style='background:{TIER_COLORS[tier]};color:#fff;padding:2px 10px;border-radius:12px;font-size:0.8rem'>{tier}</span>"


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
data, source = load_data()
if data is None:
    st.error("No data found. Run `python scripts/make_sample_fixture.py` (sample) "
             "or `python scripts/build_cache.py` (live) first.")
    st.stop()

meta = data["meta"]
df_full = data["experts"].copy()
# Re-derive a clean country + region from the affiliation text. This corrects
# older caches (where 'country' could be a postcode/department) without a rebuild.
df_full["country"] = df_full["affiliation"].apply(geo.detect_country)
df_full["region"] = df_full["country"].apply(geo.country_to_region)

st.title("🧬 KOL Influence Mapping Engine")
# Header stats are derived from the data itself (single source of truth), so they
# always match what's on screen.
_n_experts = len(df_full)
_n_trial_credits = int(df_full["trials_led"].sum())
_n_with_trials = int((df_full["trials_led"] > 0).sum())
st.caption(
    f"Therapeutic area: **{meta['indication']}**  ·  "
    f"{_n_experts:,} experts ranked from public PubMed & ClinicalTrials.gov records  ·  "
    f"{_n_trial_credits:,} trial-leadership credits across {_n_with_trials:,} experts  ·  "
    f"built {meta['built']}"
)

if source == "sample":
    st.warning(
        "⚠️ **Demo is running on a synthetic sample fixture** (fictional names). "
        "Run `python scripts/build_cache.py` to load live PubMed + ClinicalTrials.gov "
        "data before sharing publicly.",
        icon="⚠️",
    )

# ---------------------------------------------------------------------------
# Sidebar — methodology + adjustable weights + filters
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Scoring weights")
    st.caption("Transparent and adjustable — a Medical Director must be able to "
               "defend why someone is Tier 1.")
    weights = {}
    for c in COMPONENTS:
        weights[c] = st.slider(COMPONENT_LABEL[c], 0.0, 0.5,
                               float(config.SCORE_WEIGHTS[c]), 0.05)
    if abs(sum(weights.values()) - 1.0) > 1e-6 and sum(weights.values()) > 0:
        st.caption(f"Weights sum to {sum(weights.values()):.2f} — normalised automatically.")

    st.divider()
    st.header("🔎 Filters")
    tiers_sel = st.multiselect("Tier", ["Tier 1", "Tier 2", "Tier 3"],
                               default=["Tier 1", "Tier 2"])
    regions_present = set(df_full["region"])
    regions = [r for r in geo.REGION_ORDER if r in regions_present]
    region_sel = st.multiselect("Region", regions, default=[])
    countries = sorted([c for c in df_full["country"].dropna().unique()
                        if c and c != "Unknown"])
    country_sel = st.multiselect("Country", countries, default=[])
    only_rising = st.checkbox("⭐ Rising stars only")
    only_ws = st.checkbox("🎯 White-space (under-engaged) only")
    name_q = st.text_input("Search name")

df = rescore(df_full, weights)

# apply filters. Flag filters (rising / white-space) search across ALL tiers,
# since rising stars are Tier 3 by absolute score — otherwise they'd be hidden.
mask = pd.Series(True, index=df.index)
if region_sel:
    mask &= df["region"].isin(region_sel)
if country_sel:
    mask &= df["country"].isin(country_sel)
if name_q:
    mask &= df["name"].str.contains(name_q, case=False, na=False)
flag_active = only_rising or only_ws
if only_rising:
    mask &= df["rising_star"]
if only_ws:
    mask &= df["whitespace"]
if not flag_active:
    mask &= df["tier"].isin(tiers_sel)
df_view = df[mask].copy()

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_overview, tab_list, tab_net, tab_brief = st.tabs(
    ["📊 Overview", "📋 Tiered list", "🕸️ Network map", "📝 KOL brief"])

# ----- Overview -----
with tab_overview:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Experts scored", meta["summary"]["experts"])
    c2.metric("Tier 1", int((df["tier"] == "Tier 1").sum()))
    c3.metric("Tier 2", int((df["tier"] == "Tier 2").sum()))
    c4.metric("⭐ Rising stars", int(df["rising_star"].sum()))
    c5.metric("🎯 White-space", int(df["whitespace"].sum()))

    st.subheader("Influence distribution by tier")
    dist = df.groupby("tier")["influence_score"].count().reindex(
        ["Tier 1", "Tier 2", "Tier 3"]).fillna(0)
    st.bar_chart(dist, color="#2E75B6", horizontal=True)

    cc1, cc2 = st.columns(2)
    with cc1:
        st.subheader("Top experts")
        st.dataframe(
            df[["rank", "name", "tier", "influence_score", "affiliation"]].head(10),
            hide_index=True, width="stretch")
    with cc2:
        st.subheader("Research focus across the field")
        terms = (df["focus"].dropna().str.split(", ").explode())
        terms = terms[terms.str.len() > 0].value_counts().head(10)
        st.bar_chart(terms, color="#1F3864", horizontal=True)

    st.subheader("Experts by region")
    reg = df["region"].value_counts()
    reg = reg.reindex([r for r in geo.REGION_ORDER if r in reg.index])
    st.bar_chart(reg, color="#2E75B6", horizontal=True)

    st.info("**How to read this:** influence is a transparent composite of publication "
            "volume, senior authorship, recent activity, trial leadership, a citation "
            "proxy, and coauthorship-network centrality. Adjust the weights in the "
            "sidebar to stress-test the ranking.")

# ----- Tiered list -----
with tab_list:
    st.subheader(f"{len(df_view)} experts match your filters")
    show_cols = ["rank", "name", "tier", "influence_score", "affiliation",
                 "region", "country",
                 "publications", "senior_authorships", "recent_publications",
                 "trials_led", "industry_trials", "rising_star", "whitespace", "focus"]
    st.dataframe(
        df_view[show_cols],
        hide_index=True, width="stretch", height=520,
        column_config={
            "influence_score": st.column_config.ProgressColumn(
                "Influence", min_value=0, max_value=100, format="%.1f"),
            "rising_star": st.column_config.CheckboxColumn("⭐"),
            "whitespace": st.column_config.CheckboxColumn("🎯"),
        })
    st.download_button(
        "⬇️ Export to CSV (CRM-ready)",
        df_view[show_cols].to_csv(index=False).encode(),
        file_name=f"kol_tiered_list_{meta['indication'].replace(' ', '_').lower()}.csv",
        mime="text/csv")

# ----- Network map -----
with tab_net:
    st.subheader("Coauthorship network")
    st.caption("**Connections** = who has co-authored with whom (fixed — this is a "
               "historical fact). **Node size** = influence score and **colour** = tier, "
               "so both respond live to the weight sliders. Position matters: an expert "
               "linking separate research groups is strategically valuable even with fewer papers.")
    options = df_view["name"].tolist() or df["name"].tolist()
    focal_name = st.selectbox("Centre the map on", options)
    focal_key = df.loc[df["name"] == focal_name, "key"].iloc[0]
    adjacency, names = data["adjacency"], data["names"]
    try:
        import networkx as nx
        from pyvis.network import Network
        import streamlit.components.v1 as components

        neigh = adjacency.get(focal_key, [])[:25]
        keep = set(neigh) | {focal_key}

        # Edges among the kept nodes.
        edges = [(k, c) for k in keep for c in adjacency.get(k, [])
                 if c in keep and k < c]

        # Pre-compute a STABLE layout with networkx, then place nodes at fixed
        # coordinates and switch physics OFF — so the map doesn't jitter.
        sub = nx.Graph()
        sub.add_nodes_from(keep)
        sub.add_edges_from(edges)
        pos = nx.spring_layout(sub, seed=42, k=0.55)
        SCALE = 520

        net = Network(height="560px", width="100%", bgcolor="#ffffff",
                      font_color="#1F2933", notebook=False)
        net.toggle_physics(False)  # static layout — no more jitter
        score_by_key = dict(zip(df["key"], df["influence_score"]))
        tier_by_key = dict(zip(df["key"], df["tier"]))
        for k in keep:
            score = score_by_key.get(k, 0)
            # Wider, non-linear size range so weight changes are clearly visible.
            size = 8 + (score / 100) ** 1.4 * 46
            color = "#C45911" if k == focal_key else TIER_COLORS.get(
                tier_by_key.get(k, "Tier 3"), "#9DC3E6")
            x, y = pos[k]
            net.add_node(k, label=names.get(k, k), size=size, color=color,
                         x=x * SCALE, y=y * SCALE, physics=False,
                         title=f"{names.get(k, k)} · {tier_by_key.get(k, '')} · "
                               f"score {score:.0f}")
        for u, v in edges:
            net.add_edge(u, v, color="#D9E2F3")
        components.html(net.generate_html(), height=580)  # noqa: components html embed
        st.caption("Tip: scroll to zoom, drag the canvas to pan, drag a node to reposition.")
    except Exception:  # pragma: no cover
        st.warning(f"Network view needs the `pyvis` package. Connections for "
                   f"{focal_name}: {len(adjacency.get(focal_key, []))} coauthors.")

# ----- KOL brief -----
with tab_brief:
    options = df_view["name"].tolist() or df["name"].tolist()
    sel = st.selectbox("Select an expert", options, key="brief_sel")
    row = df.loc[df["name"] == sel].iloc[0]
    key = row["key"]

    left, right = st.columns([2, 1])
    with left:
        st.markdown(f"### {row['name']} &nbsp; {tier_badge(row['tier'])}",
                    unsafe_allow_html=True)
        st.caption(f"{row['affiliation']}" + (f" · {row['country']}" if row['country'] else ""))
        flags = []
        if row["rising_star"]:
            flags.append("⭐ Rising star")
        if row["whitespace"]:
            flags.append("🎯 White-space / under-engaged")
        if flags:
            st.markdown("  ".join(f"`{f}`" for f in flags))

        brief = data["briefs"].get(key)
        if brief is None:
            from kol_engine.briefs import generate_brief
            brief = generate_brief(row)
        st.markdown("#### Scientific profile")
        st.write(brief["profile"])
        st.markdown("#### Suggested scientific-exchange talking points")
        for p in brief["talking_points"]:
            st.markdown(f"- {p}")
        st.caption("Briefs are composed from the structured evidence (no fabrication). "
                   "An LLM enrichment path is available — see briefs.py.")

        det = data.get("details", {}).get(key, {})
        pubs = det.get("publications", [])
        trials = det.get("trials", [])
        with st.expander(f"📄 Publications — most recent ({len(pubs)} shown)"):
            if pubs:
                for p in pubs:
                    yr = f" ({p['year']})" if p.get("year") else ""
                    jr = f" — *{p['journal']}*" if p.get("journal") else ""
                    title = p.get("title") or "Untitled"
                    st.markdown(
                        f"- [{title}](https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/){yr}{jr}")
            else:
                st.caption("No publication records in this cache. Rebuild with "
                           "`python scripts/build_cache.py` to populate them.")
        with st.expander(f"🧪 Clinical trials led ({len(trials)} shown)"):
            if trials:
                for t in trials:
                    role = (t.get("role", "") or "").replace("_", " ").title()
                    title = t.get("title") or t["nct"]
                    sponsor = " · industry" if t.get("sponsor_class") == "INDUSTRY" else ""
                    st.markdown(
                        f"- [{t['nct']}](https://clinicaltrials.gov/study/{t['nct']}) — "
                        f"{title} · {t.get('phase', '')} · {role}{sponsor}")
            else:
                st.caption("No trial-leadership records in this cache (or none on file "
                           "for this expert).")

    with right:
        st.metric("Influence score", f"{row['influence_score']:.1f}", row["tier"])
        st.markdown("**Score breakdown** (percentile vs field)")
        comp = pd.Series({COMPONENT_LABEL[c]: row[f"c_{c}"] for c in COMPONENTS})
        st.bar_chart(comp, color="#2E75B6", horizontal=True)
        st.markdown("**Evidence**")
        st.write(f"- Publications: **{int(row['publications'])}** "
                 f"({int(row['senior_authorships'])} senior)")
        st.write(f"- Recent (last {config.RECENT_WINDOW_YEARS}y): **{int(row['recent_publications'])}**")
        st.write(f"- Trials led: **{int(row['trials_led'])}** "
                 f"({int(row['industry_trials'])} industry)")
        if row["top_journals"]:
            st.write(f"- Top journals: {row['top_journals']}")
        if row["active_years"]:
            st.write(f"- Active: {row['active_years']}")

st.divider()
st.caption("Data: PubMed/MEDLINE (NCBI E-utilities) · ClinicalTrials.gov API v2. "
           "Built as a Medical Affairs portfolio demonstration · not for clinical or "
           "promotional use.")
