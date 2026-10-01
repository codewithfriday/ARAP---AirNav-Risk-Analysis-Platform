"""Demo data: the worked examples of the AirNav Risk Analysis Manual, one study per method."""
from datetime import date, timedelta

from sqlalchemy.orm import Session

from .engines import bbn as bbn_engine
from .engines import fatigue as fat_engine
from .engines import fta as fta_engine
from .engines import lopa as lopa_engine
from .models import Action, Assessment, Control, Hazard, Project, Study, User
from .security import hash_password
from .seed import BBN_NET, FTA_TREE

DEMO_USERS = [
    ("assessor", "Ayu Assessor", "assessor", [], "Jakarta ACC"),
    ("reviewer", "Rudi Reviewer", "reviewer", [], "SQRM"),
    ("director", "Dewi Director", "authority", ["tolerable_lower", "acceptable"], "Directorate of Operations"),
    ("accexec", "Accountable Executive", "authority", ["tolerable_upper", "tolerable_lower", "acceptable"], "Board"),
    ("viewer", "Vina Viewer", "viewer", [], "Makassar ACC"),
]


def _bowtie():
    b = {
        "PB1": ("Standard phraseology", "human", "good"), "PB2": ("Stop bars operated H24", "hardware", "good"),
        "PB3": ("Driver RT training & licence", "human", "good"), "PB4": ("Follow-me / escort", "human", "good"),
        "PB5": ("Runway strip display", "human-hardware", "poor"), "PB6": ("Read-back / hear-back", "human", "good"),
        "RB1": ("RIMCAS / A-SMGCS alert", "hardware", "good"), "RB2": ("ATCO intervention", "human", "good"),
        "RB3": ("Pilot visual scan", "human", "poor"), "RB4": ("ARFF response", "human-hardware", "good"),
        "RB5": ("Go-around procedure", "human", "very good"), "RB6": ("ATCO re-sequencing", "human", "good"),
    }
    owners = {"PB2": "Aerodrome operator", "RB1": "CNS engineering", "RB4": "Aerodrome operator"}
    return {
        "hazard": "Aircraft and vehicle movements on/near active runway",
        "top_event": "Unauthorised entry onto active runway",
        "threats": [{"id": "T1", "text": "Pilot misinterprets taxi clearance", "barriers": ["PB1", "PB2"]},
                    {"id": "T2", "text": "Vehicle driver loses position awareness", "barriers": ["PB3", "PB4"]},
                    {"id": "T3", "text": "ATCO issues conflicting clearance", "barriers": ["PB5", "PB6"]}],
        "consequences": [{"id": "C1", "text": "Runway collision", "severity": "A", "barriers": ["RB1", "RB2"]},
                         {"id": "C2", "text": "High-energy rejected take-off", "severity": "C", "barriers": ["RB3", "RB4"]},
                         {"id": "C3", "text": "Go-around / loss of separation", "severity": "C", "barriers": ["RB5", "RB6"]}],
        "barriers": {k: {"id": k, "text": v[0], "kind": v[1], "effectiveness": v[2], "owner": owners.get(k, "TWR unit chief"),
                         "critical": k in ("PB2", "PB6", "RB1", "RB2"), "verification": "existing-verified"} for k, v in b.items()},
        "escalation": [{"id": "EF1", "text": "Stop bar unserviceable (U/S)", "barrier": "PB2",
                        "ef_barriers": ["No conditional clearances; follow-me mandatory"]}],
    }


def _rows(prefix, rows):
    return [{"id": f"{prefix}-{i:02d}", **r} for i, r in enumerate(rows, 1)]


