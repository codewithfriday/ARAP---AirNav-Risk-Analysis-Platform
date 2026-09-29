"""Investigation expert system (SRS §4.33, reference tests TC-IES-01 … TC-IES-05)."""
import io
import math

import pytest

from app.engines import bbn, casebn, casesearch, draft, fuzzy
from app.investigation import CATEGORIES, DEMO_OCCURRENCE, FACTORS, THESAURUS

REPORT = (
    "At 1412 UTC two aircraft of the same operator with similar callsigns were on the sector frequency. "
    "The frequency was congested and there were two blocked transmissions in the preceding minute. "
    "The controller issued a climb to FL360 to the first aircraft, but the clearance was acted on by the wrong aircraft. "
    "The readback was not detected by the controller. The investigation found that the hearback error was a contributing factor. "
    "There was no similar callsign marking on the flight strips. STCA alerted and avoiding action was given. "
    "The loss of separation was 3.4 NM and 600 ft against the required 5 NM and 1000 ft.")


def _case(client, h, ref):
    return next(c for c in client.get("/api/cases", headers=h).json() if c["ref"] == ref)


def _keys(client, h, cid):
    c = client.get(f"/api/cases/{cid}", headers=h).json()
    return c, {b["id"]: f"f:{b['factor']}" if b.get("factor") else f"b:{cid}:{b['id']}" for b in c["model"]["blocks"]}


def test_tc_ies_01_reproduces_paper_example(client, viewer):
    """Ng et al. (2022) Fig. 13: all evidence 'Support' → Fuel exhaustion 94.54 Very probable, others 4.959."""
    c = _case(client, viewer, "CASE-F01")
    full, keys = _keys(client, viewer, c["id"])
    ev = [b["id"] for b in full["model"]["blocks"] if b["kind"] == "evidence"]
    ratings = {keys[b]: "S" for b in ev}
    r = client.post("/api/ies/infer", json={"case_ids": [c["id"]], "ratings": ratings}, headers=viewer).json()
    res = r["cases"][0]
    assert res["blocks"]["h1"]["crisp"] == pytest.approx(80.5, abs=1e-3) and res["blocks"]["h1"]["term"] == "S"
    out = res["findings"][0]["outputs"]
    assert out["FE"]["crisp"] == pytest.approx(94.54, abs=0.01) and out["FE"]["term"] == "VP"
    for m in ("FC", "FL", "LF", "FS", "FO"):
        assert out[m]["crisp"] == pytest.approx(4.959, abs=0.01) and out[m]["term"] == "HU"
    # Fig. 12: two pieces of evidence not provided → not determined, and they are returned as clues
    del ratings[keys["e2"]], ratings[keys["e3"]]
    r = client.post("/api/ies/infer", json={"case_ids": [c["id"]], "ratings": ratings}, headers=viewer).json()
    assert not r["cases"][0]["findings"][0]["determined"]
    assert {x["key"] for x in r["clues"]} == {keys["e2"], keys["e3"]}
    assert r["clues"][0]["priority"] == pytest.approx(0.5)
    # contradicting evidence lowers the finding
    ratings[keys["e2"]] = "SO"; ratings[keys["e3"]] = "S"
    r = client.post("/api/ies/infer", json={"case_ids": [c["id"]], "ratings": ratings}, headers=viewer).json()
    assert r["cases"][0]["blocks"]["h1"]["term"] == "O"
    assert r["cases"][0]["findings"][0]["outputs"]["FE"]["term"] == "IM"


def test_fuzzy_weakening_rule():
    m = {"blocks": [{"id": "a", "layer": "L", "kind": "evidence", "label": "a"}, {"id": "b", "layer": "L", "kind": "evidence", "label": "b"},
                    {"id": "h", "layer": "I", "kind": "hypothesis", "label": "h", "past": "SS"}],
         "edges": [{"source": "a", "target": "h"}, {"source": "b", "target": "h"}]}
    assert fuzzy.infer(m, {"a": "SS", "b": "S"})["blocks"]["h"]["term"] == "SS"
    assert fuzzy.infer(m, {"a": "NE", "b": "S"})["blocks"]["h"]["term"] == "S"
    with pytest.raises(fuzzy.FuzzyError):
        fuzzy.topo({"blocks": m["blocks"], "edges": m["edges"] + [{"source": "h", "target": "a"}]})


