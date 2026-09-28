"""Structured expert judgement: Cooke's classical model and Delphi round statistics.

Classical model (Cooke 1991), 5/50/95 % quantiles:
  inter-quantile bins p = (0.05, 0.45, 0.45, 0.05)
  calibration  C_e = 1 − F_χ²(R−1)( 2 N · I(s, p) ),  I(s,p) = Σ s_i ln(s_i / p_i), R = 4 bins, N seed items
  information  per item: Σ p_i ln( p_i / r_i ), r_i = bin width / (U − L) on the intrinsic range
               [L, U] = [min of all quantiles and realisation, max] extended by an overshoot k (default 10 %)
               (log-uniform background uses ln-transformed values)
  weight       w_e = C_e · I_e(seed average) · 1{C_e ≥ α}, normalised
Decision maker (DM): weighted mixture of the experts' piecewise-uniform densities; DM quantiles
are read from the mixture CDF.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.stats import chi2

ENGINE_VERSION = "sej-1.0.0"
P = np.array([0.05, 0.45, 0.45, 0.05])
QLEVELS = (0.05, 0.5, 0.95)


def _range(values: list[float], k: float, log: bool):
    v = np.log(values) if log else np.array(values, dtype=float)
    lo, hi = float(v.min()), float(v.max())
    span = hi - lo if hi > lo else (abs(hi) or 1.0)
    return lo - k * span, hi + k * span


def _tr(x, log):
    return math.log(x) if log else float(x)


def _info(q, L, U):
    edges = [L, *q, U]
    widths = np.diff(edges)
    if (widths <= 0).any():
        raise ValueError("quantiles must be strictly increasing and inside the intrinsic range")
    r = widths / (U - L)
    return float(np.sum(P * np.log(P / r)))


def _cdf(x, q, L, U):
    edges = [L, *q, U]
    cum = [0.0, 0.05, 0.5, 0.95, 1.0]
    if x <= L:
        return 0.0
    if x >= U:
        return 1.0
    for i in range(4):
        if edges[i] <= x <= edges[i + 1]:
            return cum[i] + (x - edges[i]) / (edges[i + 1] - edges[i]) * (cum[i + 1] - cum[i])
    return 1.0


def classical(experts: list[str], items: list[dict], alpha: float = 0.0, overshoot: float = 0.1) -> dict:
    """items: [{"id","label","seed":bool,"realisation":float|None,"scale":"uni"|"log",
               "answers":{expert:[q5,q50,q95]}}]"""
    seeds = [it for it in items if it.get("seed")]
    if not seeds:
        raise ValueError("at least one seed (calibration) question with a known realisation is required")
    rng = {}
    for it in items:
        log = it.get("scale") == "log"
        vals = [v for e in experts for v in it["answers"][e]]
        if it.get("seed"):
            vals.append(float(it["realisation"]))
        if log and min(vals) <= 0:
            raise ValueError(f"item {it['id']}: log scale requires positive values")
        L, U = _range(vals, overshoot, log)
        rng[it["id"]] = (L, U, log)
    res = {}
    N = len(seeds)
    for e in experts:
        counts = np.zeros(4)
        infos = []
        for it in seeds:
            L, U, log = rng[it["id"]]
            q = [_tr(v, log) for v in it["answers"][e]]
            x = _tr(it["realisation"], log)
            b = 0 if x <= q[0] else 1 if x <= q[1] else 2 if x <= q[2] else 3
            counts[b] += 1
            infos.append(_info(q, L, U))
        s = counts / N
        with np.errstate(divide="ignore", invalid="ignore"):
            I = float(np.sum(np.where(s > 0, s * np.log(s / P), 0.0)))
        cal = float(1 - chi2.cdf(2 * N * I, df=3))
        inf = float(np.mean(infos))
        res[e] = {"calibration": cal, "information": inf, "bins": counts.astype(int).tolist(),
                  "unnormalised_weight": cal * inf if cal >= alpha else 0.0}
    tot = sum(r["unnormalised_weight"] for r in res.values())
    for e in experts:
        res[e]["weight"] = res[e]["unnormalised_weight"] / tot if tot > 0 else 1 / len(experts)
    ew = {e: 1 / len(experts) for e in experts}
    dm = []
    for it in items:
        L, U, log = rng[it["id"]]
        out = {"id": it["id"], "label": it.get("label", it["id"]), "seed": bool(it.get("seed"))}
        for name, w in (("performance", {e: res[e]["weight"] for e in experts}), ("equal", ew)):
            grid = np.linspace(L, U, 4001)
            F = np.array([sum(w[e] * _cdf(x, [_tr(v, log) for v in it["answers"][e]], L, U) for e in experts) for x in grid])
            qs = [float(np.interp(p, F, grid)) for p in QLEVELS]
            out[name] = [math.exp(v) if log else v for v in qs]
        dm.append(out)
    return {"engine_version": ENGINE_VERSION, "experts": res, "decision_maker": dm, "alpha": alpha, "seed_count": N}


def delphi(rounds: list[dict]) -> list[dict]:
    """rounds: [{"round": 1, "estimates": {expert: value}}] → median, quartiles, IQR, relative spread per round."""
    out = []
    for r in rounds:
        v = np.array([float(x) for x in r["estimates"].values() if x is not None and x != ""])
        if not len(v):
            continue
        q1, med, q3 = np.percentile(v, [25, 50, 75])
        out.append({"round": r["round"], "n": int(len(v)), "median": float(med), "q1": float(q1), "q3": float(q3),
                    "iqr": float(q3 - q1), "relative_iqr": float((q3 - q1) / med) if med else None,
                    "min": float(v.min()), "max": float(v.max())})
    for i in range(1, len(out)):
        prev = out[i - 1]["iqr"]
        out[i]["converging"] = out[i]["iqr"] < prev if prev else None
    return out
