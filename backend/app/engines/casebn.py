"""Bayesian network learned from the approved case library, with value-of-information clue ranking
(Manual Appendix E.6, SRS §5.13).

One network per occurrence category: a mechanism node C (the occurrence category's contributing mechanisms, e.g.
"readback/hearback error not detected") is the parent of one binary node per ORLIO factor (present / absent).

Learning (Laplace smoothing, α = 1):
    P(C = c)            = (n_c + α) / (N + K·α)
    P(F = present | c)  = (n_{c,F} + α) / (n_c + 2α)
where n_{c,F} counts approved cases of mechanism c in which factor F was a supported evidence or hypothesis block.

Evidence: the investigator's five-term rating r of a factor enters as *virtual (likelihood) evidence*
    λ(present) = crisp(r) / 100,  λ(absent) = 1 − λ(present)     (Strongly support 0.975 … Strongly oppose 0.025);
"No effect" and "Not provided" add no evidence. So an unrated factor is simply unknown — it is marginalised.

Clues: for each unrated factor F, the expected reduction in the entropy of C if F were established
    VOI(F) = H(C | e) − Σ_f P(F = f | e) · H(C | e, F = f)        (bits)
ranked high to low. This is the rigorous version of the paper's "Not provided" clue.

The network can be exported in ARAP's BBN format (Manual Ch. 17); virtual evidence becomes an observed child node,
which gives identical posteriors in the BBN engine (reference test TC-IES-03).
"""
from __future__ import annotations

import math
from typing import Any

from .fuzzy import CRISP

ENGINE_VERSION = "casebn-1.0.0"
ALPHA = 1.0


class CaseBNError(ValueError):
    pass


def case_mechanism(model: dict) -> str | None:
    """Primary mechanism of a past case: the finding output with the highest verbal probability (≥ Probable)."""
    order = ["HU", "IM", "ML", "PR", "VP", "AC"]
    best, rank = None, 2
    for b in model.get("blocks", []):
        if b.get("kind") == "finding" and isinstance(b.get("past"), dict):
            for m, t in b["past"].items():
                if t in order and order.index(t) > rank:
                    best, rank = m, order.index(t)
    return best


def case_factors(model: dict) -> dict[str, bool]:
    """factor → True (supported in the past case) / False (explicitly opposed)."""
    out: dict[str, bool] = {}
    for b in model.get("blocks", []):
        f = b.get("factor")
        if not f or b.get("kind") == "finding":
            continue
        p = b.get("past") if isinstance(b.get("past"), str) else "S"
        if p in ("S", "SS"):
            out[f] = True
        elif p in ("O", "SO") and f not in out:
            out[f] = False
    return out


def learn(cases: list[dict], mechanisms: list[str], factors: list[str] | None = None) -> dict[str, Any]:
    """cases: [{"id", "ref", "model"}]. Returns prior, CPTs and counts."""
    if not mechanisms:
        raise CaseBNError("the category has no mechanisms")
    rows = []
    for c in cases:
        m = case_mechanism(c["model"])
        if m in mechanisms:
            rows.append((m, case_factors(c["model"]), c.get("ref")))
    fs = sorted(set(factors or []) | {f for _, fd, _ in rows for f in fd})
    n = {m: sum(1 for r in rows if r[0] == m) for m in mechanisms}
    N, K = len(rows), len(mechanisms)
    prior = {m: (n[m] + ALPHA) / (N + K * ALPHA) for m in mechanisms}
    cpt = {f: {m: (sum(1 for r in rows if r[0] == m and r[1].get(f)) + ALPHA) / (n[m] + 2 * ALPHA) for m in mechanisms}
           for f in fs}
    return {"mechanisms": mechanisms, "factors": fs, "prior": prior, "cpt": cpt, "counts": n, "n_cases": N,
            "cases": [{"ref": r[2], "mechanism": r[0]} for r in rows]}


def likelihood(term: str | None) -> tuple[float, float] | None:
    if term not in CRISP or term == "NE":
        return None
    p = CRISP[term] / 100
    return p, 1 - p


