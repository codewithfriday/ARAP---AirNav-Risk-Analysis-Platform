"""Fault tree analysis engine (Manual Chapter 14, SRS §5.2).

* Exact top-event probability with a reduced ordered binary decision diagram (BDD).
* Minimal cut sets by top-down expansion with absorption (MOCUS style).
* Rare-event approximation and min-cut upper bound.
* Birnbaum and Fussell–Vesely importance.
* Basic-event probability from a direct probability, a rate × exposure time, or
  an unavailability model (repairable: λ·MTTR/(1+λ·MTTR); periodically tested: λ·T/2).
* Common-cause groups with the β-factor model.

Tree format (JSON-friendly):
    {"top": "TOP", "nodes": {
        "TOP": {"type": "or", "label": "...", "children": ["G1", "E4"]},
        "G1":  {"type": "and", "children": ["E1", "E2"]},
        "V1":  {"type": "vote", "k": 2, "children": ["E1","E2","E3"]},
        "E1":  {"type": "basic", "p": 1e-4} | {"type":"basic","rate":1e-5,"time":10}
               | {"type":"basic","rate":..., "mttr":...} | {"type":"basic","rate":...,"test_interval":...},
        "H1":  {"type": "house", "state": true}},
     "ccf_groups": [{"id": "CCF1", "members": ["E1","E2"], "beta": 0.05}]}
"""
from __future__ import annotations

import itertools
import math
from functools import lru_cache
from typing import Any

ENGINE_VERSION = "fta-1.1.0"
GATES = {"and", "or", "vote"}
LEAVES = {"basic", "undeveloped", "house"}


class FTAError(ValueError):
    pass


# ----------------------------------------------------------------- probabilities
def basic_probability(n: dict) -> tuple[float, str]:
    if n.get("type") == "house":
        return (1.0 if n.get("state") else 0.0), "house event"
    if n.get("p") is not None:
        p = float(n["p"]); f = "p (given)"
    elif n.get("rate") is not None and n.get("time") is not None:
        lam, t = float(n["rate"]), float(n["time"])
        p = 1 - math.exp(-lam * t); f = "1 − exp(−λ·t)"
    elif n.get("rate") is not None and n.get("mttr") is not None:
        x = float(n["rate"]) * float(n["mttr"]); p = x / (1 + x); f = "λ·MTTR/(1+λ·MTTR)"
    elif n.get("rate") is not None and n.get("test_interval") is not None:
        p = float(n["rate"]) * float(n["test_interval"]) / 2; f = "λ·T/2"
    else:
        raise FTAError(f"basic event {n.get('label', '')} has no probability model")
    if not 0 <= p <= 1:
        raise FTAError(f"probability out of range: {p}")
    return p, f


# ----------------------------------------------------------------- tree handling
def _validate(tree: dict) -> None:
    nodes = tree.get("nodes") or {}
    top = tree.get("top")
    if top not in nodes:
        raise FTAError("top event not found")
    seen, stack = set(), set()

    def visit(i):
        if i not in nodes:
            raise FTAError(f"unknown node '{i}'")
        if i in stack:
            raise FTAError(f"cycle detected at '{i}'")
        if i in seen:
            return
        stack.add(i)
        n = nodes[i]
        t = n.get("type")
        if t in GATES:
            ch = n.get("children") or []
            if not ch:
                raise FTAError(f"gate '{i}' has no inputs")
            if t == "vote" and not (1 <= int(n.get("k", 0)) <= len(ch)):
                raise FTAError(f"vote gate '{i}' needs 1 ≤ k ≤ number of inputs")
            for c in ch:
                visit(c)
        elif t not in LEAVES:
            raise FTAError(f"node '{i}' has unknown type '{t}'")
        stack.discard(i)
        seen.add(i)

    visit(top)


