"""DEMO-07 — stand-alone worked example of an ORLIO / ATSB-method investigation, based on the published KNKT final report
KNKT.24.10.22.04: Boeing 737-800 PK-GMP struck by an unattended lavatory service truck (LST), Kualanamu (WIMM),
16 October 2024. Facts come from that report; the ORLIO classification, ATSB test conclusions, risk ratings and the
corrective actions marked "proposed (NAVRAP example)" are the analyst's illustration, not KNKT's.
"""
from __future__ import annotations

import base64
import io

from sqlalchemy.orm import Session

SRC = "KNKT final report KNKT.24.10.22.04"


def _it(text, rating, source, etype="tangible", relevance="direct", comments="", expectation=""):
    return {"text": text, "rating": rating, "source": source, "etype": etype, "relevance": relevance, "comments": comments,
            "expectation": expectation}


def _t(items, conclusion, probability, summary="", target=None):
    t = {"items": [dict(i, id=f"i{k + 1}") for k, i in enumerate(items)], "conclusion": conclusion, "probability": probability, "summary": summary}
    if target is not None:
        t["target"] = target
    return t


def _a(aid, kind, org, desc, hierarchy, status="proposed", classes=(), notified="", target="", ref="", log=()):
    return {"id": aid, "kind": kind, "organisation": org, "description": desc, "hierarchy": hierarchy, "status": status,
            "classes": list(classes), "notified_on": notified, "target_date": target, "ref": ref, "log": list(log)}


NOTES = {"2024-10-16 06:00": "Time estimated (morning shift daily check); times on 16 October are local time (UTC+7)",
         "2024-10-17": "Date estimated — post-occurrence inspection; the report does not give the date"}

EVENTS = [
    ("2023-05", "", "Garuda Indonesia's Station Safety Audit found a baggage towing tractor operating with an unserviceable parking brake; the tractor was sent to the workshop and the finding closed", "Station Safety Audit May 2023", "Audit", False, "", ""),
    ("2023-09-13", "", "Maintenance removed the LST parking brake shoes and linings for an unrecorded reason; they were not reinstalled because parts were unavailable", "LST maintenance report", "Maintenance", True, "", "F2"),
    ("2024-04", "", "The next Station Safety Audit of the ground handler recorded no finding on the LST parking brake", "Station Safety Audit April 2024", "Audit", False, "", ""),
    ("2024-10-16 06:00", "", "The morning-shift GSE operator marked the LST service and parking brakes 'X' but recorded the vehicle serviceable (S/B)", "Daily Check Sheet, October 2024", "Ground handling", True, "IA", "F19"),
    ("2024-10-16 19:10", "", "PK-GMP departed Soekarno-Hatta (WIII) for Kualanamu (WIMM); the flight was uneventful", "Report §1.1", "Aircraft", False, "", ""),
    ("2024-10-16 21:13", "", "PK-GMP landed on runway 23 and taxied via G, A, A2 and U toward parking stand W29", "Report §1.1; FDR", "Aircraft", False, "", ""),
    ("2024-10-16 21:24", "", "GSE Operator 1 parked the LST in the equipment staging area between W28 and W29, facing northeast, with the engine running and the transmission in neutral", "CCTV; interview", "Ground handling", True, "IA", "F5"),
    ("2024-10-16 21:24", "", "GSE Operator 1 placed a wheel chock at the right aft tyre, closed the cab door and walked to W30 to operate an aircraft towing tractor", "CCTV; interview", "Ground handling", True, "IA", "F4"),
    ("2024-10-16 21:26", "", "PK-GMP turned onto the W29 lead-in line at about 5 kt ground speed with N1 about 21 %", "FDR; CCTV", "Aircraft", False, "", ""),
    ("2024-10-16 21:26", "", "The LST began to move unaided while PK-GMP was about 46 m from the parking position", "CCTV; FDR", "Ground handling", True, "OE", "F1"),
    ("2024-10-16 21:26", "", "PK-GMP stopped at the parking position and the LST struck its tail section", "CCTV", "Aircraft", True, "OE", "F1"),
    ("2024-10-16 21:27", "", "The engines were shut down; maintenance personnel told the pilot about the collision; the passengers disembarked", "Report §1.1", "Aircraft", False, "", ""),
    ("2024-10-17", "", "The LST cab was documented with the parking brake handle not set; disassembly found no shoes or linings in the parking brake drum", "Report §1.6, §1.16", "Investigation", False, "", ""),
]


