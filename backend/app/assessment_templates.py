"""Ready-to-use assessment templates (Manual Appendix C; SRS TPL-01..05).

A template creates a pre-filled assessment: scope text and a set of method studies whose content (functions,
nodes, failure modes, fault tree, barriers, argument) is proposed for the kind of change. The team reviews,
edits and rates it in workshops. With filled=True the builder also adds illustrative ratings, calculations,
hazards and actions — this is how demo project DEMO-04 is created.

Template "aim_acquisition": New AIM system acquisition, from installation to transition into operation.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from .engines import fta as fta_engine
from .engines import hra as hra_engine
from .engines import sim as sim_engine
from .models import Action, Assessment, Control, Hazard, Study

AIM_SCOPE = (
    "Acquisition, installation, data migration and transition into operation of a new Aeronautical Information Management (AIM) "
    "system replacing the legacy AIS system. Functions in scope: receipt and registration of raw data from originators; validation "
    "and verification (incl. CRC-32Q); AIXM 5.1 database and AIRAC effectivity management; NOTAM creation, validation and "
    "distribution (AFTN/AMHS); AIP/eAIP, AIP AMDT/SUP and AIC production; charts and electronic terrain and obstacle data; "
    "pre-flight information bulletins and data feeds to FDP/ATFM and external users. Interfaces: data originators (procedure "
    "design, survey, aerodrome operators, military), AMHS/AFTN, FDP/ATFM, data houses, airspace users. Out of scope: the content "
    "of source data (responsibility of the originators), the FDP/ATFM systems themselves.")
AIM_ENV = (
    "Aeronautical information for all Indonesian FIRs, published to the AIRAC 28-day cycle; NOTAM office operating H24; "
    "data integrity classification per ICAO Annex 15 and PANS-AIM (Doc 10066): critical, essential, routine. Phases: "
    "(1) specification, (2) design (PSSA), (3) installation beside the live legacy system, (4) data migration, "
    "(5) transition with shadow operation and cut-over, (6) operation and post-implementation review.")
AIM_ASSUMPTIONS = (
    "A-1 The vendor provides software assurance evidence (EUROCAE ED-153 or equivalent) for the assigned assurance level. "
    "A-2 The legacy AIS system remains available as a hot-standby fallback until the end of hypercare. "
    "A-3 Data originators continue to deliver data in the agreed formats and to the agreed timescales (formal arrangements). "
    "A-4 Cut-over is scheduled outside an AIRAC effective date and outside the NOTAM peak period. "
    "A-5 Probabilities in the fault tree are per critical data item published and are illustrative until replaced by AirNav data.")

# ---------------------------------------------------------------- FHA
AIM_FHA = [
    ("F2 Validate and verify data", "Erroneous (undetected)", "Wrong or corrupted critical data (threshold coordinates, obstacle elevation, procedure fix) passes validation and is published",
     "Aircraft flies a procedure or database built on wrong data; CFIT or runway excursion possible", "B",
     "Independent verification against the source for all critical data; CRC-32Q end to end; second-source comparison for critical items"),
    ("F4 Create and distribute NOTAM", "Total loss", "NOTAM service unavailable (system or AMHS/AFTN link down)",
     "Crews and ATC unaware of runway closures, navaid outages or airspace restrictions", "C",
     "Manual NOTAM procedure via standalone AFTN terminal; restoration within the time agreed in the service level"),
    ("F4 Create and distribute NOTAM", "Erroneous (undetected)", "NOTAM issued with wrong content (location, runway, times, coordinates)",
     "Crew uses a closed runway or restricted airspace; conflict with activity", "B",
     "Four-eyes check against originator request; automated validation of Q-code, location and times"),
    ("F4 Create and distribute NOTAM", "Delayed", "NOTAM distributed after its effective time",
     "Operations planned without the restriction; late re-planning", "C", "Time-to-distribute monitored; alert when a request is not processed within the target time"),
    ("F5 Publish AIP / eAIP (AIRAC)", "Erroneous (undetected)", "AIRAC amendment with wrong effective date, missing or superseded pages",
     "Users and data houses load inconsistent data; FMS databases differ from the published AIP", "C",
     "Publication checklist with independent sign-off; automated consistency check of effectivity"),
    ("F5 Publish AIP / eAIP (AIRAC)", "Delayed", "AIRAC publication misses the 28-day cycle or the 42/56-day advance notice",
     "Change cannot be implemented on time; interim NOTAM workload; data-house update missed", "C", "AIRAC schedule control; early-warning milestones"),
    ("F6 Charts and terrain/obstacle data", "Erroneous (undetected)", "Wrong obstacle or terrain data in charts or eTOD",
     "Minimum altitudes or procedure design based on wrong obstacle data", "B",
     "Obstacle data verified against survey source; independent check of chart production"),
    ("F7 PIB and data feeds", "Partial loss / degradation", "PIB omits a relevant NOTAM (query, filter or validity error)",
     "Crew briefed without a critical restriction", "B", "Regression test of PIB queries; comparison with legacy PIB during shadow operation"),
    ("F3 Store and manage data", "Erroneous (undetected)", "Wrong effectivity: superseded data served after the AIRAC date or new data served early",
     "Users receive data not valid at time of use", "B", "Automated effectivity tests at each AIRAC switch; audit trail of data versions"),
    ("F3 Store and manage data", "Total loss", "Database lost or corrupted without recoverable backup",
     "Loss of NOTAM continuity and of the authoritative data set", "C", "Replicated database at a separate site; restore tests every 6 months"),
    ("F8 Interfaces and data exchange", "Erroneous (detected)", "Messages or data sets rejected by AMHS, FDP or external users (format / schema errors)",
     "Manual re-processing; increased workload; delays", "D", "Interface control documents; end-to-end interface tests before cut-over"),
    ("F1 Receive raw data", "Delayed", "Raw data from originators received late or incomplete",
     "Compressed processing time increases error likelihood downstream", "C", "Formal arrangements with originators including timescales and formats"),
]

# ---------------------------------------------------------------- HAZOP (data-flow nodes)
AIM_NODES = [
    ("N1", "Originator → AIS: receipt of raw data", "Complete, correct, formally authorised raw data received in the agreed format and in time for the AIRAC or NOTAM process."),
    ("N2", "AIS entry, validation and verification → AIM database", "Every data item entered exactly as in the source, validated against rules, verified independently, protected by CRC."),
    ("N3", "AIM database → AIP/eAIP publication (AIRAC)", "The correct data set, with the correct effectivity, published on the AIRAC schedule."),
    ("N4", "NOTAM creation → AFTN/AMHS distribution → users", "Correct NOTAM distributed to all addressees before its effective time; cancelled or replaced when the condition changes."),
    ("N5", "AIM database → charts and terrain/obstacle data", "Charts and eTOD derived from the current verified data set."),
    ("N6", "AIM → PIB, FDP/ATFM and external data users", "Users receive complete and current information for their flight or system."),
    ("N7", "Legacy AIS database → new AIM database (migration)", "All records migrated completely and correctly, with integrity protection preserved."),
]
AIM_HAZOP = [  # node, parameter, guideword, deviation, causes, consequences, safeguards, severity, likelihood(demo), recommendation
    ("N1", "Content", "Other than", "Raw data in a different datum or unit than declared", "Originator uses local datum or feet/metres confusion", "Coordinates or elevations wrong after entry", "Format checks at receipt", "B", 2, "Formal arrangement specifying WGS-84 and units; automated plausibility check"),
    ("N1", "Timing", "Late", "Raw data received after the AIRAC cut-off", "Originator unaware of AIRAC dates", "Rushed processing or missed cycle", "AIRAC calendar published", "C", 3, "Originator reminders at 70 and 56 days; formal escalation"),
    ("N1", "Message", "No / Not", "Change not notified by originator", "No formal arrangement; staff turnover at originator", "Published data out of date", "None", "B", 3, "Formal arrangements with all originators; periodic data review"),
    ("N2", "Content", "Other than", "Value entered differs from source (digit transposition)", "Manual entry; time pressure; new HMI", "Erroneous data enters database", "Validation rules; four-eyes check", "B", 3, "Import from digital source where possible; verification against source, not against screen"),
    ("N2", "Content", "Part of", "CRC not computed or not checked on entry", "Function disabled or bypassed", "Later corruption undetectable", "CRC function in specification", "B", 2, "CRC mandatory and non-bypassable; alarm on missing CRC"),
    ("N3", "Timing", "Early", "Data set published with wrong effective date", "Effectivity field mis-set; time-zone handling", "Users apply data before it is valid", "Publication checklist", "B", 2, "Automated effectivity test before release"),
    ("N3", "Sequence", "Reverse", "Superseded page republished", "Version control error", "Inconsistent AIP", "Manual review", "C", 2, "Version comparison report per amendment"),
    ("N4", "Destination", "Part of", "NOTAM not delivered to all addressees", "AMHS routing table incomplete after migration", "Some users unaware of restriction", "Distribution acknowledgement", "B", 3, "Routing table verified against legacy; test messages to each addressee"),
    ("N4", "Content", "Other than", "NOTAM with wrong location indicator or runway", "Selection from list; auto-fill", "Restriction applied to wrong aerodrome", "Four-eyes check", "B", 3, "Highlight location changes; verification against request"),
    ("N4", "Message", "No / Not", "NOTAMC/NOTAMR not issued when condition ends", "No tracking of expiry", "Outdated restrictions; loss of credibility", "Daily NOTAM review", "C", 3, "Expiry tracking with alerts"),
    ("N5", "Content", "Other than", "Chart generated from superseded obstacle data", "Charting tool not linked to current data set", "Wrong minimum altitudes on chart", "Chart checking", "B", 2, "Charting reads only from the verified current data set; data-set ID printed on chart"),
    ("N6", "Content", "Part of", "PIB omits relevant NOTAM", "Query filter or area definition error", "Crew not briefed", "Legacy comparison", "B", 2, "PIB regression tests; comparison with legacy during shadow operation"),
    ("N6", "Timing", "Late", "FDP/ATFM feed updated late", "Interface queue backlog", "ATC uses outdated restrictions", "Interface monitoring", "C", 3, "Feed latency monitoring with alarm"),
    ("N7", "Message", "Less", "Records lost in migration", "Mapping gap between legacy schema and AIXM 5.1", "Missing data after cut-over", "Migration log", "B", 3, "100% record count and critical-data comparison old vs new"),
    ("N7", "Content", "Other than", "Values changed by conversion (datum, rounding, units)", "Conversion routine error", "Wrong published data", "Sample checks", "B", 3, "Automated comparison of every critical item; independent review of conversion rules"),
]

AIM_FMEA = [  # item, failure mode, cause, end effect, detection, compensation, s, o, d
    ("Primary application server", "Hangs / stops", "Software fault; resource exhaustion", "NOTAM and publication functions unavailable", "Monitoring alarm", "Fail-over to standby", 6, 3, 2),
    ("Standby server / cluster fail-over", "Fails to take over", "Same software fault; configuration drift", "Total loss of AIM service", "Fail-over test", "Manual NOTAM via AFTN terminal", 7, 2, 5),
    ("AIXM database", "Silent data corruption", "Storage fault; software defect", "Wrong data served", "CRC check on read", "Restore from verified backup", 9, 2, 4),
    ("CRC-32Q module", "CRC computed on wrong field set", "Implementation defect", "Corruption undetectable", "Test vectors at SAT", "Manual verification", 8, 2, 6),
    ("NOTAM validation rules engine", "Rule missing or wrong", "Configuration error at set-up", "Invalid NOTAM accepted", "Rule coverage test", "Four-eyes check", 7, 3, 5),
    ("AMHS/AFTN gateway", "Messages queued / lost", "Link failure; routing error", "NOTAM not delivered", "Delivery acknowledgement", "Resend; manual distribution", 7, 3, 3),
    ("Time source (NTP)", "Clock offset", "NTP failure", "NOTAM validity times wrong", "Time monitoring", "Manual time check", 6, 2, 5),
    ("eAIP web publication", "Stale content served (cache)", "Cache not invalidated at AIRAC", "Users read superseded AIP", "Version stamp check", "Manual purge", 6, 3, 4),
]

# ---------------------------------------------------------------- FTA
AIM_FTA = {"top": "TOP", "nodes": {
    "TOP": {"type": "or", "label": "Erroneous critical aeronautical data published undetected (per critical item)", "children": ["G1", "G2"]},
    "G1": {"type": "and", "label": "Wrong value introduced and detection defeated", "children": ["GIN", "GDET"]},
    "GIN": {"type": "or", "label": "Wrong value introduced", "children": ["E1", "E2", "E3"]},
    "GDET": {"type": "or", "label": "Detection defeated", "children": ["G3", "E8"]},
    "G3": {"type": "and", "label": "Validation and independent verification both miss", "children": ["E4", "E5"]},
    "G2": {"type": "and", "label": "Stored/transferred data corrupted and CRC protection absent", "children": ["E6", "E7"]},
    "E1": {"type": "basic", "label": "Originator provides wrong value", "p": 5e-4},
    "E2": {"type": "basic", "label": "AIS data-entry error (HRA task T1)", "p": 1.6e-3},
    "E3": {"type": "basic", "label": "Migration / conversion error", "p": 1e-4},
    "E4": {"type": "basic", "label": "Automated validation rules miss the error", "p": 0.2},
    "E5": {"type": "basic", "label": "Independent verification misses the error (HRA task T2)", "p": 0.06},
    "E6": {"type": "basic", "label": "Corruption in storage or transfer", "p": 1e-5},
    "E7": {"type": "basic", "label": "CRC not generated or not checked", "p": 1e-3},
    "E8": {"type": "basic", "label": "Common cause: verifier checks the system display, not the source document", "p": 1e-3},
}}

AIM_HRA = [
    {"id": "T1", "task": "Enter a critical data item (coordinate, elevation) from the source document into the new AIM HMI", "library": "heart", "gtt": "G",
     "epcs": [{"code": "9", "apoa": 0.2}, {"code": "2", "apoa": 0.1}], "justification": "Familiar task but new HMI (unlearning, APOA 0.2); moderate time pressure before AIRAC cut-off (0.1)."},
    {"id": "T2", "task": "Independently verify the entered item against the source document", "library": "heart", "gtt": "E",
     "epcs": [{"code": "2", "apoa": 0.2}], "justification": "Routine check under time pressure at AIRAC cut-off."},
]

AIM_CCA = {
    "zsa": [{"id": "Z-01", "zone": "AIM server room (primary)", "equipment": "Application and database servers, AMHS gateway", "concern": "Primary and standby in one room",
             "check": "Primary and standby in separate fire zones", "finding": "", "action": ""},
            {"id": "Z-02", "zone": "Disaster-recovery site", "equipment": "Replicated database, standby application", "concern": "Shared WAN path with primary",
             "check": "Diverse network paths", "finding": "", "action": ""}],
    "pra": [{"id": "P-01", "risk": "Fire", "zones": "AIM server room", "equipment": "Primary servers", "redundancy_defeated": False, "effect": "Loss of primary", "severity": "C", "mitigation": "DR site", "action": ""},
            {"id": "P-02", "risk": "Cyber attack", "zones": "All sites", "equipment": "Primary and DR (same software, same credentials)", "redundancy_defeated": True,
             "effect": "Loss or manipulation of all data", "severity": "B", "mitigation": "Segmentation; offline backups", "action": "See security study"}],
    "cma": [{"id": "CM-01", "claim": "Automated validation (E4) and independent verification (E5) fail independently", "items": "E4, E5", "source": "Design / specification",
             "analysis": "Verifier may check against the system display that the validation also uses, not the source (E8)", "independent": "Partly", "action": "Verification procedure requires the source document"},
            {"id": "CM-02", "claim": "Primary and standby servers fail independently", "items": "Primary, standby", "source": "Software",
             "analysis": "Same software release on both", "independent": "No", "action": "Fail-over test after every release; manual NOTAM fallback"},
            {"id": "CM-03", "claim": "CRC generation and CRC checking are independent", "items": "CRC module", "source": "Software",
             "analysis": "Both in the same module of the same product", "independent": "No", "action": "Independent CRC check by publication tool or recipient"}],
}

AIM_STPA = {
    "losses": [{"id": "L-1", "text": "Aircraft accident or serious incident caused by erroneous or missing aeronautical information"},
               {"id": "L-2", "text": "Loss of the aeronautical information service"}],
    "hazards": [{"id": "H-1", "text": "Erroneous aeronautical information published", "losses": ["L-1"]},
                {"id": "H-2", "text": "Required aeronautical information not available to users when needed", "losses": ["L-1", "L-2"]}],
    "constraints": [{"id": "SC-1", "text": "Critical data must not be published unless verified against the source independently of the system", "hazards": ["H-1"]},
                    {"id": "SC-2", "text": "NOTAM must reach all users before the effective time and be cancelled when the condition ends", "hazards": ["H-2"]}],
    "structure": {"nodes": [
        {"id": "ORIG", "label": "Data originators", "kind": "controller", "x": 0, "y": 0, "process_model": "What changed; when effective"},
        {"id": "SUP", "label": "AIS supervisor / validator", "kind": "controller", "x": 320, "y": 0, "process_model": "Workload; AIRAC status"},
        {"id": "AISO", "label": "AIS officer (NOTAM office / AIP)", "kind": "controller", "x": 160, "y": 150, "process_model": "Request content; system state"},
        {"id": "AIM", "label": "New AIM system", "kind": "automation", "x": 160, "y": 300, "process_model": "Validation rules; effectivity"},
        {"id": "USR", "label": "Users (crews, ATC, FDP/ATFM, data houses)", "kind": "process", "x": 160, "y": 450}],
        "edges": [
            {"id": "e1", "source": "ORIG", "target": "AISO", "kind": "control", "label": "raw data / NOTAM request"},
            {"id": "e2", "source": "SUP", "target": "AISO", "kind": "control", "label": "approval; priorities"},
            {"id": "e3", "source": "AISO", "target": "AIM", "kind": "control", "label": "enter, approve, release"},
            {"id": "e4", "source": "AIM", "target": "AISO", "kind": "feedback", "label": "validation warnings; status"},
            {"id": "e5", "source": "AIM", "target": "USR", "kind": "control", "label": "NOTAM, AIP, PIB, feeds"},
            {"id": "e6", "source": "USR", "target": "ORIG", "kind": "feedback", "label": "error reports"},
            {"id": "e7", "source": "AISO", "target": "SUP", "kind": "feedback", "label": "pending items"}]},
    "ucas": [
        {"id": "UCA-1", "control_action": "enter, approve, release", "type": "Providing causes hazard", "text": "AIS officer approves an auto-filled NOTAM without checking it against the request", "context": "when the new HMI pre-fills fields from a template", "hazards": ["H-1"]},
        {"id": "UCA-2", "control_action": "enter, approve, release", "type": "Providing causes hazard", "text": "Data set released for publication with unresolved validation warnings", "context": "when warnings are frequent and treated as nuisance", "hazards": ["H-1"]},
        {"id": "UCA-3", "control_action": "enter, approve, release", "type": "Not providing causes hazard", "text": "NOTAMC/NOTAMR not issued when the condition ends or changes", "context": "when expiry is not tracked by the system", "hazards": ["H-1", "H-2"]},
        {"id": "UCA-4", "control_action": "NOTAM, AIP, PIB, feeds", "type": "Too early / too late / wrong order", "text": "System serves new data before its AIRAC effective date", "context": "when effectivity is mis-set during migration", "hazards": ["H-1"]},
        {"id": "UCA-5", "control_action": "approval; priorities", "type": "Too early / too late / wrong order", "text": "Supervisor approval given too late for distribution before effective time", "context": "when approvals queue during the cut-over period", "hazards": ["H-2"]}],
    "scenarios": [
        {"id": "S-1", "uca": "UCA-1", "type": "Flawed process model", "text": "Officer believes auto-fill is correct because it was correct in training", "requirement": "Highlight auto-filled fields; verification against source in procedure (HTA 3.1)"},
        {"id": "S-2", "uca": "UCA-2", "type": "Inadequate feedback", "text": "Warnings not ranked; critical warnings buried among cosmetic ones", "requirement": "Blocking warnings for critical data; warning classification reviewed at SAT"},
        {"id": "S-3", "uca": "UCA-4", "type": "Inadequate control algorithm", "text": "Effectivity default taken from migration date", "requirement": "Automated effectivity test at every AIRAC switch (FHA F3)"}],
}

AIM_HTA = {"tasks": [
    {"id": "0", "parent": None, "title": "Publish a NOTAM with the new AIM system", "plan": "Do 1–4 in order; do 5 until the NOTAM expires or is cancelled"},
    {"id": "1", "parent": "0", "title": "Receive and check the request", "plan": "Do 1.1 then 1.2; if incomplete, return to originator"},
    {"id": "1.1", "parent": "1", "title": "Verify the originator is authorised", "error_modes": ["Check omitted"]},
    {"id": "1.2", "parent": "1", "title": "Check the request is complete and unambiguous", "error_modes": ["Information not obtained"]},
    {"id": "2", "parent": "0", "title": "Compose the NOTAM", "plan": "Do 2.1–2.3 in order", "hra": "T1"},
    {"id": "2.1", "parent": "2", "title": "Select Q-code and location indicator", "error_modes": ["Action on wrong object"]},
    {"id": "2.2", "parent": "2", "title": "Enter items B, C and E (times in UTC, text, coordinates)", "error_modes": ["Wrong action", "Wrong information communicated"]},
    {"id": "2.3", "parent": "2", "title": "Review and resolve validation warnings", "error_modes": ["Check omitted"]},
    {"id": "3", "parent": "0", "title": "Independent verification", "plan": "Do 3.1 and 3.2 by a second officer", "hra": "T2"},
    {"id": "3.1", "parent": "3", "title": "Compare every field with the source request (not with the screen)", "error_modes": ["Check omitted"]},
    {"id": "3.2", "parent": "3", "title": "Check validity times and time zone", "error_modes": ["Check omitted"]},
    {"id": "4", "parent": "0", "title": "Release and confirm distribution", "plan": "Do 4.1 then 4.2"},
    {"id": "4.1", "parent": "4", "title": "Release the NOTAM"},
    {"id": "4.2", "parent": "4", "title": "Confirm delivery acknowledgements from AMHS", "error_modes": ["Check omitted"]},
    {"id": "5", "parent": "0", "title": "Monitor, replace or cancel", "plan": "Do 5.1 daily; 5.2 when the condition changes"},
    {"id": "5.1", "parent": "5", "title": "Review active NOTAM list and expiry alerts"},
    {"id": "5.2", "parent": "5", "title": "Issue NOTAMR or NOTAMC", "error_modes": ["Action omitted", "Action too early / late"]},
]}

AIM_JHA = {"job": {"title": "Install AIM servers and network equipment beside the live legacy AIS", "location": "AIS equipment room and DR site", "permits": "Permit to work; change approval; LOTO for electrical work"},
           "rows": [
               {"id": "S-01", "step": "Deliver and position racks", "hazards": "Manual handling; floor loading; damage to live legacy racks", "controls": "Lifting equipment; floor load check; protect live racks", "hierarchy": "Engineering", "responsible": "Vendor site lead"},
               {"id": "S-02", "step": "Connect power to new racks", "hazards": "Electric shock; tripping the shared UPS feeding the legacy AIS", "controls": "Isolate and LOTO; load calculation on UPS; work in low-traffic window", "hierarchy": "Engineering", "responsible": "Facility engineer"},
               {"id": "S-03", "step": "Connect to operational network and AMHS", "hazards": "Disturbing legacy AIS traffic; configuration error", "controls": "Change approval; rollback plan; test during quiet hours", "hierarchy": "Administrative", "responsible": "Network engineer"},
               {"id": "S-04", "step": "Cable work under raised floor", "hazards": "Damage to legacy cabling; fire-suppression trigger", "controls": "Cable survey; suppression system in manual mode with fire watch", "hierarchy": "Administrative", "responsible": "Vendor site lead"},
               {"id": "S-05", "step": "Commissioning tests", "hazards": "Test messages reaching live users", "controls": "Test addressees only; TEST prefix; supervisor sign-off", "hierarchy": "Administrative", "responsible": "AIS supervisor"}]}

AIM_SWIFT = [
    {"guideword": "Equipment and utilities", "what_if": "What if connecting the new racks trips the UPS that also feeds the legacy AIS?", "consequence": "Loss of NOTAM service", "safeguards": "UPS load calculation", "severity": "C", "likelihood": 2, "recommendation": "Separate feed or UPS capacity confirmed before work", "owner": "Facilities"},
    {"guideword": "Information and communication", "what_if": "What if test NOTAMs from the new system reach live users?", "consequence": "Confusing or false restrictions", "safeguards": "Test addressees", "severity": "C", "likelihood": 2, "recommendation": "Technical block on live addressees until go-live", "owner": "AIS supervisor"},
    {"guideword": "Timing and sequence", "what_if": "What if cut-over coincides with an AIRAC effective date?", "consequence": "Publication errors or missed cycle", "safeguards": "Project plan", "severity": "C", "likelihood": 3, "recommendation": "Cut-over window at least 7 days from AIRAC dates; change freeze", "owner": "Project manager"},
    {"guideword": "People", "what_if": "What if AIS officers have not used the new system before their first live shift?", "consequence": "Entry errors; slow processing", "safeguards": "Vendor training", "severity": "B", "likelihood": 3, "recommendation": "Competence check and minimum hours on the shadow system", "owner": "AIS manager"},
    {"guideword": "Procedures", "what_if": "What if rollback is needed but the legacy database is no longer current?", "consequence": "No usable fallback", "safeguards": "None yet", "severity": "B", "likelihood": 2, "recommendation": "Keep legacy updated in parallel until end of hypercare; tested rollback", "owner": "Project manager"},
    {"guideword": "External events", "what_if": "What if a major NOTAM event (volcanic ash, runway closure wave) happens during cut-over?", "consequence": "Peak workload on an unfamiliar system", "safeguards": "None", "severity": "B", "likelihood": 2, "recommendation": "Go/no-go includes an operational-situation check; defer cut-over", "owner": "AIS manager"},
    {"guideword": "Management and organisation", "what_if": "What if schedule pressure shortens the shadow operation?", "consequence": "Defects found after go-live", "safeguards": "Project board", "severity": "B", "likelihood": 3, "recommendation": "Minimum shadow period and exit criteria in the safety case; go/no-go signed by safety", "owner": "Safety manager"},
]

AIM_SEC = [
    {"asset": "AIM database (critical data)", "threat": "Unauthorised modification of critical data", "source": "Insider (malicious)", "vulnerability": "Broad write privileges", "c": 1, "i": 5, "a": 2, "likelihood": 2, "controls": "Audit trail", "safety_severity": "B", "treatment": "Role-based access; four-eyes release; integrity monitoring", "owner": "AIM manager"},
    {"asset": "Vendor remote support access", "threat": "Compromise of vendor account", "source": "Supplier / third party", "vulnerability": "Shared credentials", "c": 3, "i": 5, "a": 4, "likelihood": 2, "controls": "VPN", "safety_severity": "B", "treatment": "Named accounts with MFA; session approval and recording", "owner": "IT security"},
    {"asset": "eAIP / NOTAM web service", "threat": "Defacement or false content", "source": "External attacker", "vulnerability": "Internet-facing web server", "c": 1, "i": 4, "a": 3, "likelihood": 3, "controls": "Firewall", "safety_severity": "C", "treatment": "Signed publications; integrity check by users; WAF", "owner": "IT security"},
    {"asset": "Primary and DR servers", "threat": "Ransomware", "source": "External attacker", "vulnerability": "Same credentials and network for primary and DR", "c": 3, "i": 4, "a": 5, "likelihood": 2, "controls": "Backups", "safety_severity": "C", "treatment": "Segmentation; offline backups; manual NOTAM fallback", "owner": "IT security"},
]

AIM_SIM_EX = {"title": "Shadow operation — new AIM system beside legacy AIS", "type": "Shadow-mode trial",
              "objectives": "Show that the new system produces the same critical data and NOTAM outputs as the legacy system and that processing time and workload are acceptable.",
              "scenarios": "One full AIRAC cycle (28 days) of live inputs processed in parallel; daily comparison; includes one AIRAC effective date.",
              "participants": "All AIS/NOTAM office shifts", "limitations": "Legacy output is the reference; errors present in both systems are not detected."}
AIM_SIM_MEASURES = [
    {"id": "M1", "label": "Differences in critical data outputs (new vs legacy) per day", "unit": "items", "better": "lower", "criterion": {"type": "threshold", "value": 0}, "baseline": [], "solution": []},
    {"id": "M2", "label": "NOTAM processing time, request to distribution", "unit": "min", "better": "lower", "criterion": {"type": "no_worse", "value": 2}, "baseline": [], "solution": []},
    {"id": "M3", "label": "NOTAM rejected by validation or AMHS per day", "unit": "msgs", "better": "lower", "criterion": {"type": "threshold", "value": 2}, "baseline": [], "solution": []},
]
AIM_SIM_DEMO = {"M1": ([], [0, 0, 0, 1, 0, 0, 0, 0]), "M2": ([14, 12, 15, 13, 16, 12, 14, 13], [15, 13, 16, 14, 15, 14, 15, 14]),
                "M3": ([1, 0, 2, 1, 1, 0, 1, 1], [2, 1, 3, 1, 2, 1, 1, 2])}


def _bowtie():
    B = {}
    def b(bid, text, kind, owner, spi="", critical=False, eff="unknown", ver="planned"):
        B[bid] = {"id": bid, "text": text, "kind": kind, "effectiveness": eff, "owner": owner, "critical": critical, "verification": ver, "spi": spi}
    b("PB1", "100% comparison of critical data, legacy vs new", "software", "AIM data manager", "Differences found / resolved", True)
    b("PB2", "FAT and SAT incl. load and CRC test vectors", "software", "Project manager", "Open SAT defects by severity", True)
    b("PB3", "Shadow operation ≥ 1 AIRAC cycle, zero-difference criterion", "procedure", "AIS manager", "Daily differences (M1)", True)
    b("PB4", "Training and competence check before live shifts", "human", "AIS manager", "% officers signed off")
    b("PB5", "End-to-end interface tests (AMHS, FDP/ATFM, data houses)", "procedure", "Network engineer", "Interface test cases passed")
    b("PB6", "Cut-over window away from AIRAC dates; change freeze", "organisational", "Project manager")
    b("PB7", "Method statement and permit to work on legacy systems", "procedure", "Facility engineer")
    b("PB8", "Go/no-go criteria signed by AIS and Safety", "organisational", "Safety manager", "", True)
    b("RB1", "Tested rollback to legacy AIS (hot standby)", "procedure", "Project manager", "Rollback test time", True)
    b("RB2", "Manual NOTAM procedure via standalone AFTN terminal", "procedure", "AIS supervisor", "Drill every 6 months", True, "good", "existing-verified")
    b("RB3", "Service-status NOTAM / AIC to users", "procedure", "AIS supervisor")
    b("RB4", "Post-publication check and NOTAM correction", "procedure", "AIM data manager", "Errors found after publication")
    b("RB5", "Notification to data houses of any published error", "procedure", "AIM data manager")
    b("RB6", "Legacy kept in parallel until end of hypercare", "organisational", "Project manager")
    return {"hazard": "Changeover of the aeronautical information service from the legacy AIS to the new AIM system",
            "top_event": "Loss of, or erroneous, aeronautical information service during transition",
            "threats": [{"id": "T1", "text": "Data migration error (records lost or converted wrongly)", "barriers": ["PB1", "PB3"]},
                        {"id": "T2", "text": "Software defect revealed under live load", "barriers": ["PB2", "PB3"]},
                        {"id": "T3", "text": "Staff unfamiliar with new HMI and procedures", "barriers": ["PB4"]},
                        {"id": "T4", "text": "Interface misconfiguration at cut-over (AMHS/AFTN, FDP)", "barriers": ["PB5", "PB8"]},
                        {"id": "T5", "text": "Cut-over coincides with AIRAC date or NOTAM peak", "barriers": ["PB6", "PB8"]},
                        {"id": "T6", "text": "Installation works disturb the legacy AIS", "barriers": ["PB7"]}],
            "consequences": [{"id": "C1", "text": "Users receive erroneous aeronautical data", "severity": "B", "barriers": ["RB4", "RB5"]},
                             {"id": "C2", "text": "NOTAM service interrupted", "severity": "C", "barriers": ["RB1", "RB2", "RB3"]},
                             {"id": "C3", "text": "AIRAC cycle missed or inconsistent", "severity": "C", "barriers": ["RB6", "RB3"]}],
            "barriers": B,
            "escalation": [{"id": "EF1", "text": "Vendor support not on site during hypercare", "barrier": "RB1", "ef_barriers": ["On-site vendor hypercare in contract"]},
                           {"id": "EF2", "text": "Schedule pressure shortens shadow operation", "barrier": "PB3", "ef_barriers": ["Minimum shadow period fixed in safety case; go/no-go by Safety"]}]}


def _gsn(ids: dict):
    def sol(sid, parent, text, key):
        return {"id": sid, "type": "solution", "parent": parent, "text": text, "evidence": {"kind": "study", "ref": ids.get(key)}}
    return {"nodes": [
        {"id": "G0", "type": "goal", "text": "The new AIM system and its transition into operation are acceptably safe"},
        {"id": "C1", "type": "context", "parent": "G0", "text": "Scope, phases and interfaces as in the assessment description"},
        {"id": "C2", "type": "context", "parent": "G0", "text": "Data integrity classification (Annex 15, PANS-AIM Doc 10066)"},
        {"id": "A1", "type": "assumption", "parent": "G0", "text": "Vendor provides software assurance evidence (ED-153)"},
        {"id": "S0", "type": "strategy", "parent": "G0", "text": "Argue over specification, design, installation, data migration, transition and operation (SAM FHA → PSSA → SSA)"},
        {"id": "G1", "type": "goal", "parent": "S0", "text": "Safety objectives are set for every failure condition of every AIM function"},
        sol("Sn1", "G1", "FHA of AIM functions", "fha"), sol("Sn2", "G1", "Data-flow HAZOP", "hazop"),
        {"id": "G2", "type": "goal", "parent": "S0", "text": "The design meets the safety objectives"},
        sol("Sn3", "G2", "FTA: undetected erroneous critical data", "fta"), sol("Sn4", "G2", "Common cause analysis", "cca"),
        sol("Sn5", "G2", "FMEA of the architecture", "fmea"), sol("Sn6", "G2", "STPA of NOTAM / publication loop", "stpa"), sol("Sn7", "G2", "Security risk assessment", "sec"),
        {"id": "G3", "type": "goal", "parent": "S0", "text": "Installation does not degrade the legacy service"},
        sol("Sn8", "G3", "JHA of installation works", "jha"), sol("Sn9", "G3", "SWIFT of installation and cut-over", "swift"),
        {"id": "G4", "type": "goal", "parent": "S0", "undeveloped": True, "text": "Migrated data is complete and correct (100% critical-data comparison report)"},
        {"id": "G5", "type": "goal", "parent": "S0", "text": "The transition is controlled, with a tested rollback"},
        sol("Sn10", "G5", "Transition bowtie", "bowtie"), sol("Sn11", "G5", "Shadow operation results", "sim"),
        {"id": "G6", "type": "goal", "parent": "S0", "text": "Staff are competent and procedures support error-free work"},
        sol("Sn12", "G6", "HTA of NOTAM publication", "hta"), sol("Sn13", "G6", "HRA of data entry and verification", "hra"),
        {"id": "G7", "type": "goal", "parent": "S0", "undeveloped": True, "text": "Post-implementation monitoring confirms the assumptions (SPIs, 30/90-day reviews)"},
    ]}


STUDIES = [  # key, method, title
    ("fha", "fha", "FHA — AIM functions and failure conditions"),
    ("hazop", "hazop", "Data-flow HAZOP — originator to user, incl. migration"),
    ("fmea", "fmea", "FMEA — AIM system architecture"),
    ("fta", "fta", "FTA — erroneous critical data published undetected"),
    ("cca", "cca", "Common cause analysis — validation, verification, redundancy"),
    ("stpa", "stpa", "STPA — NOTAM and publication control loop"),
    ("hta", "hta", "HTA — publish a NOTAM with the new system"),
    ("hra", "hra", "HRA — critical data entry and verification"),
    ("sec", "sec", "Security risk — AIM data integrity and access"),
    ("jha", "jha", "JHA — installation works beside the live legacy AIS"),
    ("swift", "swift", "SWIFT — installation effects and cut-over"),
    ("bowtie", "bowtie", "Transition bowtie — changeover to the new AIM system"),
    ("sim", "sim", "Shadow operation — acceptance measures and criteria"),
    ("gsn", "gsn", "Safety argument — new AIM system (GSN skeleton)"),
]


def _rows(prefix, items):
    return [{"id": f"{prefix}-{i:02d}", **r} for i, r in enumerate(items, 1)]


def build_aim(db: Session, a: Assessment, filled: bool = False, participants=None) -> dict:
    """Create the AIM acquisition studies in assessment `a`. Returns {key: study_id}."""
    ids: dict[str, int] = {}
    parts = participants or [{"name": "Safety assessor", "role": "Facilitator"}, {"name": "AIS/NOTAM office", "role": "SME"},
                             {"name": "AIM vendor", "role": "SME"}, {"name": "CNS/IT engineering", "role": "SME"}]

    fha_rows = _rows("FC", [{"function": f, "failure_type": t, "condition": c, "effect": e, "severity": s, "requirements": r} for f, t, c, e, s, r in AIM_FHA])
    haz_rows = []
    for i, (n, par, gw, dev, cau, con, saf, sev, lik, rec) in enumerate(AIM_HAZOP, 1):
        row = {"id": f"HP-{i:02d}", "node": n, "parameter": par, "guideword": gw, "deviation": dev, "causes": cau, "consequences": con,
               "safeguards": saf, "severity": sev, "recommendation": rec}
        if filled:
            row["likelihood"] = lik
        haz_rows.append(row)
    fmea_rows = []
    for i, (it, fm, ca, ee, det, comp, s_, o, d) in enumerate(AIM_FMEA, 1):
        row = {"id": f"FM-{i:02d}", "item": it, "failure_mode": fm, "cause": ca, "end_effect": ee, "detection_method": det, "compensation": comp, "s": s_}
        if filled:
            row.update(o=o, d=d)
        fmea_rows.append(row)
    swift_rows = [dict(r) if filled else {k: v for k, v in r.items() if k != "likelihood"} for r in AIM_SWIFT]
    hra_tasks = [dict(t) for t in AIM_HRA]
    measures = [dict(m) for m in AIM_SIM_MEASURES]
    if filled:
        for m in measures:
            m["baseline"], m["solution"] = AIM_SIM_DEMO[m["id"]]
            m["baseline_text"], m["solution_text"] = ", ".join(map(str, m["baseline"])), ", ".join(map(str, m["solution"]))

    models = {
        "fha": {"rows": fha_rows},
        "hazop": {"nodes": [{"id": n, "name": nm, "type": "data-flow", "intent": it} for n, nm, it in AIM_NODES], "rows": haz_rows},
        "fmea": {"rows": fmea_rows},
        "fta": {"tree": AIM_FTA},
        "cca": AIM_CCA, "stpa": AIM_STPA, "hta": AIM_HTA, "hra": {"tasks": hra_tasks},
        "sec": {"rows": _rows("SR", AIM_SEC)}, "jha": AIM_JHA, "swift": {"rows": _rows("W", swift_rows)},
        "bowtie": _bowtie(), "sim": {"exercise": AIM_SIM_EX, "measures": measures},
    }
    results = {}
    if filled:
        results["fta"] = fta_engine.analyse(AIM_FTA)
        results["hra"] = {"tasks": [{"id": t["id"], **hra_engine.assess(t["library"], t["gtt"], t["epcs"])} for t in hra_tasks]}
        results["sim"] = {"measures": sim_engine.analyse(measures)}
    for key, method, title in STUDIES:
        if key == "gsn":
            continue
        s = Study(assessment_id=a.id, method=method, title=title, model=models[key], results=results.get(key, {}), participants=parts)
        db.add(s); db.flush(); ids[key] = s.id
    hta = db.get(Study, ids["hta"]); hta.model = {**hta.model, "hra_study": ids["hra"]}
    s = Study(assessment_id=a.id, method="gsn", title=dict((k, t) for k, _m, t in STUDIES)["gsn"], model=_gsn(ids), participants=parts)
    db.add(s); db.flush(); ids["gsn"] = s.id

    if filled:
        _demo_hazards(db, a, ids)
    return ids


def _demo_hazards(db: Session, a: Assessment, ids: dict):
    review = date.today() + timedelta(days=90)
    items = [  # ref, title, source key, row, init S/L, residual S/L, controls, rationale
        ("AIM-01", "Erroneous critical data published undetected", "fta", "TOP", ("B", 3), ("B", 2),
         [("Independent verification against the source document", "prevention", "planned", True), ("CRC-32Q end to end", "prevention", "planned", True),
          ("Originator proof-check of critical data before publication", "prevention", "planned", True)],
         "FTA 2.9e-5 per critical item (about 1.7e-6 per hour at 40 items per AIRAC cycle) exceeds the FHA objective; originator proof-check and second-source comparison required."),
        ("AIM-02", "NOTAM service interrupted during or after cut-over", "bowtie", "C2", ("C", 3), ("C", 2),
         [("Tested rollback to legacy AIS", "recovery", "planned", True), ("Manual NOTAM via standalone AFTN terminal", "recovery", "existing-verified", True)],
         "Bowtie: two recovery barriers, one existing and drilled."),
        ("AIM-03", "Records lost or converted wrongly in data migration", "hazop", "HP-14", ("B", 3), ("B", 1),
         [("100% comparison of critical data, legacy vs new", "prevention", "planned", True), ("Shadow operation with zero-difference criterion", "prevention", "planned", True)],
         "Two independent comparisons; residual assumes both closed-verified before go-live."),
        ("AIM-04", "NOTAM not delivered to all addressees after AMHS reconfiguration", "hazop", "HP-08", ("B", 3), ("B", 2),
         [("End-to-end interface tests with each addressee", "prevention", "planned", False)], "Interface tests before cut-over."),
        ("AIM-05", "Auto-filled NOTAM approved without checking against request (STPA UCA-1)", "stpa", "UCA-1", ("B", 3), ("B", 2),
         [("Highlight auto-filled fields; verification procedure against source", "prevention", "planned", False)], "HTA step 3.1 and HMI change."),
        ("AIM-06", "Shadow operation shortened by schedule pressure", "swift", "W-07", ("B", 3), ("B", 1),
         [("Minimum shadow period and exit criteria fixed in the safety case", "prevention", "planned", True)], "Go/no-go signed by Safety."),
        ("AIM-07", "Critical-data difference found in shadow operation (M1 criterion not met)", "sim", "M1", ("B", 3), ("B", 2),
         [("Root-cause each difference before go-live; repeat comparison", "prevention", "planned", True)], "One difference on day 4 of shadow operation; criterion is zero."),
    ]
    H = {}
    for ref, title, key, row, (is_, il), (rs, rl), controls, rat in items:
        h = Hazard(ref=ref, title=title, unit="AIS / NOTAM office", system="AIM", owner="AIM manager", assessment_id=a.id,
                   source_study_id=ids[key], source_row=row, initial_severity=is_, initial_likelihood=il,
                   residual_severity=rs, residual_likelihood=rl, rationale=rat, review_date=review)
        db.add(h); db.flush(); H[ref] = h
        for text, side, ver, crit in controls:
            db.add(Control(hazard_id=h.id, text=text, side=side, verification=ver, critical=crit, kind="procedure"))
    for i, (text, owner, ref) in enumerate([
        ("Add originator proof-check and automated second-source comparison for critical data", "AIM manager", "AIM-01"),
        ("Produce and sign the 100% critical-data comparison report (legacy vs new)", "AIM data manager", "AIM-03"),
        ("Test rollback to legacy within the agreed time; record result", "Project manager", "AIM-02"),
        ("Send test messages to every AMHS addressee from the new system", "Network engineer", "AIM-04"),
        ("Change HMI to highlight auto-filled NOTAM fields; update verification procedure", "AIM vendor", "AIM-05"),
        ("Root-cause the day-4 critical-data difference and repeat the comparison", "AIM data manager", "AIM-07")], 1):
        db.add(Action(ref=f"AIM-A{i:02d}", text=text, owner=owner, due_date=date.today() + timedelta(days=30 + 10 * i),
                      hazard_id=H[ref].id, assessment_id=a.id, status="open"))


TEMPLATES = {
    "aim_acquisition": {
        "key": "aim_acquisition", "name": "New AIM system acquisition (installation → transition)", "change_type": "system",
        "manual": "Appendix C",
        "summary": "FHA of AIM functions, data-flow HAZOP (7 nodes incl. migration), FMEA, FTA of undetected erroneous critical data, CCA, "
                   "STPA, HTA + HRA, security, JHA and SWIFT of installation and cut-over, transition bowtie, shadow-operation plan and GSN skeleton.",
        "title": "Safety assessment — new AIM system acquisition", "scope": AIM_SCOPE, "environment": AIM_ENV, "assumptions": AIM_ASSUMPTIONS,
        "studies": [{"key": k, "method": m, "title": t} for k, m, t in STUDIES],
        "build": build_aim,
    },
}


from .template_org import TEMPLATE as _ORG  # noqa: E402

TEMPLATES["org_change"] = _ORG


def catalogue():
    return [{k: v for k, v in t.items() if k != "build"} for t in TEMPLATES.values()]


def seed_demo_v4(db: Session):
    """DEMO-04: the AIM acquisition template applied and completed with illustrative ratings and results."""
    from .models import Project
    if db.query(Project).filter_by(code="DEMO-04").first():
        return
    t = TEMPLATES["aim_acquisition"]
    p = Project(code="DEMO-04", title="New AIM system acquisition — installation to transition (template example)", change_type="system",
                units="AIS / NOTAM office; AIM data management; CNS/IT engineering", sponsor="Directorate of Operations",
                description="Created from the ARAP assessment template 'New AIM system acquisition' (Manual Appendix C) and completed "
                            "with illustrative ratings, calculations, hazards and actions. All numbers are illustrative.")
    db.add(p); db.flush()
    a = Assessment(project_id=p.id, title=t["title"], created_by="assessor", scope=t["scope"], environment=t["environment"], assumptions=t["assumptions"])
    db.add(a); db.flush()
    build_aim(db, a, filled=True)
    db.commit()