def seed_demo(db: Session):
    if db.query(Project).count():
        return
    for u, n, r, scope, unit in DEMO_USERS:
        if not db.query(User).filter_by(username=u).first():
            db.add(User(username=u, full_name=n, role=r, authority_scope=scope, unit=unit, password_hash=hash_password("demo1234")))
    p = Project(code="DEMO-01", title="Manual worked examples", change_type="system", units="Jakarta ACC; Soekarno-Hatta TWR",
                sponsor="SQRM", description="One study per method, reproducing the examples in the AirNav Risk Analysis Manual.")
    db.add(p); db.flush()
    a = Assessment(project_id=p.id, title="Worked examples — all twelve methods", created_by="assessor",
                   scope="Demonstration of every NAVRAP method module using the Manual's examples.",
                   environment="Illustrative values only.", assumptions="All numbers are illustrative (Manual, How to use).")
    db.add(a); db.flush()

    def study(method, title, model, results=None):
        s = Study(assessment_id=a.id, method=method, title=title, model=model, results=results or {},
                  participants=[{"name": "Ayu Assessor", "role": "Facilitator"}, {"name": "TWR ATCO", "role": "SME"}])
        db.add(s); db.flush(); return s

    bt = study("bowtie", "Runway incursion bowtie (Manual §6)", _bowtie())
    study("hazid", "HAZID — approach unit relocation (Manual §7.4)", {"rows": _rows("HZ", [
        {"guideword": "Transition", "hazard": "Loss of surveillance display at cut-over", "causes": "Data feed not re-routed; configuration error", "consequences": "Loss of separation during cut-over", "controls": "Cut-over at low traffic; old site on hot standby", "severity": "C", "likelihood": 3, "actions": "HAZOP of cut-over plan; rollback criteria", "owner": "Project manager", "detailed_method": "hazop"},
        {"guideword": "People", "hazard": "ATCOs unfamiliar with new CWP HMI", "causes": "Short training window", "consequences": "Delayed or erroneous inputs", "controls": "Simulator training", "severity": "D", "likelihood": 4, "actions": "Minimum hours on new CWP before live ops", "owner": "Training"},
        {"guideword": "Interfaces", "hazard": "Wrong telephone coordination lines to TWR", "causes": "VCCS mapping error", "consequences": "Late coordination of missed approach", "controls": "Test plan", "severity": "C", "likelihood": 3, "actions": "End-to-end line check with each TWR", "owner": "CNS engineering"},
        {"guideword": "Equipment / systems", "hazard": "Single power feed to new building", "causes": "Design", "consequences": "Total loss of service", "controls": "UPS 30 min", "severity": "B", "likelihood": 2, "actions": "Second feed or genset; FMEA of power", "owner": "Facilities", "detailed_method": "fmea"},
        {"guideword": "Environment", "hazard": "New site outside radio line of sight of low-level sector", "causes": "Topography", "consequences": "Loss of VHF contact below FL050", "controls": "None yet", "severity": "B", "likelihood": 3, "actions": "Coverage study; remote radio site", "owner": "CNS engineering"}])})
    study("hazop", "HAZOP — estimate message coordination (Manual §8.3)", {
        "nodes": [{"id": "N3", "name": "Node 3: EST/CPL message upstream → downstream", "type": "data-flow",
                   "intent": "Downstream sector receives complete, correct and timely data for every flight crossing the boundary."}],
        "rows": _rows("HP", [
            {"node": "N3", "parameter": "Message", "guideword": "No / Not", "deviation": "Estimate not received", "causes": "Link failure; flight plan not activated; address error", "consequences": "Unknown traffic enters sector", "safeguards": "Link-status alarm; verbal coordination backup", "severity": "C", "likelihood": 3, "recommendation": "Alert when a flight is within X min of boundary with no EST"},
            {"node": "N3", "parameter": "Content", "guideword": "Other than", "deviation": "Coordinated level differs from actual", "causes": "Level changed after EST; no revision", "consequences": "Level conflict downstream", "safeguards": "Mode C/S check; STCA", "severity": "B", "likelihood": 3, "recommendation": "Automatic revision message on cleared-level change"},
            {"node": "N3", "parameter": "Timing", "guideword": "Late", "deviation": "Estimate inside agreed time", "causes": "Short-notice route change", "consequences": "Workload", "safeguards": "LoA fallback: verbal", "severity": "D", "likelihood": 4, "recommendation": "Monitor late-EST rate as SPI"}])})
    study("jha", "JHA — obstruction light on radar tower (Manual §9.3)", {
        "job": {"title": "Replace obstruction light on radar tower", "location": "Radar site", "permits": "Permit to work; LOTO"},
        "rows": _rows("S", [
            {"step": "Coordinate outage and obtain permit to work", "hazards": "Radar removed without ATS awareness; RF exposure", "controls": "ATS coordination and NOTAM; transmitter locked out; permit signed", "hierarchy": "Engineering", "responsible": "Site supervisor"},
            {"step": "Inspect climbing system and weather", "hazards": "Defective fall arrest; lightning; wind", "controls": "Pre-use inspection; stop work limits", "hierarchy": "Administrative", "responsible": "Climber"},
            {"step": "Climb tower with tools", "hazards": "Fall from height; dropped objects", "controls": "Harness 100% tie-off; tethered tools; exclusion zone", "hierarchy": "PPE", "responsible": "Climber"},
            {"step": "Isolate light circuit and replace lamp", "hazards": "Electric shock", "controls": "Isolate, LOTO, test for dead", "hierarchy": "Engineering", "responsible": "Technician"},
            {"step": "Return radar to service and hand back to ATS", "hazards": "Wrong configuration", "controls": "Functional check; formal hand-back", "hierarchy": "Administrative", "responsible": "Radar engineer"}])})
    study("fmea", "FMEA — sector VHF air–ground (Manual §10.3)", {"rows": _rows("FM", [
        {"item": "Main VHF transmitter", "failure_mode": "No RF output", "cause": "PA failure", "end_effect": "Loss of main Tx on frequency", "detection_method": "Radio monitoring alarm", "compensation": "Auto switch to standby Tx", "s": 4, "o": 4, "d": 2},
        {"item": "Main VHF transmitter", "failure_mode": "Stuck PTT", "cause": "Relay / VCCS fault", "end_effect": "Frequency blocked for all users", "detection_method": "ATCO notices; timer alarm", "compensation": "PTT time-out; switch site", "s": 8, "o": 3, "d": 4},
        {"item": "VCCS", "failure_mode": "Total loss", "cause": "Software fault; power", "end_effect": "Loss of all voice at CWP", "detection_method": "Immediate", "compensation": "Backup radios at CWP", "s": 8, "o": 2, "d": 1},
        {"item": "Leased line to remote site", "failure_mode": "Loss", "cause": "Carrier outage", "end_effect": "Loss of remote coverage", "detection_method": "Link alarm", "compensation": "Second path via VSAT", "s": 6, "o": 5, "d": 2},
        {"item": "Main + standby receivers", "failure_mode": "Degraded sensitivity", "cause": "Water ingress in antenna or cable", "end_effect": "Weak/unreadable pilot calls", "detection_method": "Late — pilot complaints", "compensation": "None", "s": 6, "o": 3, "d": 7}])})
    lopa_model = {"scenario": "Level bust leading to a potential mid-air collision",
                  "initiating": {"label": "Level bust in sector X", "frequency": 0.5, "source": "Illustrative"},
                  "unit": "per year", "target": 1e-5,
                  "modifiers": [{"label": "Conflicting traffic present", "probability": 0.05}],
                  "safeguards": [{"label": "ATCO monitoring and intervention", "pfd": 0.1, "independent": True, "effective": True, "dependable": True, "auditable": True, "dependencies": ["surveillance"]},
                                 {"label": "STCA alert and ATCO resolution", "pfd": 0.1, "independent": True, "effective": True, "dependable": True, "auditable": True, "dependencies": ["surveillance"]},
                                 {"label": "ACAS II RA followed", "pfd": 0.1, "independent": True, "effective": True, "dependable": True, "auditable": True},
                                 {"label": "SFL mismatch alert (proposed)", "pfd": 0.1, "independent": True, "effective": True, "dependable": False, "auditable": True, "justification": "Proposed — tick Dependable once implemented and verified; closes the gap to 2.5e-6/yr"},
                                 {"label": "Recurrent RT training", "pfd": 0.1, "independent": False, "effective": False, "dependable": True, "auditable": True, "justification": "Supports the human IPL; not an IPL itself"}]}
    lres = lopa_engine.analyse(0.5, lopa_model["modifiers"], lopa_model["safeguards"], 1e-5)
    study("lopa", "LOPA — level bust (Manual §11.3)", lopa_model, lres)
    study("fha", "FHA — ADS-B en-route surveillance (Manual §12.3)", {"rows": _rows("FC", [
        {"function": "F1 Provide ADS-B position/identity", "failure_type": "Total loss", "condition": "Total loss of ADS-B data for all aircraft (detected)", "effect": "Revert to radar/procedural; workload peak", "severity": "C", "objective": 1e-5, "requirements": ""},
        {"function": "F1 Provide ADS-B position/identity", "failure_type": "Partial loss / degradation", "condition": "Loss of data for a single aircraft (detected)", "effect": "Procedural separation for one aircraft", "severity": "D", "objective": 1e-3},
        {"function": "F1 Provide ADS-B position/identity", "failure_type": "Erroneous (undetected)", "condition": "Undetected erroneous position of a single aircraft", "effect": "Separation on wrong position; possible LoS", "severity": "B", "objective": 1e-7, "requirements": "Integrity filtering (NIC/NACp); radar comparison"},
        {"function": "F1 Provide ADS-B position/identity", "failure_type": "Erroneous (undetected)", "condition": "Undetected erroneous position of multiple aircraft", "effect": "Several false positions; high collision risk", "severity": "A", "objective": 1e-9, "requirements": "Software assurance for ground processing"},
        {"function": "F1 Provide ADS-B position/identity", "failure_type": "Delayed", "condition": "Excessive latency of updates", "effect": "Position lag; margins eroded in turns", "severity": "C", "objective": 1e-5}])})
    study("stpa", "STPA — descent clearances (Manual §13.2)", {
        "losses": [{"id": "L-1", "text": "Mid-air collision"}, {"id": "L-2", "text": "Controlled flight into terrain"}],
        "hazards": [{"id": "H-1", "text": "Aircraft violate minimum separation", "losses": ["L-1"]},
                    {"id": "H-2", "text": "Aircraft descends below minimum safe altitude", "losses": ["L-2"]}],
        "constraints": [{"id": "SC-1", "text": "Aircraft must maintain at least minimum separation", "hazards": ["H-1"]},
                        {"id": "SC-2", "text": "Aircraft must remain at or above the applicable minimum altitude", "hazards": ["H-2"]}],
        "structure": {"nodes": [{"id": "REG", "label": "Regulator / AirNav SMS", "kind": "controller", "x": 250, "y": 0},
                                {"id": "ATCO", "label": "ATCO", "kind": "controller", "x": 250, "y": 130, "process_model": "Traffic picture; clearances issued"},
                                {"id": "ATM", "label": "ATM system (SDP/FDP, STCA)", "kind": "automation", "x": 0, "y": 240},
                                {"id": "CREW", "label": "Flight crew", "kind": "controller", "x": 250, "y": 300, "process_model": "Clearance; own position"},
                                {"id": "AC", "label": "Aircraft (FMS/AP, ACAS)", "kind": "process", "x": 250, "y": 450}],
                      "edges": [{"id": "e1", "source": "REG", "target": "ATCO", "kind": "control", "label": "procedures, rosters"},
                                {"id": "e2", "source": "ATCO", "target": "REG", "kind": "feedback", "label": "reports, SPIs"},
                                {"id": "e3", "source": "ATCO", "target": "CREW", "kind": "control", "label": "Descent clearance"},
                                {"id": "e4", "source": "CREW", "target": "ATCO", "kind": "feedback", "label": "read-back"},
                                {"id": "e5", "source": "CREW", "target": "AC", "kind": "control", "label": "Execute descent"},
                                {"id": "e6", "source": "AC", "target": "CREW", "kind": "feedback", "label": "displays, ACAS RA"},
                                {"id": "e7", "source": "ATM", "target": "ATCO", "kind": "feedback", "label": "situation display, STCA"}]},
        "ucas": [
            {"id": "UCA-1", "control_action": "Descent clearance", "type": "Not providing causes hazard", "text": "ATCO does not issue descent", "context": "when the aircraft must leave its level to avoid a conflict ahead", "hazards": ["H-1"]},
            {"id": "UCA-2", "control_action": "Descent clearance", "type": "Providing causes hazard", "text": "ATCO clears descent through an occupied level", "context": "when unseparated traffic is at that level", "hazards": ["H-1"]},
            {"id": "UCA-3", "control_action": "Descent clearance", "type": "Providing causes hazard", "text": "ATCO clears descent below MVA", "context": "when vectoring over high terrain", "hazards": ["H-2"]},
            {"id": "UCA-6", "control_action": "Descent clearance", "type": "Too early / too late / wrong order", "text": "Descent issued before preceding aircraft vacated level", "context": "when relying on the label trend", "hazards": ["H-1"]},
            {"id": "UCA-10", "control_action": "Execute descent", "type": "Stopped too soon / applied too long", "text": "Descent continued through cleared level", "context": "when the cleared level was mis-set in the FMS", "hazards": ["H-1", "H-2"]}],
        "scenarios": [{"id": "S-1", "uca": "UCA-6", "type": "Flawed process model", "text": "Mode C lag; adjacent sector stopped descent without coordination", "requirement": "Coordination rule for level changes; SFL display; STCA"},
                      {"id": "S-2", "uca": "UCA-10", "type": "Inadequate feedback", "text": "SFL not displayed to ATCO", "requirement": "SFL mismatch alert"}]})
    fres = fta_engine.analyse(FTA_TREE)
    study("fta", "FTA — loss of surveillance picture (Manual §14.3)", {"tree": FTA_TREE}, fres)
    sleeps = [[-1, 7], [23, 31], [55, 61]]
    fat_model = {"start": 0, "end": 72, "step_minutes": 5, "kss_threshold": 7,
                 "variants": [{"name": "No pre-shift nap", "sleeps": sleeps, "duties": [[7, 14], [46, 54]]},
                              {"name": "90-min nap 15:00–16:30", "sleeps": sleeps + [[39, 40.5]], "duties": [[7, 14], [46, 54]]}]}
    fr = fat_engine.run(sleeps, [[7, 14], [46, 54]], 0, 72)
    # illustrative pre-shift Samn-Perelli ratings for the night shift (controller IDs, not names)
    fat_model["sp_ratings"] = [
        {"id": "SP1", "date": "2026-09-14", "time": "21:45", "shift": "Night", "controller": "ATC-07", "position": "APP West", "score": 2, "outcome": "normal", "mitigations": [], "notes": ""},
        {"id": "SP2", "date": "2026-09-14", "time": "21:45", "shift": "Night", "controller": "ATC-12", "position": "APP East", "score": 3, "outcome": "normal", "mitigations": [], "notes": ""},
        {"id": "SP3", "date": "2026-09-14", "time": "21:50", "shift": "Night", "controller": "ATC-03", "position": "TWR", "score": 4, "outcome": "standard", "mitigations": ["Break taken earlier"], "notes": "Moved from combined APP to TWR; break at 01:30 instead of 02:00"},
        {"id": "SP4", "date": "2026-09-14", "time": "21:50", "shift": "Night", "controller": "ATC-21", "position": "ACC Sector 2", "score": 5, "outcome": "mitigated", "mitigations": ["Mandatory 15-minute walk", "Caffeine"], "notes": "Re-rated 4 after mitigation; took position 22:15"},
        {"id": "SP5", "date": "2026-09-14", "time": "21:55", "shift": "Night", "controller": "ATC-15", "position": "ACC Sector 1", "score": 6, "outcome": "home", "mitigations": [], "notes": "Replaced by standby controller"},
        {"id": "SP6", "date": "2026-09-15", "time": "05:40", "shift": "Morning", "controller": "ATC-09", "position": "APP West", "score": 4, "outcome": "normal", "mitigations": [], "notes": "Left on the busy morning position — to be reviewed"},
    ]
    sp = fat_engine.samn_perelli(fat_model["sp_ratings"])
    study("fatigue", "Fatigue — night shift with/without nap (Manual §15.4)", fat_model,
          {"duties": fr["duties"], "engine_version": fr["engine_version"], "samn_perelli": sp})
    study("fram", "FRAM — descent clearances in a busy arrival sector (Manual §16)", {"functions": [
        {"id": "F1", "name": "Manage sector workload", "type": "Organisational", "x": 180, "y": 0, "aspects": {"Output": ["Sector configuration"]}, "variability": {"timing": "Too late", "precision": "Acceptable"}},
        {"id": "F2", "name": "Plan arrival sequence", "type": "Human", "x": 0, "y": 220, "aspects": {"Output": ["Arrival sequence"], "Resource": ["Sector configuration"]}, "variability": {"timing": "On time", "precision": "Imprecise"}},
        {"id": "F3", "name": "Issue descent clearance", "type": "Human", "x": 330, "y": 220, "aspects": {"Input": ["Arrival sequence"], "Output": ["Descent clearance"], "Time": ["Sector configuration"], "Control": ["Conformance monitoring"]}, "variability": {"timing": "Too late", "precision": "Imprecise"}},
        {"id": "F4", "name": "Read back & execute", "type": "Human", "x": 660, "y": 220, "aspects": {"Input": ["Descent clearance"], "Output": ["Aircraft descending"]}, "variability": {"timing": "On time", "precision": "Imprecise"}},
        {"id": "F5", "name": "Monitor conformance", "type": "Technological", "x": 500, "y": 450, "aspects": {"Input": ["Aircraft descending"], "Output": ["Conformance monitoring"]}, "variability": {"timing": "Too late", "precision": "Acceptable"}}]})
    bres = bbn_engine.query(BBN_NET)
    bnet = {"network": BBN_NET, "positions": {"F": [0, 0], "W": [300, 0], "E": [150, 150], "S": [450, 150], "L": [300, 300]},
            "evidence": {}}
    study("bbn", "BBN — coordination error and loss of separation (Manual §17.3)", bnet, bres)

    # hazard log entries (promoted) with controls and actions
    H = []
    def hz(ref, title, unit, system, isev, ilik, rsev, rlik, controls, study_id, rationale, review_offset):
        h = Hazard(ref=ref, title=title, unit=unit, system=system, owner="TWR unit chief" if unit.endswith("TWR") else "ACC unit chief",
                   assessment_id=a.id, source_study_id=study_id, initial_severity=isev, initial_likelihood=ilik,
                   residual_severity=rsev, residual_likelihood=rlik, rationale=rationale,
                   review_date=date.today() + timedelta(days=review_offset))
        db.add(h); db.flush()
        for text, side, eff, crit in controls:
            db.add(Control(hazard_id=h.id, text=text, side=side, effectiveness=eff, critical=crit, verification="existing-verified"))
        H.append(h); return h
    h1 = hz("HZ-0001", "Unauthorised entry onto active runway", "Soekarno-Hatta TWR", "Aerodrome", "A", 3, "A", 2,
            [("Stop bars operated H24", "prevention", "good", True), ("RIMCAS / A-SMGCS alert", "recovery", "good", True)], bt.id,
            "Occurrence data 2023–2025; barrier audit results", 20)
    h2 = hz("HZ-0002", "Level bust leading to potential mid-air collision", "Jakarta ACC", "ATM", "A", 3, "A", 1,
            [("STCA", "recovery", "good", True), ("ACAS II", "recovery", "good", True)], None, "LOPA study: 2.5e-6/yr with SFL alert", 120)
    h3 = hz("HZ-0003", "Total loss of surveillance picture at ACC sector", "Jakarta ACC", "Surveillance", "B", 3, "B", 3,
            [("Radar A/B and ADS-B redundancy", "prevention", "poor", False)], None, "FTA: 1.22e-6/h dominated by single WAN", 45)
    h4 = hz("HZ-0004", "ATCO fatigue at end of night shift", "Jakarta ACC", "Roster", "C", 4, "C", 3,
            [("Pre-shift nap opportunity", "prevention", "unknown", False)], None, "Three-process model; KSS survey pending", -5)
    h5 = hz("HZ-0005", "New site outside radio line of sight of low-level sector", "Jakarta APP", "VHF", "B", 3, None, None,
            [], None, "", 60)
    today = date.today()
    for i, (text, owner, due, hid, status) in enumerate([
        ("Install diverse, physically separate surveillance data path", "CNS engineering", today + timedelta(days=90), h3.id, "open"),
        ("Implement SFL mismatch alert in ATM system", "ATM systems", today + timedelta(days=150), h2.id, "open"),
        ("Collect KSS survey for two roster cycles", "FRMS specialist", today - timedelta(days=10), h4.id, "open"),
        ("Audit stop-bar U/S procedure compliance", "Aerodrome ops", today - timedelta(days=3), h1.id, "in_progress"),
        ("Radio coverage study for new site", "CNS engineering", today + timedelta(days=30), h5.id, "open")], 1):
        db.add(Action(ref=f"ACT-{i:04d}", text=text, owner=owner, due_date=due, hazard_id=hid, assessment_id=a.id, status=status))

    # second project in review, to show workflow
    p2 = Project(code="APP-RELOC", title="Relocation of Jakarta approach unit to new ATC centre", change_type="organisational",
                 units="Jakarta APP", sponsor="Director of Operations", description="Move APP positions to the new ATC centre.")
    db.add(p2); db.flush()
    a2 = Assessment(project_id=p2.id, title="Transition safety assessment", status="in_review", created_by="assessor",
                    scope="Cut-over of APP positions, VCCS and surveillance feeds.", assumptions="Cut-over at night, low traffic.")
    db.add(a2); db.flush()
    st2 = Study(assessment_id=a2.id, method="hazid", title="Transition HAZID", model={"rows": _rows("HZ", [
        {"guideword": "Transition", "hazard": "Loss of surveillance display at cut-over", "causes": "Data feed not re-routed", "consequences": "Loss of separation during cut-over", "controls": "Cut-over at night; old site on hot standby; rollback criteria", "severity": "C", "likelihood": 2, "owner": "Project manager"}])})
    db.add(st2); db.flush()
    h6 = Hazard(ref="HZ-0006", title="Loss of surveillance display at cut-over", unit="Jakarta APP", system="Surveillance", owner="Project manager",
                assessment_id=a2.id, source_study_id=st2.id, source_row="HZ-01", initial_severity="C", initial_likelihood=3,
                residual_severity="C", residual_likelihood=2, rationale="Cut-over at night with hot-standby rollback; rehearsed twice",
                review_date=date.today() + timedelta(days=90))
    db.add(h6); db.flush()
    db.add(Control(hazard_id=h6.id, text="Old site kept on hot standby with rollback criteria", side="recovery", effectiveness="good", critical=True, verification="existing-verified"))
    db.commit()