def factors() -> list[dict]:
    F: list[dict] = []

    def add(**k):
        F.append({"further": True, "codes": [], "description": "", "actions": [], **k})

    add(id="F1", title="The unattended lavatory service truck moved unaided and struck the tail section of PK-GMP at parking stand W29", type="OE",
        description="The LST started to roll from the equipment staging area as the aircraft approached along the lead-in line, and struck the tail when the aircraft had stopped. No one was in the LST cab.",
        existence=_t([_it("CCTV shows the LST moving from the staging area and striking the tail section", "supports", "Airport CCTV"),
                      _it("Damage to the aircraft tail section and to the LST", "supports", "Damage inspection")], "supported", "VC"),
        influence=_t([_it("The contact is the occurrence", "supports", "Airport CCTV")], "supported", "VC", target="occurrence"),
        actions=[_a("A1", "org", "PT Gapura Angkasa / PT Angkasa Pura Aviasi", "Prohibit leaving motorized GSE unattended with the engine running in the equipment staging area while an aircraft is arriving at the adjacent stand", "elimination",
                    classes=["Procedures: Amend"], ref="proposed (NAVRAP example)")])
    add(id="F2", title="The LST parking brake drum had no brake shoes or linings installed, so the parking brake could not hold the vehicle", type="TFM",
        codes=["T8"], functional_area="Ground handling",
        description="Shoes and linings were removed on 13 September 2023 and not reinstalled because replacement parts were unavailable. With the handle fully applied the truck could be pushed freely.",
        existence=_t([_it("Disassembly found no shoes, linings or other components in the drum", "supports", "Post-occurrence inspection"),
                      _it("With the parking brake fully applied the truck was pushed and moved freely", "supports", "Functional test"),
                      _it("Maintenance report of 13 September 2023 records the removal", "supports", "LST maintenance report")], "supported", "VC"),
        influence=_t([_it("A functioning parking brake is designed to hold the vehicle on the measured 0.57 % slope", "supports", "Regulation KP 635/2015 (holding on 7 % slope)", "accepted", "circumstantial"),
                      _it("The handle was found not set after the occurrence, so a serviceable brake might not have been applied either", "opposes", "Cab documentation", comments="Operator 1 recalled setting it; the absence of components makes the question moot for this occurrence")],
                     "supported", "VL", "Without brake shoes the parking brake could not hold the LST whether or not the handle was set.", target="F1"),
        actions=[_a("A2", "org", "PT Gapura Angkasa — GSE maintenance", "Reinstall parking brake shoes and linings and remove the LST from service until the parking brake passes a holding test", "engineering",
                    classes=["Technical: Repair/modify"], ref="proposed (NAVRAP example)")])
    add(id="F3", sufficiency_note='The slope is a design feature of the apron drainage; no further explanation is needed for the analysis (KNKT finding 13).', title="The equipment staging area between W28 and W29 sloped down 0.57 % toward the impact point", type="LC",
        codes=["L6.3"], functional_area="Ground handling",
        existence=_t([_it("Theodolite measurement between the LST position and the impact point: 0.57 % downslope", "supports", "Site survey")], "supported", "VC"),
        influence=_t([_it("The LST rolled in the downslope direction once moving", "supports", "CCTV", relevance="circumstantial")], "supported", "L",
                     "The slope combined with the unrestrained wheels let the LST keep rolling.", target="F1"),
        actions=[_a("A3", "org", "PT Angkasa Pura Aviasi", "Mark level GSE parking positions in staging areas and require GSE to park perpendicular to, or facing away from, the aircraft path", "engineering",
                    classes=["Technical: New/install"], ref="proposed (NAVRAP example)")])
    add(id="F4", actions=[_a("A19", "org", "PT Gapura Angkasa", "Include chock placement (chock in contact with the tyre, front and rear of the wheel) in recurrent GSE operator training with a practical assessment", "administrative", ref="proposed (NAVRAP example)")], title="GSE Operator 1 placed the wheel chock at the right aft tyre in a position that did not restrain the wheel", type="IA",
        codes=["I4.3"], role="Ground crew", error_type="action",
        rationale="Placing a chock was a routine task he had done many times; he was already planning to go to W30 to tow another aircraft; it was late evening, 6 h 30 min into his shift after seven aircraft; nothing in the procedure or the equipment showed whether the chock was in contact with the tyre.",
        existence=_t([_it("CCTV shows him placing the chock and leaving", "supports", "Airport CCTV"),
                      _it("No bump at the start of the movement, as would be expected if the tyre had rolled over a chock in contact", "supports", "Airport CCTV", relevance="circumstantial", expectation="expected_not_seen"),
                      _it("The triangle chocks were dimensioned to hold the LST", "supports", "Chock dimensions", "tangible", "ancillary")],
                     "supported", "L", "The absence of a bump indicates that the chock was not in contact with the tyre."),
        influence=_t([_it("A chock in contact would have held the LST against the measured slope", "supports", "Chock dimensions; site survey", relevance="circumstantial")],
                     "supported", "VL", "", target="F1"))
    add(id="F5", title="GSE Operator 1 left the LST unattended with the engine running and the transmission in neutral", type="IA",
        codes=["I4.3"], role="Ground crew", error_type="decision",
        rationale="The engine had been hard to restart (a low-battery starter problem was recorded); the Ground Operation Manual allowed an engine-running unattended GSE in extremely cold weather if the parking brake was set and a chock placed; he was needed at W30 to tow another departing aircraft.",
        existence=_t([_it("Operator 1 stated he kept the engine running", "supports", "Interview", "testimonial"),
                      _it("Daily Check Sheet records a low-battery starter problem 1–5 September 2024", "supports", "Daily Check Sheet", relevance="circumstantial")], "supported", "VC"),
        influence=_t([_it("Engine vibration is one of the candidate forces that started the movement", "supports", "Report analysis §2.1", "accepted", "circumstantial")],
                     "supported", "L", "", target="F6"),
        actions=[_a("A4", "org", "PT Gapura Angkasa — GSE maintenance", "Repair the LST starting system so the engine can be shut down when the vehicle is left", "engineering",
                    classes=["Technical: Repair/modify"], ref="proposed (NAVRAP example)")])
    add(id="F6", title="Vibration from the running LST engine and the approaching aircraft, with engine suction, may have started the LST moving", type="LC",
        codes=["L6.3"], functional_area="Ground handling",
        description="The investigation could not identify the force that started the movement. The aircraft was at ground idle (N1 about 21 %) and the LST was outside the 3.1 m engine inlet hazard area.",
        existence=_t([_it("The LST engine was running", "supports", "Interview", "testimonial"),
                      _it("The aircraft was taxiing 46 m away at ground idle when the LST started to move", "supports", "FDR; CCTV")], "supported", "VC"),
        influence=_t([_it("The force that started the movement could not be identified", "unsure", "Report analysis §2.1"),
                      _it("The LST was outside the 3.1 m inlet hazard area of the engine", "opposes", "Boeing inlet hazard data", "accepted")],
                     "not_supported", "ALAN", "KNKT lists this as a contributing factor ('might have triggered'). Under the ATSB standard of proof (likely, ≥ 66 %) NAVRAP records it as an other safety factor.", target="F1"),
        importance={"passed": True, "justification": "Unattended running GSE close to arriving aircraft is a recurring exposure; the triggering mechanism matters for staging-area design."},
        actions=[_a("A5", "org", "PT Angkasa Pura Aviasi", "Keep the staging area beside an arrival stand clear of unattended running GSE from block-in minus 5 minutes until chocks-on", "administrative",
                    classes=["Procedures: New"], ref="proposed (NAVRAP example)")])
    add(id="F7", title="GSE Operator 1 was 6 h 30 min into an 8-hour shift, had handled seven aircraft and was working at about 2130 local time", type="LC",
        codes=["L1.3", "L3.1"], functional_area="Ground handling",
        description="Afternoon shift 1500–2300 LT. Around 2100 LT the circadian rhythm starts preparing the body for rest; vigilance and thoroughness of routine checks can decline without the person noticing.",
        existence=_t([_it("Shift 1500–2300 LT; seven aircraft handled", "supports", "Roster; interview"),
                      _it("Occurrence at about 2126 LT", "supports", "CCTV")], "supported", "VC"),
        influence=_t([_it("Fatigue and time-of-day effects reduce thoroughness of routine tasks", "supports", "ICAO Doc 9966", "accepted", "circumstantial"),
                      _it("No direct evidence of his alertness at the time", "unsure", "Interview", "testimonial")],
                     "not_supported", "ALAN", "KNKT: 'might have influenced' the improper placement. Recorded as an other safety factor under the ATSB standard of proof.", target="F4"),
        importance={"passed": True, "justification": "Late-evening shifts and back-to-back turnarounds recur every day; fatigue risk for ground staff is not managed."},
        actions=[_a("A6", "org", "PT Gapura Angkasa", "Introduce fatigue risk management for GSE operators: task allocation that avoids one operator covering two stands at the same time late in the shift", "administrative",
                    classes=["Policy: New"], ref="proposed (NAVRAP example)")])
    add(id="F8", title="GSE Operator 1 was planning his next task at W30 while placing the wheel chock", type="LC",
        codes=["L1.7", "L3.2"], functional_area="Ground handling",
        existence=_t([_it("He left the LST to operate the towing tractor at W30 for a departing aircraft", "supports", "CCTV; interview")], "supported", "L"),
        influence=_t([_it("Preoccupation with the next task is a plausible reason for a routine action done less thoroughly", "supports", "Report analysis §2.2", "accepted", "circumstantial")],
                     "not_supported", "ALAN", "", target="F4"),
        importance={"passed": True, "justification": "Single operators covering consecutive tasks on adjacent stands is a normal staffing pattern."})
    add(id="F9", sufficiency_note="Chock placement is a single-person task by design under the ground handler's SOP; the absence of verification is explained by the procedure design itself (see F12 and the recommendation 04-G-2024-22.03).", title="There was no means to verify that a wheel chock had been placed in contact with the tyre other than the operator's own action", type="RC",
        codes=["R3", "R1.3"], functional_area="Ground handling", control_function="preventive",
        safety_issue=True, issue_owner="PT Gapura Angkasa", issue_status="pending",
        existence=_t([_it("The Ground Operation Manual only requires the chock to be 'positioned properly'; no check or second person", "supports", "GOM 6.1.2"),
                      _it("Investigation found no other means of verification", "supports", "Report §1.17")], "supported", "VL"),
        influence=_t([_it("An independent check or a visible chock-contact cue would probably have revealed the gap before he left", "supports", "Investigation team judgement", "testimonial", "circumstantial")],
                     "supported", "L", "", target="F4"),
        risk={"scheme": "atsb", "worst_possible": "An unrestrained vehicle rolls into a person or an aircraft during boarding, causing fatal injury.",
              "existing_controls": [{"text": "Operator places chock (GOM 6.1.2)", "effectiveness": "Single action, no verification"},
                                    {"text": "Parking brake", "effectiveness": "Not reliable while unserviceable vehicles stay in use"}],
              "worst_credible": "An improperly chocked GSE rolls into a parked aircraft or ground staff, causing structural damage and a serious injury.",
              "consequence": "D", "consequence_justification": "Major: occasional serious injury to ground staff and aircraft damage; no passenger exposure in the credible scenario.",
              "likelihood": 4, "likelihood_justification": "Occasional: chocks are placed thousands of times a year at the station; improper placement is undetectable by design.",
              "sensitivity": {"consequence": "C", "likelihood": 4}},
        actions=[_a("A7", "recommendation", "PT Gapura Angkasa", "KNKT 04-G-2024-22.03: develop a mechanism to verify the proper placement of the wheel chock", "administrative",
                    classes=["Procedures: New"], ref="KNKT 04-G-2024-22.03"),
                 _a("A8", "org", "PT Gapura Angkasa", "Use chocks with a high-visibility contact indicator and a 'chocks in contact' call-out confirmed by a second person before leaving the vehicle", "engineering",
                    classes=["Technical: New/install", "Procedures: Amend"], ref="proposed (NAVRAP example)")],
        evaluation={"residual": {"consequence": "D", "likelihood": 2}, "alarp": True,
                    "practicability": {"risk": "Significant", "knowledge": "Chock verification practices exist in the industry", "means": "Indicators and call-outs are simple", "cost": "Low"}})
    add(id="F10", title="Ground handler practice assessed GSE with an unserviceable parking brake as serviceable, on the assumption that wheel chocks could replace the parking brake", type="RC",
        codes=["R6.3", "R3"], functional_area="Ground handling", control_function="preventive",
        safety_issue=True, issue_owner="PT Gapura Angkasa", issue_status="pending",
        description="After September 2023 every PMI left the parking brake unmarked and recorded the braking system 'OK'; daily checks from August to October 2024 marked the brakes 'X' yet the final status 'S/B'. GOM 6.1.2 required an inoperative parking brake to make the GSE unserviceable.",
        existence=_t([_it("PMI records after removal: parking brake not marked, braking system 'OK'", "supports", "PMI checklists"),
                      _it("Daily Check Sheets: brakes 'X' with final status 'S/B' on the day", "supports", "Daily Check Sheet October 2024"),
                      _it("GOM 6.1.2 prohibits use of GSE with an inoperative parking brake", "supports", "GOM 6.1.2", relevance="ancillary")], "supported", "VC"),
        influence=_t([_it("The morning-shift operator released the LST as serviceable on this basis", "supports", "Daily Check Sheet", relevance="circumstantial")],
                     "supported", "VL", "", target="F19"),
        risk={"scheme": "airnav", "worst_possible": "Unserviceable GSE rolls into an aircraft with passengers boarding, causing injuries and hull damage.",
              "existing_controls": [{"text": "Daily check by operator", "effectiveness": "Defect recorded but vehicle released"},
                                    {"text": "PMI every 450 h", "effectiveness": "Parking brake not checked after removal"},
                                    {"text": "Wheel chocks", "effectiveness": "Depend on correct placement (F9)"}],
              "worst_credible": "A GSE with an unserviceable parking brake and a misplaced chock rolls into a parked aircraft (as in this occurrence), with possible injury to staff nearby.",
              "consequence": "C", "consequence_justification": "Major (AirNav scheme): significant aircraft damage and possible injury.",
              "likelihood": 4, "likelihood_justification": "Occasional: the practice applied to every GSE with a brake defect for more than a year.",
              "sensitivity": {"consequence": "C", "likelihood": 3}},
        actions=[_a("A9", "recommendation", "PT Gapura Angkasa", "KNKT 04-G-2024-22.02: ensure the serviceability of the parking brake of the GSE to prevent the risk of collision", "elimination",
                    classes=["Procedures: Review", "Organisational surveillance: QA, audits, monitoring"], ref="KNKT 04-G-2024-22.02"),
                 _a("A10", "org", "PT Gapura Angkasa", "Amended the Daily Check Sheet so that parking brake and service brake results are recorded separately", "administrative",
                    status="closed", classes=["Procedures: Amend"], ref="safety action taken (KNKT report §4)")],
        evaluation={"residual": {"consequence": "C", "likelihood": 2}, "alarp": False})
    add(id="F11", title="The lavatory service truck, built in 1986, was reconditioned without the documentation required by the GSE Maintenance & Technical Support Manual", type="OI",
        codes=["O1"], functional_area="Ground handling", influence_kind="internal", safety_issue=True, issue_owner="PT Gapura Angkasa", issue_status="pending",
        description="Its technical specification and applicable maintenance manuals could not be identified. Regulation KP 635/2015 sets a maximum age of 15 years for this GSE.",
        existence=_t([_it("No reconditioning documentation found", "supports", "Report §1.6", expectation="expected_not_seen"),
                      _it("Manual 3.6 requires formal documentation of reconditioning", "supports", "GSE Maintenance & Technical Support Manual", relevance="ancillary")], "supported", "VC"),
        influence=_t([_it("Without specifications the correct brake parts may have been harder to obtain", "unsure", "Investigation team judgement", "testimonial", "circumstantial")],
                     "not_supported", "ALAN", "", target="F2"),
        importance={"passed": True, "justification": "Undocumented reconditioning leaves maintenance of all such GSE without a technical basis."},
        risk={"scheme": "atsb", "worst_possible": "Reconditioned GSE with unknown specifications fails in service near aircraft.",
              "existing_controls": [{"text": "PMI checklist", "effectiveness": "Generic; not tied to the vehicle's specification"}],
              "worst_credible": "A safety-critical defect on reconditioned GSE goes unrecognised and the vehicle damages an aircraft.",
              "consequence": "D", "consequence_justification": "Major: aircraft damage, possible minor injury.",
              "likelihood": 3, "likelihood_justification": "Remote: needs a defect that the generic checklist cannot recognise."},
        actions=[_a("A11", "recommendation", "PT Gapura Angkasa", "KNKT 04-G-2024-22.01: ensure that the reconditioning of all GSE is implemented in accordance with the applicable procedures", "administrative",
                    classes=["Procedures: Review"], ref="KNKT 04-G-2024-22.01")])
    add(id="F12", title="The Daily Check Sheet recorded parking brake and service brake results in a single column", type="RC",
        codes=["R3"], functional_area="Ground handling", control_function="preventive",
        existence=_t([_it("Daily Check Sheet layout", "supports", "Daily Check Sheet")], "supported", "VC"),
        influence=_t([_it("A shared column made a brake 'X' less specific", "unsure", "Investigation team judgement", "testimonial", "circumstantial")],
                     "not_supported", "ALAN", "", target="F19"),
        importance={"passed": True, "justification": "Check-sheet design affects every daily check; the ground handler has already changed it."},
        actions=[_a("A12", "org", "PT Gapura Angkasa", "Separate check-result columns for parking brake and service brake (done)", "administrative",
                    status="closed", classes=["Procedures: Amend"], ref="safety action taken (KNKT report §4)")])
    add(id="F13", title="Regulation KP 635 of 2015 required a functional parking brake yet allowed wheel chocks alone as the holding device", type="OI",
        codes=["O3"], functional_area="Ground handling", influence_kind="external", safety_issue=True, issue_owner="DGCA", issue_status="pending",
        existence=_t([_it("Article 2 text: parking brake as safety feature; 'parking brakes and/or wheel chocks' as safety device holding on a 7 % slope", "supports", "DG Regulation KP 635/2015")], "supported", "VC"),
        influence=_t([_it("The ground handler's manual referenced KP 635/2015; personnel assumed chocks could replace the parking brake", "supports", "GOM; interviews", relevance="circumstantial")],
                     "supported", "L", "", target="F10"),
        risk={"scheme": "atsb", "worst_possible": "Industry-wide use of GSE without parking brakes leads to a collision with an aircraft during boarding.",
              "existing_controls": [{"text": "Operators' own manuals", "effectiveness": "Follow the regulation's wording"}],
              "worst_credible": "Several ground handlers keep GSE with unserviceable parking brakes in service; a vehicle rolls into an aircraft.",
              "consequence": "C", "consequence_justification": "Hazardous: major aircraft damage and serious injury possible near boarding passengers.",
              "likelihood": 3, "likelihood_justification": "Remote: requires a misplaced chock as well; exposure is national."},
        actions=[_a("A13", "recommendation", "DGCA", "KNKT 04-R-2024-22.06: review Regulation KP 635 of 2015 to prevent confusion about the minimum requirements of the GSE", "administrative",
                    classes=["Mandatory requirements: Review of requirements"], ref="KNKT 04-R-2024-22.06")])
    add(id="F14", title="Since 2020 the DGCA has had no safety oversight programme for the operation of motorized GSE", type="OI",
        codes=["O3"], functional_area="Ground handling", influence_kind="external", safety_issue=True, issue_owner="DGCA", issue_status="pending",
        description="The amendment of Aviation Law Article 219 abolished certification of airport facilities, and PM 36/2021 excluded motorized GSE from the facilities to be standardised.",
        existence=_t([_it("Aviation Law Art. 219 amended 2020; PM 77/2015 repealed by PM 36/2021", "supports", "Regulations")], "supported", "VC"),
        influence=_t([_it("No external check existed to stop GSE with unserviceable brakes being operated", "supports", "Report analysis §2.3.2", relevance="circumstantial")],
                     "supported", "L", "", target="F10"),
        risk={"scheme": "atsb", "worst_possible": "Unsafe GSE across Indonesian airports causes a serious ground accident.",
              "existing_controls": [{"text": "Operator audits of ground handlers", "effectiveness": "Did not detect this defect (F15)"},
                                    {"text": "Airport supervision", "effectiveness": "Did not check brakes (F16)"}],
              "worst_credible": "Unsafe GSE remains in service at several airports and collides with an aircraft.",
              "consequence": "C", "consequence_justification": "Hazardous.", "likelihood": 3, "likelihood_justification": "Remote."},
        actions=[_a("A14", "recommendation", "DGCA", "KNKT 04-R-2024-22.07: include the GSE operations in the safety oversight program", "administrative",
                    classes=["Mandatory requirements: Review of requirements", "External surveillance: QA, audits, monitoring"], ref="KNKT 04-R-2024-22.07")])
    add(id="F15", title="The aircraft operator's Station Safety Audits did not lead to effective correction of unserviceable GSE parking brakes", type="OI",
        codes=["O4"], functional_area="Ground handling", influence_kind="external", safety_issue=True, issue_owner="PT Garuda Indonesia", issue_status="partially",
        existence=_t([_it("May 2023 SSA closed by sending one tractor to the workshop", "supports", "SSA May 2023"),
                      _it("April 2024 SSA: no finding on the LST, the only LST at the station", "supports", "SSA April 2024", expectation="expected_not_seen")], "supported", "VC"),
        influence=_t([_it("An effective audit would probably have found the LST brake defect in April 2024", "supports", "Investigation team judgement", "testimonial", "circumstantial")],
                     "supported", "L", "", target="F10"),
        risk={"scheme": "atsb", "worst_possible": "Ground handling defects persist undetected at a station and cause a collision.",
              "existing_controls": [{"text": "Periodic SSA", "effectiveness": "Sample-based; GSE maintenance not covered"}],
              "worst_credible": "Recurring GSE defects remain undetected; a vehicle strikes an aircraft.",
              "consequence": "D", "consequence_justification": "Major.", "likelihood": 4, "likelihood_justification": "Occasional."},
        actions=[_a("A15", "recommendation", "PT Garuda Indonesia", "KNKT 04-O-2024-22.05: improve the Station Safety Audit to ensure that the operation of unserviceable motorized GSE can be prevented", "administrative",
                    classes=["Organisational surveillance: QA, audits, monitoring"], ref="KNKT 04-O-2024-22.05"),
                 _a("A16", "org", "PT Garuda Indonesia", "Notice to Auditor (pre-audit reminder to check GSE maintenance programme implementation); Special Audit at Kualanamu 13–15 Nov 2024; audit of the ground handler's head office (PMI in AMTISS) with weekly follow-up", "administrative",
                    status="monitor", classes=["Organisational surveillance: QA, audits, monitoring"], ref="safety action taken (KNKT report §4)",
                    log=[{"date": "2024-11-15", "text": "Special Audit Kualanamu: LST daily check records May–Oct 2024 not properly completed; controller assigned"}])],
        evaluation={"residual": {"consequence": "D", "likelihood": 2}, "alarp": True})
    add(id="F16", sufficiency_note="The checklist content reflects the airport operator's interpretation of KP 635/2015 (F13); no further organisational factor was established.", title="The airport operator's GSE supervision checklist had no items for parking brakes or wheel chocks", type="RC",
        codes=["R3"], functional_area="Ground handling", control_function="recovery", safety_issue=True, issue_owner="PT Angkasa Pura Aviasi", issue_status="pending",
        description="The SOP required Airside Operation Officers to check hand brakes, parking brakes and chocks during five daily patrols and CCTV monitoring, but the checklist had no such items and the logbook recorded no brake findings from September 2023 to the occurrence.",
        existence=_t([_it("Checklist content", "supports", "Airside Operation Officer checklist"),
                      _it("No brake findings in the daily logbook since September 2023", "supports", "Daily logbook", expectation="expected_not_seen")], "supported", "VC"),
        influence=_t([_it("Supervision without a brake item could not detect GSE operated with unserviceable brakes", "supports", "Report analysis §2.3.2", relevance="circumstantial")],
                     "supported", "L", "", target="F10"),
        risk={"scheme": "atsb", "worst_possible": "Unsafe GSE operates airside unchecked and strikes an aircraft or person.",
              "existing_controls": [{"text": "Five daily patrols; CCTV", "effectiveness": "No brake/chock item"}],
              "worst_credible": "GSE with defective brakes operates undetected and collides with an aircraft.",
              "consequence": "D", "consequence_justification": "Major.", "likelihood": 4, "likelihood_justification": "Occasional."},
        actions=[_a("A17", "recommendation", "PT Angkasa Pura Aviasi", "KNKT 04-B-2024-22.04: ensure the supervision of motorized GSE is able to detect the operation of GSE with an unserviceable parking brake", "administrative",
                    classes=["Procedures: Amend"], ref="KNKT 04-B-2024-22.04")])
    add(id="F17", title="GSE Operator 1 drove the LST without a lavatory service system competency certificate", type="IA", role="Ground crew",
        further=False, exclusion_reason="Not a safety factor (trivial risk)",
        further_justification="He held a valid airside driving permit; the lavatory system was to be operated by GSE Operator 2, who held that competency. Driving and parking were within his permit.")
    add(id="F18", title="The GSE operator lost awareness of the LST", type="IA", role="Ground crew",
        further=False, exclusion_reason="Restates the problem (e.g. 'loss of situation awareness')", further_justification="Restates F4–F5; the reasons are analysed as F7–F9.")
    add(id="F19", title="The morning-shift GSE operator recorded the LST brakes as unserviceable but released the vehicle as serviceable", type="IA",
        codes=["I4.3"], role="Ground crew", error_type="decision",
        rationale="The practice at the station, and the regulation the manual referred to, treated wheel chocks as an acceptable substitute for the parking brake; the same entry had been made daily for weeks.",
        existence=_t([_it("Daily Check Sheet 16 October 2024: brakes 'X', final status 'S/B'", "supports", "Daily Check Sheet")], "supported", "VC"),
        influence=_t([_it("Had the LST been labelled unserviceable it would not have been used that evening", "supports", "GOM 6.1.2", relevance="circumstantial")],
                     "supported", "VL", "", target="F1"),
        actions=[_a("A18", "org", "PT Gapura Angkasa", "Lock-out/tag-out: any brake defect on the daily check makes the GSE unserviceable and physically tagged, with the key returned to maintenance", "elimination",
                    classes=["Procedures: Amend"], ref="proposed (NAVRAP example)")])
    # reasonableness / practicability of the organisational findings (ATSB Analysis §6) — illustrative judgements
    pract = {
        "F10": {"risk": "Significant", "knowledge": "Parking brake serviceability is a basic GSE requirement (KP 635/2015)",
                "means": "Daily check and workshop process already exist", "cost": "Low — repair or withdraw the vehicle"},
        "F11": {"risk": "Significant", "knowledge": "The handler's own manual required reconditioning records",
                "means": "Existing manual and records system", "cost": "Low"},
        "F13": {"risk": "Significant", "knowledge": "Contradiction visible in the text of the regulation",
                "means": "Regulatory amendment", "cost": "Moderate (rule-making effort)"},
        "F14": {"risk": "Significant", "knowledge": "GSE oversight is a regulator function under the CASR framework",
                "means": "Surveillance programme and inspectors", "cost": "Moderate"},
        "F15": {"risk": "Significant", "knowledge": "Audit follow-up of fleet-wide findings is common SMS practice",
                "means": "Existing Station Safety Audit programme", "cost": "Low"},
        "F16": {"risk": "Significant", "knowledge": "Airside vehicle inspections commonly cover brakes and chocks",
                "means": "Add items to the existing supervision checklist", "cost": "Low"},
    }
    for f in F:
        if f["id"] in pract:
            ev = f.setdefault("evaluation", {})
            ev["practicability"] = pract[f["id"]]
    return F


