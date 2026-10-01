"""Demo project DEMO-02: worked examples of the thirteen methods added in Manual edition 0.2."""
from sqlalchemy.orm import Session

from . import seed2 as S
from .engines import crm, eta, hra, orc, rbd, sej, sim
from .models import Assessment, Project, Study


def _rows(prefix, rows):
    return [{"id": f"{prefix}-{i:02d}", **r} for i, r in enumerate(rows, 1)]


def gsn_model(fha_id=None, fta_id=None, sim_id=None):
    n = [
        {"id": "G1", "type": "goal", "text": "Introduction of ADS-B surveillance in en-route sector X is acceptably safe"},
        {"id": "C1", "type": "context", "parent": "G1", "text": "Scope, environment and assumptions of assessment DEMO-01"},
        {"id": "C2", "type": "context", "parent": "G1", "text": "AirNav risk classification scheme, version 1"},
        {"id": "S1", "type": "strategy", "parent": "G1", "text": "Argue over the specification, the implementation and the transition"},
        {"id": "G2", "type": "goal", "parent": "S1", "text": "Every FHA failure condition meets its safety objective"},
        {"id": "S2", "type": "strategy", "parent": "G2", "text": "Argue over each failure condition FC-1 … FC-5"},
        {"id": "G3", "type": "goal", "parent": "S2", "text": "FC-3 (undetected erroneous position, one aircraft) ≤ 1×10⁻⁷ per operating hour"},
        {"id": "Sn1", "type": "solution", "parent": "G3", "text": "FHA worksheet — objectives", "evidence": {"kind": "study", "ref": fha_id}},
        {"id": "Sn2", "type": "solution", "parent": "G3", "text": "FTA result for the integrity-monitoring architecture", "evidence": {"kind": "study", "ref": fta_id}},
        {"id": "G4", "type": "goal", "parent": "S2", "text": "FC-4 (undetected erroneous position, several aircraft) ≤ 1×10⁻⁹ per operating hour", "undeveloped": True},
        {"id": "A1", "type": "assumption", "parent": "G4", "text": "Radar coverage above FL245 remains available as an independent cross-check"},
        {"id": "G5", "type": "goal", "parent": "S1", "text": "Residual risks are ALARP and accepted by the proper authority"},
        {"id": "Sn3", "type": "solution", "parent": "G5", "text": "Hazard log entry HZ-0003 with acceptance record", "evidence": {"kind": "hazard", "ref": "HZ-0003"}},
        {"id": "J1", "type": "justification", "parent": "G5", "text": "Acceptance authorities follow Manual Table 3.3"},
        {"id": "G6", "type": "goal", "parent": "S1", "text": "Transition to operations does not increase controller workload beyond acceptable limits"},
        {"id": "Sn4", "type": "solution", "parent": "G6", "text": "Real-time simulation results (workload, R/T occupancy)", "evidence": {"kind": "study", "ref": sim_id}},
    ]
    return {"nodes": n}


HTA = {"tasks": [
    {"id": "0", "parent": None, "title": "Respond to an STCA alert", "plan": "Do 1–3 in order without delay; do 4 once separation is increasing."},
    {"id": "1", "parent": "0", "title": "Detect the alert", "plan": "Do 1.1 then 1.2", "hra": "T1"},
    {"id": "1.1", "parent": "1", "title": "See / hear the alert on the situation display", "error_modes": ["Information not obtained"]},
    {"id": "1.2", "parent": "1", "title": "Identify the aircraft pair involved", "error_modes": ["Action on wrong object"]},
    {"id": "2", "parent": "0", "title": "Assess the situation", "plan": "Do 2.1 and 2.2 together"},
    {"id": "2.1", "parent": "2", "title": "Check levels, tracks and clearances of both aircraft"},
    {"id": "2.2", "parent": "2", "title": "Decide the resolution (turn and/or level)", "error_modes": ["Wrong action"]},
    {"id": "3", "parent": "0", "title": "Issue avoiding action", "plan": "Do 3.1; if no read-back in 5 s repeat 3.1; then 3.2"},
    {"id": "3.1", "parent": "3", "title": "Transmit instruction with 'avoiding action' phraseology", "error_modes": ["Action too early / late", "Wrong information communicated"]},
    {"id": "3.2", "parent": "3", "title": "Obtain and check read-back", "error_modes": ["Check omitted"]},
    {"id": "4", "parent": "0", "title": "Monitor and restore normal operations", "plan": "Do 4.1 continuously; 4.2 when clear of conflict; 4.3 after the event"},
    {"id": "4.1", "parent": "4", "title": "Monitor separation until increasing"},
    {"id": "4.2", "parent": "4", "title": "Issue further clearances to resume the plan"},
    {"id": "4.3", "parent": "4", "title": "Report the occurrence", "error_modes": ["Information not communicated"]},
]}

