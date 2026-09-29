"""Mamdani fuzzy inference over ORLIO AcciMaps (Manual Appendix E, SRS §5.12).

Follows Ng, Bil, Sardina & O'Bree (2022), "Designing an expert system to support aviation occurrence
investigations", Expert Systems with Applications 207, 117994:

* evidence is rated on five terms (Strongly oppose … Strongly support), each converted to a fixed crisp value;
* input sets are trapezoids that do not overlap, output sets are triangles;
* AND = min, implication = min (truncation), aggregation = max, defuzzification = centroid;
* hypothesis blocks output the support scale, finding blocks a verbal probability for every mechanism.

Differences from the paper (documented in the Manual):
* "Not provided" evidence is unknown, not a middle value: a rule that needs it cannot fire; if no rule fires the
  block is "not determined" and the missing evidence is returned as a *clue*;
* besides the paper's confirming rule, default rule sets include weakening rules (one input only "No effect")
  and contradicting rules (one input opposed), so opposing evidence is reasoned about.

AcciMap format (the `model` of a case):
    {"blocks": [{"id": "E1", "layer": "L", "kind": "evidence|hypothesis|finding", "label": "...",
                 "factor": "L-SIMILAR-CALLSIGN", "past": "S" | {"M2": "VP", ...}}],
     "edges": [{"source": "E1", "target": "H1", "role": "input|context"}],
     "rules": {"H1": [{"when": {"E1": ["S", "SS"]}, "then": "S", "weight": 1}],
               "F1": [{"when": {...}, "then": {"M2": "VP", "M1": "HU"}}]}}
"""
from __future__ import annotations

from typing import Any

import numpy as np

ENGINE_VERSION = "fuzzy-1.0.0"

LAYERS = ["O", "R", "L", "I", "E"]
LAYER_NAMES = {"O": "Organisational influences", "R": "Risk controls", "L": "Local conditions",
               "I": "Individual actions", "E": "Occurrence events"}

SUPPORT = ["SO", "O", "NE", "S", "SS"]
SUPPORT_LABEL = {"SO": "Strongly oppose", "O": "Oppose", "NE": "No effect", "S": "Support", "SS": "Strongly support"}
CRISP = {"SO": 2.5, "O": 19.5, "NE": 50.0, "S": 80.5, "SS": 97.5}
# input trapezoids (a, b, c, d) — ATSB evidence-table bands, no overlap (paper Fig. 6 and 9: Support = [66 67 94 95])
IN_MF = {"SO": (-1, 0, 4, 5), "O": (5, 6, 33, 34), "NE": (34, 35, 65, 66), "S": (66, 67, 94, 95), "SS": (95, 96, 100, 101)}
# hypothesis output triangles (paper Fig. 7); centroids equal the crisp input values, so a result propagates unchanged
OUT_SUPPORT = {"SO": (0, 2.5, 5), "O": (5, 19.5, 34), "NE": (34, 50, 66), "S": (66, 80.5, 95), "SS": (95, 97.5, 100)}

PROB = ["HU", "IM", "ML", "PR", "VP", "AC"]
PROB_LABEL = {"HU": "Highly unlikely", "IM": "Improbable", "ML": "More or less likely", "PR": "Probable",
              "VP": "Very probable", "AC": "Almost certain"}
# finding output triangles on the IPCC verbal-probability bands (paper Fig. 8, Table 2). The paper does not publish
# the peaks; ARAP places them so that a fully fired set defuzzifies to the values in the paper's Fig. 13
# (Very probable 94.54, Highly unlikely 4.959).
OUT_PROB = {"HU": (0, 4.877, 10), "IM": (10, 21.5, 33), "ML": (33, 49.5, 66), "PR": (66, 78, 90),
            "VP": (90, 94.62, 99), "AC": (99, 99.5, 100)}

U = np.linspace(0, 100, 10001)


class FuzzyError(ValueError):
    pass


def trap(x: float, p) -> float:
    a, b, c, d = p
    if x < a or x > d:
        return 0.0
    if b <= x <= c:
        return 1.0
    if x < b:
        return (x - a) / (b - a)
    return (d - x) / (d - c)


def tri_curve(p) -> np.ndarray:
    a, b, c = p
    y = np.zeros_like(U)
    if b > a:
        m = (U >= a) & (U <= b)
        y[m] = (U[m] - a) / (b - a)
    if c > b:
        m = (U >= b) & (U <= c)
        y[m] = np.maximum(y[m], (c - U[m]) / (c - b))
    y[U == b] = 1.0
    return y


_CURVES = {**{("S", k): tri_curve(v) for k, v in OUT_SUPPORT.items()}, **{("P", k): tri_curve(v) for k, v in OUT_PROB.items()}}


