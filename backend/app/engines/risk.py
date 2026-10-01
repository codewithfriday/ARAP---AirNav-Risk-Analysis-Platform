"""Risk classification scheme engine (Manual Chapter 3).

The scheme is configuration data: severity levels, likelihood levels with optional
quantitative bands, the matrix regions and the acceptance authority per region.
"""
from __future__ import annotations

import math
from typing import Any

ENGINE_VERSION = "risk-1.0.0"

DEFAULT_SCHEME: dict[str, Any] = {
    "version": 1,
    "severity": [
        {"code": "A", "name": "Catastrophic", "name_id": "Katastrofik"},
        {"code": "B", "name": "Hazardous", "name_id": "Berbahaya"},
        {"code": "C", "name": "Major", "name_id": "Mayor"},
        {"code": "D", "name": "Minor", "name_id": "Minor"},
        {"code": "E", "name": "Negligible", "name_id": "Dapat diabaikan"},
    ],
    # quantitative bands per operating hour: lower bound inclusive, upper bound exclusive
    "likelihood": [
        {"level": 5, "name": "Frequent", "name_id": "Sering", "lower": 1e-3, "upper": None},
        {"level": 4, "name": "Occasional", "name_id": "Kadang-kadang", "lower": 1e-5, "upper": 1e-3},
        {"level": 3, "name": "Remote", "name_id": "Jarang", "lower": 1e-7, "upper": 1e-5},
        {"level": 2, "name": "Improbable", "name_id": "Tidak mungkin", "lower": 1e-9, "upper": 1e-7},
        {"level": 1, "name": "Extremely improbable", "name_id": "Sangat tidak mungkin", "lower": None, "upper": 1e-9},
    ],
    "quantitative_unit": "per operating hour",
    "regions": [
        {"key": "intolerable", "name": "Intolerable", "color": "#B23A3A", "authority": None,
         "action": "Do not introduce or continue; redesign or add controls.",
         "cells": ["5A", "5B", "5C", "4A", "4B", "3A"]},
        {"key": "tolerable_upper", "name": "Tolerable (upper)", "color": "#D98E04",
         "authority": "Accountable Executive", "action": "Additional controls; ALARP justification; monitoring plan.",
         "cells": ["5D", "4C", "3B", "2A"]},
        {"key": "tolerable_lower", "name": "Tolerable (lower)", "color": "#E3B23C",
         "authority": "Director of Operations / Engineering", "action": "Mitigate where reasonably practicable; document ALARP.",
         "cells": ["5E", "4D", "4E", "3C", "3D", "2B", "2C", "1A"]},
        {"key": "acceptable", "name": "Acceptable", "color": "#3C8D5A", "authority": "Unit / branch manager",
         "action": "Accept; monitor.", "cells": ["3E", "2D", "2E", "1B", "1C", "1D", "1E"]},
    ],
    # ordering from worst to best, used for "highest region" logic
    "region_order": ["intolerable", "tolerable_upper", "tolerable_lower", "acceptable"],
}


def _atsb_cells():
    """ATSB 6×6 (Guidelines — Analysis v1.07 p.173). The published colours are not available in text form; NAVRAP assigns the
    cells by the same pattern as the AirNav 5×5, scaled to 6×6: rank sum r = likelihood (1–6) + consequence (F=1 … A=6);
    critical r ≥ 10; significant 6 ≤ r ≤ 9, shaded upper (8–9) and lower (6–7) like AirNav's tolerable bands;
    broadly acceptable r ≤ 5. Every Catastrophic (B) and Very large vehicle catastrophic (A) cell is at least significant,
    as ATSB requires (p.166)."""
    cons = "FEDCBA"
    out = {"critical": [], "significant_upper": [], "significant_lower": [], "broadly_acceptable": []}
    for lk in range(1, 7):
        for i, c in enumerate(cons, 1):
            r = lk + i
            key = ("critical" if r >= 10 else "significant_upper" if r >= 8 else "significant_lower" if r >= 6 else "broadly_acceptable")
            out[key].append(f"{lk}{c}")
    return out


