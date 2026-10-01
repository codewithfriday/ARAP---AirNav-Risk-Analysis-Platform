"""Species-based wildlife strike risk assessment (Manual ch. 31).

Structure after Allan (2006), as used in UK CAA CAP 772: each species (or species group) is rated separately.
  • Likelihood — mean number of strikes per year with that species over the review period.
  • Severity   — share of that species' strikes that caused damage or had an effect on flight.
                 With too few strikes for a stable percentage, a surrogate from body mass and flocking is used.
  • Risk       — likelihood class × severity class, banded high / moderate / low.
The default bands below are NAVRAP defaults in the style of that method; every aerodrome should calibrate them.
"""
from __future__ import annotations

ENGINE_VERSION = "wildlife-1.0.0"

LABELS = {5: "Very high", 4: "High", 3: "Moderate", 2: "Low", 1: "Very low"}

DEFAULT_BANDS = {
    # lower bounds for classes 5..2 (anything below the last is class 1)
    "likelihood_per_year": [10.0, 3.0, 1.0, 0.3],      # >10, 3–10, 1–3, 0.3–1, <0.3 strikes per year
    "severity_damage_pct": [20.0, 10.0, 5.0, 1.0],     # >20%, 10–20%, 5–10%, 1–5%, <1% damaging / effect on flight
    "surrogate_mass_kg": [1.8, 1.0, 0.3, 0.1],         # ≥1.8, 1–1.8, 0.3–1, 0.1–0.3, <0.1 kg
    "risk_high": 12,                                  # likelihood × severity ≥ 12 → high
    "risk_moderate": 6,                               # 6–11 → moderate, ≤ 5 → low
    "min_strikes_for_data_severity": 5,
}


def _cls(value: float, bounds: list[float], strict_top: bool = True) -> int:
    """Class 5..1 from descending lower bounds. The top class is strictly greater than its bound (">10")."""
    for i, b in enumerate(bounds):
        if (value > b) if (i == 0 and strict_top) else (value >= b):
            return 5 - i
    return 1


def _slope(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else None


def analyse(model: dict) -> dict:
    bands = {**DEFAULT_BANDS, **(model.get("bands") or {})}
    years = [str(y) for y in (model.get("years") or [])]
    if not years:
        raise ValueError("define the review period (years)")
    movements = {str(k): float(v) for k, v in (model.get("movements") or {}).items() if v not in (None, "")}
    total_mov = sum(movements.get(y, 0) for y in years)
    species = model.get("species") or []
    if not species:
        raise ValueError("add at least one species")
    all_strikes = sum(sum(float((sp.get("strikes") or {}).get(y) or 0) for y in years) for sp in species)
    out = []
    for sp in species:
        s = [float((sp.get("strikes") or {}).get(y) or 0) for y in years]
        d = [float((sp.get("damaging") or {}).get(y) or 0) for y in years]
        n, nd = sum(s), sum(d)
        if nd > n:
            raise ValueError(f"{sp.get('common') or sp.get('id')}: damaging strikes exceed strikes")
        per_year = n / len(years)
        lik = _cls(per_year, bands["likelihood_per_year"])
        dmg_pct = 100 * nd / n if n else None
        if n >= bands["min_strikes_for_data_severity"]:
            sev, basis = _cls(dmg_pct, bands["severity_damage_pct"]), "strike data"
        else:
            mass = float(sp.get("mass_kg") or 0)
            sev = _cls(mass, bands["surrogate_mass_kg"], strict_top=False)
            if sp.get("flocking"):
                sev = min(5, sev + 1)
            basis = f"surrogate (mass {mass:g} kg{', flocking' if sp.get('flocking') else ''})"
        score = lik * sev
        level = "high" if score >= bands["risk_high"] else "moderate" if score >= bands["risk_moderate"] else "low"
        rate = [(s[i] / movements[y] * 1e4) if movements.get(y) else None for i, y in enumerate(years)]
        valid = [(i, r) for i, r in enumerate(rate) if r is not None]
        out.append({
            "id": sp.get("id"), "common": sp.get("common"), "scientific": sp.get("scientific"),
            "strikes": n, "damaging": nd, "per_year": per_year,
            "rate_per_10k": (n / total_mov * 1e4) if total_mov else None,
            "rate_by_year": dict(zip(years, rate)),
            "trend_per_year": _slope([i for i, _ in valid], [r for _, r in valid]),
            "damage_pct": dmg_pct, "share_pct": 100 * n / all_strikes if all_strikes else None,
            "likelihood": lik, "likelihood_label": LABELS[lik],
            "severity": sev, "severity_label": LABELS[sev], "severity_basis": basis,
            "score": score, "risk": level,
        })
    out.sort(key=lambda r: (-r["score"], -r["strikes"]))
    for i, r in enumerate(out, 1):
        r["rank"] = i
    return {"engine_version": ENGINE_VERSION, "bands": bands, "years": years, "total_strikes": all_strikes,
            "total_movements": total_mov, "rate_per_10k": (all_strikes / total_mov * 1e4) if total_mov else None,
            "species": out,
            "counts": {k: sum(1 for r in out if r["risk"] == k) for k in ("high", "moderate", "low")}}
