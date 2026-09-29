from datetime import date, timedelta


def test_health_and_auth(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/projects").status_code == 401
    assert client.post("/api/auth/login", data={"username": "admin", "password": "wrong"}).status_code == 401


def test_demo_seeded_all_methods(client, viewer):
    projects = client.get("/api/projects", headers=viewer).json()
    demo = next(p for p in projects if p["code"] == "DEMO-01")
    a = client.get(f"/api/projects/{demo['id']}", headers=viewer).json()["assessments"][0]
    full = client.get(f"/api/assessments/{a['id']}", headers=viewer).json()
    assert {s["method"] for s in full["studies"]} == {"bowtie", "hazid", "hazop", "jha", "fmea", "lopa", "fha", "stpa",
                                                     "fta", "fatigue", "fram", "bbn"}


def test_viewer_cannot_edit(client, viewer):
    r = client.post("/api/projects", json={"code": "X", "title": "x"}, headers=viewer)
    assert r.status_code == 403


def test_full_workflow_and_locking(client, assessor, reviewer, director, accexec):
    p = client.post("/api/projects", json={"code": "T-1", "title": "Test change"}, headers=assessor).json()
    a = client.post("/api/assessments", json={"project_id": p["id"], "title": "A"}, headers=assessor).json()
    s = client.post("/api/studies", json={"assessment_id": a["id"], "method": "hazid", "title": "H"}, headers=assessor).json()
    # promote a worksheet row to the hazard log
    hz = client.post(f"/api/studies/{s['id']}/promote", headers=assessor,
                     json=[{"row_id": "HZ-01", "title": "Wrong lines to TWR", "severity": "C", "likelihood": 3,
                            "controls": ["Test plan"]}]).json()
    assert hz[0]["initial_risk"]["index"] == "3C" and hz[0]["controls"][0]["text"] == "Test plan"
    # promoting the same row again updates rather than duplicates
    hz2 = client.post(f"/api/studies/{s['id']}/promote", headers=assessor,
                      json=[{"row_id": "HZ-01", "title": "Wrong telephone lines to TWR", "severity": "C", "likelihood": 3}]).json()
    assert hz2[0]["ref"] == hz[0]["ref"]
    # residual rating without rationale is refused (COM-08)
    body = {"title": "Wrong telephone lines to TWR", "assessment_id": a["id"], "initial_severity": "C", "initial_likelihood": 3,
            "residual_severity": "C", "residual_likelihood": 2}
    assert client.put(f"/api/hazards/{hz[0]['id']}", json=body, headers=assessor).status_code == 422
    body["rationale"] = "End-to-end line check planned"
    assert client.put(f"/api/hazards/{hz[0]['id']}", json=body, headers=assessor).status_code == 200
    # workflow
    assert client.post(f"/api/assessments/{a['id']}/transition", json={"action": "endorse"}, headers=reviewer).status_code == 409
    assert client.post(f"/api/assessments/{a['id']}/transition", json={"action": "submit"}, headers=assessor).status_code == 200
    assert client.post(f"/api/assessments/{a['id']}/transition", json={"action": "return"}, headers=reviewer).status_code == 422
    assert client.post(f"/api/assessments/{a['id']}/transition", json={"action": "endorse", "comment": "ok"}, headers=reviewer).status_code == 200
    # locked now
    assert client.put(f"/api/studies/{s['id']}", json={"model": {"rows": []}}, headers=assessor).status_code == 409
    # 2C is tolerable (lower): director may accept
    full = client.get(f"/api/assessments/{a['id']}", headers=director).json()
    assert full["worst_residual_region"] == "tolerable_lower"
    r = client.post(f"/api/assessments/{a['id']}/transition", json={"action": "accept"}, headers=director)
    assert r.status_code == 200 and r.json()["status"] == "accepted"
    # new version unlocks a copy
    b = client.post(f"/api/assessments/{a['id']}/new-version", headers=assessor).json()
    assert b["version"] == 2 and b["status"] == "draft" and len(b["studies"]) == 1


def test_acceptance_authority_enforced(client, assessor, reviewer, director, accexec):
    p = client.post("/api/projects", json={"code": "T-2", "title": "High risk change"}, headers=assessor).json()
    a = client.post("/api/assessments", json={"project_id": p["id"], "title": "A"}, headers=assessor).json()
    client.post("/api/hazards", headers=assessor, json={"title": "X", "assessment_id": a["id"], "initial_severity": "B",
                                                         "initial_likelihood": 3})  # 3B tolerable upper
    for act, h in (("submit", assessor), ("endorse", reviewer)):
        assert client.post(f"/api/assessments/{a['id']}/transition", json={"action": act}, headers=h).status_code == 200
    assert client.post(f"/api/assessments/{a['id']}/transition", json={"action": "accept"}, headers=director).status_code == 403
    assert client.post(f"/api/assessments/{a['id']}/transition", json={"action": "accept"}, headers=accexec).status_code == 200


def test_intolerable_cannot_be_accepted(client, assessor, reviewer, admin):
    p = client.post("/api/projects", json={"code": "T-3", "title": "Intolerable"}, headers=assessor).json()
    a = client.post("/api/assessments", json={"project_id": p["id"], "title": "A"}, headers=assessor).json()
    client.post("/api/hazards", headers=assessor, json={"title": "Y", "assessment_id": a["id"], "initial_severity": "A", "initial_likelihood": 4})
    client.post(f"/api/assessments/{a['id']}/transition", json={"action": "submit"}, headers=assessor)
    client.post(f"/api/assessments/{a['id']}/transition", json={"action": "endorse"}, headers=reviewer)
    assert client.post(f"/api/assessments/{a['id']}/transition", json={"action": "accept"}, headers=admin).status_code == 409


def test_calc_endpoints(client, viewer):
    from app.seed import BBN_NET, FTA_TREE
    assert abs(client.post("/api/calc/fta", json={"tree": FTA_TREE}, headers=viewer).json()["top_probability"] - 1.22e-6) < 1e-9
    assert client.post("/api/calc/fta", json={"tree": {"top": "X", "nodes": {}}}, headers=viewer).status_code == 422
    m = client.post("/api/calc/bbn", json={"network": BBN_NET, "targets": ["F"], "evidence": {"L": "yes"}}, headers=viewer).json()
    assert abs(m["marginals"]["F"]["yes"] - 0.3901) < 1e-4
    o = client.post("/api/calc/objective", json={"severity": "B"}, headers=viewer).json()
    assert o["max_frequency"] == 1e-7
    f = client.post("/api/calc/fatigue", json={"sleeps": [[-1, 7], [23, 31], [55, 61]], "duties": [[46, 54]], "end": 72}, headers=viewer).json()
    assert abs(f["duties"][0]["min_alertness"] - 5.18) < 0.05


def test_hazard_log_export_similar_dashboard_report_audit(client, viewer, reviewer, assessor):
    r = client.get("/api/hazards/export.csv", headers=viewer)
    assert r.status_code == 200 and "HZ-0001" in r.text
    sim = client.get("/api/hazards/similar", params={"text": "Unauthorised entry onto the active runway"}, headers=viewer).json()
    assert sim and sim[0]["ref"] == "HZ-0001"
    d = client.get("/api/dashboard", headers=viewer).json()
    assert d["hazards_total"] >= 5 and d["overdue_actions"]
    a = client.get("/api/assessments", headers=viewer).json()[-1]
    rep = client.get(f"/api/assessments/{a['id']}/report.docx", headers=viewer)
    assert rep.status_code == 200 and rep.content[:2] == b"PK"
    assert client.get("/api/audit", headers=viewer).status_code == 403
    assert len(client.get("/api/audit", headers=reviewer).json()) > 0


def test_action_closure_requires_evidence(client, assessor):
    a = client.post("/api/actions", json={"text": "Do it", "owner": "x", "due_date": str(date.today() + timedelta(days=5))}, headers=assessor).json()
    assert client.put(f"/api/actions/{a['id']}", json={"text": "Do it", "status": "closed"}, headers=assessor).status_code == 422
    assert client.put(f"/api/actions/{a['id']}", json={"text": "Do it", "status": "closed", "closure_evidence": "Report #12"}, headers=assessor).status_code == 200


def test_risk_scheme_versioning(client, admin, viewer):
    cur = client.get("/api/risk/scheme", headers=viewer).json()
    bad = dict(cur["data"]); bad["regions"] = bad["regions"][:2]
    assert client.put("/api/risk/scheme", json=bad, headers=admin).status_code == 422
    assert client.put("/api/risk/scheme", json=cur["data"], headers=viewer).status_code == 403
    r = client.put("/api/risk/scheme", json=cur["data"], headers=admin).json()
    assert r["version"] == cur["version"] + 1


def test_empty_assessment_cannot_be_accepted(client, assessor, reviewer, admin):
    p = client.post("/api/projects", json={"code": "T-4", "title": "Empty"}, headers=assessor).json()
    a = client.post("/api/assessments", json={"project_id": p["id"], "title": "A"}, headers=assessor).json()
    client.post(f"/api/assessments/{a['id']}/transition", json={"action": "submit"}, headers=assessor)
    client.post(f"/api/assessments/{a['id']}/transition", json={"action": "endorse"}, headers=reviewer)
    r = client.post(f"/api/assessments/{a['id']}/transition", json={"action": "accept"}, headers=admin)
    assert r.status_code == 409 and "no hazards" in r.json()["detail"]


def test_v2_demo_and_calc_endpoints(client, viewer):
    from app import seed2 as S
    projects = client.get("/api/projects", headers=viewer).json()
    demo2 = next(p for p in projects if p["code"] == "DEMO-02")
    a = client.get(f"/api/projects/{demo2['id']}", headers=viewer).json()["assessments"][0]
    full = client.get(f"/api/assessments/{a['id']}", headers=viewer).json()
    assert {s["method"] for s in full["studies"]} == {"crm", "eta", "hra", "orc", "gsn", "cca", "rbd", "swift", "hta", "sim", "sej", "sec", "inv", "wildlife"}
    assert len(client.get("/api/meta/methods", headers=viewer).json()) == 29
    v = client.post("/api/calc/crm", json={"dimension": "vertical", "params": S.CRM_VERTICAL}, headers=viewer).json()
    assert abs(v["total"] - 1.873e-9) < 1e-11
    L, m = S.CRM_LATERAL, S.CRM_LAT_MODEL
    params = {k: L[k] for k in ("pz0", "lx", "lz", "sx", "dv", "v", "zdot", "ydot_sy", "tls")} | {"ey_same": L["ey_same"], "ey_opp": L["ey_opp"], "ly": m["lam_y"], "py_sy": 1e-6}
    lat = client.post("/api/calc/crm", headers=viewer, json={"dimension": "lateral", "params": params,
                      "curve": {"lam_y": m["lam_y"], "model": m["model"], "scale": m["scale"], "spacings": [10, 15]}}).json()
    assert abs(lat["minimum_spacing"]["minimum_spacing"] - 11.68) < 0.01
    assert abs(client.post("/api/calc/eta", json=S.ETA_MODEL, headers=viewer).json()["sequences"][-1]["frequency"] - 5e-5) < 1e-12
    assert abs(client.post("/api/calc/hra", json=S.HRA_TASKS[0], headers=viewer).json()["hep"] - 0.002016) < 1e-9
    assert client.post("/api/calc/hra", json={"library": "cara", "gtt": "ZZ"}, headers=viewer).status_code == 422
    assert client.post("/api/calc/erc", json={"outcome": "Major accident", "barriers": "Limited"}, headers=viewer).json()["risk_index"] == 21
    assert client.post("/api/calc/rat", json=S.RAT_CASE, headers=viewer).json()["severity_score"] == 7
    assert abs(client.post("/api/calc/rbd", json=S.RBD_VHF, headers=viewer).json()["downtime_hours_per_year"] - 0.423) < 0.001
    assert abs(client.post("/api/calc/markov", json=S.MARKOV_STANDBY, headers=viewer).json()["unavailability"] - 2.0396e-6) < 1e-9
    sej = client.post("/api/calc/sej", json={"experts": S.SEJ_EXPERTS, "items": S.SEJ_ITEMS}, headers=viewer).json()
    assert sej["experts"]["Expert C"]["weight"] < 1e-4
    assert client.post("/api/calc/delphi", json=S.DELPHI_ROUNDS, headers=viewer).json()[2]["converging"]
    assert all(x["criterion_met"] for x in client.post("/api/calc/sim", json=S.SIM_MEASURES, headers=viewer).json())
    assert client.post("/api/calc/security", json={"likelihood": 3, "c": 1, "i": 5, "a": 3}, headers=viewer).json()["level"] == "Very high"
    bars = client.get("/api/barriers", headers=viewer).json()
    assert any(b["barrier_id"] == "PB2" for b in bars)
    fails = client.get("/api/barriers/failures", headers=viewer).json()
    assert any(f["link"].endswith(":PB3") for f in fails)
    assert "cara" in client.get("/api/meta/hra", headers=viewer).json()
    assert client.get("/api/meta/orc", headers=viewer).json()["erc"]["matrix"][0][3] == 2500
    rep = client.get(f"/api/assessments/{a['id']}/report.docx", headers=viewer)
    assert rep.status_code == 200


def test_studies_index_and_barrier_links(client, viewer):
    idx = client.get("/api/studies", headers=viewer).json()
    assert len(idx) >= 25 and {"id", "method", "title", "assessment"} <= set(idx[0])
    ftas = client.get("/api/studies?method=fta", headers=viewer).json()
    assert ftas and all(s["method"] == "fta" for s in ftas)
    bars = client.get("/api/barriers", headers=viewer).json()
    fails = client.get("/api/barriers/failures", headers=viewer).json()
    keys = {f"{b['study_id']}:{b['barrier_id']}" for b in bars}
    assert fails and all(f["link"] in keys for f in fails)


def test_demo3_alternate_h24_case_study(client, viewer):
    """DEMO-03 reproduces SRA/MOC/OPS/001/IX/2026: 40 hazards, 15 intolerable now, none residual; FTA 4.6e-3 → 2.9e-4."""
    projects = client.get("/api/projects", headers=viewer).json()
    p = next(x for x in projects if x["code"] == "DEMO-03")
    a = client.get(f"/api/projects/{p['id']}", headers=viewer).json()["assessments"][0]
    full = client.get(f"/api/assessments/{a['id']}", headers=viewer).json()
    assert sorted(s["method"] for s in full["studies"]) == ["bowtie", "fta", "fta", "gsn", "hazid", "stpa"]
    hz = [h for h in client.get("/api/hazards", headers=viewer).json() if h["ref"].startswith("ALT-")]
    assert len(hz) == 40
    cur = [h["initial_risk"]["region"] for h in hz]
    res = [h["residual_risk"]["region"] for h in hz]
    assert cur.count("intolerable") == 15
    assert res.count("intolerable") == 0 and res.count("acceptable") == 16
    ftas = {s["title"]: s for s in full["studies"] if s["method"] == "fta"}
    tops = sorted(client.get(f"/api/studies/{s['id']}", headers=viewer).json()["results"]["top_probability"] for s in ftas.values())
    assert abs(tops[0] - 2.887e-4) < 5e-7 and abs(tops[1] - 4.56e-3) < 1e-6
    acts = [x for x in client.get("/api/actions", headers=viewer).json() if x["ref"].startswith("ALT-PK")]
    assert len(acts) == 8


def test_wildlife_calc_endpoint(client, viewer):
    from app.seed_wildlife import WILDLIFE_MODEL
    r = client.post("/api/calc/wildlife", json=WILDLIFE_MODEL, headers=viewer).json()
    top = r["species"][0]
    assert top["scientific"] == "Bubulcus ibis" and top["risk"] == "high" and top["score"] == 20
    bad = dict(WILDLIFE_MODEL, species=[dict(WILDLIFE_MODEL["species"][0], damaging={"2021": 99})])
    assert client.post("/api/calc/wildlife", json=bad, headers=viewer).status_code == 422


def test_assessment_template_aim(client, viewer, assessor):
    """TC-TPL-01: creating an assessment from the AIM template gives 14 pre-filled studies; ratings left to the team."""
    cat = client.get("/api/assessment-templates", headers=viewer).json()
    t = next(x for x in cat if x["key"] == "aim_acquisition")
    assert len(t["studies"]) == 14 and "build" not in t
    pid = client.get("/api/projects", headers=viewer).json()[0]["id"]
    a = client.post("/api/assessments", headers=assessor, json={"project_id": pid, "title": t["title"], "scope": t["scope"], "template": "aim_acquisition"}).json()
    methods = sorted(s["method"] for s in a["studies"])
    assert methods == sorted(["fha", "hazop", "fmea", "fta", "cca", "stpa", "hta", "hra", "sec", "jha", "swift", "bowtie", "sim", "gsn"])
    sid = {s["method"]: s["id"] for s in a["studies"]}
    haz = client.get(f"/api/studies/{sid['hazop']}", headers=viewer).json()["model"]
    assert len(haz["nodes"]) == 7 and all("likelihood" not in r for r in haz["rows"])
    fha = client.get(f"/api/studies/{sid['fha']}", headers=viewer).json()["model"]["rows"]
    assert len(fha) == 12 and {r["failure_type"] for r in fha} >= {"Erroneous (undetected)", "Total loss", "Delayed"}
    gsn = client.get(f"/api/studies/{sid['gsn']}", headers=viewer).json()["model"]["nodes"]
    linked = {n["evidence"]["ref"] for n in gsn if n["type"] == "solution"}
    assert linked <= set(sid.values()) and None not in linked
    fta = client.post("/api/calc/fta", headers=viewer, json={"tree": client.get(f"/api/studies/{sid['fta']}", headers=viewer).json()["model"]["tree"]}).json()
    assert abs(fta["top_probability"] - 2.857e-5) < 1e-8
    assert client.post("/api/assessments", headers=assessor, json={"project_id": pid, "title": "x", "template": "nope"}).status_code == 422


def test_demo4_aim(client, viewer):
    p = next(x for x in client.get("/api/projects", headers=viewer).json() if x["code"] == "DEMO-04")
    a = client.get(f"/api/projects/{p['id']}", headers=viewer).json()["assessments"][0]
    full = client.get(f"/api/assessments/{a['id']}", headers=viewer).json()
    assert len(full["studies"]) == 14 and len(full["hazards"]) == 7 and len(full["actions"]) == 6
    sim = next(s for s in full["studies"] if s["method"] == "sim")
    res = client.get(f"/api/studies/{sim['id']}", headers=viewer).json()["results"]["measures"]
    assert [m["criterion_met"] for m in res] == [False, True, True]


def test_assessment_template_org_change(client, viewer, assessor):
    """TC-TPL-02: organisational change template — 11 studies, function map unassessed, HAZID with organisational guidewords."""
    t = next(x for x in client.get("/api/assessment-templates", headers=viewer).json() if x["key"] == "org_change")
    assert len(t["studies"]) == 11
    pid = client.get("/api/projects", headers=viewer).json()[0]["id"]
    a = client.post("/api/assessments", headers=assessor, json={"project_id": pid, "title": t["title"], "template": "org_change"}).json()
    by = {}
    for s in a["studies"]:
        by.setdefault(s["method"], []).append(s["id"])
    assert sorted(by) == sorted(["orgmap", "fha", "stpa", "hazid", "hta", "sej", "swift", "bowtie", "spi", "gsn"]) and len(by["stpa"]) == 2
    fmap = client.get(f"/api/studies/{by['orgmap'][0]}", headers=viewer).json()["model"]["rows"]
    assert len(fmap) == 18 and all(r["competence"] == "unknown" for r in fmap)
    assert sum(1 for r in fmap if not r["new_owner"]) == 2          # orphan functions proposed by the design
    hz = client.get(f"/api/studies/{by['hazid'][0]}", headers=viewer).json()["model"]
    assert hz["guidewords"][0] == "Roles and responsibilities" and all("likelihood" not in r for r in hz["rows"])


def test_demo5_org_change(client, viewer):
    p = next(x for x in client.get("/api/projects", headers=viewer).json() if x["code"] == "DEMO-05")
    a = client.get(f"/api/projects/{p['id']}", headers=viewer).json()["assessments"][0]
    full = client.get(f"/api/assessments/{a['id']}", headers=viewer).json()
    assert len(full["studies"]) == 11 and len(full["hazards"]) == 7 and len(full["actions"]) == 6
    sej = next(s for s in full["studies"] if s["method"] == "sej")
    d = client.get(f"/api/studies/{sej['id']}", headers=viewer).json()["results"]["delphi"]
    assert [round(r["median"], 3) for r in d] == [0.125, 0.12, 0.12] and d[-1]["converging"]
