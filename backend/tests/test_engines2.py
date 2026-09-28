"""Reference tests for the engines added in v0.2 (SRS §9, TC-CRM … TC-SIM)."""
import math

import numpy as np
import pytest
from scipy.stats import chi2

from app import seed2 as S
from app.engines import crm, eta, hra, orc, rbd, sej, sim


# ---------------------------------------------------------------- CRM
def test_tc_crm_01_vertical_formula():
    p = S.CRM_VERTICAL
    r = crm.vertical(**p)
    base = p["pz_sz"] * p["py0"] * p["lx"] / p["sx"]
    same = base * p["ez_same"] * (p["dv"] / (2 * p["lx"]) + p["ydot"] / (2 * p["ly"]) + p["zdot"] / (2 * p["lz"]))
    opp = base * p["ez_opp"] * (2 * p["v"] / (2 * p["lx"]) + p["ydot"] / (2 * p["ly"]) + p["zdot"] / (2 * p["lz"]))
    assert math.isclose(r["total"], same + opp, rel_tol=1e-12)
    assert math.isclose(r["total"], 1.873e-9, rel_tol=1e-3) and r["meets_tls"]


def test_tc_crm_02_lateral_min_spacing():
    m, L = S.CRM_LAT_MODEL, S.CRM_LATERAL
    res = crm.minimum_spacing(m["lam_y"], m["model"], m["scale"], L)
    assert abs(res["minimum_spacing"] - 11.68) < 0.01
    assert math.isclose(res["risk"], 5e-9, rel_tol=1e-6)


def test_lateral_overlap_densities():
    # Gaussian: numeric integral of the difference density over ±λy around S equals the approximation
    sigma, lam, s = 2.0, 0.03, 5.0
    xs = np.linspace(s - lam, s + lam, 2001)
    sd = math.sqrt(2) * sigma
    exact = np.trapezoid(np.exp(-0.5 * (xs / sd) ** 2) / (sd * math.sqrt(2 * math.pi)), xs)
    assert math.isclose(crm.lateral_overlap(s, lam, "gaussian", sigma), exact, rel_tol=1e-3)
    # Laplace difference density integrates to 1
    b = 0.9
    xs = np.linspace(-60, 60, 200001)
    f = (1 + np.abs(xs) / b) * np.exp(-np.abs(xs) / b) / (4 * b)
    assert math.isclose(np.trapezoid(f, xs), 1.0, rel_tol=1e-4)
    with pytest.raises(ValueError):
        crm.lateral_overlap(5, lam, "cauchy", 1)


# ---------------------------------------------------------------- ETA
def test_tc_eta_01():
    r = eta.analyse(S.ETA_MODEL)
    f = {x["sequence"]: x["frequency"] for x in r["sequences"]}
    assert math.isclose(r["probability_check"], 1.0)
    assert math.isclose(f["S"], 0.0225) and math.isclose(f["F-S"], 0.002)
    assert math.isclose(f["F-F-S"], 4.5e-4) and math.isclose(f["F-F-F"], 5.0e-5)
    # without the dependency override the all-fail frequency equals the LOPA value 2.5e-5
    m = dict(S.ETA_MODEL); m["overrides"] = {}
    assert math.isclose({x["sequence"]: x["frequency"] for x in eta.analyse(m)["sequences"]}["F-F-F"], 2.5e-5)


def test_eta_full_tree_mode():
    m = {"initiating": {"frequency": 1}, "events": [{"id": "A", "label": "A", "p_success": 0.7}, {"id": "B", "label": "B", "p_success": 0.4}],
         "terminate_on_success": False}
    r = eta.analyse(m)
    assert len(r["sequences"]) == 4 and math.isclose(sum(x["probability"] for x in r["sequences"]), 1)


# ---------------------------------------------------------------- HRA
def test_tc_hra_01():
    heps = [hra.assess(t["library"], t["gtt"], t["epcs"])["hep"] for t in S.HRA_TASKS]
    assert math.isclose(heps[0], 0.0004 * 2.8 * 1.5 * 1.2, rel_tol=1e-12)
    assert math.isclose(heps[1], 0.005 * 4.6 * 2.5, rel_tol=1e-12)
    assert math.isclose(heps[2], 0.003 * 2.0 * 1.8, rel_tol=1e-12)
    with pytest.raises(ValueError):
        hra.assess("cara", "Z9", [])
    assert hra.assess("heart", "A", [{"code": "1", "apoa": 1}])["hep"] == 1.0   # capped


# ---------------------------------------------------------------- ERC / RAT
def test_tc_erc_01():
    got = [(orc.erc(c["outcome"], c["barriers"])["risk_index"], orc.erc(c["outcome"], c["barriers"])["band"]) for c in S.ERC_CASES]
    assert got == [(102, "red"), (50, "amber"), (1, "green")]
    assert orc.erc("Major accident", "Limited")["risk_index"] == 21
    assert orc.erc("Catastrophic accident", "Not effective")["risk_index"] == 2500


def test_tc_rat_01():
    r = orc.rat(S.RAT_CASE)
    assert (r["risk_of_collision"], r["controllability"], r["severity_score"]) == (5, 2, 7)
    with pytest.raises(ValueError):
        orc.rat({"separation": "bogus"})


