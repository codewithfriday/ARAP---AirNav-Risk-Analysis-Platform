"""DEMO-06 — ATSB-method analysis of the illustrative loss-of-separation occurrence OCC-ILL-01 (not a real occurrence)."""
from __future__ import annotations

from sqlalchemy.orm import Session


def _it(text, rating, source, etype="tangible", relevance="direct", comments="", expectation=""):
    return {"text": text, "rating": rating, "source": source, "etype": etype, "relevance": relevance, "comments": comments,
            "expectation": expectation}


def _test(items, conclusion, probability, summary="", target=None):
    t = {"items": [dict(i, id=f"i{k + 1}") for k, i in enumerate(items)], "conclusion": conclusion, "probability": probability, "summary": summary}
    if target is not None:
        t["target"] = target
    return t


EVENTS = [
    ("01:30", "", "The supervisor combined sectors UPPER-E and UPPER-W on one frequency", "Night staffing plan", "Sector log", "ATC", True, "LC", "F7"),
    ("01:58", "", "ABC612 and ABC621 checked in on the combined frequency at FL320", "Both of one (fictitious) operator", "RT recording", "Aircraft", False, "", ""),
    ("02:06", "02:07", "Two transmissions on the frequency were blocked", "Simultaneous transmissions", "RT recording", "ATC", True, "LC", "F5"),
    ("02:07:40", "", "The controller cleared ABC612 to climb to FL340", "", "RT recording", "ATC", False, "", ""),
    ("02:07:46", "", "ABC621 read back the climb clearance with its own callsign", "", "RT recording", "Aircraft", True, "IA", "F2"),
    ("02:07:50", "", "The controller did not challenge the readback from ABC621", "Controller interview: heard 'six-two-one' as 'six-one-two'", "RT recording; interview", "ATC", True, "IA", "F3"),
    ("02:08:10", "", "ABC621 left FL320 climbing", "Mode C", "Radar replay", "Aircraft", True, "OE", "F1"),
    ("02:09:05", "", "STCA alerted ABC621 against opposite-direction traffic at FL330", "55 s before closest point of approach", "System log; radar replay", "ATC", True, "PC", "F10"),
    ("02:09:12", "", "The controller instructed ABC621 to stop climb and turn right 30 degrees", "", "RT recording", "ATC", True, "PA", "F11"),
    ("02:09:40", "", "Separation reduced to 3.2 NM and 400 ft (5 NM / 1000 ft required)", "Closest point of approach", "Radar replay", "Aircraft", False, "", ""),
    ("02:15", "", "The controller reported the occurrence to the supervisor", "", "Occurrence report", "ATC", False, "", ""),
]