CCA = {
    "zsa": _rows("Z", [
        {"zone": "ACC equipment room 1", "equipment": "Main SDP servers; fallback SDP servers; core network switches",
         "concern": "Main and fallback processing co-located", "check": "Redundant items in separate fire zones",
         "finding": "Both SDP chains in one room and one fire zone", "action": "Relocate fallback to equipment room 2"},
        {"zone": "ACC power room", "equipment": "UPS A/B, generator switchgear, main distribution board",
         "concern": "Shared cable route to equipment rooms", "check": "Diverse cable routes for A and B feeds",
         "finding": "A and B feeds share one cable tray for 30 m", "action": "Separate trays or fire-rated barrier"},
        {"zone": "Radar site Cengkareng", "equipment": "MSSR, ADS-B ground station, site UPS",
         "concern": "Lightning exposure of tower and cabling", "check": "Lightning protection and surge arrestors to standard",
         "finding": "Surge arrestors on data lines missing", "action": "Install surge protection"}]),
    "pra": _rows("P", [
        {"risk": "Fire", "zones": "ACC equipment room 1", "equipment": "Main and fallback SDP", "redundancy_defeated": True,
         "effect": "Total loss of surveillance processing", "severity": "B", "mitigation": "Gas suppression; fire detection", "action": "See Z-01"},
        {"risk": "Earthquake", "zones": "ACC building", "equipment": "All ACC systems", "redundancy_defeated": True,
         "effect": "Evacuation; loss of ACC", "severity": "B", "mitigation": "Contingency ACC; seismic racks", "action": "Test contingency transfer annually"},
        {"risk": "Volcanic ash", "zones": "Radar and VHF sites (Java)", "equipment": "HVAC intakes, generators",
         "redundancy_defeated": False, "effect": "Overheating; generator failure", "severity": "C", "mitigation": "Filters; ash procedure", "action": "Stock spare filters at sites"},
        {"risk": "Lightning", "zones": "Radar site Cengkareng", "equipment": "MSSR and ADS-B station", "redundancy_defeated": True,
         "effect": "Loss of both sensors at one site", "severity": "C", "mitigation": "Second radar site", "action": "See Z-03"}]),
    "cma": _rows("CM", [
        {"claim": "Main SDP (E5) and fallback (E6) fail independently", "items": "E5, E6", "source": "Software",
         "analysis": "Fallback runs the same software baseline as the main system", "independent": "No", "action": "Diverse fallback or β-factor in FTA"},
        {"claim": "Mains (E7), UPS (E8) and generator (E9) fail independently", "items": "E7, E8, E9", "source": "Location",
         "analysis": "UPS and generator switchgear share the power room (fire zone)", "independent": "Partly", "action": "Include fire CCF in FTA"},
        {"claim": "Radar A, radar B and ADS-B inputs are independent", "items": "E1, E2, E3", "source": "Shared utilities (power, HVAC, network)",
         "analysis": "All three use the single surveillance WAN (E4)", "independent": "No", "action": "Diverse data path (FTA shows 82% of risk)"}]),
}