def _expand_ccf(tree: dict) -> tuple[dict, dict[str, float], dict[str, str]]:
    """Return (tree with CCF OR-substructures, probabilities of leaves, formulas)."""
    nodes = {k: dict(v) for k, v in tree["nodes"].items()}
    probs, forms = {}, {}
    for i, n in nodes.items():
        if n.get("type") in LEAVES:
            if n.get("type") == "undeveloped" and n.get("p") is None and n.get("rate") is None:
                raise FTAError(f"undeveloped event '{i}' needs a probability")
            probs[i], forms[i] = basic_probability(n)
    for g in tree.get("ccf_groups") or []:
        beta = float(g["beta"]); cid = g["id"]
        if not 0 <= beta <= 1:
            raise FTAError("beta must be in [0,1]")
        pc = None
        for m in g["members"]:
            if m not in probs:
                raise FTAError(f"CCF member '{m}' is not a basic event")
            p = probs[m]
            pc = beta * p if pc is None else max(pc, beta * p)
            ind = f"{m}__ind"
            probs[ind] = (1 - beta) * p; forms[ind] = f"(1−β)·p, β={beta}"
            nodes[ind] = {"type": "basic", "label": f"{nodes[m].get('label', m)} (independent)"}
            nodes[m] = {"type": "or", "label": nodes[m].get("label", m), "children": [ind, cid], "_ccf": True}
            del probs[m]
        probs[cid] = pc; forms[cid] = f"β·p, β={beta}"
        nodes[cid] = {"type": "basic", "label": g.get("label", f"Common cause {cid}")}
    return {"top": tree["top"], "nodes": nodes}, probs, forms


# ----------------------------------------------------------------- BDD
class BDD:
    """Minimal reduced ordered BDD with an ite cache. Terminals: 0 and 1."""

    def __init__(self, order: list[str]):
        self.order = {v: i for i, v in enumerate(order)}
        self.vars = order
        self.nodes: list[tuple[int, int, int]] = [(-1, 0, 0), (-1, 1, 1)]  # 0 and 1 terminals
        self.unique: dict[tuple[int, int, int], int] = {}
        self.cache: dict[tuple[str, int, int], int] = {}

    def mk(self, v: int, lo: int, hi: int) -> int:
        if lo == hi:
            return lo
        key = (v, lo, hi)
        if key not in self.unique:
            self.nodes.append(key)
            self.unique[key] = len(self.nodes) - 1
        return self.unique[key]

    def var(self, name: str) -> int:
        return self.mk(self.order[name], 0, 1)

    def _level(self, u: int) -> int:
        return self.nodes[u][0] if u > 1 else len(self.order)

    def apply(self, op: str, a: int, b: int) -> int:
        if op == "and":
            if a == 0 or b == 0: return 0
            if a == 1: return b
            if b == 1: return a
        else:
            if a == 1 or b == 1: return 1
            if a == 0: return b
            if b == 0: return a
        if a == b:
            return a
        key = (op, min(a, b), max(a, b))
        if key in self.cache:
            return self.cache[key]
        la, lb = self._level(a), self._level(b)
        v = min(la, lb)
        a0, a1 = (self.nodes[a][1], self.nodes[a][2]) if la == v else (a, a)
        b0, b1 = (self.nodes[b][1], self.nodes[b][2]) if lb == v else (b, b)
        r = self.mk(v, self.apply(op, a0, b0), self.apply(op, a1, b1))
        self.cache[key] = r
        return r

    def prob(self, u: int, p: dict[str, float]) -> float:
        memo: dict[int, float] = {0: 0.0, 1: 1.0}

        def rec(x):
            if x in memo:
                return memo[x]
            v, lo, hi = self.nodes[x]
            q = p[self.vars[v]]
            memo[x] = (1 - q) * rec(lo) + q * rec(hi)
            return memo[x]

        return rec(u)


def _build_bdd(tree: dict, leaves: list[str]) -> tuple[BDD, int]:
    b = BDD(leaves)
    nodes = tree["nodes"]
    memo: dict[str, int] = {}

    def build(i):
        if i in memo:
            return memo[i]
        n = nodes[i]
        t = n["type"]
        if t in LEAVES:
            r = b.var(i)
        elif t == "and":
            r = 1
            for c in n["children"]:
                r = b.apply("and", r, build(c))
        elif t == "or":
            r = 0
            for c in n["children"]:
                r = b.apply("or", r, build(c))
        else:  # vote k-of-n
            k = int(n["k"])
            ch = [build(c) for c in n["children"]]
            r = 0
            for combo in itertools.combinations(ch, k):
                term = 1
                for x in combo:
                    term = b.apply("and", term, x)
                r = b.apply("or", r, term)
        memo[i] = r
        return r

    return b, build(tree["top"])


