"""Reference models for the thirteen methods added in Manual edition 0.2 (illustrative values)."""
FT = 6076.12  # ft per NM

CRM_VERTICAL = {"pz_sz": 1.0e-8, "py0": 0.5, "lx": 184 / FT, "ly": 175 / FT, "lz": 50 / FT, "sx": 80.0,
                "ez_same": 0.15, "ez_opp": 0.05, "dv": 20.0, "v": 470.0, "ydot": 42.0, "zdot": 1.5}
CRM_LATERAL = {"pz0": 0.52, "lx": 184 / FT, "lz": 50 / FT, "sx": 80.0, "ey_same": 0.10, "ey_opp": 0.0,
               "dv": 20.0, "v": 470.0, "zdot": 1.5, "ydot_sy": 4.0, "tls": 5e-9}
CRM_LAT_MODEL = {"model": "laplace", "scale": 0.9, "lam_y": 175 / FT}

ETA_MODEL = {
    "initiating": {"label": "Conflict following a level bust", "frequency": 0.025, "unit": "per year"},
    "events": [{"id": "B1", "label": "ATCO detects and resolves", "p_success": 0.9},
               {"id": "B2", "label": "STCA alert and ATCO resolution", "p_success": 0.9},
               {"id": "B3", "label": "ACAS II RA followed", "p_success": 0.9}],
    "overrides": {"F": {"B2": {"p_success": 0.8}}},
    "outcomes": {"S": {"label": "Resolved by ATCO — no loss of separation", "severity": "D"},
                 "F-S": {"label": "Loss of separation, resolved after STCA", "severity": "C"},
                 "F-F-S": {"label": "Serious loss of separation, resolved by ACAS", "severity": "B"},
                 "F-F-F": {"label": "Near mid-air collision / collision", "severity": "A"}},
    "terminate_on_success": True,
}

HRA_TASKS = [
    {"id": "T1", "task": "ATCO acts correctly on an STCA alert", "library": "cara", "gtt": "B3",
     "epcs": [{"code": "17", "apoa": 0.2}, {"code": "6", "apoa": 0.1}, {"code": "13", "apoa": 0.1}]},
    {"id": "T2", "task": "ATCO detects a level bust by monitoring the display (no alert)", "library": "cara", "gtt": "B1",
     "epcs": [{"code": "17", "apoa": 0.4}, {"code": "6", "apoa": 0.3}]},
    {"id": "T3", "task": "Technician restores radar to operational configuration after maintenance", "library": "heart", "gtt": "F",
     "epcs": [{"code": "17", "apoa": 0.5}, {"code": "14", "apoa": 0.4}]},
]

ERC_CASES = [
    {"id": "OCC-101", "title": "Level bust FL240→FL232 with crossing traffic; STCA; ATCO resolved; 2.8 NM / 700 ft",
     "outcome": "Catastrophic accident", "barriers": "Limited"},
    {"id": "OCC-102", "title": "Vehicle entered runway strip without clearance; stopped by RIMCAS alert; no aircraft on approach",
     "outcome": "Catastrophic accident", "barriers": "Effective"},
    {"id": "OCC-103", "title": "Frequency congestion delayed a descent clearance; no conflict",
     "outcome": "No accident outcome", "barriers": "Effective"},
]
RAT_CASE = {"separation": "50_75", "closure": "medium", "detection": "late", "planning": "inadequate",
            "execution": "correct", "ground_safety_net": "triggered", "recovery": "correct", "airborne_safety_net": "na"}

RBD_VHF = {"type": "series", "label": "Sector frequency available at CWP", "children": [
    {"type": "parallel", "label": "Radio chains", "children": [
        {"type": "block", "label": "Main Tx/Rx chain", "mtbf": 20000, "mttr": 4},
        {"type": "block", "label": "Standby Tx/Rx chain", "mtbf": 20000, "mttr": 4}]},
    {"type": "parallel", "label": "Links to remote site", "children": [
        {"type": "block", "label": "Leased line", "mtbf": 4000, "mttr": 8},
        {"type": "block", "label": "VSAT backup", "mtbf": 3000, "mttr": 12}]},
    {"type": "block", "label": "VCCS", "mtbf": 50000, "mttr": 2},
    {"type": "parallel", "label": "Power", "children": [
        {"type": "block", "label": "Mains", "mtbf": 2000, "mttr": 2},
        {"type": "block", "label": "UPS", "mtbf": 30000, "mttr": 8}]}]}