KEY_FINDINGS = [
    {"id": "K1", "statement": "The parking brake handle was found not set after the occurrence; without shoes or linings the parking brake would not have held the LST either way", "kind": "other_key",
     "items": [dict(_it("Cab documentation after the occurrence", "supports", "Report §1.6"), id="i1"),
               dict(_it("Operator 1 recalled setting the brake", "opposes", "Interview", "testimonial"), id="i2")], "conclusion": "supported", "probability": "VL", "add_to_key": True},
    {"id": "K2", "statement": "The aircraft was serviceable and its engine inlet hazard area (3.1 m) did not reach the LST", "kind": "other_key",
     "items": [dict(_it("No aircraft system malfunction reported; valid C of A", "supports", "Report §1.6"), id="i1"),
               dict(_it("LST position relative to the inlet hazard area", "supports", "Site survey; Boeing data"), id="i2")], "conclusion": "supported", "probability": "VL", "add_to_key": True},
    {"id": "K3", "statement": "The cockpit voice recorder had been overwritten and provided no data", "kind": "intermediate",
     "items": [dict(_it("CVR download", "supports", "Report §1.11"), id="i1")], "conclusion": "supported", "probability": "VC", "add_to_key": False},
]


def report_data() -> dict:
    return {
        "report_no": "NAVRAP-ORLIO-KNKT.24.10.22.04",
        "prepared_by": "NAVRAP worked example — ORLIO analysis using the ATSB method, based on the KNKT final report",
        "status": "Example (not an official report)",
        "consequences": "No injuries to the 109 persons on board (2 pilots, 5 flight attendants, 102 passengers) or to ground staff. "
                        "The tail section of PK-GMP and the lavatory service truck were damaged. No environmental impact was reported.",
        "personnel": [
            {"role": "GSE Operator 1 (drove and parked the LST)", "details": "30 years; 12 years as GSE operator; valid airside driving permit and competency for several GSE but not the lavatory service system; afternoon shift 1500–2300 LT; about 6 h 30 min on duty; seven aircraft handled."},
            {"role": "GSE Operator 2 (standby)", "details": "29 years; 10 years as GSE operator; valid airside driving permit and competency including the lavatory service system; waiting in the staging area to chock the nose wheel and operate the lavatory system."},
            {"role": "Maintenance personnel", "details": "On standby at W29 for the arrival; informed the pilot of the collision after engine shutdown."},
            {"role": "Morning-shift GSE operator", "details": "Performed the LST daily check on 16 October 2024."},
            {"role": "Flight crew", "details": "Two pilots; no flight crew factor identified. Five flight attendants."},
        ],
        "assets": [
            {"item": "Aircraft", "details": "Boeing 737-800 PK-GMP, PT Garuda Indonesia; valid C of A and C of R; no system malfunction. FDR: ground speed about 5 kt, N1 about 21 % (ground idle) during the turn-in. CVR overwritten."},
            {"item": "Lavatory service truck (LST)", "details": "Lavatory service system on a Mitsubishi truck built in 1986, reconditioned without documentation. Parking brake: ratchet-bar handle and cable to a drum on the propeller shaft; shoes and linings removed 13 September 2023. Two triangle wheel chocks chained to the aft right fender. Low-battery starter problem recorded."},
            {"item": "Aerodrome", "details": "Kualanamu International Airport (WIMM), PT Angkasa Pura Aviasi; Apron W, parking stand W29; equipment staging area between W28 and W29 with a 0.57 % downslope toward the impact point."},
        ],
        "environment": "Night (about 2126 LT). The LST was parked facing northeast, opposite to the aircraft's parking manoeuvre. Weather was not reported as a factor.",
        "immediate_actions": [
            "2127 LT: engines shut down; maintenance personnel informed the pilot that the aircraft had collided with the LST.",
            "Passengers disembarked normally; no injuries.",
            "The LST cab was documented (parking brake handle not set) and the vehicle retained for inspection; the parking brake drum was later disassembled.",
            "Airport CCTV and FDR data were secured. The CVR had been overwritten — preserving the CVR after a ground occurrence is a lesson for operators.",
            "Site survey of the slope between the LST position and the impact point (theodolite).",
        ],
        "interviews": [
            {"person": "GSE Operator 1", "summary": "Recalled setting the parking brake and placing the chock at the right aft tyre. Kept the engine running because it had been difficult to start. Went to W30 to operate the towing tractor for a departure and did not see the LST move."},
            {"person": "GSE Operator 2", "summary": "Was in the staging area between W29 and W30, ready to chock the nose wheel and operate the lavatory service. Was watching the aircraft and could not prevent the collision."},
            {"person": "Maintenance personnel", "summary": "On standby at W29 watching the aircraft; informed the pilot after engine shutdown."},
            {"person": "Morning-shift GSE operator", "summary": "Found the parking brake unserviceable during the daily check and marked it 'X'; marked the vehicle serviceable on the understanding that wheel chocks could replace the parking brake."},
        ],
        "layer_notes": {
            "E": "Control was lost when the unattended LST began to roll while PK-GMP was about 46 m from its parking position; the LST struck the tail as the aircraft stopped.",
            "I": "The actions are analysed for why they made sense at the time; none involved disregard of a rule the individuals knew to apply.",
            "L": "",
            "R": "Three layers of defence were weak at the same time: the parking brake (removed and not reinstated), the wheel chock (placed without verification) and the serviceability checks (which accepted the chock as a substitute).",
            "O": "The assumption that chocks can replace a parking brake traces to an ambiguous regulation, an oversight gap since 2020, and audit and supervision that did not look at GSE braking.",
        },
        "attachments": [],
        "source": f"{SRC} (Komite Nasional Keselamatan Transportasi). Facts are taken from the report; the ORLIO/ATSB analysis, risk ratings and actions marked 'proposed (NAVRAP example)' are illustrative.",
    }


