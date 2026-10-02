"""DEMO-08 — surveillance radar performance degradation worked example (TC-RDR-01 … TC-RDR-03)."""
from app import radar_demo as R
from app.engines import atsb


def test_tc_rdr_01_coverage():
    cov = R.coverage()
    assert {c["phase"] for c in cov} == {p for p, _ in R.PHASES}
    assert {t for c in cov for t in c["types"]} == set(R.HAZARD_TYPES)
    methods = {c["method"] for c in cov}
    assert len(methods) == 27 and not methods & {"wildlife", "orgmap", "ies"}
    for pid, _ in R.PHASES:   # every phase has at least one study, every hazard type at least two methods
        assert any(c["phase"] == pid for c in cov)
    for t in R.HAZARD_TYPES:
        assert sum(t in c["types"] for c in cov) >= 2 or t == "OHS"


def test_tc_rdr_02_results():
    r = R._results()
    assert abs(r["fta"]["top_probability"] - 9.4478e-6) / 9.4478e-6 < 1e-3
    assert abs(r["fta"]["residual"]["top_probability"] / r["fta"]["top_probability"] - 0.1) < 1e-9
    assert r["crm"]["lateral"]["meets_tls"] is False and abs(r["crm"]["lateral"]["minimum_spacing"]["minimum_spacing"] - 11.68) < 0.01
    lp = r["lopa"]
    assert {x["label"] for x in lp["rejected_safeguards"]} == {"STCA alert and controller resolution", "ADS-B / radar position comparison alert (proposed)"}
    assert abs(lp["mitigated_frequency"] - 2e-4) < 1e-12 and not lp["target_met"]
    assert abs(r["rbd"]["markov"]["availability"] - 0.8232) < 1e-3 and abs(r["rbd"]["markov_monitored"]["availability"] - 0.9612) < 1e-3
    assert [round(t["hep"], 4) for t in r["hra"]["tasks"]] == [0.0888, 0.2024, 0.0205, 0.0432]
    assert max(d["max_kss"] for d in r["fatigue"]["duties"]) > max(d["max_kss"] for d in r["fatigue"]["duties_8h"])
    assert r["bbn"]["marginals"]["RJ"]["yes"] > 0.7
    a = r["atsb"]
    assert a["check_counts"]["error"] == 0 and a["check_counts"]["warning"] == 0
    assert {i["id"] for i in a["issues"]} == {"F6", "F7"}
    assert [o["erc"]["risk_index"] for o in r["orc"]["occurrences"]] == [102, 1, 50]


def test_tc_rdr_03_seeded(client, viewer):
    projects = client.get("/api/projects", headers=viewer).json()
    p = next(x for x in projects if x["code"] == "DEMO-08")
    full = client.get(f"/api/projects/{p['id']}", headers=viewer).json()
    assert len(full["assessments"]) == 6
    studies = [s for s in client.get("/api/studies", headers=viewer).json() if s["assessment"]["id"] in {a["id"] for a in full["assessments"]}]
    assert len(studies) == len(R.STUDIES)
    ids = {s["id"] for s in studies}
    gsn = next(s for s in studies if s["method"] == "gsn")
    g = client.get(f"/api/studies/{gsn['id']}", headers=viewer).json()
    sols = [n for n in g["model"]["nodes"] if n["type"] == "solution"]
    assert len(sols) == 26 and all(n["evidence"]["ref"] in ids for n in sols)
    hz = [h for h in client.get("/api/hazards", headers=viewer).json() if h["ref"].startswith("RDR-")]
    assert len(hz) == 12 and all(h["source_study_id"] in ids for h in hz)
    st = next(s for s in studies if s["method"] == "atsb")
    rep = client.post(f"/api/studies/{st['id']}/investigation-report", json={"format": "json"}, headers=viewer)
    assert rep.status_code == 200 and rep.json()["meta"]["project"].startswith("DEMO-08")
    m = client.get(f"/api/studies/{st['id']}", headers=viewer).json()["model"]
    assert atsb.analyse(m)["counts"]["contributing"] == 8
