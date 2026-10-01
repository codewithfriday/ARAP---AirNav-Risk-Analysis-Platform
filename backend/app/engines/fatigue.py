"""Three-process model of alertness (Manual Chapter 15, SRS §5.1).

Simplified Åkerstedt–Folkard model with the parameters reported by Ingre et al. (2014).
Times are hours from 00:00 on day 1. Sleep periods are [start, end) intervals.
Results are group-average predictions, not a measure of an individual's fatigue.
"""
from __future__ import annotations

import math

ENGINE_VERSION = "fatigue-1.0.0"

DEFAULTS = {"la": 2.4, "ha": 14.3, "d": -0.0353, "g": -0.381, "ca": 2.5, "p": 16.8,
            "wc": -5.72, "wd": -1.51, "kss_a": 10.6, "kss_b": -0.6, "s0": 13.0,
            "brake": False, "bl": 12.2, "ultradian": False, "ua": 0.5, "um": -0.5}
NOTICE = ("Model predictions are group averages for healthy adults; they are not a measure "
          "of an individual's fatigue and do not account for workload, caffeine or sleep disorders.")


def simulate(sleeps: list[list[float]], start: float, end: float, step_minutes: float = 5.0,
             params: dict | None = None, initial_awake_hours: float = 2.0) -> list[dict]:
    p = {**DEFAULTS, **(params or {})}
    dt = step_minutes / 60.0
    n = int(round((end - start) / dt))
    S = p["s0"]
    asleep_prev = None
    wake_t = start - initial_awake_hours
    out = []
    for i in range(n):
        t = start + i * dt
        asleep = any(a <= t < b for a, b in sleeps)
        if asleep:
            if p["brake"] and S >= p["bl"]:
                # braked recovery: slower approach above the brake level (approximation of the braked form)
                S = p["ha"] - (p["ha"] - S) * math.exp(p["g"] * 0.5 * dt)
            else:
                S = p["ha"] - (p["ha"] - S) * math.exp(p["g"] * dt)
        else:
            if asleep_prev:
                wake_t = t
            S = p["la"] + (S - p["la"]) * math.exp(p["d"] * dt)
        C = p["ca"] * math.cos(math.pi * (t - p["p"]) / 12)
        U = p["ua"] * math.cos(math.pi * (t - p["p"] - 3) / 6) + p["um"] if p["ultradian"] else 0.0
        W = 0.0 if asleep else p["wc"] * math.exp(p["wd"] * (t - wake_t))
        A = S + C + U + W
        out.append({"t": round(t, 6), "asleep": asleep, "S": S, "C": C, "W": W,
                    "alertness": None if asleep else A,
                    "kss": None if asleep else p["kss_a"] + p["kss_b"] * A})
        asleep_prev = asleep
    return out


def duty_indicators(series: list[dict], duty: list[float], kss_threshold: float = 7.0) -> dict:
    a, b = duty
    pts = [x for x in series if a <= x["t"] < b and x["alertness"] is not None]
    if not pts:
        return {"duty": duty, "note": "no awake points in duty"}
    mn = min(pts, key=lambda x: x["alertness"])
    share = sum(1 for x in pts if x["kss"] >= kss_threshold) / len(pts)
    dt = (pts[1]["t"] - pts[0]["t"]) if len(pts) > 1 else 0
    h = mn["t"] % 24
    return {"duty": duty, "min_alertness": mn["alertness"], "min_time_hours": mn["t"],
            "min_clock": f"{int(h):02d}:{int(round((h % 1) * 60)) % 60:02d}",
            "max_kss": max(x["kss"] for x in pts), "share_at_or_above_threshold": share,
            "hours_at_or_above_threshold": share * len(pts) * dt, "kss_threshold": kss_threshold}


def run(sleeps, duties, start=0.0, end=None, step_minutes=5.0, params=None, kss_threshold=7.0) -> dict:
    end = end if end is not None else max([b for _, b in (sleeps + duties)] + [start + 24])
    series = simulate(sleeps, start, end, step_minutes, params)
    return {"engine_version": ENGINE_VERSION, "notice": NOTICE, "params": {**DEFAULTS, **(params or {})},
            "series": series, "duties": [duty_indicators(series, d, kss_threshold) for d in duties]}