# ------------------------------------------------------------------ schematic figures (drawn from the report's text)
def _png(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    import matplotlib.pyplot as plt
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def figures() -> list[dict]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, Polygon, Rectangle
    out = []
    # A1: site sketch
    f, ax = plt.subplots(figsize=(7.2, 4.2)); ax.set_xlim(0, 100); ax.set_ylim(0, 60); ax.axis("off")
    ax.add_patch(Rectangle((0, 0), 100, 60, fc="#F3F4F6", ec="none"))
    for x, n in ((18, "W28"), (52, "W29"), (86, "W30")):
        ax.plot([x, x], [8, 44], color="#D4A017", lw=1.5, ls="--"); ax.text(x, 46, n, ha="center", fontsize=9, weight="bold")
    ax.add_patch(Rectangle((26, 8), 17, 12, fc="#FDE68A", ec="#B45309", lw=1)); ax.text(34.5, 9.5, "equipment staging area", ha="center", fontsize=6.5)
    ax.add_patch(Rectangle((8, 54), 84, 5, fc="#D1D5DB", ec="none")); ax.text(50, 56.5, "terminal / apron edge", ha="center", va="center", fontsize=6.5)
    plane = Polygon([(52, 51), (53.4, 48.5), (53.4, 41), (62, 36.5), (62, 35), (53.4, 37), (53.4, 28), (56.5, 25.2), (56.5, 24), (52, 25),
                     (47.5, 24), (47.5, 25.2), (50.6, 28), (50.6, 37), (42, 35), (42, 36.5), (50.6, 41), (50.6, 48.5)],
                    closed=True, fc="white", ec="#1F3A5F", lw=1.3, zorder=3)
    ax.add_patch(plane); ax.text(63, 40, "PK-GMP\n(stopped at W29,\nnose-in)", fontsize=7, color="#1F3A5F")
    ax.add_patch(Rectangle((37, 13), 6, 4, fc="#B23A3A", ec="black")); ax.text(36.5, 21.5, "LST parked here\n(facing NE, engine running)", fontsize=6.5, ha="right")
    ax.add_patch(FancyArrowPatch((43, 16), (50.5, 23.6), arrowstyle="-|>", mutation_scale=12, color="#B23A3A", lw=1.6))
    ax.text(47, 13.2, "unaided roll,\n0.57 % downslope", fontsize=6.5, color="#B23A3A", ha="left")
    ax.text(57.5, 22, "impact: tail section", fontsize=6.5, ha="left", color="#B23A3A", weight="bold")
    ax.annotate("", xy=(52, 21), xytext=(52, 4), arrowprops=dict(arrowstyle="->", color="#1F3A5F", ls="--"))
    ax.text(54, 5, "aircraft taxied in along the W29 lead-in line;\nthe LST began to roll when it was ~46 m from its stop",
            fontsize=6.2, color="#1F3A5F")
    ax.text(1, 1, "Schematic drawn by NAVRAP from the report's description — not to scale; not a KNKT figure.", fontsize=6, color="#6B7280")
    out.append({"id": "IMG1", "caption": "Schematic of the occurrence site at Apron W, parking stand W29 (not to scale)", "data": _png(f)})
    # A2: parking brake chain
    f, ax = plt.subplots(figsize=(7.2, 2.2)); ax.set_xlim(0, 100); ax.set_ylim(0, 30); ax.axis("off")
    boxes = [(10, "Ratchet-bar handle\n(cab)"), (34, "Cable"), (58, "Brake drum on\npropeller shaft"), (84, "Shoes and linings\nNOT INSTALLED")]
    for x, t in boxes:
        bad = "NOT" in t
        ax.add_patch(Rectangle((x - 10, 10), 20, 12, fc="#FEE2E2" if bad else "white", ec="#B23A3A" if bad else "#1F3A5F", lw=1.2))
        ax.text(x, 16, t, ha="center", va="center", fontsize=7, weight="bold" if bad else "normal")
    for a, b in ((20, 24), (44, 48), (68, 74)):
        ax.add_patch(FancyArrowPatch((a, 16), (b, 16), arrowstyle="-|>", mutation_scale=10, color="#6B7280"))
    ax.text(50, 3, "Handle moves freely and locks at any position, but with no friction parts the truck rolls even with the handle fully applied (functional test).",
            ha="center", fontsize=6.5, color="#374151")
    out.append({"id": "IMG2", "caption": "LST parking brake chain and the missing components (schematic)", "data": _png(f)})
    # A3: serviceability timeline
    f, ax = plt.subplots(figsize=(7.2, 2.4)); ax.set_xlim(0, 100); ax.set_ylim(0, 30); ax.axis("off")
    ax.plot([4, 96], [15, 15], color="#1F3A5F", lw=2)
    ev = [(6, "May 2023\nSSA: tractor with\nU/S parking brake\n(closed: to workshop)"), (24, "13 Sep 2023\nbrake shoes and\nlinings removed"),
          (42, "Sep 2023 – 2024\nPMIs: parking brake\nnot marked; 'OK'"), (58, "Apr 2024\nSSA: no finding\non the LST"),
          (75, "Aug – Oct 2024\ndaily checks: brakes\n'X', vehicle 'S/B'"), (93, "16 Oct 2024\noccurrence")]
    for x, t in ev:
        ax.plot([x], [15], "o", color="#B23A3A" if "occurrence" in t else "#1F3A5F", ms=7)
        ax.text(x, 19 if ev.index((x, t)) % 2 == 0 else 2, t, ha="center", fontsize=6.3, va="bottom")
    out.append({"id": "IMG3", "caption": "How the unserviceable parking brake stayed in service, September 2023 – October 2024", "data": _png(f)})
    return out


def model() -> dict:
    ev = [{"id": f"E{k + 1}", "start": s, "end": e, "title": t, "comments": NOTES.get(s, ""), "source": src, "theme": th, "display": True,
           "safety_factor": sf, "sf_type": st, "factor_id": fid} for k, (s, e, t, src, th, sf, st, fid) in enumerate(EVENTS)]
    rep = report_data()
    rep["attachments"] = figures()
    return {"occurrence": {"ref": "KNKT.24.10.22.04", "date": "2024-10-16", "occurrence_type": "Ground collision — GSE with aircraft (serious incident)",
                           "title": "Boeing 737-800 PK-GMP struck by an unattended lavatory service truck at parking stand W29, Kualanamu (WIMM)",
                           "location": "Kualanamu International Airport (WIMM), Deli Serdang, North Sumatra, Indonesia", "time": "about 2126 LT (UTC+7)",
                           "operator": "PT Garuda Indonesia (aircraft); PT Gapura Angkasa (ground handling); PT Angkasa Pura Aviasi (airport)",
                           "summary": "After a scheduled flight from Jakarta, PK-GMP was taxiing onto parking stand W29 when the lavatory service truck, "
                                      "parked unattended with its engine running in the adjacent staging area, began to roll and struck the aircraft's tail "
                                      "as it stopped. The truck's parking brake had no brake shoes or linings and the wheel chock was not in contact with the tyre."},
            "events": ev, "factors": factors(), "key_findings": KEY_FINDINGS, "report": rep,
            "review": {k: True for k in ("sufficiency", "missing", "enhance", "sense", "fair_individual", "fair_org", "organised", "no_merge", "bias")},
            "stop_rule": "Stopped at the regulator: the regulation's wording and the absence of GSE oversight are the highest-level factors that an organisation could practicably address."}


def seed_demo_knkt(db: Session):
    from .api.common import active_scheme
    from .engines import atsb as engine
    from .models import Assessment, Project, RiskScheme, Study
    if db.query(Project).filter_by(code="DEMO-07").first():
        return
    p = Project(code="DEMO-07", title="Case study: KNKT.24.10.22.04 — B737-800 PK-GMP struck by a lavatory service truck, Kualanamu",
                change_type="investigation", units="Apron W, Kualanamu (WIMM)", sponsor="Safety & Quality",
                description="Stand-alone worked example of an ORLIO investigation using the ATSB method, built from the published KNKT final report "
                            "KNKT.24.10.22.04. Facts are from the report; the ORLIO/ATSB analysis and the actions marked 'proposed (NAVRAP example)' are illustrative.")
    db.add(p); db.flush()
    rs = db.query(RiskScheme).order_by(RiskScheme.version.desc()).first()
    a = Assessment(project_id=p.id, title="ORLIO safety investigation — PK-GMP / lavatory service truck collision, 16 October 2024",
                   created_by="assessor", risk_scheme_version=rs.version if rs else 1,
                   scope="Analysis of the serious incident with the ATSB method: sequence of events, safety factors, tests, safety issues, corrective actions.",
                   environment="Apron W, Kualanamu International Airport, night; ground handling by PT Gapura Angkasa.",
                   assumptions=f"Facts from {SRC}. Risk ratings and proposed corrective actions are the analyst's illustration.")
    db.add(a); db.flush()
    m = model()
    db.add(Study(assessment_id=a.id, method="atsb", title="ORLIO analysis (ATSB method) — KNKT.24.10.22.04", model=m,
                 results=engine.analyse(m, active_scheme(db)), template_version="1.0"))
    db.commit()