def tri(x: float, p) -> float:
    a, b, c = p
    if x < a or x > c:
        return 0.0
    if x == b:
        return 1.0
    return (x - a) / (b - a) if x < b else (c - x) / (c - b)


def term_of(x: float, scale: str) -> str:
    sets = OUT_SUPPORT if scale == "S" else OUT_PROB
    return max(sets, key=lambda k: (tri(x, sets[k]), -abs(sets[k][1] - x)))


def mu_in(x: float | None, terms) -> float:
    if x is None:
        return 0.0
    return max(trap(x, IN_MF[t]) for t in terms)


# ------------------------------------------------------------------ structure
def blocks_by_id(model: dict) -> dict[str, dict]:
    out = {}
    for b in model.get("blocks", []):
        if b["id"] in out:
            raise FuzzyError(f"duplicate block id {b['id']}")
        if b.get("layer") not in LAYERS:
            raise FuzzyError(f"block {b['id']}: layer must be one of {LAYERS}")
        if b.get("kind") not in ("evidence", "hypothesis", "finding"):
            raise FuzzyError(f"block {b['id']}: kind must be evidence, hypothesis or finding")
        out[b["id"]] = b
    return out


def inputs_of(model: dict) -> dict[str, list[str]]:
    ids = blocks_by_id(model)
    ins: dict[str, list[str]] = {k: [] for k in ids}
    for e in model.get("edges", []):
        if e.get("role", "input") != "input":
            continue
        if e["source"] not in ids or e["target"] not in ids:
            raise FuzzyError(f"edge {e['source']}→{e['target']} refers to a missing block")
        ins[e["target"]].append(e["source"])
    return ins


def topo(model: dict) -> list[str]:
    ins = inputs_of(model)
    order, state = [], {}

    def visit(n):
        if state.get(n) == 1:
            raise FuzzyError(f"cycle through block {n}")
        if state.get(n) == 2:
            return
        state[n] = 1
        for p in ins[n]:
            visit(p)
        state[n] = 2
        order.append(n)
    for n in ins:
        visit(n)
    return order


# ------------------------------------------------------------------ default rules
def _up(p: str) -> list[str]:
    return ["S", "SS"] if p in ("S", "SS") else ["O", "SO"] if p in ("O", "SO") else ["NE"]


def _opp(p: str) -> list[str] | None:
    return ["O", "SO"] if p in ("S", "SS") else ["S", "SS"] if p in ("O", "SO") else None


_WEAK_S = {"SS": "S", "S": "NE", "NE": "NE", "O": "NE", "SO": "O"}
_CONTRA_S = {"SS": "O", "S": "O", "NE": "NE", "O": "S", "SO": "S"}
_WEAK_P = {"AC": "VP", "VP": "PR", "PR": "ML", "ML": "ML", "IM": "ML", "HU": "IM"}
_CONTRA_P = {"AC": "IM", "VP": "IM", "PR": "IM", "ML": "ML", "IM": "ML", "HU": "ML"}


def _past_term(b: dict) -> str:
    """The state an input block had in the past occurrence (derived blocks: their past output)."""
    p = b.get("past") or "S"
    return p if isinstance(p, str) else "S"


def default_rules(model: dict) -> dict[str, list[dict]]:
    """Confirming rule (the paper's rule) + one weakening and one contradicting rule per input."""
    ids = blocks_by_id(model)
    ins = inputs_of(model)
    rules: dict[str, list[dict]] = {}
    for bid, b in ids.items():
        if b["kind"] == "evidence" or not ins[bid]:
            continue
        past = b.get("past") or ("S" if b["kind"] == "hypothesis" else {})
        if b["kind"] == "finding" and not isinstance(past, dict):
            raise FuzzyError(f"finding {bid}: past must map each mechanism to a verbal probability")
        weak = (lambda o: _WEAK_S[o]) if b["kind"] == "hypothesis" else (lambda o: {k: _WEAK_P[v] for k, v in o.items()})
        contra = (lambda o: _CONTRA_S[o]) if b["kind"] == "hypothesis" else (lambda o: {k: _CONTRA_P[v] for k, v in o.items()})
        pt = {i: _past_term(ids[i]) for i in ins[bid]}
        rs = [{"when": {i: _up(pt[i]) for i in ins[bid]}, "then": past, "weight": 1, "kind": "confirming"}]
        for i in ins[bid]:
            if pt[i] != "NE":
                rs.append({"when": {j: (["NE"] if j == i else _up(pt[j])) for j in ins[bid]}, "then": weak(past),
                           "weight": 1, "kind": "weakening"})
        for i in ins[bid]:
            o = _opp(pt[i])
            if o:
                rs.append({"when": {i: o}, "then": contra(past), "weight": 1, "kind": "contradicting"})
        rules[bid] = rs
    return rules


