"""Reference test cases — SRS Section 9. The engines must reproduce the Manual's worked examples."""
import math

import pytest

from app.engines import bbn, fatigue, fmea, fta, lopa, risk
from app.seed import BBN_NET, FTA_TREE


# ---------------------------------------------------------------- risk
def test_tc_risk_01():
    r = risk.classify("B", 3)
    assert r["index"] == "3B" and r["region"] == "tolerable_upper" and r["authority"] == "Accountable Executive"


def test_tc_risk_02():
    r = risk.classify("A", 3)
    assert r["region"] == "intolerable" and r["acceptable_to_approve"] is False


def test_all_25_cells_mapped():
    for s in "ABCDE":
        for l in range(1, 6):
            risk.classify(s, l)


def test_frequency_mapping_and_units():
    assert risk.likelihood_from_frequency(1.22e-6)["level"] == 3
    assert risk.likelihood_from_frequency(1e-7)["level"] == 3   # lower bound inclusive
    with pytest.raises(ValueError):
        risk.likelihood_from_frequency(1e-6, unit="per year")


def test_tc_fha_01():
    o = risk.safety_objective("B", "tolerable_lower")
    assert o["likelihood_level"] == 2 and o["max_frequency"] == 1e-7
    assert risk.safety_objective("A")["max_frequency"] == 1e-9
    assert risk.safety_objective("C")["max_frequency"] == 1e-5


# ---------------------------------------------------------------- FMEA
def test_tc_fmea_01():
    rows = [{"item": "Main VHF Tx", "failure_mode": "No RF", "s": 4, "o": 4, "d": 2},
            {"item": "Main VHF Tx", "failure_mode": "Stuck PTT", "s": 8, "o": 3, "d": 4},
            {"item": "VCCS", "failure_mode": "Total loss", "s": 8, "o": 2, "d": 1},
            {"item": "Leased line", "failure_mode": "Loss", "s": 6, "o": 5, "d": 2},
            {"item": "Receivers", "failure_mode": "Degraded sensitivity", "s": 6, "o": 3, "d": 7}]
    out = fmea.analyse(rows)
    top = [r for r in out["rows"] if r.get("rank") == 1][0]
    assert top["rpn"] == 126 and top["failure_mode"] == "Degraded sensitivity"
    assert [r["high_severity"] for r in out["rows"]] == [False, True, True, False, False]


def test_fmeca_criticality():
    out = fmea.analyse([{"item": "X", "failure_mode": "a", "s": 5, "o": 1, "d": 1, "rate": 1e-4, "alpha": 0.6, "beta": 0.5, "time": 100},
                        {"item": "X", "failure_mode": "b", "s": 5, "o": 1, "d": 1, "rate": 1e-4, "alpha": 0.4, "beta": 1, "time": 100}])
    assert math.isclose(out["item_criticality"][0]["criticality"], 0.5 * 0.6 * 1e-4 * 100 + 0.4 * 1e-4 * 100)
    assert out["warnings"] == []


# ---------------------------------------------------------------- LOPA
def _lopa(extra=False):
    sg = [{"label": "ATCO monitoring", "pfd": 0.1, "independent": True, "effective": True, "dependable": True, "auditable": True},
          {"label": "STCA", "pfd": 0.1, "independent": True, "effective": True, "dependable": True, "auditable": True},
          {"label": "ACAS II", "pfd": 0.1, "independent": True, "effective": True, "dependable": True, "auditable": True}]
    if extra:
        sg.append({"label": "SFL mismatch alert", "pfd": 0.1, "independent": True, "effective": True, "dependable": True, "auditable": True})
    return lopa.analyse(0.5, [{"label": "Conflict geometry", "probability": 0.05}], sg, 1e-5)


def test_tc_lopa_01():
    r = _lopa()
    assert math.isclose(r["mitigated_frequency"], 2.5e-5, abs_tol=1e-9)
    assert math.isclose(r["ratio_to_target"], 2.5) and not r["target_met"]


def test_tc_lopa_02():
    r = _lopa(True)
    assert math.isclose(r["mitigated_frequency"], 2.5e-6, abs_tol=1e-9) and r["target_met"]