def factors():
    F = []

    def add(**k):
        F.append({"further": True, "codes": [], "description": "", **k})
    add(id="F1", title="ABC621 climbed from FL320 on a clearance intended for ABC612", type="OE",
        description="The occurrence event: ABC621 climbed toward FL340 into opposite-direction traffic at FL330, resulting in a loss of separation.",
        existence=_test([_it("Mode C shows ABC621 leaving FL320 at 02:08:10", "supports", "Radar replay"),
                         _it("Crew report states they climbed after reading back the clearance", "supports", "Crew report", "testimonial")],
                        "supported", "VC", "Recorded data establish the event."),
        influence=_test([_it("Without the climb the aircraft would have remained 1,000 ft below the traffic", "supports", "Radar replay")],
                        "supported", "VC", "", target="occurrence"))
    add(id="F2", title="The flight crew of ABC621 accepted and read back the climb clearance intended for ABC612", type="IA",
        codes=["I1.6"], role="Flight crew (all)", error_type="information",
        existence=_test([_it("ABC621 read back 'climb FL340, ABC621'", "supports", "RT recording")], "supported", "VC"),
        influence=_test([_it("The climb followed the readback within 24 s", "supports", "Radar replay", relevance="circumstantial"),
                         _it("Crew stated they believed the clearance was for them", "supports", "Crew report", "testimonial")],
                        "supported", "VL", "", target="F1"))
    add(id="F3", title="The controller did not detect that the readback of the climb clearance came from ABC621", type="IA",
        codes=["I3.3"], role="Air traffic controller", error_type="information",
        existence=_test([_it("No correction was transmitted after the readback", "supports", "RT recording"),
                         _it("Controller stated he heard the expected callsign", "supports", "Controller interview", "testimonial")],
                        "supported", "VL", "Recorded and testimonial evidence converge."),
        influence=_test([_it("A challenge at 02:07:50 would have stopped the climb before 02:08:10", "supports", "Radar replay; RT recording",
                              relevance="circumstantial", comments="Counterfactual: probably no loss of separation")],
                        "supported", "VL", "", target="F1"))
    add(id="F4", title="Two aircraft of one operator with callsigns differing only in the order of the last two digits were on the same frequency",
        type="LC", codes=["L3.6"], functional_area="Air traffic control",
        existence=_test([_it("Flight plans ABC612 and ABC621; both on frequency from 01:58", "supports", "Flight plan data; RT recording")], "supported", "VC"),
        influence=_test([_it("Crew and controller both reported confusing the callsigns", "supports", "Crew report; controller interview", "testimonial"),
                         _it("Similar-callsign confusion is a known mechanism of readback/hearback errors", "supports", "EUROCONTROL guidance", "accepted",
                             "circumstantial")],
                        "supported", "L", "", target="F2"))
    add(id="F5", title="Two transmissions were blocked on the combined frequency in the minute before the clearance", type="LC",
        codes=["L3.6"], functional_area="Air traffic control",
        existence=_test([_it("Two blocked transmissions at 02:06–02:07", "supports", "RT recording")], "supported", "VC"),
        influence=_test([_it("Controller described the frequency as 'busy and messy' just before the clearance", "supports", "Controller interview", "testimonial"),
                         _it("Readback at 02:07:46 was clear on the recording", "opposes", "RT recording")],
                        "supported", "L", "Frequency congestion probably reduced the controller's attention to the readback.", target="F3"))
    add(id="F6", title="The controller was in the last two hours of a night duty that began at 22:00", type="LC",
        codes=["L1.3"], functional_area="Air traffic control",
        existence=_test([_it("Roster: on duty 22:00–07:00 with one 30-min break", "supports", "Roster record"),
                         _it("Controller reported feeling alert", "unsure", "Controller interview", "testimonial")], "supported", "L"),
        influence=_test([_it("Fatigue model: moderate alertness reduction at 02:00", "supports", "Fatigue model (Manual Ch. 15)", "accepted", "circumstantial"),
                         _it("Controller performed other tasks correctly in the same period", "opposes", "RT recording")],
                        "not_supported", "ALAN", "Influence could not be established to the standard of proof.", target="F3"),
        importance={"passed": True, "justification": "Night duties of this pattern recur on every roster; fatigue may influence future hearback performance."})
    add(id="F7", title="Sectors were combined at 01:30 with traffic still above the daytime combining threshold", type="LC",
        codes=["L3.1"], functional_area="Air traffic control",
        existence=_test([_it("Sector log: combined 01:30; 9 aircraft in the combined area", "supports", "Sector log; radar replay")], "supported", "VL"),
        influence=_test([_it("Only 6 aircraft were on frequency at 02:07", "opposes", "Radar replay"),
                         _it("Controller did not describe workload as high", "opposes", "Controller interview", "testimonial")],
                        "not_supported", "U", "", target="F3"),
        importance={"passed": True, "justification": "No night combining criteria exist; combined sectors increase exposure to similar-callsign and congestion effects."})
    add(id="F8", title="The unit had no procedure or display aid to alert controllers to similar callsigns on the same frequency", type="RC",
        codes=["R3", "R1.1"], functional_area="Air traffic control", control_function="preventive",
        safety_issue=True, issue_owner="AirNav — ACC unit", issue_status="partially",
        sufficiency_note="Why no similar-callsign control existed is explained by F9 at the organisational level; not analysed further (stop rule).",
        existence=_test([_it("Unit procedures contain no similar-callsign instruction", "supports", "Unit operations manual"),
                         _it("Track labels have no similar-callsign marking", "supports", "ATM system configuration", "tangible")], "supported", "VL"),
        influence=_test([_it("A marked label would probably have prompted a callsign check at readback", "supports", "Expert judgement (investigation team)",
                              "testimonial", "circumstantial")], "supported", "L", "", target="F3"),
        risk={"scheme": "airnav", "worst_possible": "Mid-air collision between two airliners after a clearance is taken by the wrong aircraft.",
              "existing_controls": [{"text": "STCA", "effectiveness": "Effective in this occurrence; not in inhibition areas"},
                                    {"text": "ACAS on both aircraft", "effectiveness": "Independent last-line control"}],
              "worst_credible": "Loss of separation with a near collision when STCA alerts late; ACAS resolves it.",
              "consequence": "B", "consequence_justification": "Hazardous: large reduction in safety margins; ACAS remains.",
              "likelihood": 3, "likelihood_justification": "Remote: similar-callsign readback errors reported several times a year network-wide; needs a conflicting aircraft and a late STCA.",
              "sensitivity": {"consequence": "B", "likelihood": 4}},
        actions=[{"id": "A1", "kind": "org", "organisation": "AirNav — ACC unit", "description": "Similar-callsign marking on track labels; local instruction to confirm callsigns at readback.",
                  "classes": ["Technical: New/install", "Procedures: New"], "status": "monitor", "notified_on": "2026-08-20",
                  "log": [{"date": "2026-09-10", "text": "Label marking in test; instruction issued."}]}],
        evaluation={"residual": {"consequence": "B", "likelihood": 2}, "alarp": True,
                    "practicability": {"risk": "Significant before action", "knowledge": "Industry practice exists", "means": "ATM label change available",
                                       "cost": "Low"}})
    add(id="F9", title="Similar-callsign de-confliction was not coordinated between the air navigation service provider and the operator", type="OI",
        codes=["O1"], functional_area="Air traffic control", safety_issue=True, issue_owner="AirNav and the operator", issue_status="pending",
        existence=_test([_it("No callsign de-confliction agreement or data exchange with the operator", "supports", "Safety office records")], "supported", "L"),
        influence=_test([_it("The operator scheduled ABC612 and ABC621 in the same sector at the same time", "supports", "Flight plan data", relevance="circumstantial")],
                        "supported", "L", "", target="F4"),
        risk={"scheme": "atsb", "worst_possible": "Mid-air collision of two passenger aircraft.",
              "existing_controls": [{"text": "Controller readback/hearback", "effectiveness": "Vulnerable to similar callsigns"}],
              "worst_credible": "Clearance taken by the wrong aircraft with conflicting traffic; separation lost before STCA alerts.",
              "consequence": "B", "consequence_justification": "Catastrophic outcome credible for passenger operations if STCA and ACAS both fail to resolve.",
              "likelihood": 2, "likelihood_justification": "Improbable: requires similar callsigns, a hearback error and failure of two independent controls."},
        actions=[{"id": "A2", "kind": "recommendation", "organisation": "Operator and AirNav safety office",
                  "description": "Establish a similar-callsign de-confliction process with operators, using AirNav's occurrence data.",
                  "classes": ["Organisational surveillance: Risk assessment"], "status": "proposed", "notified_on": "2026-03-20", "log": []}],
        evaluation={})
    add(id="F10", title="STCA alerted 55 seconds before the closest point of approach", type="PC", codes=["R1.4"], functional_area="Air traffic control",
        existence=_test([_it("STCA alert logged at 02:09:05", "supports", "System log")], "supported", "VC"),
        influence=_test([_it("Avoiding action followed the alert within 7 s", "supports", "RT recording; system log")], "supported", "VL", "", target="occurrence"))
    add(id="F11", title="The controller gave avoiding action within seven seconds of the STCA alert", type="PA", codes=["PA"], role="Air traffic controller",
        existence=_test([_it("Instruction at 02:09:12", "supports", "RT recording")], "supported", "VC"),
        influence=_test([_it("Separation started increasing at 02:09:40", "supports", "Radar replay")], "supported", "VL", "", target="occurrence"))
    add(id="F12", title="The controller lost situation awareness", type="IA", further=False,
        exclusion_reason="Restates the problem (e.g. 'loss of situation awareness')",
        further_justification="Restates F3; the reasons are analysed as F4–F8.")
    return F


