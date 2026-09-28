"""Occurrence risk classification.

* ARMS Event Risk Classification (ERC) — ARMS Working Group (2010).
* EUROCONTROL Risk Analysis Tool (RAT) scoring — severity = risk of collision + controllability.
  The official RAT look-up table that maps the scores to severity classes A–E is published by
  EUROCONTROL and is not embedded here; ARAP computes the scores and the analyst records the class.
"""
from __future__ import annotations

ENGINE_VERSION = "orc-1.0.0"

ERC_OUTCOMES = ["Catastrophic accident", "Major accident", "Minor injuries or damage", "No accident outcome"]
ERC_BARRIERS = ["Effective", "Limited", "Minimal", "Not effective"]
ERC_MATRIX = [[50, 102, 502, 2500], [10, 21, 101, 500], [2, 4, 20, 100], [1, 1, 1, 1]]
ERC_BANDS = [(100, "red", "High — investigate and take action immediately"),
             (20, "amber", "Medium — consider investigation or request more information"),
             (0, "green", "Low — record in the database; use for trend analysis")]


def erc(outcome: str, barriers: str, bands=ERC_BANDS) -> dict:
    if outcome not in ERC_OUTCOMES or barriers not in ERC_BARRIERS:
        raise ValueError("unknown outcome or barrier-effectiveness category")
    v = ERC_MATRIX[ERC_OUTCOMES.index(outcome)][ERC_BARRIERS.index(barriers)]
    for threshold, colour, meaning in bands:
        if v >= threshold:
            return {"engine_version": ENGINE_VERSION, "method": "ARMS ERC", "risk_index": v, "band": colour,
                    "meaning": meaning, "outcome": outcome, "barriers": barriers}
    raise ValueError("no band")


RAT_ITEMS = {
    "separation": {"label": "Minimum separation achieved", "options": {
        "not_infringed": ("Separation ≥ minimum", 0), "over75": ("> 75% of minimum", 1), "50_75": ("> 50% and ≤ 75%", 3),
        "25_50": ("> 25% and ≤ 50%", 7), "under25": ("≤ 25% of minimum", 10)}},
    "closure": {"label": "Rate of closure", "options": {
        "none": ("None", 0), "low": ("Low (≤ 85 kt, ≤ 1000 ft/min)", 1), "medium": ("Medium (≤ 205 kt, ≤ 2000 ft/min)", 2),
        "high": ("High (≤ 700 kt, ≤ 4000 ft/min)", 4), "very_high": ("Very high (> 700 kt, > 4000 ft/min)", 5)}},
    "detection": {"label": "Conflict detection (ATM ground)", "ground": True, "options": {
        "detected": ("Detected", 0), "late": ("Detected late", 1), "not_detected": ("Not detected", 2), "na": ("Not applicable", 0)}},
    "planning": {"label": "Planning (ATM ground)", "ground": True, "options": {
        "correct": ("Plan correct", 0), "inadequate": ("Plan inadequate", 1), "none": ("No plan", 2), "na": ("Not applicable", 0)}},
    "execution": {"label": "Execution", "ground": True, "options": {
        "correct": ("Execution correct", 0), "inadequate": ("Execution inadequate", 1), "none": ("No execution", 2), "na": ("Not applicable", 0)}},
    "ground_safety_net": {"label": "Ground safety net (STCA / MSAW / APW)", "ground": True, "options": {
        "triggered": ("Triggered", 0), "not_triggered": ("Not triggered", 2), "na": ("Not applicable", 0)}},
    "recovery": {"label": "Recovery", "ground": True, "options": {
        "correct": ("Recovery correct", 0), "inadequate": ("Recovery inadequate", 1), "none": ("No recovery / worsened", 2), "na": ("Not applicable", 0)}},
    "airborne_safety_net": {"label": "Airborne safety net / pilot initiative", "options": {
        "effective": ("TCAS/GPWS or see-and-avoid effective", 0), "none": ("No RA / warning", 2), "na": ("Not applicable", 0)}},
}


def rat(answers: dict, items: dict = RAT_ITEMS) -> dict:
    rows, roc, ctrl, ground = [], 0, 0, 0
    for key, item in items.items():
        a = answers.get(key)
        if a is None:
            continue
        if a not in item["options"]:
            raise ValueError(f"invalid answer for {key}")
        pts = item["options"][a][1]
        if key in ("separation", "closure"):
            roc += pts
        else:
            ctrl += pts
            if item.get("ground"):
                ground += pts
        rows.append({"item": key, "label": item["label"], "answer": item["options"][a][0], "points": pts})
    return {"engine_version": ENGINE_VERSION, "method": "RAT scoring", "risk_of_collision": roc, "controllability": ctrl,
            "severity_score": roc + ctrl, "atm_ground_controllability": ground, "rows": rows,
            "note": "Assign the ESARR 2 severity class (A–E) with the EUROCONTROL RAT look-up table."}