def test_lopa_rejects_non_ipl_and_flags_dependency():
    r = lopa.analyse(1, [], [{"label": "Training", "pfd": 0.1, "independent": True},
                             {"label": "A", "pfd": 0.1, "independent": True, "effective": True, "dependable": True, "auditable": True, "dependencies": ["radar"]},
                             {"label": "B", "pfd": 0.1, "independent": True, "effective": True, "dependable": True, "auditable": True, "dependencies": ["radar"]}], 1e-3)
    assert r["rejected_safeguards"][0]["label"] == "Training"
    assert r["warnings"]


# ---------------------------------------------------------------- FTA
def test_tc_fta_01():
    r = fta.analyse(FTA_TREE)
    assert math.isclose(r["top_probability"], 1.2200e-6, rel_tol=1e-3)
    sets = {tuple(c["events"]) for c in r["cut_sets"]}
    assert sets == {("E4",), ("E5", "E6"), ("E7", "E8", "E9"), ("E1", "E2", "E3")}
    assert r["single_points_of_failure"] == ["E4"]


def test_tc_fta_02():
    imp = {x["event"]: x for x in fta.analyse(FTA_TREE)["importance"]}
    assert math.isclose(imp["E4"]["fussell_vesely"], 0.820, rel_tol=5e-3)
    assert math.isclose(imp["E5"]["fussell_vesely"], 0.164, rel_tol=5e-3)
    assert math.isclose(imp["E7"]["fussell_vesely"], 0.0164, rel_tol=5e-3)
    assert math.isclose(imp["E5"]["birnbaum"], 0.0100, rel_tol=5e-3)


def test_fta_exact_vs_bruteforce_shared_events():
    # shared event B makes rare-event approximation inexact; BDD must be exact
    tree = {"top": "T", "nodes": {"T": {"type": "or", "children": ["G1", "G2"]},
                                  "G1": {"type": "and", "children": ["A", "B"]},
                                  "G2": {"type": "and", "children": ["B", "C"]},
                                  "A": {"type": "basic", "p": 0.3}, "B": {"type": "basic", "p": 0.4}, "C": {"type": "basic", "p": 0.5}}}
    r = fta.analyse(tree)
    exact = 0.4 * (1 - 0.7 * 0.5)
    assert math.isclose(r["top_probability"], exact, rel_tol=1e-12)
    assert r["approximation_differs"]


def test_fta_vote_ccf_and_rate_models():
    tree = {"top": "T", "nodes": {"T": {"type": "vote", "k": 2, "children": ["A", "B", "C"]},
                                  "A": {"type": "basic", "rate": 1e-3, "time": 10},
                                  "B": {"type": "basic", "rate": 1e-3, "mttr": 10},
                                  "C": {"type": "basic", "rate": 2e-3, "test_interval": 10}},
            "ccf_groups": [{"id": "CCF", "members": ["A", "B"], "beta": 0.1}]}
    r = fta.analyse(tree)
    assert r["top_probability"] > 0 and "CCF" in {e for c in r["cut_sets"] for e in c["events"]}
    with pytest.raises(fta.FTAError):
        fta.analyse({"top": "T", "nodes": {"T": {"type": "and", "children": ["T"]}}})


# ---------------------------------------------------------------- BBN
def test_tc_bbn_01():
    m = bbn.query(BBN_NET)["marginals"]
    assert math.isclose(m["E"]["yes"], 0.00446, rel_tol=1e-6)
    assert math.isclose(m["L"]["yes"], 2.453e-4, rel_tol=1e-6)


def test_tc_bbn_02():
    m = bbn.query(BBN_NET, ["F", "W", "S"], {"L": "yes"})["marginals"]
    assert abs(m["F"]["yes"] - 0.3901) < 1e-4
    assert abs(m["W"]["high"] - 0.5448) < 1e-4
    assert abs(m["S"]["no"] - 0.1091) < 1e-4


