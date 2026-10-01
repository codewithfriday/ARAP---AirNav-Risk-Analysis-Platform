"""ATSB safety investigation analysis (SRS §4.34, reference tests TC-ATB-01 … TC-ATB-05)."""
from datetime import date

import pytest

from app.engines import atsb, fuzzy, risk


def _t(conclusion, prob, n_sup=1, n_opp=0, target=None, sources=None):
    items = [{"text": f"s{i}", "rating": "supports", "source": (sources or [f"src{i}"] * 9)[i]} for i in range(n_sup)]
    items += [{"text": f"o{i}", "rating": "opposes", "source": f"osrc{i}"} for i in range(n_opp)]
    d = {"items": items, "conclusion": conclusion, "probability": prob}
    if target:
        d["target"] = target
    return d


def test_tc_atb_01_atsb_matrix():
    S = risk.ATSB_SCHEME
    cells = [c for r in S["regions"] for c in r["cells"]]
    assert len(cells) == 36 and len(set(cells)) == 36
    lvl = lambda cell: risk.classify_issue("atsb", cell[1], int(cell[0]))["issue_level"]
    assert lvl("6C") == "critical" and lvl("4A") == "critical" and lvl("5B") == "critical"
    assert lvl("3E") == "broadly_acceptable" and lvl("1C") == "broadly_acceptable"
    assert lvl("6F") == "significant" and risk.classify("F", 6, S)["region"] == "significant_lower"
    for lk in range(1, 7):                      # catastrophic ⇒ at least significant regardless of likelihood (Guidelines p.166)
        assert lvl(f"{lk}B") != "broadly_acceptable" and lvl(f"{lk}A") != "broadly_acceptable"
    # colours follow the AirNav 5×5
    an = {r["key"]: r["color"] for r in risk.DEFAULT_SCHEME["regions"]}
    at = {r["key"]: r["color"] for r in S["regions"]}
    assert at["critical"] == an["intolerable"] and at["significant_upper"] == an["tolerable_upper"]
    assert at["significant_lower"] == an["tolerable_lower"] and at["broadly_acceptable"] == an["acceptable"]
    # AirNav ratings map onto the same three levels
    assert risk.classify_issue("airnav", "A", 5)["issue_level"] == "critical"
    assert risk.classify_issue("airnav", "B", 3)["issue_level"] == "significant"
    assert risk.classify_issue("airnav", "E", 1)["issue_level"] == "broadly_acceptable"


def test_tc_atb_02_finding_types():
    F = [
        {"id": "OE", "title": "The aircraft climbed through the cleared level", "type": "OE",
         "existence": _t("supported", "VC"), "influence": _t("supported", "VC", target="occurrence")},
        {"id": "IA", "title": "The controller did not detect the readback error", "type": "IA", "codes": ["I3.3"],
         "existence": _t("supported", "VL"), "influence": _t("supported", "L", target="OE")},
        {"id": "LC", "title": "The controller was on a night duty", "type": "LC", "codes": ["L1.3"],
         "existence": _t("supported", "L"), "influence": _t("not_supported", "ALAN", target="IA"),
         "importance": {"passed": True, "justification": "recurs"}},
        {"id": "RC", "title": "No rest-break rule existed for night duty", "type": "RC", "codes": ["R5"],
         "existence": _t("supported", "VL"), "influence": _t("supported", "L", target="LC")},
        {"id": "NX", "title": "The radar was unserviceable during the occurrence", "type": "LC", "existence": _t("not_supported", "U")},
        {"id": "LOW", "title": "The frequency was congested at the time", "type": "LC",
         "existence": _t("supported", "ALAN"), "influence": _t("supported", "L", target="IA")},
        {"id": "PA", "title": "The pilot followed the ACAS resolution advisory", "type": "PA",
         "existence": _t("supported", "VC"), "influence": _t("supported", "VL", target="occurrence")},
        {"id": "X", "title": "The controller lost situation awareness", "type": "IA", "further": False, "exclusion_reason": "Restates the problem"},
    ]
    ft = {k: v["finding_type"] for k, v in atsb.finding_types(F).items()}
    assert ft == {"OE": "contributing", "IA": "contributing", "LC": "other", "RC": "other", "NX": "not_established",
                  "LOW": "not_established", "PA": "positive", "X": "excluded"}
    # RC influenced only the non-contributing LC ⇒ other safety factor (Tools p.125); LOW: existence below the standard of proof is not established


