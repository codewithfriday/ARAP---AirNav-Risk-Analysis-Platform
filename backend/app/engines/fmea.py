"""FMEA / FMECA calculations (Manual Chapter 10, SRS §5.3)."""
from __future__ import annotations

from collections import defaultdict

ENGINE_VERSION = "fmea-1.0.0"


def rpn(s: int, o: int, d: int) -> int:
    for x in (s, o, d):
        if not 1 <= int(x) <= 10:
            raise ValueError("S, O and D must be 1–10")
    return int(s) * int(o) * int(d)


def analyse(rows: list[dict], high_severity: int = 8) -> dict:
    """rows: dicts with item, failure_mode, s, o, d and optionally rate (λp), alpha, beta, time, severity_class."""
    out, crit = [], defaultdict(float)
    alpha_sum = defaultdict(float)
    for r in rows:
        item = dict(r)
        if all(item.get(k) not in (None, "") for k in ("s", "o", "d")):
            item["rpn"] = rpn(item["s"], item["o"], item["d"])
        item["high_severity"] = bool(item.get("s")) and int(item["s"]) >= high_severity
        if all(item.get(k) not in (None, "") for k in ("rate", "alpha", "beta", "time")):
            cm = float(item["beta"]) * float(item["alpha"]) * float(item["rate"]) * float(item["time"])
            item["mode_criticality"] = cm
            crit[(item.get("item"), item.get("severity_class") or str(item.get("s")))] += cm
            alpha_sum[item.get("item")] += float(item["alpha"])
        out.append(item)
    ranked = sorted([x for x in out if "rpn" in x], key=lambda x: -x["rpn"])
    for i, x in enumerate(ranked, 1):
        x["rank"] = i
    warnings = [f"Mode ratios (α) for item '{k}' sum to {v:.3f}, not 1" for k, v in alpha_sum.items() if abs(v - 1) > 1e-6]
    return {"engine_version": ENGINE_VERSION, "rows": out,
            "item_criticality": [{"item": k[0], "severity_class": k[1], "criticality": v} for k, v in crit.items()],
            "warnings": warnings}