def test_tc_ies_02_bayesian_network(client, viewer):
    r = client.post("/api/ies/bn", json={"category": "ats-los", "ratings": {}}, headers=viewer).json()
    assert r["n_cases"] == 9 and r["counts"]["M2"] == 2
    assert r["prior"]["M2"] == pytest.approx(3 / 15, abs=1e-4)          # (2 + 1) / (9 + 6)
    # one rating by hand: similar callsigns present in 1 of 2 M2 cases and in no other case
    r = client.post("/api/ies/bn", json={"category": "ats-los", "ratings": {"f:L-SIMILAR-CALLSIGN": "SS"}}, headers=viewer).json()
    n = {"M1": 1, "M2": 2, "M3": 1, "M4": 2, "M5": 2, "M6": 1}
    lam = 0.975
    raw = {m: (n[m] + 1) / 15 * (lam * p + (1 - lam) * (1 - p))
           for m, p in {m: ((1 if m == "M2" else 0) + 1) / (n[m] + 2) for m in n}.items()}
    z = sum(raw.values())
    for m in n:
        assert r["posterior"][m] == pytest.approx(raw[m] / z, abs=1e-4)
    assert r["leading"] == "M2"
    assert all(c["factor"] != "L-SIMILAR-CALLSIGN" for c in r["clues"])
    assert all(c["voi_bits"] >= 0 for c in r["clues"]) and r["clues"] == sorted(r["clues"], key=lambda c: -c["voi_bits"])


def test_tc_ies_03_export_matches_bbn_engine(client, db_cases):
    ratings = {"L-SIMILAR-CALLSIGN": "SS", "I-HEARBACK-MISSED": "S", "L-COMBINED-SECTORS": "O"}
    net = casebn.learn(db_cases, [m["code"] for m in CATEGORIES["ats-los"]["mechanisms"]])
    post = casebn.posterior(net, ratings)
    exp = casebn.to_bbn(net, ratings)
    q = bbn.query(exp["network"], ["C"], exp["evidence"])
    got = q["marginals"]["C"] if "marginals" in q else q["C"]
    for i, m in enumerate(net["mechanisms"]):
        v = got[m] if isinstance(got, dict) else got[i]
        assert v == pytest.approx(post[m], abs=1e-6)


@pytest.fixture
def db_cases():
    from app.db import SessionLocal
    from app.models import InvCase
    with SessionLocal() as db:
        return [{"id": c.id, "ref": c.ref, "model": c.model} for c in db.query(InvCase).filter_by(category="ats-los", status="approved")]


def test_search_thesaurus_and_ranking(client, viewer):
    norm = casesearch.Normaliser(THESAURUS)
    assert norm.tokens("fuel added at Brisbane")[0] == norm.tokens("the pilot refuelled")[-1]
    r = client.post("/api/ies/search", json={"category": "ats-los", "text": DEMO_OCCURRENCE}, headers=viewer).json()
    top = [x["ref"] for x in r["results"][:3]]
    assert "CASE-01" in top and "I-HEARBACK-MISSED" in r["detected_factors"]
    assert r["results"][0]["matched_terms"]


def test_demo_investigation_study(client, viewer):
    s = next(x for x in client.get("/api/studies?method=ies", headers=viewer).json())
    st = client.get(f"/api/studies/{s['id']}", headers=viewer).json()
    res = st["results"]
    c1 = next(c for c in res["fuzzy"]["cases"] if c["ref"] == "CASE-01")
    assert c1["findings"][0]["outputs"]["M2"]["term"] == "VP"
    assert res["fuzzy"]["clues"] and res["bn"]["leading"] == "M2"


def test_case_lifecycle(client, viewer, assessor, reviewer, admin):
    body = {"title": "Test case", "category": "ats-los", "summary": "x"}
    assert client.post("/api/cases", json=body, headers=viewer).status_code == 403
    c = client.post("/api/cases", json=body, headers=assessor).json()
    assert c["status"] == "draft" and c["ref"].startswith("CASE-")
    # not approvable while empty; assessors cannot approve
    assert client.post(f"/api/cases/{c['id']}/approve", headers=assessor).status_code == 403
    assert client.post(f"/api/cases/{c['id']}/approve", headers=reviewer).status_code == 409
    m = {"blocks": [{"id": "e1", "layer": "L", "kind": "evidence", "label": "Similar callsigns", "factor": "L-SIMILAR-CALLSIGN", "past": "S"},
                    {"id": "f1", "layer": "E", "kind": "finding", "label": "LOS", "past": {"M2": "VP", "M1": "HU"}}],
         "edges": [{"source": "e1", "target": "f1"}]}
    bad = dict(body, model={**m, "edges": m["edges"] + [{"source": "f1", "target": "e1"}]})
    assert client.put(f"/api/cases/{c['id']}", json=bad, headers=assessor).status_code == 422
    assert client.put(f"/api/cases/{c['id']}", json=dict(body, model=m), headers=assessor).status_code == 200
    assert "no rules" in client.post(f"/api/cases/{c['id']}/approve", headers=reviewer).json()["detail"]
    r = client.post(f"/api/cases/{c['id']}/default-rules", headers=assessor).json()
    assert len(r["model"]["rules"]["f1"]) == 3  # confirming, weakening, contradicting
    r = client.post(f"/api/cases/{c['id']}/approve", headers=reviewer)
    assert r.status_code == 200 and r.json()["approved_by"] == "reviewer"
    # editing an approved case returns it to draft
    r = client.put(f"/api/cases/{c['id']}", json=dict(body, title="Test case (edited)", model=r.json()["model"]), headers=assessor).json()
    assert r["status"] == "draft"
    client.post(f"/api/cases/{c['id']}/approve", headers=reviewer)
    assert client.delete(f"/api/cases/{c['id']}", headers=assessor).status_code == 403
    assert client.delete(f"/api/cases/{c['id']}", headers=admin).status_code == 200


