"""Event tree analysis (IEC 62502).

Model:
    {"initiating": {"label": ..., "frequency": 0.025, "unit": "per year"},
     "events": [{"id": "B1", "label": "STCA alerts", "p_success": 0.9}, ...],
     "overrides": {"S-F": {"B3": {"p_success": 0.8}}},   # conditional probabilities by path prefix
     "outcomes": {"S": {...}}, "terminate_on_success": true}

Each branch goes up (success) or down (failure). With terminate_on_success, a success ends the
sequence (the barrier has stopped escalation) — the usual form for barrier event trees.
"""
from __future__ import annotations

ENGINE_VERSION = "eta-1.0.0"


def analyse(model: dict) -> dict:
    ie = model["initiating"]
    f0 = float(ie["frequency"])
    events = model.get("events") or []
    if f0 < 0:
        raise ValueError("initiating frequency must be non-negative")
    if not events:
        raise ValueError("at least one functional event (barrier) is required")
    for e in events:
        if not 0 <= float(e["p_success"]) <= 1:
            raise ValueError(f"p_success of {e['id']} must be in [0,1]")
    overrides = model.get("overrides") or {}
    terminate = model.get("terminate_on_success", True)
    outcome_meta = model.get("outcomes") or {}
    seqs = []

    def walk(i, path, prob):
        if i == len(events):
            seqs.append((path, prob)); return
        e = events[i]
        key = "-".join(path)
        ps = float(overrides.get(key, {}).get(e["id"], {}).get("p_success", e["p_success"]))
        s_path, f_path = path + ["S"], path + ["F"]
        if terminate:
            seqs.append((s_path, prob * ps))
        else:
            walk(i + 1, s_path, prob * ps)
        walk(i + 1, f_path, prob * (1 - ps))

    walk(0, [], 1.0)
    out = []
    for path, p in seqs:
        key = "-".join(path)
        meta = outcome_meta.get(key, {})
        stopped_by = events[len(path) - 1]["label"] if path[-1] == "S" else None
        out.append({"sequence": key, "path": path, "probability": p, "frequency": f0 * p,
                    "label": meta.get("label") or (f"Stopped by {stopped_by}" if stopped_by else "All barriers failed"),
                    "severity": meta.get("severity")})
    total = sum(o["probability"] for o in out)
    by_sev = {}
    for o in out:
        if o["severity"]:
            by_sev[o["severity"]] = by_sev.get(o["severity"], 0.0) + o["frequency"]
    return {"engine_version": ENGINE_VERSION, "initiating_frequency": f0, "unit": ie.get("unit", "per year"),
            "sequences": out, "probability_check": total, "frequency_by_severity": by_sev,
            "worst_sequence": out[-1] if out else None}