SWIFT = _rows("W", [
    {"guideword": "Procedures", "what_if": "What if the runway is handed back before all works vehicles have left?", "consequence": "Aircraft lands with vehicle on runway",
     "safeguards": "Works completion check; runway inspection", "severity": "A", "likelihood": 2, "recommendation": "Signed hand-back with vehicle count", "owner": "Aerodrome ops"},
    {"guideword": "Information and communication", "what_if": "What if the NOTAM for the closure is not published in time?", "consequence": "Crews plan for a closed runway",
     "safeguards": "ATIS; TWR check", "severity": "C", "likelihood": 3, "recommendation": "NOTAM 7 days ahead; AIM checklist", "owner": "AIM"},
    {"guideword": "Equipment and utilities", "what_if": "What if runway lighting is left in the wrong configuration after works?", "consequence": "Misleading lighting at night",
     "safeguards": "Lighting check before re-opening", "severity": "C", "likelihood": 2, "recommendation": "Add lighting to hand-back checklist", "owner": "AFL engineering"},
    {"guideword": "Timing and sequence", "what_if": "What if works overrun into the morning arrival peak?", "consequence": "Single-runway ops at peak; holding",
     "safeguards": "Flow measures", "severity": "D", "likelihood": 3, "recommendation": "Hard stop time; contingency flow plan", "owner": "APP supervisor"},
    {"guideword": "People", "what_if": "What if a works driver is unfamiliar with the aerodrome at night?", "consequence": "Vehicle incursion onto taxiway in use",
     "safeguards": "Escort", "severity": "B", "likelihood": 2, "recommendation": "Mandatory escort; briefing", "owner": "Works contractor"}])

SEC = _rows("SR", [
    {"asset": "ADS-B ground station / SDP input", "threat": "Injection of false ADS-B targets (spoofing)", "source": "External attacker",
     "vulnerability": "ADS-B messages unauthenticated", "c": 1, "i": 5, "a": 3, "likelihood": 3, "controls": "Radar cross-check where available; multilateration",
     "safety_severity": "B", "treatment": "Plausibility checks; alerting on radar/ADS-B mismatch", "owner": "CNS engineering"},
    {"asset": "Flight data processing (FDP)", "threat": "Ransomware encrypts FDP servers", "source": "External attacker",
     "vulnerability": "Flat network between office and ops systems", "c": 3, "i": 4, "a": 5, "likelihood": 2, "controls": "Backups; antivirus",
     "safety_severity": "C", "treatment": "Network segmentation; offline backups; contingency strips", "owner": "IT security"},
    {"asset": "VCCS maintenance access", "threat": "Compromise of vendor remote-maintenance account", "source": "Supplier / third party",
     "vulnerability": "Shared vendor credentials", "c": 3, "i": 4, "a": 5, "likelihood": 2, "controls": "VPN",
     "safety_severity": "B", "treatment": "Named accounts with MFA; session approval and logging", "owner": "IT security"},
    {"asset": "ATM adaptation data", "threat": "Unauthorised change to sector or safety-net parameters", "source": "Insider (accidental)",
     "vulnerability": "No two-person rule on adaptation changes", "c": 1, "i": 5, "a": 2, "likelihood": 2, "controls": "Change log",
     "safety_severity": "B", "treatment": "Two-person rule; checksum verification before loading", "owner": "ATM systems"}])

