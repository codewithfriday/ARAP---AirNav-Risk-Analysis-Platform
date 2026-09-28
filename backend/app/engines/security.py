"""Security risk scoring (ISO/IEC 27005 style): risk = likelihood × impact, impact = max(C, I, A), each 1–5."""
ENGINE_VERSION = "security-1.0.0"
LEVELS = [(15, "Very high"), (10, "High"), (5, "Medium"), (1, "Low")]


def score(likelihood: int, c: int, i: int, a: int) -> dict:
    for x in (likelihood, c, i, a):
        if not 1 <= int(x) <= 5:
            raise ValueError("likelihood and C/I/A impacts must be 1–5")
    impact = max(int(c), int(i), int(a))
    s = int(likelihood) * impact
    level = next(name for t, name in LEVELS if s >= t)
    return {"engine_version": ENGINE_VERSION, "impact": impact, "score": s, "level": level}