def test_tc_atb_03_checks_and_safety_issues():
    F = [
        {"id": "OE", "title": "The aircraft climbed through the cleared level", "type": "OE",
         "existence": _t("supported", "VC"), "influence": _t("supported", "VC", target="occurrence")},
        {"id": "IA", "title": "The controller failed to monitor", "type": "IA", "codes": ["I3.5"],
         "existence": _t("supported", "L", n_sup=0), "influence": _t("supported", "L", target="OE")},
        {"id": "BAD", "title": "The pilot read back the wrong level", "type": "IA", "safety_issue": True, "codes": ["I1.6"], "role": "Pilot in command",
         "error_type": "action", "existence": _t("supported", "VC"), "influence": _t("supported", "VL", target="OE")},
        {"id": "Q", "title": "Similar-callsign coordination with operators was not in place", "type": "OI", "codes": ["O1"], "safety_issue": True,
         "issue_owner": "ANSP", "existence": _t("supported", "VL", n_sup=2, sources=["Audit", "Audit"]), "influence": _t("supported", "L", target="BAD"),
         "risk": {"scheme": "atsb", "consequence": "B", "likelihood": 2, "worst_credible": "x", "consequence_justification": "y", "likelihood_justification": "z"},
         "actions": [{"id": "A", "kind": "recommendation", "notified_on": "2026-01-10", "log": [{"date": "2026-02-01", "text": "reply"}]}],
         "evaluation": {"residual": {"consequence": "B", "likelihood": 2}, "alarp": False}, "issue_status": "pending"},
        {"id": "Z", "title": "Nothing", "type": "LC", "further": False},
    ]
    r = atsb.analyse({"factors": F, "events": [{"id": "E1", "title": "x"}]}, today=date(2026, 10, 1))
    codes = {(c["ref"], c["code"]) for c in r["checks"]}
    assert ("IA", "writing") in codes                       # 'failed' is judgemental
    assert ("IA", "ignorance") in codes                     # supported with no supporting item
    assert ("IA", "classify") in codes                      # role / error type missing
    assert ("IA", "fairness") in codes                      # individual action without identified reasons
    assert ("BAD", "issue_type") in codes                   # an individual action cannot be a safety issue
    assert ("Z", "exclusion") in codes                      # not analysed further without a reason
    assert ("Q", "independence") in codes                   # same source twice
    assert ("Q", "compound") not in codes                   # 90 % × 66 % ≈ 59 %
    assert ("E1", "event_time") in codes and ("E1", "writing") in codes
    assert ("Q", "follow_up") in codes and r["factors"]["Q"]["follow_up_due"] == "2026-08-02"
    q = r["factors"]["Q"]
    assert q["issue_level"] == "significant" and q["risk"]["index"] == "2B" and q["action_evaluation"] == "further"
    assert r["issues"][0]["id"] == "Q"
    # ALARP judged ⇒ significant residual needs no further action
    F[3]["evaluation"]["alarp"] = True
    assert atsb.analyse({"factors": F})["factors"]["Q"]["action_evaluation"] == "no_further"
    # compound probability warning when both only 'likely'
    F[3]["existence"]["probability"] = "L"
    assert ("Q", "compound") in {(c["ref"], c["code"]) for c in atsb.analyse({"factors": F})["checks"]}


def test_tc_atb_04_demo_and_api(client, viewer, assessor):
    m = client.get("/api/meta/atsb", headers=viewer).json()
    i3 = next(g for g in m["taxonomy"]["IA"] if g["code"] == "I3")
    assert [c["code"] for c in i3["children"]] == ["I3.1", "I3.2", "I3.3", "I3.4", "I3.5", "I3.6"]
    assert {p["code"]: p["lower"] for p in m["probability"]}["L"] == 66 and m["standard_of_proof"] == 66
    sc = client.get("/api/risk/atsb-scheme", headers=viewer).json()["data"]
    assert len(sc["severity"]) == 6 and len(sc["likelihood"]) == 6
    st = next(s for s in client.get("/api/studies?method=atsb", headers=viewer).json())
    full = client.get(f"/api/studies/{st['id']}", headers=viewer).json()
    r = client.post("/api/calc/atsb", json={"model": full["model"]}, headers=viewer).json()
    assert r["counts"]["contributing"] == 7 and r["counts"]["other"] == 2 and r["counts"]["positive"] == 2
    assert [i["risk"]["index"] for i in r["issues"]] == ["3B", "2B"] and {i["level"] for i in r["issues"]} == {"significant"}
    assert r["check_counts"]["error"] == 0
    assert [f["id"] for f in r["findings"]["contributing"]][0] == "F1"


def test_tc_atb_05_ies_atsb_alignment(client, viewer):
    meta = client.get("/api/ies/meta", headers=viewer).json()
    los = {f["code"]: f for f in meta["categories"]["ats-los"]["factors"]}
    assert los["I-HEARBACK-MISSED"]["atsb"] == "I3.3" and los["R-STCA-LATE"]["atsb"] == "R1.4"
    assert meta["prob_terms"]["VP"] == "Very likely" and "T" in meta["layers"]
    m = {"blocks": [{"id": "t", "layer": "T", "kind": "evidence", "label": "Software anomaly"},
                    {"id": "h", "layer": "E", "kind": "hypothesis", "label": "h", "past": "S"}], "edges": [{"source": "t", "target": "h"}]}
    assert fuzzy.infer(m, {"t": "S"})["blocks"]["h"]["term"] == "S"
    # 'Unsure' is a rating: no evidence for the network, and no longer a clue
    r = client.post("/api/ies/bn", json={"category": "ats-los", "ratings": {"f:I-MONITORING-LAPSE": "U"}}, headers=viewer).json()
    assert all(c["factor"] != "I-MONITORING-LAPSE" for c in r["clues"]) and r["evidence_used"] == []