# ---------------------------------------------------------------- RBD / Markov
def test_tc_rbd_01_analytic():
    a1, a2 = 20000 / 20004, 4000 / 4008
    s = {"type": "series", "children": [{"type": "block", "mtbf": 20000, "mttr": 4}, {"type": "block", "mtbf": 4000, "mttr": 8}]}
    assert math.isclose(rbd.rbd(s)["availability"], a1 * a2, rel_tol=1e-12)
    p = {"type": "parallel", "children": [{"type": "block", "mtbf": 20000, "mttr": 4}] * 2}
    assert math.isclose(rbd.rbd(p)["unavailability"], (1 - a1) ** 2, rel_tol=1e-9)
    k = {"type": "koon", "k": 2, "children": [{"type": "block", "mtbf": 20000, "mttr": 4}] * 3}
    assert math.isclose(rbd.rbd(k)["availability"], 3 * a1 ** 2 - 2 * a1 ** 3, rel_tol=1e-12)
    r = rbd.rbd(S.RBD_VHF)
    assert r["blocks"][0]["block"] == "VCCS" and abs(r["downtime_hours_per_year"] - 0.423) < 0.001


def test_tc_mkv_01():
    lam, mu = 1e-3, 0.1
    two = rbd.markov([{"id": "U", "up": True}, {"id": "D", "up": False}], [{"from": "U", "to": "D", "rate": lam}, {"from": "D", "to": "U", "rate": mu}])
    assert math.isclose(two["availability"], mu / (lam + mu), rel_tol=1e-9)
    assert math.isclose(two["mttff_hours"], 1 / lam, rel_tol=1e-9)
    r = rbd.markov(**S.MARKOV_STANDBY)
    assert math.isclose(r["unavailability"], 2.0396e-6, rel_tol=1e-3)
    assert r["unavailability"] > 40 * rbd.rbd({"type": "parallel", "children": [{"type": "block", "mtbf": 20000, "mttr": 4}] * 2})["unavailability"]


# ---------------------------------------------------------------- SEJ
def test_tc_sej_01():
    r = sej.classical(S.SEJ_EXPERTS, S.SEJ_ITEMS)
    I = 2 * 0.5 * math.log(0.5 / 0.45)
    assert math.isclose(r["experts"]["Expert A"]["calibration"], 1 - chi2.cdf(2 * 4 * I, 3), rel_tol=1e-9)
    assert r["experts"]["Expert C"]["calibration"] < 1e-3
    assert math.isclose(sum(e["weight"] for e in r["experts"].values()), 1.0)
    assert r["experts"]["Expert A"]["weight"] > r["experts"]["Expert B"]["weight"] > r["experts"]["Expert C"]["weight"]
    q = next(d for d in r["decision_maker"] if d["id"] == "Q1")["performance"]
    assert q[0] < q[1] < q[2] and abs(q[1] - 0.0815) < 0.002


def test_tc_sej_02_delphi():
    d = sej.delphi(S.DELPHI_ROUNDS)
    assert [x["median"] for x in d] == [0.1, 0.1, 0.1]
    assert d[2]["converging"] and math.isclose(d[2]["iqr"], 0.02)


# ---------------------------------------------------------------- simulation
def test_tc_sim_01():
    r = {x["id"]: x for x in sim.analyse(S.SIM_MEASURES)}
    v = np.array(S.SIM_MEASURES[0]["solution"])
    assert math.isclose(r["M1"]["solution"]["mean"], v.mean())
    assert r["M1"]["criterion_met"] and r["M2"]["criterion_met"] and r["M3"]["criterion_met"]
    assert r["M1"]["p_value"] < 0.001


def test_wildlife_species_matrix_cattle_egret():
    """Manual §31.4 / TC-WLD-01: Bubulcus ibis 62 strikes in 5 years, 7 damaging → L5 × S4 = 20, high, ranked first."""
    from app.engines import wildlife
    from app.seed_wildlife import WILDLIFE_MODEL
    r = wildlife.analyse(WILDLIFE_MODEL)
    eg = r["species"][0]
    assert eg["scientific"] == "Bubulcus ibis" and eg["rank"] == 1
    assert eg["per_year"] == 12.4 and abs(eg["damage_pct"] - 11.29) < 0.01
    assert (eg["likelihood"], eg["severity"], eg["score"], eg["risk"]) == (5, 4, 20, "high")
    assert abs(eg["rate_per_10k"] - 1.896) < 1e-3
    by = {x["scientific"]: x for x in r["species"]}
    # few strikes → body-mass surrogate: 1.0 kg → class 4, flocking +1 → 5
    assert by["Pteropus vampyrus"]["severity"] == 5 and by["Pteropus vampyrus"]["severity_basis"].startswith("surrogate")
    assert by["Hirundo rustica"]["risk"] == "low" and by["Ardeola speciosa"]["score"] == 8
    assert r["counts"] == {"high": 1, "moderate": 3, "low": 2}
    assert abs(r["rate_per_10k"] - 6.972) < 1e-3
