"""Collision risk modelling — Reich model (ICAO Doc 9689, Doc 9574).

Occupancy form, as used in ICAO regional monitoring agency reports:

    N = P_s(S) · P_o(0) · (λx / Sx) · { E_same · [ |Δv|/(2λx) + |v_o|/(2λ_o) + |v_s|/(2λ_s) ]
                                       + E_opp  · [ 2|v|/(2λx) + |v_o|/(2λ_o) + |v_s|/(2λ_s) ] }

For vertical risk (RVSM):  P_s(S)=P_z(S_z), P_o(0)=P_y(0), v_o=ẏ (lateral), v_s=ż (vertical).
For lateral risk (parallel routes): P_s(S)=P_y(S_y), P_o(0)=P_z(0), v_o=ż, v_s=ẏ(S_y).

Units: λ and Sx in NM, speeds in knots → N in fatal accidents per flight hour
(the occupancy definition counts both aircraft of a pair, so no further factor of 2 is applied).
"""
from __future__ import annotations

import math

ENGINE_VERSION = "crm-1.0.0"
FT_PER_NM = 6076.12

TLS = {"rvsm_technical": 2.5e-9, "rvsm_total": 5e-9, "lateral": 5e-9, "longitudinal": 5e-9}


def reich(p_sep: float, p_other0: float, lx: float, l_other: float, l_sep: float, sx: float,
          e_same: float, e_opp: float, dv: float, v: float, v_other: float, v_sep: float) -> dict:
    for name, val in (("lambda_x", lx), ("lambda_other", l_other), ("lambda_sep", l_sep), ("S_x", sx)):
        if val <= 0:
            raise ValueError(f"{name} must be positive")
    if not (0 <= p_sep <= 1 and 0 <= p_other0 <= 1):
        raise ValueError("overlap probabilities must be in [0,1]")
    same_terms = abs(dv) / (2 * lx) + abs(v_other) / (2 * l_other) + abs(v_sep) / (2 * l_sep)
    opp_terms = 2 * abs(v) / (2 * lx) + abs(v_other) / (2 * l_other) + abs(v_sep) / (2 * l_sep)
    base = p_sep * p_other0 * (lx / sx)
    same = base * e_same * same_terms
    opp = base * e_opp * opp_terms
    return {"same_direction": same, "opposite_direction": opp, "total": same + opp}


def vertical(pz_sz: float, py0: float, lx: float, ly: float, lz: float, sx: float, ez_same: float, ez_opp: float,
             dv: float, v: float, ydot: float, zdot: float, tls: float = TLS["rvsm_technical"]) -> dict:
    r = reich(pz_sz, py0, lx, ly, lz, sx, ez_same, ez_opp, dv, v, ydot, zdot)
    return {"engine_version": ENGINE_VERSION, "dimension": "vertical", **r, "tls": tls,
            "meets_tls": r["total"] <= tls, "ratio_to_tls": r["total"] / tls}


def lateral(py_sy: float, pz0: float, lx: float, ly: float, lz: float, sx: float, ey_same: float, ey_opp: float,
            dv: float, v: float, zdot: float, ydot_sy: float, tls: float = TLS["lateral"]) -> dict:
    r = reich(py_sy, pz0, lx, lz, ly, sx, ey_same, ey_opp, dv, v, zdot, ydot_sy)
    return {"engine_version": ENGINE_VERSION, "dimension": "lateral", **r, "tls": tls,
            "meets_tls": r["total"] <= tls, "ratio_to_tls": r["total"] / tls}


def lateral_overlap(spacing: float, lam_y: float, model: str, scale: float) -> float:
    """P_y(S_y) ≈ 2 λy · f_d(S_y), where f_d is the density of the difference of two independent
    lateral deviations. model='gaussian': each deviation N(0, σ²) with σ=scale;
    model='laplace': each deviation double-exponential with scale b=scale."""
    if scale <= 0:
        raise ValueError("scale must be positive")
    d = abs(spacing)
    if model == "gaussian":
        s = math.sqrt(2) * scale
        f = math.exp(-0.5 * (d / s) ** 2) / (s * math.sqrt(2 * math.pi))
    elif model == "laplace":
        b = scale
        f = (1 + d / b) * math.exp(-d / b) / (4 * b)
    else:
        raise ValueError("model must be gaussian or laplace")
    return min(1.0, 2 * lam_y * f)


def spacing_curve(lam_y: float, model: str, scale: float, spacings: list[float], other: dict) -> list[dict]:
    out = []
    for s in spacings:
        py = lateral_overlap(s, lam_y, model, scale)
        r = lateral(py, other["pz0"], other["lx"], lam_y, other["lz"], other["sx"], other["ey_same"], other["ey_opp"],
                    other["dv"], other["v"], other["zdot"], other["ydot_sy"], other.get("tls", TLS["lateral"]))
        out.append({"spacing": s, "py_sy": py, "risk": r["total"]})
    return out


def minimum_spacing(lam_y: float, model: str, scale: float, other: dict, lo: float = 0.5, hi: float = 200.0) -> dict:
    """Smallest route spacing (NM) at which lateral risk meets the TLS (risk decreases with spacing)."""
    tls = other.get("tls", TLS["lateral"])
    f = lambda s: lateral(lateral_overlap(s, lam_y, model, scale), other["pz0"], other["lx"], lam_y, other["lz"],
                          other["sx"], other["ey_same"], other["ey_opp"], other["dv"], other["v"], other["zdot"],
                          other["ydot_sy"], tls)["total"]
    if f(hi) > tls:
        return {"minimum_spacing": None, "note": f"TLS not met even at {hi} NM"}
    if f(lo) <= tls:
        return {"minimum_spacing": lo, "risk": f(lo), "tls": tls}
    for _ in range(80):
        mid = (lo + hi) / 2
        if f(mid) > tls:
            lo = mid
        else:
            hi = mid
    return {"minimum_spacing": hi, "risk": f(hi), "tls": tls}
