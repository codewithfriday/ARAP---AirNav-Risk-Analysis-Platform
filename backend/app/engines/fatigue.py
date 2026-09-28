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