LAM, MU, COVERAGE = 1 / 20000, 1 / 4, 0.99
# main/standby radio chains, one repair team, switchover succeeds with probability c (coverage)
MARKOV_STANDBY = {"states": [{"id": "S2", "label": "Main in service, standby ready", "up": True},
                             {"id": "S1", "label": "On standby, main in repair", "up": True},
                             {"id": "S0", "label": "No radio chain in service", "up": False}],
                  "transitions": [{"from": "S2", "to": "S1", "rate": COVERAGE * LAM, "label": "main fails, switchover OK"},
                                  {"from": "S2", "to": "S0", "rate": (1 - COVERAGE) * LAM, "label": "main fails, switchover fails"},
                                  {"from": "S1", "to": "S0", "rate": LAM, "label": "standby fails"},
                                  {"from": "S1", "to": "S2", "rate": MU, "label": "main repaired"},
                                  {"from": "S0", "to": "S1", "rate": MU, "label": "one chain restored"}]}

SEJ_EXPERTS = ["Expert A", "Expert B", "Expert C"]
SEJ_ITEMS = [
    {"id": "S1", "label": "Level busts reported in sector X last year", "seed": True, "realisation": 14, "scale": "uni",
     "answers": {"Expert A": [8, 12, 18], "Expert B": [5, 10, 30], "Expert C": [20, 25, 35]}},
    {"id": "S2", "label": "STCA alerts per 1000 flights (sector X)", "seed": True, "realisation": 2.1, "scale": "uni",
     "answers": {"Expert A": [1.0, 2.0, 3.0], "Expert B": [0.5, 1.5, 5.0], "Expert C": [3.0, 4.0, 6.0]}},
    {"id": "S3", "label": "Median ATCO response time to STCA (s)", "seed": True, "realisation": 9, "scale": "uni",
     "answers": {"Expert A": [6, 9, 14], "Expert B": [4, 8, 20], "Expert C": [12, 15, 20]}},
    {"id": "S4", "label": "Read-back errors per 1000 clearances", "seed": True, "realisation": 3.5, "scale": "uni",
     "answers": {"Expert A": [2, 3.5, 6], "Expert B": [1, 4, 10], "Expert C": [6, 8, 12]}},
    {"id": "Q1", "label": "P(ATCO does not resolve a level-bust conflict before STCA)", "seed": False, "scale": "log",
     "answers": {"Expert A": [0.03, 0.08, 0.2], "Expert B": [0.01, 0.1, 0.4], "Expert C": [0.1, 0.2, 0.4]}},
]
DELPHI_ROUNDS = [{"round": 1, "estimates": {"A": 0.05, "B": 0.2, "C": 0.1, "D": 0.02, "E": 0.3}},
                 {"round": 2, "estimates": {"A": 0.08, "B": 0.12, "C": 0.1, "D": 0.05, "E": 0.15}},
                 {"round": 3, "estimates": {"A": 0.08, "B": 0.1, "C": 0.1, "D": 0.07, "E": 0.12}}]

SIM_MEASURES = [
    {"id": "M1", "label": "Workload (ISA, 1–5), executive ATCO", "unit": "ISA", "better": "lower",
     "criterion": {"type": "threshold", "value": 3.5},
     "baseline": [3.4, 3.8, 3.6, 4.0, 3.5, 3.9, 3.7, 3.6], "solution": [3.0, 3.3, 3.1, 3.4, 2.9, 3.2, 3.3, 3.1]},
    {"id": "M2", "label": "STCA alerts per hour", "unit": "/h", "better": "lower", "criterion": {"type": "no_worse", "value": 0.0},
     "baseline": [1.2, 0.8, 1.5, 1.0, 1.1, 0.9, 1.3, 1.0], "solution": [0.9, 0.7, 1.1, 0.8, 1.0, 0.6, 0.9, 0.8]},
    {"id": "M3", "label": "R/T occupancy", "unit": "%", "better": "lower", "criterion": {"type": "threshold", "value": 60},
     "baseline": [58, 63, 61, 66, 59, 64, 62, 60], "solution": [49, 53, 51, 55, 50, 52, 54, 50]},
]