_AC = _atsb_cells()
ATSB_SCHEME: dict[str, Any] = {
    "version": "ATSB-1.07",
    "key": "atsb",
    "name": "ATSB 6×6 (safety issues)",
    "severity": [
        {"code": "A", "name": "Very large vehicle catastrophic", "short": "V. large catastrophic",
         "description": "As catastrophic, for very large passenger-carrying operations (>100 people exposed). Property damage >$500 million."},
        {"code": "B", "name": "Catastrophic", "description": "Fatalities to a significant proportion of occupants; loss of aircraft; all safety margins lost. Property >$50 million."},
        {"code": "C", "name": "Hazardous", "description": "Serious or fatal injury to a small proportion of occupants; major damage; large reduction in safety margin. Property >$5 million."},
        {"code": "D", "name": "Major", "description": "Minor injuries, occasional serious injury, physical distress to occupants. Property >$500,000."},
        {"code": "E", "name": "Minor", "description": "No injuries or damage likely; slight reduction in safety margins or functional capabilities. Property >$50,000."},
        {"code": "F", "name": "Negligible", "description": "Little consequence on safety margins. Property <$50,000."},
    ],
    "likelihood": [
        {"level": 6, "name": "Very frequent", "description": "Very likely to occur many times (occurring all the time)", "indicative": "at least 10 times a year"},
        {"level": 5, "name": "Frequent", "description": "Likely to occur many times (has occurred frequently)", "indicative": "at least once a year"},
        {"level": 4, "name": "Occasional", "description": "Likely to occur sometimes (has occurred infrequently)", "indicative": "at least once every 10 years"},
        {"level": 3, "name": "Remote", "description": "Unlikely to occur, but possible (has occurred rarely)", "indicative": "at least once every 100 years"},
        {"level": 2, "name": "Improbable", "description": "Very unlikely to occur (not known to have occurred)", "indicative": "at least once every 1,000 years"},
        {"level": 1, "name": "Extremely improbable", "description": "Almost inconceivable that the event will occur", "indicative": "virtually never"},
    ],
    "quantitative_unit": "per year (exposure × frequency)",
    "regions": [
        {"key": "critical", "name": "Critical safety issue", "level": "critical", "color": "#B23A3A", "authority": None,
         "action": "Communicate immediately; obtain safety action as soon as possible; recommendation if not reduced below critical.", "cells": _AC["critical"]},
        {"key": "significant_upper", "name": "Significant safety issue (near critical)", "level": "significant", "color": "#D98E04", "authority": "Accountable Executive",
         "action": "Communicate as soon as possible; action before the final report (interim report); recommendation if not ALARP.", "cells": _AC["significant_upper"]},
        {"key": "significant_lower", "name": "Significant safety issue", "level": "significant", "color": "#E3B23C", "authority": "Director of Operations / Engineering",
         "action": "Communicate; follow up through regular liaison; recommendation with the final report if not ALARP.", "cells": _AC["significant_lower"]},
        {"key": "broadly_acceptable", "name": "Broadly acceptable — not a safety issue", "level": "broadly_acceptable", "color": "#3C8D5A",
         "authority": "Unit / branch manager", "action": "Not a safety issue; report any action as 'other safety action'.", "cells": _AC["broadly_acceptable"]},
    ],
    "region_order": ["critical", "significant_upper", "significant_lower", "broadly_acceptable"],
}

# AirNav region → ATSB safety-issue level, so a safety issue can be rated on either matrix
AIRNAV_TO_ATSB_LEVEL = {"intolerable": "critical", "tolerable_upper": "significant", "tolerable_lower": "significant", "acceptable": "broadly_acceptable"}
ISSUE_LEVEL_NAME = {"critical": "Critical", "significant": "Significant", "broadly_acceptable": "Broadly acceptable"}


def classify_issue(scheme_key: str, severity: str, likelihood: int, airnav: dict | None = None) -> dict:
    """Rate a potential safety issue on the AirNav 5×5 or the ATSB 6×6; both give an ATSB safety-issue level."""
    if scheme_key == "atsb":
        r = classify(severity, int(likelihood), ATSB_SCHEME)
        level = next(x["level"] for x in ATSB_SCHEME["regions"] if x["key"] == r["region"])
    else:
        r = classify(severity, int(likelihood), airnav or DEFAULT_SCHEME)
        level = AIRNAV_TO_ATSB_LEVEL.get(r["region"], "significant")
    return {**r, "scheme": scheme_key, "issue_level": level, "issue_level_name": ISSUE_LEVEL_NAME[level]}


def classify(severity: str, likelihood: int, scheme: dict | None = None) -> dict:
    scheme = scheme or DEFAULT_SCHEME
    severity = severity.upper()
    if severity not in {s["code"] for s in scheme["severity"]}:
        raise ValueError(f"unknown severity {severity}")
    if likelihood not in {l["level"] for l in scheme["likelihood"]}:
        raise ValueError(f"unknown likelihood {likelihood}")
    index = f"{likelihood}{severity}"
    for r in scheme["regions"]:
        if index in r["cells"]:
            return {"index": index, "region": r["key"], "region_name": r["name"], "color": r["color"],
                    "authority": r["authority"], "action": r["action"], "acceptable_to_approve": r["authority"] is not None}
    raise ValueError(f"cell {index} not mapped to a region")


def likelihood_from_frequency(value: float, unit: str | None = None, scheme: dict | None = None) -> dict:
    """Map a frequency/probability onto a likelihood level using the quantitative bands."""
    scheme = scheme or DEFAULT_SCHEME
    if unit is not None and unit != scheme["quantitative_unit"]:
        raise ValueError(f"unit '{unit}' is not comparable with scheme unit '{scheme['quantitative_unit']}'")
    if value < 0 or math.isnan(value):
        raise ValueError("frequency must be non-negative")
    for l in scheme["likelihood"]:
        lo = l["lower"] if l["lower"] is not None else -math.inf
        hi = l["upper"] if l["upper"] is not None else math.inf
        if lo <= value < hi:
            return {"level": l["level"], "name": l["name"], "unit": scheme["quantitative_unit"]}
    raise ValueError("value outside all bands")


def safety_objective(severity: str, target_region: str = "tolerable_lower", scheme: dict | None = None) -> dict:
    """FHA: the maximum frequency (upper band limit) at which a failure condition of this
    severity stays at or better than the target region (Manual §12.3)."""
    scheme = scheme or DEFAULT_SCHEME
    order = scheme["region_order"]
    if target_region not in order:
        raise ValueError("unknown region")
    ok = set(order[order.index(target_region):])
    best = None
    for l in sorted(scheme["likelihood"], key=lambda x: -x["level"]):  # from most to least frequent
        if classify(severity, l["level"], scheme)["region"] in ok:
            best = l
            break
    if best is None:
        return {"severity": severity, "max_frequency": None, "likelihood_level": None,
                "note": "No likelihood level reaches the target region"}
    return {"severity": severity, "likelihood_level": best["level"], "max_frequency": best["upper"],
            "unit": scheme["quantitative_unit"], "target_region": target_region}


def worst_region(regions: list[str], scheme: dict | None = None) -> str | None:
    scheme = scheme or DEFAULT_SCHEME
    order = scheme["region_order"]
    present = [r for r in regions if r in order]
    return min(present, key=order.index) if present else None