# ------------------------------------------------------------------ inference
def _defuzz(fired: list[tuple[float, str]], scale: str) -> float | None:
    agg = np.zeros_like(U)
    for deg, term in fired:
        if deg > 0:
            agg = np.maximum(agg, np.minimum(deg, _CURVES[(scale, term)]))
    s = agg.sum()
    return float((U * agg).sum() / s) if s > 0 else None


def evaluate_block(block: dict, rules: list[dict], values: dict[str, float | None], mechanisms: list[str] | None = None) -> dict:
    fired = []
    for k, r in enumerate(rules):
        degs = [mu_in(values.get(i), terms) for i, terms in r["when"].items()]
        d = (min(degs) if degs else 0.0) * float(r.get("weight", 1))
        if d > 0:
            fired.append((k, d))
    if block["kind"] == "hypothesis":
        crisp = _defuzz([(d, rules[k]["then"]) for k, d in fired], "S")
        return {"determined": crisp is not None, "crisp": crisp, "term": term_of(crisp, "S") if crisp is not None else None,
                "fired": [{"rule": k, "degree": round(d, 4), "kind": rules[k].get("kind")} for k, d in fired]}
    outs = {}
    mechs = mechanisms or sorted({m for r in rules for m in (r["then"] or {})})
    for m in mechs:
        c = _defuzz([(d, rules[k]["then"][m]) for k, d in fired if m in (rules[k]["then"] or {})], "P")
        outs[m] = {"crisp": c, "term": term_of(c, "P") if c is not None else None}
    det = any(o["crisp"] is not None for o in outs.values())
    return {"determined": det, "outputs": outs,
            "fired": [{"rule": k, "degree": round(d, 4), "kind": rules[k].get("kind")} for k, d in fired]}


def infer(model: dict, states: dict[str, str | None], mechanisms: list[str] | None = None) -> dict[str, Any]:
    """states: evidence block id → term (SO…SS) or None/'NP' for not provided."""
    ids = blocks_by_id(model)
    ins = inputs_of(model)
    rules = model.get("rules") or default_rules(model)
    values: dict[str, float | None] = {}
    res: dict[str, dict] = {}
    for bid in topo(model):
        b = ids[bid]
        if b["kind"] == "evidence" or not ins[bid]:
            s = states.get(bid)
            if s not in CRISP:
                s = None
            values[bid] = CRISP[s] if s else None
            res[bid] = {"kind": "evidence", "state": s}
            continue
        r = evaluate_block(b, rules.get(bid, []), values, mechanisms)
        r["kind"] = b["kind"]
        r["missing"] = [i for i in ins[bid] if values.get(i) is None]
        res[bid] = r
        values[bid] = r.get("crisp") if b["kind"] == "hypothesis" else None
    return {"blocks": res, "clues": clues(model, res, rules), "engine_version": ENGINE_VERSION}


def clues(model: dict, res: dict, rules: dict) -> list[dict]:
    """Evidence the past occurrence needed that is not provided now, for every block that could not be determined."""
    ids = blocks_by_id(model)
    out: dict[str, dict] = {}

    def need(bid: str, via: str, prio: float, seen: set):
        if bid in seen:
            return
        seen.add(bid)
        r = res[bid]
        if r["kind"] == "evidence":
            if r["state"] is None:
                c = out.setdefault(bid, {"block": bid, "label": ids[bid].get("label", bid), "layer": ids[bid]["layer"],
                                         "factor": ids[bid].get("factor"), "for": [], "priority": 0.0})
                if via not in c["for"]:
                    c["for"].append(via)
                c["priority"] = max(c["priority"], prio)
            return
        if r["determined"]:
            return
        conf = next((x for x in rules.get(bid, []) if x.get("kind", "confirming") == "confirming"), None)
        if conf:
            n = len(conf["when"])
            sat = sum(1 for i, t in conf["when"].items() if mu_in(_val(res, i), t) > 0)
            p = sat / n if n else 0
        else:
            p = 0
        for i in r["missing"]:
            need(i, bid, p, seen)
    for bid, r in res.items():
        if r["kind"] != "evidence" and not r["determined"]:
            need(bid, bid, 0, set())
    return sorted(out.values(), key=lambda c: -c["priority"])


def _val(res, i):
    r = res.get(i, {})
    if r.get("kind") == "evidence":
        return CRISP.get(r.get("state")) if r.get("state") else None
    return r.get("crisp")
