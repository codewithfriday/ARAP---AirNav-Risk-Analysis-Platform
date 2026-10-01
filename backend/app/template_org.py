"""Assessment template "Major organisational change" (Manual Appendix D; SRS TPL-06).

Reference scenario (illustrative, used for the proposed content and for demo project DEMO-05): restructuring of the
operations of a branch — Approach (APP) and Tower (TWR) merged into one Terminal Unit; watch supervision and training
coordination combined in "Operations Supervisor" posts; the branch Safety & Quality function and ATCO competence
assessment moved to regional units; CNS maintenance planning centralised. Edit the function map and structures for the
actual change.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from .engines import sej as sej_engine
from .models import Action, Assessment, Control, Hazard, Study

SCOPE = (
    "Major change in organisation structure affecting safety-related functions: merger of the APP and TWR units of Branch X into a "
    "Terminal Unit; combination of watch supervision and on-the-job-training (OJT) coordination into Operations Supervisor posts; "
    "transfer of the branch Safety & Quality (S&Q) function and of ATCO competence assessment to regional units; centralisation of "
    "CNS maintenance planning. In scope: every safety-related function, post, reporting line, delegation and barrier owner affected, "
    "from planning through execution to 12 months after implementation. Out of scope: changes to airspace, procedures or equipment "
    "(assessed separately if they follow).")
ENV = (
    "Phases: (1) planning and design of the new structure; (2) consultation and appointments; (3) execution in phases with go/no-go per "
    "phase; (4) post-implementation monitoring at 3, 6 and 12 months. Branch X: TWR + APP, H24, about 95,000 movements a year; "
    "46 ATCOs; peak season July–August. Regulatory basis: management of change in the SMS (ICAO Annex 19, Doc 9859; CASR Part 19).")
ASSUMPTIONS = (
    "A-1 Head-count in the new structure is as in the HR design; no net reduction of ATCO operational posts. "
    "A-2 DGCA delegation for competence assessment can be transferred to the regional training unit before phase 3. "
    "A-3 Staff keep their licences, ratings and unit endorsements through the change. "
    "A-4 A baseline safety culture survey is carried out before the change is announced.")

HAZID_GUIDEWORDS = ["Roles and responsibilities", "Authority and delegation", "Competence", "Workload and staffing", "Interfaces",
                    "Communication and reporting", "Corporate memory", "Contractors and outsourcing", "Culture and morale", "Transition"]

# function, category, current owner, new owner, competence, capacity, authority, handover, action  (last 4 + action only in demo)
FUNCTIONS = [
    ("Accept residual risk in the Tolerable (lower) region for branch changes", "SMS", "Director of Operations", "Regional Operations Director", "confirmed", "adequate", "pending", "planned", "Written delegation from the Accountable Executive before phase 3"),
    ("Own and review branch hazard-log entries", "SMS", "Branch Safety Officer", "Regional S&Q Unit", "confirmed", "stretched", "in place", "planned", "Hazard-by-hazard handover list; review dates re-assigned"),
    ("Triage occurrence reports (ERC) within 72 h", "SMS", "Branch Safety Officer", "Regional S&Q Unit", "confirmed", "overloaded", "in place", "planned", "Regional workload ×3; two additional analyst posts or keep branch triage"),
    ("Investigate branch occurrences", "SMS", "Branch Safety Officer (trained investigator)", "Regional S&Q Unit", "gap", "stretched", "in place", "planned", "Only one trained investigator in the regional unit; SOAM/HFACS course"),
    ("Safety Manager reports directly to the Accountable Executive", "SMS", "Safety Manager → Accountable Executive", "Regional S&Q Unit → Regional Operations Director", "confirmed", "adequate", "none", "not planned", "Restore direct line to the Accountable Executive (independence of the safety function)"),
    ("Facilitate safety assessments of branch changes", "SMS", "Branch Safety Officer", "Regional S&Q Unit", "confirmed", "stretched", "in place", "planned", "Prioritise; train two facilitators in the Terminal Unit"),
    ("Supervise the APP watch", "Operations", "APP Watch Supervisor", "Operations Supervisor (TWR + APP)", "confirmed", "stretched", "in place", "done", "Deputy supervisor at peak hours (HTA)"),
    ("Supervise the TWR watch", "Operations", "TWR Watch Supervisor", "Operations Supervisor (TWR + APP)", "confirmed", "stretched", "in place", "done", "As above"),
    ("Coordinate OJT and allocate OJTIs", "Training and competence", "Training Coordinator", "Operations Supervisor (TWR + APP)", "confirmed", "overloaded", "in place", "planned", "Keep a dedicated OJT coordinator during the first 12 months"),
    ("Assess ATCO competence and endorse unit ratings", "Training and competence", "Branch Chief Instructor", "Regional Training Unit", "confirmed", "adequate", "pending", "planned", "DGCA delegation to be transferred (assumption A-2)"),
    ("Roster ATCOs and apply fatigue limits", "Operations", "APP and TWR unit chiefs", "Terminal Unit Manager", "confirmed", "adequate", "in place", "not planned", "Handover of roster rules and fatigue records"),
    ("Maintain letters of agreement with ACC, adjacent APPs and aerodrome operator", "Operations", "APP Unit Chief", "", "unknown", "unknown", "none", "not planned", "Assign to the Terminal Unit Manager; list of LoAs and review dates"),
    ("Own the ATS contingency plan", "Operations", "APP and TWR unit chiefs", "Terminal Unit Manager", "confirmed", "adequate", "in place", "planned", ""),
    ("Plan CNS preventive maintenance", "Technical", "Branch Technical Manager", "Regional Technical Planning", "confirmed", "adequate", "in place", "planned", ""),
    ("Hand equipment back to ATS after maintenance", "Technical", "Technician on duty", "Technician on duty", "confirmed", "adequate", "in place", "done", "Unchanged"),
    ("Barrier owner: stop bars operated H24 (runway incursion bowtie)", "Barrier owner", "TWR Unit Chief", "Terminal Unit Manager", "confirmed", "adequate", "in place", "planned", "Update bowtie barrier register"),
    ("Barrier owner: A-SMGCS / runway strip display configuration", "Barrier owner", "TWR Unit Chief", "", "unknown", "unknown", "none", "not planned", "Assign owner; update bowtie barrier register"),
    ("Barrier owner: STCA parameters (level-bust bowtie)", "Barrier owner", "ACC Unit Chief + CNS", "ACC Unit Chief + CNS", "confirmed", "adequate", "in place", "done", "Unchanged"),
]

FHA = [
    ("Triage occurrence reports", "Delayed", "Occurrence reports triaged later than 72 h", "Serious occurrences investigated late; repeat events", "C", "Triage capacity sized to regional volume; SPI S-04"),
    ("Investigate branch occurrences", "Partial loss / degradation", "Investigations shallow or late (competence and capacity gap)", "Causes not found; barriers not repaired", "C", "Trained investigators before transfer; SPI S-08"),
    ("Safety Manager independent line", "Erroneous (undetected)", "Safety function reports through the operations line it oversees", "Safety concerns filtered; risk accepted without independent challenge", "B", "Direct reporting line of the Safety Manager to the Accountable Executive"),
    ("Supervise the watch", "Partial loss / degradation", "Combined supervisor overloaded at peak (sector split, OJT, events together)", "Late sector split; overload not detected; loss of separation", "B", "Deputy supervisor at peaks; supervisor task priorities (HTA plan 0)"),
    ("Coordinate OJT", "Partial loss / degradation", "OJT supervised less closely", "Trainee error not caught in time", "C", "Dedicated OJT coordinator for 12 months"),
    ("Maintain letters of agreement", "Total loss", "No owner: LoAs not reviewed after changes", "Coordination procedures out of date", "C", "Named owner and LoA review schedule"),
    ("Roster and fatigue limits", "Partial loss / degradation", "Roster rules and fatigue records not handed over", "Fatigue-related error", "B", "Formal handover of roster rules; fatigue model check of first rosters"),
    ("Accept residual risk", "Erroneous (undetected)", "Risk accepted by a post without written delegation", "Invalid acceptance; unmanaged risk", "C", "Written delegations before go-live"),
    ("Barrier ownership", "Total loss", "Barrier without owner degrades unnoticed", "Weakened defence against runway incursion", "B", "Every barrier in the bowtie library re-assigned"),
]


def _struct(new: bool):
    if not new:
        nodes = [
            {"id": "AE", "label": "Accountable Executive", "kind": "controller", "x": 250, "y": 0, "process_model": "Safety performance; risk acceptance"},
            {"id": "SM", "label": "Safety Manager (Dir. S&Q)", "kind": "controller", "x": 520, "y": 120, "process_model": "Hazard log; occurrence trends"},
            {"id": "DO", "label": "Director of Operations", "kind": "controller", "x": 0, "y": 120, "process_model": "Operational performance"},
            {"id": "GM", "label": "Branch GM", "kind": "controller", "x": 0, "y": 260, "process_model": "Branch resources"},
            {"id": "BSO", "label": "Branch Safety Officer", "kind": "controller", "x": 520, "y": 260, "process_model": "Branch occurrences; hazards"},
            {"id": "APP", "label": "APP Unit Chief + supervisor", "kind": "controller", "x": 0, "y": 400, "process_model": "APP watch; LoAs"},
            {"id": "TWR", "label": "TWR Unit Chief + supervisor", "kind": "controller", "x": 260, "y": 400, "process_model": "TWR watch; barriers"},
            {"id": "TC", "label": "Training Coordinator", "kind": "controller", "x": 520, "y": 400, "process_model": "OJT status"},
            {"id": "ATCO", "label": "ATCOs (TWR, APP)", "kind": "process", "x": 260, "y": 540}]
        edges = [("AE", "DO", "control", "objectives, resources"), ("AE", "SM", "control", "safety policy"), ("SM", "AE", "feedback", "safety reports, SPIs"),
                 ("DO", "GM", "control", "directives"), ("GM", "APP", "control", "resources"), ("GM", "TWR", "control", "resources"),
                 ("SM", "BSO", "control", "SMS procedures"), ("BSO", "SM", "feedback", "occurrences, hazards"),
                 ("APP", "ATCO", "control", "supervision, roster"), ("TWR", "ATCO", "control", "supervision, roster"), ("TC", "ATCO", "control", "OJT"),
                 ("ATCO", "BSO", "feedback", "occurrence reports"), ("ATCO", "APP", "feedback", "workload, events")]
    else:
        nodes = [
            {"id": "AE", "label": "Accountable Executive", "kind": "controller", "x": 250, "y": 0, "process_model": "Safety performance; risk acceptance"},
            {"id": "ROD", "label": "Regional Operations Director", "kind": "controller", "x": 0, "y": 120, "process_model": "Regional operations; accepts Tolerable (lower) risk"},
            {"id": "RSQ", "label": "Regional S&Q Unit", "kind": "controller", "x": 520, "y": 260, "process_model": "Hazard log; occurrences of 6 branches"},
            {"id": "RTU", "label": "Regional Training Unit", "kind": "controller", "x": 520, "y": 400, "process_model": "Competence assessment"},
            {"id": "GM", "label": "Branch GM", "kind": "controller", "x": 0, "y": 260, "process_model": "Branch resources"},
            {"id": "TUM", "label": "Terminal Unit Manager", "kind": "controller", "x": 0, "y": 400, "process_model": "TWR + APP; rosters; LoAs?"},
            {"id": "OS", "label": "Operations Supervisor (TWR + APP + OJT)", "kind": "controller", "x": 260, "y": 400, "process_model": "Both watches; trainees"},
            {"id": "ATCO", "label": "ATCOs (Terminal Unit)", "kind": "process", "x": 260, "y": 540}]
        edges = [("AE", "ROD", "control", "objectives, resources"), ("ROD", "RSQ", "control", "priorities (S&Q under operations)"), ("RSQ", "ROD", "feedback", "safety reports"),
                 ("ROD", "AE", "feedback", "operations + safety report"), ("ROD", "GM", "control", "directives"), ("GM", "TUM", "control", "resources"),
                 ("TUM", "OS", "control", "watch plan"), ("OS", "ATCO", "control", "supervision, OJT"), ("RTU", "ATCO", "control", "assessment"),
                 ("ATCO", "RSQ", "feedback", "occurrence reports"), ("ATCO", "OS", "feedback", "workload, events"), ("OS", "TUM", "feedback", "watch reports")]
    return {"nodes": nodes, "edges": [{"id": f"e{i}", "source": a, "target": b, "kind": k, "label": l} for i, (a, b, k, l) in enumerate(edges, 1)]}


LOSSES = [{"id": "L-1", "text": "Aircraft accident or serious incident in Branch X airspace or on the aerodrome"},
          {"id": "L-2", "text": "Loss of the ability of the SMS to detect and correct safety problems"}]
HAZ = [{"id": "H-1", "text": "Safety-related function not performed, or performed without competence, capacity or authority", "losses": ["L-1", "L-2"]},
       {"id": "H-2", "text": "Safety information does not reach, or is filtered before, the level that must act on it", "losses": ["L-2", "L-1"]}]
CONS = [{"id": "SC-1", "text": "Every safety-related function must have a named, competent, authorised owner with capacity", "hazards": ["H-1"]},
        {"id": "SC-2", "text": "The safety function must report to the Accountable Executive independently of the operations line", "hazards": ["H-2"]}]
UCAS = [
    {"id": "UCA-1", "control_action": "priorities (S&Q under operations)", "type": "Providing causes hazard", "text": "Regional Operations Director deprioritises an investigation in own area", "context": "when operational targets conflict with safety findings", "hazards": ["H-2"]},
    {"id": "UCA-2", "control_action": "operations + safety report", "type": "Not providing causes hazard", "text": "Safety concerns not reported to the Accountable Executive", "context": "when the safety report is merged into the operations report", "hazards": ["H-2"]},
    {"id": "UCA-3", "control_action": "supervision, OJT", "type": "Too early / too late / wrong order", "text": "Operations Supervisor splits sectors too late", "context": "when handling OJT and an abnormal event at the same time at peak", "hazards": ["H-1"]},
    {"id": "UCA-4", "control_action": "supervision, OJT", "type": "Not providing causes hazard", "text": "Trainee on position without close OJTI monitoring", "context": "when the supervisor is also the OJT coordinator and is busy", "hazards": ["H-1"]},
    {"id": "UCA-5", "control_action": "watch plan", "type": "Not providing causes hazard", "text": "LoA changes not made after an adjacent unit changes its procedure", "context": "when no post owns the LoAs", "hazards": ["H-1"]},
]
SCEN = [
    {"id": "S-1", "uca": "UCA-1", "type": "Inadequate control algorithm", "text": "No rule protecting safety investigations from operational priorities", "requirement": "S&Q reports directly to the Accountable Executive; investigation priorities set by S&Q"},
    {"id": "S-2", "uca": "UCA-3", "type": "Flawed process model", "text": "Supervisor's picture of both watches degraded while managing OJT", "requirement": "Deputy supervisor at peak; sector-split triggers in the watch plan"},
    {"id": "S-3", "uca": "UCA-5", "type": "Missing controller", "text": "Function dropped in the merger (orphan)", "requirement": "Function map: every function has a named owner before go-live"},
]

HAZID_ROWS = [
    ("Roles and responsibilities", "LoA maintenance and A-SMGCS barrier have no owner in the new structure", "Functions not listed in the new job descriptions", "Out-of-date coordination; degraded barrier", "Function map", "C", 3, "Assign owners; update job descriptions and bowtie register", "Terminal Unit Manager"),
    ("Authority and delegation", "Risk accepted or ratings endorsed by posts without written delegation", "Delegations not transferred at go-live", "Invalid decisions; regulatory finding", "Delegation register", "C", 3, "Delegations signed before each phase go-live", "Accountable Executive"),
    ("Competence", "Regional S&Q lacks trained investigators for the added volume", "One trained investigator in the region", "Shallow investigations", "Investigation procedure", "C", 3, "SOAM/HFACS training for two analysts before transfer", "Regional S&Q"),
    ("Workload and staffing", "Operations Supervisor overloaded at peak (two watches + OJT)", "Merged role without deputy", "Late sector split; missed overload", "Supervisor procedures", "B", 3, "Deputy at peaks; HTA-based task priorities", "Terminal Unit Manager"),
    ("Workload and staffing", "Occurrence triage backlog at regional level", "Volume ×3, same staff", "Serious events triaged late", "None", "C", 4, "Two analyst posts or keep branch triage for 6 months", "Regional S&Q"),
    ("Interfaces", "Aerodrome operator and ACC do not know new contact points", "Communication plan omits external partners", "Coordination delays in events", "None", "C", 3, "Contact list and LoA annex updated before go-live", "Terminal Unit Manager"),
    ("Communication and reporting", "Safety function reports through operations line", "S&Q placed under Regional Operations Director", "Safety concerns filtered", "None", "B", 3, "Direct line to the Accountable Executive", "Accountable Executive"),
    ("Corporate memory", "Experienced unit chiefs leave or retire during the change", "Uncertainty; early retirement offers", "Loss of local knowledge of hazards and LoAs", "None", "C", 3, "Retention agreements; documented handover files", "HR"),
    ("Culture and morale", "Reporting drops during the change", "Uncertainty; fear of blame in new structure", "Hazards not reported", "Just culture policy", "C", 3, "Communication plan; visible leadership; monitor reporting rate", "Safety Manager"),
    ("Transition", "Parallel reporting lines during the phased change", "Old and new posts both active", "Instructions conflict; responsibilities unclear", "None", "C", 3, "Transition responsibility chart per phase; single point of contact", "Branch GM"),
]

HTA = {"tasks": [
    {"id": "0", "parent": None, "title": "Manage the terminal watch (Operations Supervisor, merged role)", "plan": "Do 1 at start of watch; 2 continuously; 3 as scheduled; 4 when an event occurs (4 has priority over 3 and 5); 5 when time allows"},
    {"id": "1", "parent": "0", "title": "Prepare the watch", "plan": "1.1 then 1.2 then 1.3"},
    {"id": "1.1", "parent": "1", "title": "Check staffing and fatigue status of both watches", "error_modes": ["Check omitted"]},
    {"id": "1.2", "parent": "1", "title": "Review NOTAM, equipment status and expected traffic", "error_modes": ["Information not obtained"]},
    {"id": "1.3", "parent": "1", "title": "Brief TWR and APP teams"},
    {"id": "2", "parent": "0", "title": "Monitor traffic and configure sectors", "plan": "2.1 continuously; 2.2 when load reaches the split trigger"},
    {"id": "2.1", "parent": "2", "title": "Monitor load on TWR and APP positions", "error_modes": ["Information not obtained"]},
    {"id": "2.2", "parent": "2", "title": "Split or combine sectors / open positions", "error_modes": ["Action too early / late"]},
    {"id": "3", "parent": "0", "title": "Manage on-the-job training", "plan": "3.1 before each session; 3.2 during"},
    {"id": "3.1", "parent": "3", "title": "Allocate OJTI and trainee to position", "error_modes": ["Wrong action"]},
    {"id": "3.2", "parent": "3", "title": "Monitor trainee sessions", "error_modes": ["Check omitted"]},
    {"id": "4", "parent": "0", "title": "Handle abnormal events", "plan": "4.1 then 4.2; 4.3 after the event"},
    {"id": "4.1", "parent": "4", "title": "Coordinate with aerodrome, ACC and technical staff", "error_modes": ["Information not communicated"]},
    {"id": "4.2", "parent": "4", "title": "Apply contingency / degraded-mode procedures", "error_modes": ["Action omitted"]},
    {"id": "4.3", "parent": "4", "title": "Report the occurrence", "error_modes": ["Action omitted"]},
    {"id": "5", "parent": "0", "title": "Administration (roster changes, reports)", "plan": "Only when 2–4 are under control"},
]}

SWIFT = [
    ("People", "What if key staff (unit chiefs, the trained investigator) leave before handover?", "Loss of knowledge; functions uncovered", "Notice periods", "C", 3, "Retention agreements; handover files signed off before release", "HR"),
    ("Procedures", "What if delegations are not signed at the go-live date of a phase?", "Decisions taken without authority", "Delegation register", "C", 3, "Go/no-go criterion: all delegations signed", "Transition board"),
    ("Information and communication", "What if open hazard-log actions and investigation files are not transferred?", "Actions lost; overdue reviews", "None", "C", 3, "Transfer list with acknowledgement per item", "Branch Safety Officer"),
    ("Management and organisation", "What if old and new reporting lines run in parallel for weeks?", "Conflicting instructions", "None", "C", 3, "Responsibility chart per phase; single point of contact", "Branch GM"),
    ("Timing and sequence", "What if the merger phase falls in the July–August peak?", "Merged supervisor overloaded at peak", "Project plan", "B", 3, "No operational phase change between June and September", "Transition board"),
    ("People", "What if the announcement causes a rise in sick leave and a drop in reporting?", "Staffing gaps; hazards unreported", "Just culture policy", "C", 3, "Communication plan; staff support; monitor SPIs S-05, S-07", "Safety Manager"),
    ("Equipment and utilities", "What if new posts lack system access (hazard log, rostering, reporting tool) on day one?", "Functions not performed", "IT request process", "D", 3, "Access rights prepared and tested before go-live", "IT"),
    ("External events", "What if a serious incident occurs during the transition week?", "Unclear investigation ownership", "None", "C", 2, "Interim rule: previous owner investigates until handover date", "Safety Manager"),
]

SPIS = [  # indicator, type, linked, baseline, target, alert, frequency, owner, escalation, demo current, demo status
    ("Vacant or acting posts among safety-critical functions", "leading", "Function map", "0", "0", "≥ 2", "monthly", "HR", "Transition board; delay next phase", "1", "amber"),
    ("Function-map rows with gaps (owner, competence, capacity, authority, handover)", "leading", "Function map", "18 to assess", "0 at go-live", "≥ 1 at go-live", "weekly", "Transition board", "No go-live for the phase", "13", "red"),
    ("Overdue hazard-log actions and reviews (%)", "leading", "SMS hazard log", "6%", "≤ 5%", "> 15%", "monthly", "Regional S&Q", "Report to Accountable Executive", "9%", "amber"),
    ("Occurrence reports triaged within 72 h (%)", "leading", "FHA triage", "97%", "≥ 95%", "< 85%", "monthly", "Regional S&Q", "Restore branch triage", "88%", "amber"),
    ("Voluntary safety reports per month vs baseline", "leading", "Reporting culture", "24 / month", "≥ baseline", "drop > 30%", "monthly", "Safety Manager", "Staff engagement; review communication", "19", "amber"),
    ("Trainees waiting for OJTI allocation", "leading", "OJT coordination", "2", "≤ 3", "rising 2 months", "monthly", "Terminal Unit Manager", "Dedicated OJT coordinator", "3", "green"),
    ("Overtime hours per ATCO per month", "leading", "Fatigue / roster", "8 h", "≤ 10 h", "> 12 h", "monthly", "Terminal Unit Manager", "Roster review; fatigue model", "11 h", "amber"),
    ("Median time to close an investigation (days)", "lagging", "Investigation", "28", "≤ 30", "> 60", "quarterly", "Regional S&Q", "Add investigators", "41", "amber"),
    ("Safety culture survey index (0–100)", "leading", "Culture", "68", "≥ 68", "drop ≥ 5 points", "6-monthly", "Safety Manager", "Culture action plan", "—", ""),
    ("Occurrences with organisational factors coded (HFACS organisational influences)", "lagging", "Investigations", "2 / quarter", "≤ baseline", "rising 2 quarters", "quarterly", "Regional S&Q", "Review of the new structure", "3", "amber"),
]

DELPHI_Q = "Probability that a serious-occurrence report is not triaged within 72 h in the first 6 months after transfer to the regional unit"
DELPHI = [{"round": 1, "estimates": {"P1": 0.05, "P2": 0.25, "P3": 0.10, "P4": 0.15, "P5": 0.02, "P6": 0.20}},
          {"round": 2, "estimates": {"P1": 0.08, "P2": 0.18, "P3": 0.12, "P4": 0.12, "P5": 0.06, "P6": 0.15}},
          {"round": 3, "estimates": {"P1": 0.10, "P2": 0.15, "P3": 0.12, "P4": 0.12, "P5": 0.08, "P6": 0.12}}]


def _bowtie():
    B = {}
    def b(bid, text, kind, owner, spi="", critical=False):
        B[bid] = {"id": bid, "text": text, "kind": kind, "effectiveness": "unknown", "owner": owner, "critical": critical, "verification": "planned", "spi": spi}
    b("PB1", "Function map: named owner for every safety function, signed off", "organisational", "Transition board", "S-02 rows with gaps", True)
    b("PB2", "Competence verified and delegations signed before each phase", "organisational", "Accountable Executive", "S-01 vacant/acting posts", True)
    b("PB3", "Workload assessment of new posts (HTA); deputies at peaks", "organisational", "Terminal Unit Manager", "S-07 overtime", True)
    b("PB4", "Retention and knowledge-transfer plan; overlap period", "organisational", "HR")
    b("PB5", "Control and feedback loops checked (STPA); S&Q independent", "organisational", "Accountable Executive", "", True)
    b("PB6", "Consultation, communication plan and staff support", "organisational", "Safety Manager", "S-05 voluntary reports")
    b("PB7", "Phased implementation with go/no-go per phase", "organisational", "Transition board", "", True)
    b("RB1", "Transition safety board reviews SPIs weekly", "organisational", "Safety Manager", "all SPIs", True)
    b("RB2", "Escalation route to the Safety Manager and Accountable Executive", "procedure", "Safety Manager")
    b("RB3", "Reversion: function returned to its previous owner (interim)", "organisational", "Transition board", "", True)
    b("RB4", "Independent safety audit at 3 months", "organisational", "Regional S&Q")
    b("RB5", "Investigation of occurrences with organisational-factor coding", "procedure", "Regional S&Q", "S-10")
    return {"hazard": "Reorganisation of safety-related functions (planning, execution, post-implementation)",
            "top_event": "Safety-related function not performed, or performed without competence, capacity or authority",
            "threats": [{"id": "T1", "text": "Function left without an owner (orphan)", "barriers": ["PB1", "PB7"]},
                        {"id": "T2", "text": "New owner lacks competence or authority", "barriers": ["PB2", "PB7"]},
                        {"id": "T3", "text": "New owner overloaded (merged posts)", "barriers": ["PB3"]},
                        {"id": "T4", "text": "Key staff leave; corporate memory lost", "barriers": ["PB4"]},
                        {"id": "T5", "text": "Reporting and feedback lines broken or filtered", "barriers": ["PB5"]},
                        {"id": "T6", "text": "Uncertainty and stress reduce performance and reporting", "barriers": ["PB6"]}],
            "consequences": [{"id": "C1", "text": "Hazard not identified or not controlled (latent)", "severity": "B", "barriers": ["RB1", "RB4"]},
                             {"id": "C2", "text": "Occurrence not reported or investigated; repeat event", "severity": "C", "barriers": ["RB5", "RB2"]},
                             {"id": "C3", "text": "Degraded operational supervision; loss of separation", "severity": "B", "barriers": ["RB1", "RB3"]}],
            "barriers": B,
            "escalation": [{"id": "EF1", "text": "Phase change coincides with peak season", "barrier": "PB3", "ef_barriers": ["No operational phase change June–September"]},
                           {"id": "EF2", "text": "Budget pressure to reduce posts", "barrier": "PB3", "ef_barriers": ["Minimum staffing fixed in the safety case"]}]}


def _gsn(ids):
    def sol(sid, parent, text, key):
        return {"id": sid, "type": "solution", "parent": parent, "text": text, "evidence": {"kind": "study", "ref": ids.get(key)}}
    return {"nodes": [
        {"id": "G0", "type": "goal", "text": "The new organisation delivers all safety-related functions at least as safely as the current organisation, including during the transition"},
        {"id": "C1", "type": "context", "parent": "G0", "text": "Description of the change and phases (assessment scope)"},
        {"id": "C2", "type": "context", "parent": "G0", "text": "AirNav risk classification scheme; SMS roles (Doc 9859)"},
        {"id": "A1", "type": "assumption", "parent": "G0", "text": "Head-count as in the HR design; no net reduction of operational ATCO posts"},
        {"id": "S0", "type": "strategy", "parent": "G0", "text": "Argue over functions, control loops, hazards, people and workload, transition and monitoring"},
        {"id": "G1", "type": "goal", "parent": "S0", "text": "Every safety-related function has a named, competent, authorised owner with capacity"},
        sol("Sn1", "G1", "Organisational function map", "orgmap"), sol("Sn2", "G1", "FHA of organisational functions", "fha"),
        {"id": "G2", "type": "goal", "parent": "S0", "text": "Control and feedback loops are at least as effective; the safety function stays independent"},
        sol("Sn3", "G2", "STPA — current structure", "stpa_old"), sol("Sn4", "G2", "STPA — new structure", "stpa_new"),
        {"id": "G3", "type": "goal", "parent": "S0", "text": "Organisational hazards are identified, rated and controlled"},
        sol("Sn5", "G3", "HAZID with organisational guidewords", "hazid"), sol("Sn6", "G3", "Delphi estimate of triage risk", "sej"),
        {"id": "G4", "type": "goal", "parent": "S0", "text": "Merged posts are workable at peak"},
        sol("Sn7", "G4", "HTA of the Operations Supervisor role", "hta"),
        {"id": "G5", "type": "goal", "parent": "S0", "text": "The transition is controlled phase by phase, with reversion possible"},
        sol("Sn8", "G5", "SWIFT of the transition plan", "swift"), sol("Sn9", "G5", "Transition bowtie", "bowtie"),
        {"id": "G6", "type": "goal", "parent": "S0", "text": "Post-implementation monitoring with alert levels and reversal criteria is in place"},
        sol("Sn10", "G6", "SPI register", "spi"),
        {"id": "G7", "type": "goal", "parent": "S0", "undeveloped": True, "text": "Safety culture is maintained (survey at 6 and 12 months no worse than baseline)"},
    ]}


STUDIES = [
    ("orgmap", "orgmap", "Organisational function map — current to new owner"),
    ("fha", "fha", "FHA — organisational functions and failure conditions"),
    ("stpa_old", "stpa", "STPA — current control structure"),
    ("stpa_new", "stpa", "STPA — new control structure"),
    ("hazid", "hazid", "HAZID — organisational guidewords"),
    ("hta", "hta", "HTA — Operations Supervisor (merged role)"),
    ("sej", "sej", "Delphi — likelihood of triage failure after transfer"),
    ("swift", "swift", "SWIFT — transition plan"),
    ("bowtie", "bowtie", "Transition bowtie — safety function not performed"),
    ("spi", "spi", "SPI register — post-implementation monitoring"),
    ("gsn", "gsn", "Safety argument — major organisational change"),
]


def build_org(db: Session, a: Assessment, filled: bool = False, participants=None) -> dict:
    ids: dict[str, int] = {}
    parts = participants or [{"name": "Safety assessor", "role": "Facilitator"}, {"name": "Operations management", "role": "SME"},
                             {"name": "ATCO representatives", "role": "SME"}, {"name": "HR", "role": "SME"}]
    fmap = []
    for i, (fn, cat, old, new, comp, cap, auth, hand, act) in enumerate(FUNCTIONS, 1):
        row = {"id": f"FN-{i:02d}", "function": fn, "category": cat, "old_owner": old, "new_owner": new}
        row.update({"competence": comp, "capacity": cap, "authority": auth, "handover": hand, "action": act} if filled else
                   {"competence": "unknown", "capacity": "unknown", "authority": "unknown", "handover": "unknown", "action": ""})
        fmap.append(row)
    hz = []
    for i, (gw, h, c, cons, ctl, sev, lik, act, own) in enumerate(HAZID_ROWS, 1):
        row = {"id": f"HZ-{i:02d}", "guideword": gw, "hazard": h, "causes": c, "consequences": cons, "controls": ctl, "severity": sev, "actions": act, "owner": own}
        if filled:
            row["likelihood"] = lik
        hz.append(row)
    sw = []
    for i, (gw, wi, cons, saf, sev, lik, rec, own) in enumerate(SWIFT, 1):
        row = {"id": f"W-{i:02d}", "guideword": gw, "what_if": wi, "consequence": cons, "safeguards": saf, "severity": sev, "recommendation": rec, "owner": own}
        if filled:
            row["likelihood"] = lik
        sw.append(row)
    spis = []
    for i, (ind, typ, link, base, tgt, alert, freq, own, esc, cur, st) in enumerate(SPIS, 1):
        row = {"id": f"S-{i:02d}", "indicator": ind, "type": typ, "linked": link, "baseline": base if filled else "", "target": tgt, "alert": alert,
               "frequency": freq, "owner": own, "escalation": esc}
        if filled:
            row.update(current=cur, status=st)
        spis.append(row)
    sej_model = {"experts": [], "items": [], "alpha": 0,
                 "delphi": {"question": DELPHI_Q, "rounds": DELPHI if filled else [{"round": 1, "estimates": {}}]}}
    models = {
        "orgmap": {"rows": fmap},
        "fha": {"rows": [{"id": f"FC-{i:02d}", "function": f, "failure_type": t, "condition": c, "effect": e, "severity": s, "requirements": r}
                         for i, (f, t, c, e, s, r) in enumerate(FHA, 1)]},
        "stpa_old": {"losses": LOSSES, "hazards": HAZ, "constraints": CONS, "structure": _struct(False), "ucas": [], "scenarios": []},
        "stpa_new": {"losses": LOSSES, "hazards": HAZ, "constraints": CONS, "structure": _struct(True), "ucas": UCAS, "scenarios": SCEN},
        "hazid": {"guidewords": HAZID_GUIDEWORDS, "rows": hz},
        "hta": HTA, "sej": sej_model, "swift": {"rows": sw}, "bowtie": _bowtie(), "spi": {"rows": spis},
    }
    results = {"sej": {"delphi": sej_engine.delphi(DELPHI)}} if filled else {}
    for key, method, title in STUDIES:
        if key == "gsn":
            continue
        s = Study(assessment_id=a.id, method=method, title=title, model=models[key], results=results.get(key, {}), participants=parts)
        db.add(s); db.flush(); ids[key] = s.id
    s = Study(assessment_id=a.id, method="gsn", title=dict((k, t) for k, _m, t in STUDIES)["gsn"], model=_gsn(ids), participants=parts)
    db.add(s); db.flush(); ids["gsn"] = s.id
    if filled:
        _demo_hazards(db, a, ids)
    return ids


def _demo_hazards(db, a, ids):
    review = date.today() + timedelta(days=90)
    items = [
        ("ORG-01", "Safety function reports through the operations line it oversees", "stpa_new", "UCA-1", ("B", 3), ("B", 1), "Direct reporting line of the Safety Manager / Regional S&Q to the Accountable Executive", "Structural fix removes the conflict (STPA S-1)."),
        ("ORG-02", "Letters of agreement and A-SMGCS barrier without an owner (orphan functions)", "orgmap", "FN-12", ("C", 3), ("C", 1), "Owners assigned in the function map; job descriptions and bowtie register updated", "Named owners before go-live."),
        ("ORG-03", "Regional occurrence triage overloaded (volume ×3)", "orgmap", "FN-03", ("C", 4), ("C", 2), "Two analyst posts, or branch triage kept for 6 months; SPI S-04", "Delphi median 0.12 before mitigation."),
        ("ORG-04", "Operations Supervisor overloaded at peak (two watches + OJT)", "hta", "0", ("B", 3), ("B", 2), "Deputy supervisor at peaks; dedicated OJT coordinator for 12 months", "HTA plan shows concurrent demands at peak."),
        ("ORG-05", "Decisions taken without written delegation at phase go-live", "swift", "W-02", ("C", 3), ("C", 1), "Go/no-go criterion: all delegations signed", "Delegation register checked at each go/no-go."),
        ("ORG-06", "Key staff leave before handover; local knowledge lost", "swift", "W-01", ("C", 3), ("C", 2), "Retention agreements; handover files signed off before release", "Residual allows for unplanned departures."),
        ("ORG-07", "Phase change during the peak season", "swift", "W-05", ("B", 3), ("B", 1), "No operational phase change between June and September", "Timing constraint in the transition plan."),
    ]
    H = {}
    for ref, title, key, row, (is_, il), (rs, rl), ctl, rat in items:
        h = Hazard(ref=ref, title=title, unit="Branch X Terminal Unit; Regional S&Q", system="Organisation", owner="Transition board", assessment_id=a.id,
                   source_study_id=ids[key], source_row=row, initial_severity=is_, initial_likelihood=il, residual_severity=rs, residual_likelihood=rl,
                   rationale=rat, review_date=review)
        db.add(h); db.flush(); H[ref] = h
        db.add(Control(hazard_id=h.id, text=ctl, side="prevention", kind="organisational", verification="planned", critical=True))
    for i, (text, owner, ref) in enumerate([
        ("Amend the organisation chart: Regional S&Q reports to the Accountable Executive", "Accountable Executive", "ORG-01"),
        ("Assign owners for LoA maintenance and A-SMGCS configuration; update job descriptions and the bowtie register", "Terminal Unit Manager", "ORG-02"),
        ("Decide: two regional analyst posts or branch triage for 6 months", "Regional Operations Director", "ORG-03"),
        ("Define deputy supervisor cover at peaks and keep the OJT coordinator for 12 months", "Terminal Unit Manager", "ORG-04"),
        ("Complete and sign the delegation register before phase 3", "Accountable Executive", "ORG-05"),
        ("Agree retention and handover files for unit chiefs and the trained investigator", "HR", "ORG-06")], 1):
        db.add(Action(ref=f"ORG-A{i:02d}", text=text, owner=owner, due_date=date.today() + timedelta(days=20 + 10 * i), hazard_id=H[ref].id, assessment_id=a.id, status="open"))


def seed_demo_v5(db: Session):
    from .models import Project
    if db.query(Project).filter_by(code="DEMO-05").first():
        return
    p = Project(code="DEMO-05", title="Major organisational change — Branch X Terminal Unit (template example)", change_type="organisational",
                units="Branch X TWR and APP; Regional S&Q; Regional Training Unit", sponsor="Directorate of Operations",
                description="Created from the NAVRAP assessment template 'Major organisational change' (Manual Appendix D) and completed with "
                            "illustrative assessments, Delphi rounds, SPI values, hazards and actions. All values are illustrative.")
    db.add(p); db.flush()
    a = Assessment(project_id=p.id, title="Safety assessment — major organisational change", created_by="assessor", scope=SCOPE, environment=ENV, assumptions=ASSUMPTIONS)
    db.add(a); db.flush()
    build_org(db, a, filled=True)
    db.commit()


TEMPLATE = {
    "key": "org_change", "name": "Major organisational change (planning → post-implementation)", "change_type": "organisational", "manual": "Appendix D",
    "summary": "Organisational function map (18 functions incl. SMS roles and barrier owners), FHA of organisational functions, STPA of the current and "
               "new control structures, HAZID with organisational guidewords, HTA of a merged post, Delphi, SWIFT of the transition plan, "
               "transition bowtie, SPI register and GSN argument.",
    "title": "Safety assessment — major organisational change", "scope": SCOPE, "environment": ENV, "assumptions": ASSUMPTIONS,
    "studies": [{"key": k, "method": m, "title": t} for k, m, t in STUDIES],
    "build": build_org,
}
