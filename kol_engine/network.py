"""Coauthorship network construction and centrality.

A coauthorship graph captures *positional* influence: an expert who connects
otherwise-separate research groups (high betweenness) is strategically valuable
to engage even if their raw publication count is not the highest.
"""
from __future__ import annotations

import networkx as nx

from .disambiguate import Expert


def build_graph(experts: dict[str, Expert]) -> nx.Graph:
    g = nx.Graph()
    for k, e in experts.items():
        g.add_node(k, name=e.name, pubs=e.pub_count)
    for k, e in experts.items():
        for c in e.coauthors:
            if c in experts and not g.has_edge(k, c):
                g.add_edge(k, c)
    return g


def centrality_scores(g: nx.Graph) -> dict[str, float]:
    """Blend degree and betweenness centrality into a single 0-1 score.

    Betweenness is approximated with k-sampling on large graphs to stay fast
    enough for an interactive app.
    """
    if g.number_of_nodes() == 0:
        return {}
    degree = nx.degree_centrality(g)
    n = g.number_of_nodes()
    if n > 400:
        k = min(300, n)
        between = nx.betweenness_centrality(g, k=k, seed=42, normalized=True)
    else:
        between = nx.betweenness_centrality(g, normalized=True)

    def _norm(d: dict) -> dict:
        if not d:
            return {}
        mx = max(d.values()) or 1.0
        return {k: v / mx for k, v in d.items()}

    deg_n, btw_n = _norm(degree), _norm(between)
    return {k: 0.5 * deg_n.get(k, 0.0) + 0.5 * btw_n.get(k, 0.0) for k in g.nodes}


def ego_edges(g: nx.Graph, key: str, max_neighbors: int = 25) -> list[tuple[str, str]]:
    """Edges among an expert and their strongest neighbours, for visualisation."""
    if key not in g:
        return []
    neighbors = sorted(g.neighbors(key), key=lambda c: g.degree(c), reverse=True)[:max_neighbors]
    keep = set(neighbors) | {key}
    return [(u, v) for u, v in g.edges() if u in keep and v in keep]
