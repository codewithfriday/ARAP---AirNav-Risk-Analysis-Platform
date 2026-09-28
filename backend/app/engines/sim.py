"""Simulation (real-time / fast-time) result statistics.

For each measure: mean, standard deviation and 95 % confidence interval per condition (baseline,
solution); Welch's t-test for the difference; check of the success criterion
(e.g. solution mean ≤ threshold, or solution not worse than baseline by more than a margin).
"""
from __future__ import annotations

import math

import numpy as np
from scipy import stats

ENGINE_VERSION = "sim-1.0.0"


def describe(values: list[float]) -> dict:
    v = np.array([float(x) for x in values if x is not None and x != ""], dtype=float)
    n = len(v)
    if n == 0:
        return {"n": 0}
    m = float(v.mean())
    sd = float(v.std(ddof=1)) if n > 1 else 0.0
    half = float(stats.t.ppf(0.975, n - 1) * sd / math.sqrt(n)) if n > 1 else None
    return {"n": n, "mean": m, "sd": sd, "ci95": [m - half, m + half] if half is not None else None}


def analyse(measures: list[dict]) -> list[dict]:
    """measures: [{"id","label","unit","better":"lower"|"higher","criterion":{"type":"threshold"|"no_worse","value":x},
                   "baseline":[...], "solution":[...]}]"""
    out = []
    for m in measures:
        b, s = describe(m.get("baseline") or []), describe(m.get("solution") or [])
        r = {"id": m["id"], "label": m.get("label"), "unit": m.get("unit", ""), "baseline": b, "solution": s}
        if b.get("n", 0) > 1 and s.get("n", 0) > 1:
            t, p = stats.ttest_ind(m["solution"], m["baseline"], equal_var=False)
            r["difference"] = s["mean"] - b["mean"]
            r["welch_t"], r["p_value"] = float(t), float(p)
        c = m.get("criterion") or {}
        better = m.get("better", "lower")
        if s.get("n") and c.get("type") == "threshold":
            r["criterion_met"] = s["mean"] <= c["value"] if better == "lower" else s["mean"] >= c["value"]
        elif s.get("n") and b.get("n") and c.get("type") == "no_worse":
            diff = s["mean"] - b["mean"]
            r["criterion_met"] = diff <= c["value"] if better == "lower" else -diff <= c["value"]
        out.append(r)
    return out