# ----------------------------------------------------------------- cut sets
def _minimise(sets: list[frozenset]) -> list[frozenset]:
    sets = sorted(set(sets), key=len)
    out: list[frozenset] = []
    for s in sets:
        if not any(o <= s for o in out):
            out.append(s)
    return out


def minimal_cut_sets(tree: dict, max_order: int | None = None, max_sets: int = 200000) -> tuple[list[frozenset], bool]:
    nodes = tree["nodes"]
    truncated = False

    @lru_cache(maxsize=None)
    def cs(i) -> tuple[frozenset, ...]:
        nonlocal truncated
        n = nodes[i]
        t = n["type"]
        if t == "house":
            return (frozenset(),) if n.get("state") else tuple()
        if t in LEAVES:
            return (frozenset([i]),)
        child = [cs(c) for c in n["children"]]
        if t == "or":
            res = [s for c in child for s in c]
        elif t == "and":
            res = [frozenset()]
            for c in child:
                res = [a | b for a in res for b in c]
                if max_order:
                    before = len(res); res = [x for x in res if len(x) <= max_order]; truncated |= len(res) < before
                res = _minimise(res)
                if len(res) > max_sets:
                    raise FTAError("cut-set explosion; set a truncation order")
        else:
            k = int(n["k"])
            res = []
            for combo in itertools.combinations(child, k):
                part = [frozenset()]
                for c in combo:
                    part = [a | b for a in part for b in c]
                res.extend(part)
        if max_order:
            before = len(res); res = [x for x in res if len(x) <= max_order]; truncated |= len(res) < before
        return tuple(_minimise(res))

    return list(cs(tree["top"])), truncated


# ----------------------------------------------------------------- main entry
def analyse(tree: dict, max_order: int | None = None) -> dict[str, Any]:
    _validate(tree)
    t2, probs, forms = _expand_ccf(tree)
    leaves = sorted(probs)
    # variable order: order of first appearance in depth-first traversal (good heuristic)
    order: list[str] = []
    seen = set()

    def dfs(i):
        if i in seen:
            return
        seen.add(i)
        n = t2["nodes"][i]
        if n["type"] in LEAVES:
            order.append(i)
        else:
            for c in n["children"]:
                dfs(c)

    dfs(t2["top"])
    leaves = order
    bdd, root = _build_bdd(t2, leaves)
    p_exact = bdd.prob(root, probs)

    mcs, truncated = minimal_cut_sets(t2, max_order)
    cut = []
    for s in mcs:
        pr = math.prod(probs[e] for e in s) if s else 1.0
        cut.append({"events": sorted(s), "order": len(s), "probability": pr})
    cut.sort(key=lambda c: -c["probability"])
    rare = sum(c["probability"] for c in cut)
    upper = 1 - math.prod(1 - c["probability"] for c in cut)
    for c in cut:
        c["contribution"] = c["probability"] / rare if rare > 0 else 0.0

    imp = []
    for e in leaves:
        p1 = dict(probs); p1[e] = 1.0
        p0 = dict(probs); p0[e] = 0.0
        t1, t0 = bdd.prob(root, p1), bdd.prob(root, p0)
        imp.append({"event": e, "label": t2["nodes"][e].get("label", e), "probability": probs[e], "formula": forms[e],
                    "birnbaum": t1 - t0, "fussell_vesely": (p_exact - t0) / p_exact if p_exact > 0 else 0.0})
    imp.sort(key=lambda x: -x["fussell_vesely"])
    diff = abs(rare - p_exact) / p_exact if p_exact > 0 else 0.0
    return {"engine_version": ENGINE_VERSION, "top_probability": p_exact, "rare_event_approximation": rare,
            "min_cut_upper_bound": upper, "approximation_differs": diff > 0.01, "cut_sets": cut,
            "cut_sets_truncated": truncated, "importance": imp, "single_points_of_failure":
                [c["events"][0] for c in cut if c["order"] == 1], "bdd_nodes": len(bdd.nodes)}