def posterior(net: dict, ratings: dict[str, str]) -> dict[str, float]:
    post = {}
    for m in net["mechanisms"]:
        v = net["prior"][m]
        for f, t in ratings.items():
            lam = likelihood(t)
            if lam is None or f not in net["cpt"]:
                continue
            p = net["cpt"][f][m]
            v *= lam[0] * p + lam[1] * (1 - p)
        post[m] = v
    z = sum(post.values())
    if z <= 0:
        raise CaseBNError("evidence has zero probability")
    return {m: v / z for m, v in post.items()}


def entropy(d: dict[str, float]) -> float:
    return -sum(p * math.log2(p) for p in d.values() if p > 0)


def analyse(net: dict, ratings: dict[str, str], factor_meta: dict[str, dict] | None = None) -> dict[str, Any]:
    ratings = {f: t for f, t in (ratings or {}).items() if t in CRISP}
    post = posterior(net, ratings)
    h = entropy(post)
    used = [f for f, t in ratings.items() if f in net["cpt"] and t != "NE"]
    clues = []
    for f in net["factors"]:
        if f in ratings:  # rated (even "No effect"): no longer a clue
            continue
        cp = net["cpt"][f]
        p_true = sum(post[m] * cp[m] for m in post)
        post_t = {m: post[m] * cp[m] / p_true for m in post} if p_true > 0 else post
        post_f = {m: post[m] * (1 - cp[m]) / (1 - p_true) for m in post} if p_true < 1 else post
        voi = h - (p_true * entropy(post_t) + (1 - p_true) * entropy(post_f))
        lead_t = max(post_t, key=post_t.get)
        meta = (factor_meta or {}).get(f, {})
        clues.append({"factor": f, "label": meta.get("label", f), "layer": meta.get("layer"),
                      "p_present": round(p_true, 4), "voi_bits": round(voi, 4),
                      "if_present": {"mechanism": lead_t, "p": round(post_t[lead_t], 4)},
                      "if_absent": {"mechanism": max(post_f, key=post_f.get), "p": round(max(post_f.values()), 4)}})
    clues.sort(key=lambda c: -c["voi_bits"])
    lead = max(post, key=post.get)
    return {"prior": {m: round(v, 4) for m, v in net["prior"].items()}, "posterior": {m: round(v, 4) for m, v in post.items()},
            "leading": lead, "entropy_bits": round(h, 4), "evidence_used": used, "clues": clues,
            "n_cases": net["n_cases"], "counts": net["counts"], "engine_version": ENGINE_VERSION}


def to_bbn(net: dict, ratings: dict[str, str], labels: dict[str, str] | None = None) -> dict[str, Any]:
    """Export to ARAP's BBN format. Rated factors get an observed child 'obs_<factor>' carrying the virtual evidence."""
    labels = labels or {}
    ms = net["mechanisms"]
    nodes = [{"id": "C", "label": "Mechanism", "states": ms, "parents": [], "cpt": [round(net["prior"][m], 6) for m in ms]}]
    evidence = {}
    for f in net["factors"]:
        nid = _nid(f)
        nodes.append({"id": nid, "label": labels.get(f, f), "states": ["present", "absent"], "parents": ["C"],
                      "cpt": [[round(net["cpt"][f][m], 6), round(1 - net["cpt"][f][m], 6)] for m in ms]})
        lam = likelihood(ratings.get(f))
        if lam:
            # P(obs = yes | F) ∝ λ(F): a child observed "yes" reproduces the virtual evidence exactly
            nodes.append({"id": f"obs_{nid}", "label": f"Rating: {labels.get(f, f)} ({ratings[f]})", "states": ["yes", "no"],
                          "parents": [nid], "cpt": [[lam[0], 1 - lam[0]], [lam[1], 1 - lam[1]]]})
            evidence[f"obs_{nid}"] = "yes"
    return {"network": {"nodes": nodes}, "evidence": evidence}


def _nid(f: str) -> str:
    return "F_" + "".join(ch if ch.isalnum() else "_" for ch in f)
