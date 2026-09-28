"""Reliability block diagrams (IEC 61078) and Markov analysis (IEC 61165).

RBD structure (JSON tree):
    {"type": "series"|"parallel"|"koon", "k": 2, "label": ..., "children": [...]}
    {"type": "block", "label": "Main Tx", "mtbf": 20000, "mttr": 4}      # hours
Steady-state availability of a block A = MTBF / (MTBF + MTTR); independent blocks.

Markov: continuous-time chain with states [{"id","label","up"}] and transitions
[{"from","to","rate"}] (per hour). Steady-state distribution π solves πQ = 0, Σπ = 1.
Also mean time to first failure (MTTFF) from an initial up state, treating down states as absorbing.
"""
from __future__ import annotations

import itertools
import math

import numpy as np

ENGINE_VERSION = "rbd-1.0.0"
HOURS_PER_YEAR = 8760.0


def _avail(node: dict) -> float:
    t = node["type"]
    if t == "block":
        mtbf, mttr = float(node["mtbf"]), float(node.get("mttr", 0))
        if mtbf <= 0 or mttr < 0:
            raise ValueError(f"block {node.get('label')}: MTBF must be > 0 and MTTR ≥ 0")
        return mtbf / (mtbf + mttr)
    ch = [_avail(c) for c in node.get("children") or []]
    if not ch:
        raise ValueError(f"{t} group '{node.get('label', '')}' has no children")
    if t == "series":
        return math.prod(ch)
    if t == "parallel":
        return 1 - math.prod(1 - a for a in ch)
    if t == "koon":
        k = int(node["k"])
        if not 1 <= k <= len(ch):
            raise ValueError("k must be between 1 and n")
        total = 0.0
        for up in itertools.product([0, 1], repeat=len(ch)):
            if sum(up) >= k:
                total += math.prod(a if u else 1 - a for a, u in zip(ch, up))
        return total
    raise ValueError(f"unknown node type {t}")


def rbd(structure: dict) -> dict:
    a = _avail(structure)
    blocks = []

    def collect(n, path):
        if n["type"] == "block":
            blocks.append((n, path))
        for i, c in enumerate(n.get("children") or []):
            collect(c, path + [i])
    collect(structure, [])
    importance = []
    for b, _ in blocks:
        saved = (b["mtbf"], b.get("mttr", 0))
        b["mttr"] = 0
        a_perfect = _avail(structure)
        b["mtbf"], b["mttr"] = saved
        importance.append({"block": b.get("label"), "availability": b["mtbf"] / (b["mtbf"] + b.get("mttr", 0)),
                           "improvement_if_perfect": a_perfect - a})
    importance.sort(key=lambda x: -x["improvement_if_perfect"])
    return {"engine_version": ENGINE_VERSION, "availability": a, "unavailability": 1 - a,
            "downtime_hours_per_year": (1 - a) * HOURS_PER_YEAR, "blocks": importance}


def markov(states: list[dict], transitions: list[dict], initial: str | None = None) -> dict:
    ids = [s["id"] for s in states]
    if len(set(ids)) != len(ids) or not ids:
        raise ValueError("state ids must be unique and non-empty")
    n = len(ids)
    idx = {s: i for i, s in enumerate(ids)}
    Q = np.zeros((n, n))
    for t in transitions:
        r = float(t["rate"])
        if r < 0:
            raise ValueError("rates must be non-negative")
        if t["from"] not in idx or t["to"] not in idx or t["from"] == t["to"]:
            raise ValueError("invalid transition")
        Q[idx[t["from"]], idx[t["to"]]] += r
    np.fill_diagonal(Q, -Q.sum(axis=1))
    A = np.vstack([Q.T, np.ones(n)])
    b = np.zeros(n + 1); b[-1] = 1
    pi, *_ = np.linalg.lstsq(A, b, rcond=None)
    pi = np.clip(pi, 0, None); pi = pi / pi.sum()
    up = [i for i, s in enumerate(states) if s.get("up")]
    down = [i for i in range(n) if i not in up]
    avail = float(pi[up].sum())
    # frequency of failures: flow from up to down states
    ffreq = float(sum(pi[i] * Q[i, j] for i in up for j in down))
    res = {"engine_version": ENGINE_VERSION, "steady_state": {ids[i]: float(pi[i]) for i in range(n)},
           "availability": avail, "unavailability": 1 - avail, "failure_frequency_per_hour": ffreq,
           "mtbf_system_hours": (avail / ffreq) if ffreq > 0 else None,
           "mean_down_time_hours": ((1 - avail) / ffreq) if ffreq > 0 else None}
    start = initial or (ids[up[0]] if up else None)
    if start and up and down:
        # MTTFF: expected time to reach any down state from start, down states absorbing
        Qu = Q[np.ix_(up, up)]
        try:
            m = np.linalg.solve(-Qu, np.ones(len(up)))
            res["mttff_hours"] = float(m[up.index(idx[start])])
        except np.linalg.LinAlgError:
            res["mttff_hours"] = None
    return res
