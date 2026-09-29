"""Archive, restore and delete projects (SRS COM-17, COM-18; TC-PRJ-01)."""


def _codes(client, headers, **params):
    return {p["code"] for p in client.get("/api/projects", headers=headers, params=params).json()}


def _project_with_content(client, assessor, code):
    p = client.post("/api/projects", json={"code": code, "title": "Disposable"}, headers=assessor).json()
    a = client.post("/api/assessments", json={"project_id": p["id"], "title": "A"}, headers=assessor).json()
    s = client.post("/api/studies", json={"assessment_id": a["id"], "method": "hazid", "title": "H"}, headers=assessor).json()
    hz = client.post(f"/api/studies/{s['id']}/promote", headers=assessor,
                     json=[{"row_id": "HZ-01", "title": "Test hazard", "severity": "C", "likelihood": 3, "controls": ["C1"]}]).json()
    client.post("/api/actions", json={"text": "Fix", "owner": "x", "hazard_id": hz[0]["id"], "assessment_id": a["id"]}, headers=assessor)
    return p, a, s, hz[0]


def test_archive_and_restore(client, assessor, viewer):
    p = client.post("/api/projects", json={"code": "ARC-1", "title": "To archive"}, headers=assessor).json()
    a = client.post("/api/assessments", json={"project_id": p["id"], "title": "A"}, headers=assessor).json()
    assert client.post(f"/api/projects/{p['id']}/archive", headers=viewer).status_code == 403
    r = client.post(f"/api/projects/{p['id']}/archive", headers=assessor)
    assert r.status_code == 200 and r.json()["status"] == "archived"
    assert client.post(f"/api/projects/{p['id']}/archive", headers=assessor).status_code == 409
    # hidden from the lists by default, still readable, visible on request
    assert "ARC-1" not in _codes(client, viewer)
    assert "ARC-1" in _codes(client, viewer, include_archived="true")
    assert client.get(f"/api/projects/{p['id']}", headers=viewer).status_code == 200
    assert a["id"] not in {x["id"] for x in client.get("/api/assessments", headers=viewer).json()}
    assert a["id"] in {x["id"] for x in client.get("/api/assessments", headers=viewer, params={"include_archived": "true"}).json()}
    # no new assessments in an archived project
    assert client.post("/api/assessments", json={"project_id": p["id"], "title": "B"}, headers=assessor).status_code == 409
    r = client.post(f"/api/projects/{p['id']}/restore", headers=assessor)
    assert r.status_code == 200 and r.json()["status"] == "active"
    assert "ARC-1" in _codes(client, viewer)
    assert client.post(f"/api/projects/{p['id']}/restore", headers=assessor).status_code == 409


def test_delete_project(client, admin, assessor, reviewer):
    p, a, s, hz = _project_with_content(client, assessor, "DEL-1")
    # admin only, and the code must be typed
    assert client.delete(f"/api/projects/{p['id']}", params={"confirm": "DEL-1"}, headers=assessor).status_code == 403
    assert client.delete(f"/api/projects/{p['id']}", params={"confirm": "DEL-2"}, headers=admin).status_code == 422
    assert client.delete(f"/api/projects/{p['id']}", headers=admin).status_code == 422
    r = client.delete(f"/api/projects/{p['id']}", params={"confirm": "DEL-1"}, headers=admin)
    assert r.status_code == 200, r.text
    assert r.json() == {"deleted": "DEL-1", "assessments": 1, "studies": 1, "hazards": 1, "actions": 1}
    assert client.get(f"/api/projects/{p['id']}", headers=admin).status_code == 404
    assert client.get(f"/api/assessments/{a['id']}", headers=admin).status_code == 404
    assert client.get(f"/api/studies/{s['id']}", headers=admin).status_code == 404
    assert hz["id"] not in {h["id"] for h in client.get("/api/hazards", headers=admin).json()}
    log = client.get("/api/audit", params={"entity": "project"}, headers=reviewer).json()
    entry = next(e for e in log if e["action"] == "delete" and e["entity_id"] == str(p["id"]))
    assert entry["username"] == "admin" and entry["before"]["code"] == "DEL-1" and entry["before"]["deleted"]["hazards"] == 1


def test_delete_refused_when_assessment_locked(client, admin, assessor):
    from app.db import SessionLocal
    from app.models import Assessment
    p, a, _, _ = _project_with_content(client, assessor, "DEL-LOCK")
    with SessionLocal() as db:
        db.get(Assessment, a["id"]).status = "accepted"; db.commit()
    r = client.delete(f"/api/projects/{p['id']}", params={"confirm": "DEL-LOCK"}, headers=admin)
    assert r.status_code == 409 and "archive the project instead" in r.json()["detail"]
    assert client.get(f"/api/projects/{p['id']}", headers=admin).status_code == 200


def test_deleted_demo_is_not_reseeded(client, admin, viewer):
    demo = next(p for p in client.get("/api/projects", headers=viewer).json() if p["code"] == "DEMO-05")
    assert client.delete(f"/api/projects/{demo['id']}", params={"confirm": "DEMO-05"}, headers=admin).status_code == 200
    from app.main import init_db
    init_db()  # what happens at the next start-up
    assert "DEMO-05" not in _codes(client, viewer, include_archived="true")
    assert "DEMO-04" in _codes(client, viewer)