INV = {
    "occurrence": {"ref": "OCC-102", "date": "2026-08-14", "location": "Soekarno-Hatta, RWY 07L",
                   "summary": "At night a works vehicle entered the runway strip of 07L without clearance. RIMCAS alerted; the TWR ATCO instructed "
                              "an aircraft on 4 NM final to go around. Closest distance about 3.5 NM."},
    "soam": {
        "barriers": [{"text": "Driver RT training and licence", "category": "Awareness", "status": "failed", "bowtie_link": None},
                     {"text": "Follow-me / escort for works vehicles", "category": "Restriction", "status": "absent", "bowtie_link": None},
                     {"text": "Stop bar at holding point K3", "category": "Restriction", "status": "failed", "bowtie_link": None},
                     {"text": "RIMCAS alert", "category": "Detection", "status": "effective", "bowtie_link": None},
                     {"text": "ATCO go-around instruction", "category": "Control and recovery", "status": "effective", "bowtie_link": None}],
        "human": ["Driver crossed the lit stop bar believing the runway was closed", "TWR did not challenge the driver's position report"],
        "contextual": [{"category": "Workplace conditions", "text": "Night works; poor signage visibility near K3"},
                       {"category": "Human performance limitations", "text": "Driver's mental model: runway closed for works"},
                       {"category": "Physiological and emotional factors", "text": "Driver at end of 12-hour shift"}],
        "orgfactors": [{"category": "Training (TR)", "text": "Contractor drivers not trained on runway closure procedures"},
                       {"category": "Change management (CM)", "text": "Works plan changed the closure time without a risk assessment"},
                       {"category": "Communication (CO)", "text": "Revised closure time not briefed to contractor"}],
        "actions": [{"text": "Escort all contractor vehicles at night", "addresses": "Follow-me / escort", "owner": "Aerodrome ops"},
                    {"text": "Include contractors in RT and aerodrome familiarisation training", "addresses": "Training (TR)", "owner": "Aerodrome ops"},
                    {"text": "Risk-assess any change to works timing", "addresses": "Change management (CM)", "owner": "SQRM"}]},
    "hfacs": {"selected": {"Skill-based errors": "Driver crossed lit stop bar", "Adverse physiological states": "12-hour shift",
                           "Physical environment": "Poor signage at night", "Inadequate supervision": "No escort for contractor",
                           "Organisational process": "Works-timing change not risk-assessed"}},
    "tripod": {"events": [{"id": "EV1", "agent": "Works vehicle movement", "object": "Active runway 07L / aircraft on final",
                           "event": "Vehicle enters runway strip without clearance",
                           "barriers": [{"barrier": "Stop bar at K3", "status": "failed", "immediate_cause": "Driver crossed lit stop bar",
                                         "precondition": "Driver believed runway was closed", "underlying_cause": "Closure time change not communicated",
                                         "brf": "Communication (CO)"},
                                        {"barrier": "Escort of contractor vehicles", "status": "missing", "immediate_cause": "",
                                         "precondition": "", "underlying_cause": "Escort not required by works procedure", "brf": "Procedures (PR)"}]}]},
}