def test_tc_bbn_03():
    assert math.isclose(bbn.query(BBN_NET, ["L"], {"F": "yes"})["marginals"]["L"]["yes"], 6.38e-4, rel_tol=1e-6)
    assert math.isclose(bbn.query(BBN_NET, ["L"], {"F": "yes", "W": "high"})["marginals"]["L"]["yes"], 1.10e-3, rel_tol=1e-6)


def test_bbn_matches_bruteforce_oracle():
    for tgt, ev in [("F", {"L": "yes"}), ("E", {"S": "no"}), ("W", {"E": "yes", "S": "yes"})]:
        a = bbn.query(BBN_NET, [tgt], ev)["marginals"][tgt]
        b = bbn.enumerate_joint(BBN_NET, tgt, ev)
        for k in a:
            assert abs(a[k] - b[k]) < 1e-9


def test_bbn_rejects_cycle_and_bad_cpt():
    net = {"nodes": [{"id": "A", "states": ["y", "n"], "parents": ["B"], "cpt": [[0.5, 0.5], [0.5, 0.5]]},
                     {"id": "B", "states": ["y", "n"], "parents": ["A"], "cpt": [[0.5, 0.5], [0.5, 0.5]]}]}
    with pytest.raises(bbn.BBNError):
        bbn.query(net)
    with pytest.raises(bbn.BBNError):
        bbn.query({"nodes": [{"id": "A", "states": ["y", "n"], "parents": [], "cpt": [0.5, 0.6]}]})


# ---------------------------------------------------------------- fatigue
SLEEP_NO_NAP = [[-1, 7], [23, 31], [55, 61]]
SLEEP_NAP = [[-1, 7], [23, 31], [39, 40.5], [55, 61]]
NIGHT = [46, 54]


def test_tc_fat_01():
    d = fatigue.run(SLEEP_NO_NAP, [NIGHT], 0, 72)["duties"][0]
    assert abs(d["min_alertness"] - 5.18) <= 0.05
    assert abs(d["min_time_hours"] - 53.9167) <= 5 / 60
    assert abs(d["max_kss"] - 7.49) <= 0.05
    assert abs(d["share_at_or_above_threshold"] - 0.396) <= 0.01


def test_tc_fat_02():
    d = fatigue.run(SLEEP_NAP, [NIGHT], 0, 72)["duties"][0]
    assert abs(d["min_alertness"] - 6.30) <= 0.05
    assert abs(d["max_kss"] - 6.82) <= 0.05
    assert d["share_at_or_above_threshold"] == 0


def test_tc_fat_03_samn_perelli():
    from app.engines import fatigue
    assert [fatigue.sp_light(s)["key"] for s in range(1, 8)] == ["green"] * 3 + ["caution", "amber", "red", "red"]
    r = fatigue.samn_perelli([
        {"id": "a", "score": 2, "outcome": "normal"},
        {"id": "b", "score": 4, "outcome": "normal"},           # caution needs standard position + earlier break
        {"id": "c", "score": 4, "outcome": "standard"},
        {"id": "d", "score": 5, "outcome": "mitigated"},        # ok, but mitigation not named
        {"id": "e", "score": 5, "outcome": "standard"},         # amber needs mitigation first
        {"id": "f", "score": 6, "outcome": "admin"},
        {"id": "g", "score": 7, "outcome": "mitigated"},        # red must be removed from control
        {"id": "h", "score": 6},                                # open
        {"id": "i", "score": None},
    ])
    assert r["counts"] == {"green": 1, "caution": 2, "amber": 2, "red": 3} and r["n"] == 8
    codes = {(c["ref"], c["code"], c["severity"]) for c in r["checks"]}
    assert ("g", "sp_response", "error") in codes and ("b", "sp_response", "warning") in codes and ("e", "sp_response", "warning") in codes
    assert ("h", "sp_open", "warning") in codes and ("d", "sp_mitigation", "info") in codes
    assert not any(c["ref"] in ("a", "c", "f") for c in r["checks"])
    assert abs(r["mean_score"] - 39 / 8) < 1e-9
    with __import__("pytest").raises(ValueError):
        fatigue.samn_perelli([{"score": 8}])
