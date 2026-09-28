"""Bayesian belief network engine — exact inference by variable elimination
(Manual Chapter 17, SRS §5.4).

Network format:
    {"nodes": [{"id": "F", "label": "Fatigue", "states": ["yes","no"], "parents": [],
                "cpt": [0.15, 0.85]},
               {"id": "E", "states": ["yes","no"], "parents": ["F","W"],
                "cpt": [[[0.02,0.98],[0.008,0.992]], [[0.006,0.994],[0.002,0.998]]]}]}
The CPT is nested by parent states in the order of `parents`, innermost list = distribution of the node.
"""
from __future__ import annotations

import itertools
from typing import Any

import numpy as np

ENGINE_VERSION = "bbn-1.0.0"


class BBNError(ValueError):
    pass


class Factor:
    def __init__(self, vars_: list[str], table: np.ndarray):
        self.vars = list(vars_)
        self.t = table

    def product(self, other: "Factor") -> "Factor":
        allv = self.vars + [v for v in other.vars if v not in self.vars]
        letters = {v: chr(97 + i) for i, v in enumerate(allv)}
        if len(allv) > 26:
            raise BBNError("factor too large")
        expr = f"{''.join(letters[v] for v in self.vars)},{''.join(letters[v] for v in other.vars)}->{''.join(letters[v] for v in allv)}"
        return Factor(allv, np.einsum(expr, self.t, other.t))

    def sum_out(self, v: str) -> "Factor":
        i = self.vars.index(v)
        return Factor(self.vars[:i] + self.vars[i + 1:], self.t.sum(axis=i))

    def reduce(self, v: str, state_idx: int) -> "Factor":
        if v not in self.vars:
            return self
        i = self.vars.index(v)
        return Factor(self.vars[:i] + self.vars[i + 1:], np.take(self.t, state_idx, axis=i))


def validate(net: dict) -> dict[str, dict]:
    nodes = {n["id"]: n for n in net.get("nodes", [])}
    if not nodes:
        raise BBNError("network has no nodes")
    for n in nodes.values():
        if len(n.get("states", [])) < 2:
            raise BBNError(f"node {n['id']} needs at least two states")
        for p in n.get("parents", []):
            if p not in nodes:
                raise BBNError(f"unknown parent {p} of {n['id']}")
    # cycle check (Kahn)
    indeg = {k: len(v.get("parents", [])) for k, v in nodes.items()}
    children = {k: [] for k in nodes}
    for k, v in nodes.items():
        for p in v.get("parents", []):
            children[p].append(k)
    q = [k for k, d in indeg.items() if d == 0]
    seen = 0
    while q:
        k = q.pop(); seen += 1
        for c in children[k]:
            indeg[c] -= 1
            if indeg[c] == 0:
                q.append(c)
    if seen != len(nodes):
        raise BBNError("the graph contains a cycle")
    for n in nodes.values():
        shape = tuple(len(nodes[p]["states"]) for p in n.get("parents", [])) + (len(n["states"]),)
        arr = np.asarray(n["cpt"], dtype=float)
        if arr.shape != shape:
            raise BBNError(f"CPT of {n['id']} has shape {arr.shape}, expected {shape}")
        if (arr < 0).any() or not np.allclose(arr.sum(axis=-1), 1.0, atol=1e-9):
            raise BBNError(f"CPT of {n['id']}: each distribution must be non-negative and sum to 1")
    return nodes


def _factors(nodes: dict) -> list[Factor]:
    return [Factor(list(n.get("parents", [])) + [k], np.asarray(n["cpt"], dtype=float)) for k, n in nodes.items()]


def query(net: dict, targets: list[str] | None = None, evidence: dict[str, str] | None = None) -> dict[str, Any]:
    nodes = validate(net)
    evidence = evidence or {}
    ev_idx = {}
    for k, s in evidence.items():
        if k not in nodes:
            raise BBNError(f"evidence on unknown node {k}")
        if s not in nodes[k]["states"]:
            raise BBNError(f"state {s} not in node {k}")
        ev_idx[k] = nodes[k]["states"].index(s)
    targets = targets or [k for k in nodes if k not in evidence]
    base = _factors(nodes)
    for k, i in ev_idx.items():
        base = [f.reduce(k, i) for f in base]
    p_evidence = None
    result = {}
    for tgt in targets:
        if tgt in ev_idx:
            dist = np.zeros(len(nodes[tgt]["states"])); dist[ev_idx[tgt]] = 1
            result[tgt] = dict(zip(nodes[tgt]["states"], dist.tolist()))
            continue
        fs = list(base)
        elim = [v for v in nodes if v != tgt and v not in ev_idx]
        # min-degree heuristic
        while elim:
            def cost(v):
                vs = set()
                for f in fs:
                    if v in f.vars:
                        vs |= set(f.vars)
                return len(vs)
            v = min(elim, key=cost); elim.remove(v)
            rel = [f for f in fs if v in f.vars]
            fs = [f for f in fs if v not in f.vars]
            if rel:
                prod = rel[0]
                for f in rel[1:]:
                    prod = prod.product(f)
                fs.append(prod.sum_out(v))
        prod = fs[0]
        for f in fs[1:]:
            prod = prod.product(f)
        # prod has only tgt (or scalar factors multiplied in)
        t = prod.t if prod.vars == [tgt] else prod.t.reshape(-1)
        z = float(t.sum())
        if z <= 0:
            raise BBNError("evidence has zero probability")
        p_evidence = z
        result[tgt] = dict(zip(nodes[tgt]["states"], (t / z).tolist()))
    return {"engine_version": ENGINE_VERSION, "marginals": result, "evidence": evidence,
            "probability_of_evidence": p_evidence if evidence else 1.0}


def enumerate_joint(net: dict, target: str, evidence: dict[str, str] | None = None) -> dict[str, float]:
    """Brute-force oracle used in tests (small networks only)."""
    nodes = validate(net)
    evidence = evidence or {}
    names = list(nodes)
    acc = np.zeros(len(nodes[target]["states"]))
    for combo in itertools.product(*[range(len(nodes[n]["states"])) for n in names]):
        a = dict(zip(names, combo))
        if any(nodes[k]["states"][a[k]] != s for k, s in evidence.items()):
            continue
        p = 1.0
        for n in names:
            cpt = np.asarray(nodes[n]["cpt"], dtype=float)
            idx = tuple(a[x] for x in nodes[n].get("parents", [])) + (a[n],)
            p *= cpt[idx]
        acc[a[target]] += p
    return dict(zip(nodes[target]["states"], (acc / acc.sum()).tolist()))


def sensitivity(net: dict, target: str, target_state: str, evidence: dict | None = None) -> list[dict]:
    """Tornado data: effect on P(target=state) of setting each other node to each of its states."""
    base = query(net, [target], evidence)["marginals"][target][target_state]
    out = []
    for n in net["nodes"]:
        if n["id"] == target or (evidence and n["id"] in evidence):
            continue
        vals = []
        for s in n["states"]:
            ev = dict(evidence or {}); ev[n["id"]] = s
            try:
                vals.append(query(net, [target], ev)["marginals"][target][target_state])
            except BBNError:
                pass
        if vals:
            out.append({"node": n["id"], "label": n.get("label", n["id"]), "min": min(vals), "max": max(vals),
                        "swing": max(vals) - min(vals), "base": base})
    return sorted(out, key=lambda x: -x["swing"])
