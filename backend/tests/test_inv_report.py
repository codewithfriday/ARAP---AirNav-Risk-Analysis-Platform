"""DEMO-07 worked example (KNKT.24.10.22.04) and the investigation report generator (TC-ATB-06 … TC-ATB-08)."""
import base64
import io

from app import inv_report, knkt_demo
from app.engines import atsb


def test_tc_atb_06_knkt_example():
    m = knkt_demo.model()
    r = atsb.analyse(m)
    ft = {k: v["finding_type"] for k, v in r["factors"].items()}
    # the four KNKT contributing factors are represented by contributing safety factors
    assert {"F2", "F4", "F9", "F10", "F19"} <= {k for k, v in ft.items() if v == "contributing"}
    assert ft["F17"] == ft["F18"] == "excluded"
    # KNKT's fourth contributing factor (vibration/suction) did not reach 'likely' under the ATSB standard of proof
    assert ft["F6"] == "other"
    assert r["check_counts"]["error"] == 0 and r["check_counts"]["warning"] == 0
    ids = {i["id"] for i in r["issues"]}
    assert {"F9", "F10", "F13", "F14", "F15", "F16"} <= ids
    refs = {a.get("ref") for f in m["factors"] for a in f.get("actions", [])}
    for n in ("22.01", "22.02", "22.03", "22.04", "22.05", "22.06", "22.07"):
        assert any(x and x.endswith(n) for x in refs), n


def test_tc_atb_07_report_structure():
    m = knkt_demo.model()
    rep = inv_report.build_report(m)
    assert [s["title"][:2] for s in rep["sections"]] == ["1.", "2.", "3.", "4.", "5.", "6."]
    heads = [b["text"] for s in rep["sections"] for b in s["blocks"] if b["type"] == "h"]
    for h in ("1.1 Synopsis", "1.2 Consequences", "1.3 Core finding", "2.1 Occurrence timeline", "2.3 Immediate actions taken",
              "3.1 Occurrence events (O)", "3.2 Individual actions (I)", "3.3 Local conditions (L)", "3.4 Risk controls (R)",
              "3.5 Organisational influences (O)"):
        assert h in heads, h
    assert any(h.startswith("Appendix C") for h in heads)
    s5 = next(s for s in rep["sections"] if s["id"] == "s5")
    t = next(b for b in s5["blocks"] if b["type"] == "table")
    assert t["header"] == ["ORLIO layer", "Identified deficiency", "Corrective action required", "Action owner", "Target date"]
    assert any(r[2].startswith("[Elimination]") for r in t["rows"]) and any(r[4] == "[Date]" for r in t["rows"])
    # every contributing factor (except the occurrence event) has a corrective action row
    contrib = [f for f in m["factors"] if atsb.analyse(m)["factors"][f["id"]]["finding_type"] == "contributing" and f["type"] != "OE"]
    for f in contrib:
        assert any(r[1].startswith(f["id"] + " ") for r in t["rows"]), f["id"]
    # 4.1 chain reaches the occurrence; the local-rationality text appears for individual actions
    s4 = next(s for s in rep["sections"] if s["id"] == "s4")
    items = next(b for b in s4["blocks"] if b["type"] == "numbered")["items"]
    assert all(i.rstrip(".").endswith("the occurrence") for i in items)
    s3 = next(s for s in rep["sections"] if s["id"] == "s3")
    assert any(k == "Why it made sense at the time" for b in s3["blocks"] if b["type"] == "kv" for k, _ in b["rows"])


def test_tc_atb_07b_missing_action_flagged():
    m = knkt_demo.model()
    for f in m["factors"]:
        if f["id"] == "F3":
            f["actions"] = []
    r = atsb.analyse(m)
    assert ("F3", "corrective") in {(c["ref"], c["code"]) for c in r["checks"]}
    rep = inv_report.build_report(m, r)
    t = next(b for b in rep["sections"][4]["blocks"] if b["type"] == "table")
    row = next(x for x in t["rows"] if x[1].startswith("F3 "))
    assert row[2].startswith("[No corrective action") and row[3] == "[Owner]"


def test_tc_atb_08_renderers_and_api(client, viewer):
    m = knkt_demo.model()
    rep = inv_report.build_report(m)
    png = inv_report.factor_map_png(m, atsb.analyse(m))
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    from docx import Document
    d = Document(io.BytesIO(inv_report.to_docx(rep)))
    assert any(p.text.startswith("5. Safety recommendations") for p in d.paragraphs) and len(d.inline_shapes) >= 4
    assert inv_report.to_pdf(rep)[:5] == b"%PDF-"
    # API: DEMO-07 seeded, JSON / DOCX / PDF
    st = [s for s in client.get("/api/studies?method=atsb", headers=viewer).json()]
    knkt = next(s for s in st if "KNKT" in s["title"] or "PK-GMP" in s["title"])
    r = client.post(f"/api/studies/{knkt['id']}/investigation-report", json={"format": "json"}, headers=viewer)
    assert r.status_code == 200 and r.json()["meta"]["project"].startswith("DEMO-07")
    img = next(b for b in r.json()["sections"][5]["blocks"] if b["type"] == "image")
    assert base64.b64decode(img["data"].split(",", 1)[1])[:4] == b"\x89PNG"
    r = client.post(f"/api/studies/{knkt['id']}/investigation-report", json={"format": "pdf"}, headers=viewer)
    assert r.status_code == 200 and r.content[:5] == b"%PDF-"
    r = client.post(f"/api/studies/{knkt['id']}/investigation-report", json={"format": "docx", "model": {"factors": []}}, headers=viewer)
    assert r.status_code == 200 and r.content[:2] == b"PK"
    other = next(s for s in client.get("/api/studies?method=fta", headers=viewer).json())
    assert client.post(f"/api/studies/{other['id']}/investigation-report", json={}, headers=viewer).status_code == 422