def seed_demo_v2(db: Session):
    if db.query(Project).filter_by(code="DEMO-02").first():
        return
    p = Project(code="DEMO-02", title="Manual worked examples — extended methods (edition 0.2)", change_type="airspace",
                units="Jakarta ACC; Soekarno-Hatta TWR", sponsor="SQRM",
                description="One study per method added in Manual edition 0.2 (chapters 18–30).")
    db.add(p); db.flush()
    a = Assessment(project_id=p.id, title="Worked examples — thirteen extended methods", created_by="assessor",
                   scope="Demonstration of the extended NAVRAP method modules using the Manual's examples.",
                   environment="Illustrative values only.", assumptions="All numbers are illustrative.")
    db.add(a); db.flush()
    ids = {}

    def study(key, method, title, model, results=None):
        s = Study(assessment_id=a.id, method=method, title=title, model=model, results=results or {},
                  participants=[{"name": "Ayu Assessor", "role": "Facilitator"}, {"name": "SME", "role": "SME"}])
        db.add(s); db.flush(); ids[key] = s.id; return s

    L, m = S.CRM_LATERAL, S.CRM_LAT_MODEL
    crm_model = {"vertical": {**S.CRM_VERTICAL, "tls": 2.5e-9},
                 "lateral": {**{k: L[k] for k in ("pz0", "lx", "lz", "sx", "ey_same", "ey_opp", "dv", "v", "zdot", "ydot_sy", "tls")},
                             "ly": m["lam_y"], "model": m["model"], "scale": m["scale"], "spacing": 15.0,
                             "spacings": [5, 7.5, 10, 12.5, 15, 20, 25, 30]}}
    study("crm", "crm", "CRM — RVSM vertical risk and parallel-route spacing (Manual §18.4)", crm_model,
          {"vertical": crm.vertical(**S.CRM_VERTICAL)})
    study("eta", "eta", "ETA — conflict after a level bust (Manual §19.3)", S.ETA_MODEL, eta.analyse(S.ETA_MODEL))
    study("hra", "hra", "HRA — controller and technician tasks (Manual §20.4)", {"tasks": S.HRA_TASKS},
          {"tasks": [{"id": t["id"], **hra.assess(t["library"], t["gtt"], t["epcs"])} for t in S.HRA_TASKS]})
    occ = [dict(c, rat={}, severity_class="", notes="") for c in S.ERC_CASES]
    occ[0]["rat"] = S.RAT_CASE; occ[0]["severity_class"] = "B"
    study("orc", "orc", "Occurrence risk classification — ERC and RAT (Manual §21.4)", {"occurrences": occ})
    study("cca", "cca", "Common cause analysis — ACC surveillance chain (Manual §23.3)", CCA)
    study("rbd", "rbd", "RBD and Markov — sector VHF availability (Manual §24.4)", {"rbd": S.RBD_VHF, "markov": S.MARKOV_STANDBY},
          {"rbd": rbd.rbd(S.RBD_VHF), "markov": rbd.markov(**S.MARKOV_STANDBY)})
    study("swift", "swift", "SWIFT — night works on runway 07L/25R (Manual §25.3)", {"rows": SWIFT})
    study("hta", "hta", "HTA — respond to an STCA alert (Manual §26.3)", {**HTA, "hra_study": ids.get("hra")})
    simm = {"exercise": {"title": "RTS of new arrival procedure (sector APP-N)", "type": "Real-time simulation",
                         "objectives": "Show the new procedure does not increase workload or R/T occupancy and does not add conflicts.",
                         "scenarios": "Peak traffic 38 arrivals/h; 8 runs per condition; 4 ATCO teams; counterbalanced order",
                         "participants": "8 current APP ATCOs, 4 pseudo-pilots"}, "measures": S.SIM_MEASURES}
    study("sim", "sim", "Simulation — new arrival procedure (Manual §27.4)", simm, {"measures": sim.analyse(S.SIM_MEASURES)})
    sejm = {"experts": S.SEJ_EXPERTS, "items": S.SEJ_ITEMS, "alpha": 0.0,
            "delphi": {"question": "Probability that the ATCO does not resolve a level-bust conflict before STCA", "rounds": S.DELPHI_ROUNDS}}
    study("sej", "sej", "Expert judgement — ATCO detection probability (Manual §28.4)", sejm,
          {"classical": sej.classical(S.SEJ_EXPERTS, S.SEJ_ITEMS), "delphi": sej.delphi(S.DELPHI_ROUNDS)})
    study("sec", "sec", "Security risk assessment — surveillance and FDP (Manual §29.4)", {"rows": SEC})
    study("inv", "inv", "Investigation OCC-102 — works vehicle on runway strip (Manual §30.5)", INV)
    # GSN last so it can reference evidence in both demo projects
    fha = db.query(Study).filter_by(method="fha").first()
    fta = db.query(Study).filter_by(method="fta").first()
    study("gsn", "gsn", "Safety argument — ADS-B introduction (Manual §22.3)", gsn_model(fha.id if fha else None, fta.id if fta else None, ids.get("sim")))
    # link the investigation's failed barriers to the demo bowtie barriers
    bt = db.query(Study).filter_by(method="bowtie").first()
    if bt:
        inv = db.get(Study, ids["inv"])
        model = dict(inv.model)
        soam = dict(model["soam"])
        links = {"Driver RT training and licence": "PB3", "Follow-me / escort for works vehicles": "PB4", "Stop bar at holding point K3": "PB2",
                 "RIMCAS alert": "RB1", "ATCO go-around instruction": "RB2"}
        soam["barriers"] = [dict(b, bowtie_link=f"{bt.id}:{links[b['text']]}") for b in soam["barriers"]]
        model["soam"] = soam
        inv.model = model
    db.commit()