# ------------------------------------------------------------------ Samn-Perelli fatigue checklist (pre-shift self-rating)
# A 7-point self-rating of mental exhaustion and cognitive slowing (Samn & Perelli, 1982). It complements the
# three-process model: the model predicts group-average alertness for a roster; the rating captures how the
# individual controller feels before taking a position.
SP_VERSION = "samn-perelli-1.0.0"
SP_SCALE = [
    (1, "Fully alert, wide awake"),
    (2, "Very lively, responsive, but not at peak"),
    (3, "Okay, somewhat fresh"),
    (4, "A little tired, less than fresh"),
    (5, "Moderately tired, let down"),
    (6, "Extremely tired, very difficult to concentrate"),
    (7, "Completely exhausted, unable to function"),
]
SP_LIGHTS = [
    {"key": "green", "name": "Green light", "scores": [1, 2, 3], "color": "#3C8D5A", "min_outcome": 0,
     "action": "The controller can proceed to their shift normally."},
    {"key": "caution", "name": "Caution light", "scores": [4], "color": "#E3B23C", "min_outcome": 1,
     "action": "The supervisor assigns the controller to a standard position (avoiding highly complex, high-traffic sectors) "
               "and schedules their break slightly earlier."},
    {"key": "amber", "name": "Amber light", "scores": [5], "color": "#D98E04", "min_outcome": 2,
     "action": "Immediate mitigation before the controller takes over a position — for example a mandatory 15-minute walk, "
               "a dose of caffeine, or adjusting the rotation schedule."},
    {"key": "red", "name": "Red light", "scores": [6, 7], "color": "#B23A3A", "min_outcome": 3,
     "action": "The controller is an operational risk: pull them from active control duties, place them on administrative "
               "desk tasks, or send them home to rest."},
]
# outcomes recorded by the supervisor, ranked by how much they reduce exposure
SP_OUTCOMES = [
    ("normal", "Proceeded to the shift normally", 0),
    ("standard", "Standard position, earlier break", 1),
    ("mitigated", "Mitigated before taking a position", 2),
    ("admin", "Removed from control — administrative desk tasks", 3),
    ("home", "Removed from control — sent home to rest", 3),
]
SP_MITIGATIONS = ["Mandatory 15-minute walk", "Caffeine", "Rotation schedule adjusted", "Break taken earlier", "Paired with another controller"]


def sp_light(score: int) -> dict:
    for l in SP_LIGHTS:
        if score in l["scores"]:
            return l
    raise ValueError(f"Samn-Perelli score must be 1–7, got {score}")


def samn_perelli(ratings: list[dict]) -> dict:
    """Classify pre-shift Samn-Perelli ratings and check the supervisor's recorded response against the action thresholds."""
    rank = {k: r for k, _, r in SP_OUTCOMES}
    label = dict((k, n) for k, n, _ in SP_OUTCOMES)
    rows, checks = [], []
    counts = {l["key"]: 0 for l in SP_LIGHTS}
    dist = {s: 0 for s, _ in SP_SCALE}
    for r in ratings:
        sc = r.get("score")
        if sc in (None, ""):
            rows.append({"id": r.get("id"), "light": None}); continue
        sc = int(sc)
        l = sp_light(sc)
        counts[l["key"]] += 1; dist[sc] += 1
        out = r.get("outcome") or ""
        ok = None if not out else rank.get(out, -1) >= l["min_outcome"]
        who = r.get("controller") or r.get("id") or "rating"
        if out and not ok:
            sev = "error" if l["key"] == "red" else "warning"
            checks.append({"severity": sev, "ref": r.get("id"), "code": "sp_response",
                           "message": f"{who}: score {sc} ({l['name']}) but recorded '{label.get(out, out)}' — {l['action']}"})
        if not out and l["key"] != "green":
            checks.append({"severity": "warning" if l["key"] in ("amber", "red") else "info", "ref": r.get("id"), "code": "sp_open",
                           "message": f"{who}: score {sc} ({l['name']}) — record the supervisor's response. {l['action']}"})
        if l["key"] == "amber" and out == "mitigated" and not r.get("mitigations"):
            checks.append({"severity": "info", "ref": r.get("id"), "code": "sp_mitigation",
                           "message": f"{who}: record which mitigation was applied before taking the position"})
        rows.append({"id": r.get("id"), "score": sc, "description": dict(SP_SCALE)[sc], "light": l["key"], "light_name": l["name"],
                     "color": l["color"], "required_action": l["action"], "response_ok": ok})
    n = sum(counts.values())
    order = {"error": 0, "warning": 1, "info": 2}
    checks.sort(key=lambda c: order[c["severity"]])
    return {"engine_version": SP_VERSION, "rows": rows, "counts": counts, "distribution": dist, "n": n,
            "share_not_green": (n - counts["green"]) / n if n else 0.0,
            "mean_score": (sum(s * k for s, k in dist.items()) / n) if n else None, "checks": checks}


def sp_meta() -> dict:
    return {"scale": [{"score": s, "description": d} for s, d in SP_SCALE], "lights": SP_LIGHTS,
            "outcomes": [{"key": k, "name": n, "rank": r} for k, n, r in SP_OUTCOMES], "mitigations": SP_MITIGATIONS,
            "version": SP_VERSION}