KEY_FINDINGS = [
    {"id": "K1", "statement": "The radar replay and the RT recording were synchronised to within one second", "kind": "intermediate",
     "items": [dict(_it("Time check of the voice recorder against radar UTC", "supports", "Technical services report"), id="i1")],
     "conclusion": "supported", "probability": "VC", "add_to_key": False},
    {"id": "K2", "statement": "The STCA parameters in the sector matched the configuration baseline", "kind": "other_key",
     "items": [dict(_it("Configuration audit of STCA parameters", "supports", "ATM system configuration"), id="i1")],
     "conclusion": "supported", "probability": "VL", "add_to_key": True},
]


def model() -> dict:
    ev = [{"id": f"E{k + 1}", "start": s, "end": e, "title": t, "comments": c, "source": src, "theme": th, "display": True,
           "safety_factor": sf, "sf_type": st, "factor_id": fid} for k, (s, e, t, c, src, th, sf, st, fid) in enumerate(EVENTS)]
    return {"occurrence": {"ref": "OCC-ILL-01", "date": "2026-02-14", "title": "Loss of separation, similar callsigns, combined upper sectors (illustrative)",
                           "summary": "ABC621 climbed on a clearance intended for ABC612; STCA alerted and avoiding action was given. Minimum 3.2 NM / 400 ft. "
                                      "Fictitious operator and callsigns.",
                           "occurrence_type": "Loss of separation"},
            "events": ev, "factors": factors(), "key_findings": KEY_FINDINGS,
            "review": {"organised": True, "no_merge": True, "bias": True},
            "stop_rule": "Analysis stopped at the organisational level: the operator's scheduling process is outside AirNav's control and is addressed by recommendation A2."}


def seed_demo_atsb(db: Session):
    from .engines import atsb as engine
    from .models import Assessment, Project, Study
    from .api.common import active_scheme
    p = db.query(Project).filter_by(code="DEMO-06").first()
    if not p:
        return
    a = db.query(Assessment).filter_by(project_id=p.id).order_by(Assessment.id).first()
    if not a or db.query(Study).filter_by(assessment_id=a.id, method="atsb").first():
        return
    m = model()
    db.add(Study(assessment_id=a.id, method="atsb", title="ATSB safety investigation analysis — OCC-ILL-01", model=m,
                 results=engine.analyse(m, active_scheme(db)), template_version="1.0"))
    db.commit()