def test_tc_ies_04_offline_draft(client, assessor, reviewer):
    r = client.post("/api/cases/draft", json={"category": "ats-los", "title": "Drafted", "text": REPORT, "use_ai": True}, headers=assessor)
    assert r.status_code == 422 and "not configured" in r.json()["detail"]
    r = client.post("/api/cases/draft", json={"category": "ats-los", "title": "Drafted", "source": "test", "text": REPORT}, headers=assessor)
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["status"] == "draft" and c["provenance"]["method"] == "heuristic" and c["mechanism"] == "M2"
    factors = {b.get("factor") for b in c["model"]["blocks"]}
    assert {"L-SIMILAR-CALLSIGN", "L-FREQ-CONGESTION", "I-HEARBACK-MISSED", "R-CALLSIGN-ALERT", "E-LOS"} <= factors
    assert all(b["quote_verified"] for b in c["model"]["blocks"] if b.get("quote"))
    assert client.post(f"/api/cases/{c['id']}/approve", headers=reviewer).status_code == 200
    # PDF upload goes through the same drafter
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import Paragraph, SimpleDocTemplate
    from reportlab.lib.styles import getSampleStyleSheet
    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4).build([Paragraph(REPORT, getSampleStyleSheet()["Normal"])])
    r = client.post("/api/cases/draft-pdf", headers=assessor, data={"category": "ats-los", "title": "From PDF"},
                    files={"file": ("report.pdf", buf.getvalue(), "application/pdf")})
    assert r.status_code == 200, r.text
    assert r.json()["report_text"] and r.json()["n_blocks"] >= 5


def test_tc_ies_05_llm_draft_is_verified():
    """The AI drafter's output is checked: invented quotes are flagged and unknown factor codes dropped."""
    sent = {}

    def fake_post(url, key, payload):
        sent.update(payload)
        return {"model": "claude-test", "content": [{"type": "tool_use", "name": "record_accimap", "input": {
            "mechanism": "M2", "summary": "Hearback error.",
            "blocks": [{"id": "e1", "layer": "L", "kind": "evidence", "label": "Similar callsigns", "factor": "L-SIMILAR-CALLSIGN",
                        "quote": "two aircraft of the same operator with similar callsigns were on the sector frequency", "past": "SS"},
                       {"id": "e2", "layer": "I", "kind": "evidence", "label": "Invented", "factor": "X-UNKNOWN",
                        "quote": "the controller was distracted by a phone call", "past": "S"},
                       {"id": "f1", "layer": "E", "kind": "finding", "label": "LOS", "quote": "The loss of separation was 3.4 NM"}],
            "edges": [{"source": "e1", "target": "f1"}, {"source": "e2", "target": "f1"}, {"source": "f1", "target": "zz"}]}}]}
    out = draft.draft(REPORT, CATEGORIES["ats-los"], FACTORS["ats-los"], casesearch.Normaliser(THESAURUS), use_ai=True,
                      key="k", model_name="m", url="u", post=fake_post)
    assert sent["tool_choice"]["name"] == "record_accimap" and "REPORT TEXT" in sent["messages"][0]["content"]
    b = {x["id"]: x for x in out["model"]["blocks"]}
    assert b["e1"]["quote_verified"] and not b["e2"]["quote_verified"] and out["unverified_quotes"] == 1
    assert b["e2"]["factor"] is None and b["e2"]["factor_suggested"] == "X-UNKNOWN"
    assert b["f1"]["past"]["M2"] == "VP" and len(out["model"]["edges"]) == 2
    assert out["model"]["rules"]["f1"]


def test_bn_export_creates_study(client, assessor):
    s = next(x for x in client.get("/api/studies?method=ies", headers=assessor).json())
    r = client.post("/api/ies/bn/export", headers=assessor,
                    json={"assessment_id": s["assessment"]["id"], "category": "ats-los", "ratings": {"f:L-SIMILAR-CALLSIGN": "SS"}})
    assert r.status_code == 200
    st = r.json()
    assert st["method"] == "bbn" and st["model"]["evidence"] == {"obs_F_L_SIMILAR_CALLSIGN": "yes"}
    q = client.post("/api/calc/bbn", json={"network": st["model"]["network"], "evidence": st["model"]["evidence"]}, headers=assessor)
    assert q.status_code == 200
