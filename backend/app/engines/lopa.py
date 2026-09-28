"""Layer of Protection Analysis (Manual Chapter 11, SRS §5.3)."""
from __future__ import annotations

import math

ENGINE_VERSION = "lopa-1.0.0"
CRITERIA = ("independent", "effective", "dependable", "auditable")


def analyse(initiating_frequency: float, conditional_modifiers: list[dict] | None, safeguards: list[dict],
            target_frequency: float, unit: str = "per year") -> dict:
    if initiating_frequency < 0 or target_frequency <= 0:
        raise ValueError("frequencies must be positive")
    steps = [{"label": "Initiating event", "factor": None, "frequency": initiating_frequency}]
    f = initiating_frequency
    for cm in conditional_modifiers or []:
        p = float(cm["probability"])
        if not 0 <= p <= 1:
            raise ValueError("conditional modifier must be a probability")
        f *= p
        steps.append({"label": cm.get("label", "Conditional modifier"), "factor": p, "frequency": f})
    credited, rejected = [], []
    deps: dict[str, list[str]] = {}
    for sg in safeguards:
        missing = [c for c in CRITERIA if not sg.get(c)]
        if missing:
            rejected.append({"label": sg.get("label"), "missing_criteria": missing})
            continue
        pfd = float(sg["pfd"])
        if not 0 < pfd <= 1:
            raise ValueError("PFD must be in (0,1]")
        f *= pfd
        credited.append(sg.get("label"))
        steps.append({"label": sg.get("label", "IPL"), "factor": pfd, "frequency": f})
        for d in sg.get("dependencies") or []:
            deps.setdefault(d, []).append(sg.get("label"))
    warnings = [f"IPLs {', '.join(v)} share dependency '{k}' — independence must be justified"
                for k, v in deps.items() if len(v) > 1]
    ratio = f / target_frequency
    return {"engine_version": ENGINE_VERSION, "mitigated_frequency": f, "unit": unit, "target_frequency": target_frequency,
            "ratio_to_target": ratio, "target_met": f <= target_frequency,
            "additional_risk_reduction_required": max(1.0, ratio),
            "additional_orders_of_magnitude": max(0.0, math.log10(ratio)) if ratio > 0 else 0.0,
            "steps": steps, "credited_ipls": credited, "rejected_safeguards": rejected, "warnings": warnings}
