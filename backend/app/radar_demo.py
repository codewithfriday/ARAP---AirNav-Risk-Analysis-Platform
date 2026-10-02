"""DEMO-08 — stand-alone worked example: surveillance radar performance degradation (illustrative).

The MSSR Mode S at the (fictitious) Bukit Sari radar site, which feeds ACC Sector E3 (lower airspace) and the approach
unit APP-S, degrades gradually: lower probability of detection in the north-east quadrant, growing azimuth bias, more
false (reflected) targets and Mode C garbling. The example follows the change through six lifecycle phases, one
assessment per phase, and uses every method that is relevant to a phase and to a hazard type. All names, numbers and
events are illustrative.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from .engines import bbn as bbn_engine
from .engines import crm as crm_engine
from .engines import eta as eta_engine
from .engines import fatigue as fat_engine
from .engines import fta as fta_engine
from .engines import hra as hra_engine
from .engines import lopa as lopa_engine
from .engines import orc as orc_engine
from .engines import rbd as rbd_engine
from .engines import sej as sej_engine
from .engines import sim as sim_engine
from .seed2 import CRM_LATERAL, CRM_LAT_MODEL

CODE = "DEMO-08"
SITE = "Bukit Sari MSSR Mode S"
SECTOR = "ACC Sector E3 (FL100–FL245)"

# ------------------------------------------------------------------ phases and hazard types
PHASES = [
    ("P1", "Concept — degraded radar and the refurbishment decision"),
    ("P2", "Design — degraded-mode operation and the refurbished surveillance chain"),
    ("P3", "Implementation and transition — radar refurbishment works and return to service"),
    ("P4", "Operations — living with residual degradation"),
    ("P5", "Occurrence investigation — OCC-RDR-01 loss of separation"),
    ("P6", "Safety performance monitoring and safety argument"),
]
HAZARD_TYPES = {
    "TEC": "Technical (equipment, software)",
    "HUM": "Human performance",
    "PRO": "Procedural / operational",
    "ORG": "Organisational",
    "ENV": "Environmental (RF, structures, weather)",
    "SEC": "Security",
    "OHS": "Occupational (workers)",
}

# key, phase, method, title, hazard types covered
STUDIES = [
    ("hazid", "P1", "hazid", "HAZID — operating Sector E3 with a degrading MSSR (all hazard types)", ["TEC", "HUM", "PRO", "ORG", "ENV", "SEC"]),
    ("fha", "P1", "fha", "FHA — surveillance functions for Sector E3 and their failure conditions", ["TEC", "PRO"]),
    ("bowtie", "P1", "bowtie", "Bowtie — separation provided on degraded surveillance data", ["TEC", "HUM", "PRO", "ORG", "ENV", "SEC"]),
    ("sej", "P1", "sej", "Expert judgement — probability that a track jump goes undetected", ["HUM", "TEC"]),
    ("fmea", "P2", "fmea", "FMEA — radar sensor to controller display chain", ["TEC", "ENV"]),
    ("fta", "P2", "fta", "FTA — undetected erroneous position displayed in Sector E3", ["TEC", "HUM", "ORG"]),
    ("cca", "P2", "cca", "Common cause analysis — radar, ADS-B, STCA and the controller's cross-check", ["TEC", "ENV"]),
    ("rbd", "P2", "rbd", "RBD and Markov — surveillance availability and the cost of late detection", ["TEC", "ORG"]),
    ("stpa", "P2", "stpa", "STPA — declaring and applying degraded surveillance mode", ["HUM", "PRO", "ORG", "TEC"]),
    ("hazop", "P2", "hazop", "HAZOP — radar data flow and the degraded-mode declaration", ["TEC", "PRO"]),
    ("sec", "P2", "sec", "Security risk — radar, ADS-B fallback and remote maintenance", ["SEC"]),
    ("crm", "P2", "crm", "CRM — can parallel routes stay in use without radar monitoring?", ["PRO", "TEC"]),
    ("lopa", "P2", "lopa", "LOPA — undetected track jump leading to a mid-air collision", ["TEC", "HUM", "PRO"]),
    ("eta", "P2", "eta", "ETA — outcomes of an undetected position error in a conflict", ["TEC", "HUM"]),
    ("hta", "P2", "hta", "HTA — operate Sector E3 in degraded surveillance mode", ["HUM", "PRO"]),
    ("hra", "P2", "hra", "HRA — detecting degradation and applying the degraded mode", ["HUM"]),
    ("jha", "P3", "jha", "JHA — rotary joint and encoder replacement on the radar tower", ["OHS"]),
    ("swift", "P3", "swift", "SWIFT — radar outage windows and return to service", ["PRO", "TEC", "HUM", "ENV", "ORG"]),
    ("sim", "P3", "sim", "Simulation — Sector E3 without the Bukit Sari radar (ADS-B and procedural)", ["HUM", "PRO"]),
    ("fatigue", "P3", "fatigue", "Fatigue — ATSEP night works roster for the refurbishment", ["HUM", "ORG"]),
    ("fram", "P4", "fram", "FRAM — work-as-done with intermittent track quality", ["HUM", "PRO", "ORG", "TEC"]),
    ("bbn", "P4", "bbn", "BBN — diagnosing the cause of radar degradation from its symptoms", ["TEC", "ENV"]),
    ("orc", "P5", "orc", "Occurrence risk classification — occurrences during the degradation", ["TEC", "HUM", "PRO"]),
    ("atsb", "P5", "atsb", "ORLIO analysis (ATSB method) — OCC-RDR-01 loss of separation", ["TEC", "HUM", "PRO", "ORG"]),
    ("inv", "P5", "inv", "SOAM, HFACS and Tripod Beta — OCC-RDR-01", ["HUM", "ORG", "TEC"]),
    ("spi", "P6", "spi", "SPI register — radar performance and degraded-mode indicators", ["TEC", "HUM", "ORG", "SEC", "ENV"]),
    ("gsn", "P6", "gsn", "Safety argument — degraded operation, refurbishment and return to service", ["TEC", "HUM", "PRO", "ORG", "ENV", "SEC", "OHS"]),
]
NOT_USED = [
    ("Wildlife strike risk", "No wildlife hazard is involved."),
    ("Organisational function map", "No safety-related function changes owner."),
    ("Investigation expert system (ORLIO)", "The case library holds no surveillance-degradation cases yet; add OCC-RDR-01 to it once its AcciMap is approved."),
]


def _rows(prefix, rows):
    return [{"id": f"{prefix}-{i:02d}", **r} for i, r in enumerate(rows, 1)]


SCENARIO = (
    f"The {SITE} (fictitious) is the only radar covering {SECTOR} below FL150 in the north-east quadrant; above FL150 the Gunung Tinggi "
    "MSSR overlaps in the west, and three ADS-B ground stations cover the sector above FL100 (about 70 % of flights are ADS-B equipped). "
    "From June to August 2026 the radar degraded gradually: Mode S/SSR probability of detection fell from 99.6 % to 97.1 % overall and to "
    "about 94 % between 030° and 090°; azimuth bias grew to 0.14°; reflected false targets appeared after a telecommunication tower was "
    "built 1.2 km north-east of the site; Mode C garbling rose in dense traffic. The remote monitoring (RMM) raised no alarm because its "
    "thresholds detect hard failures only. Controllers described the tracks as 'jumpy' but few formal reports were made. On 21 August a "
    "loss of separation (OCC-RDR-01) occurred when a coasting track hid a converging aircraft. The radar's rotary joint and azimuth encoder "
    "were found worn; they are replaced during night outage windows, after which the radar is re-aligned and returned to service."
)

# ================================================================ P1 — concept
HAZID = _rows("HZ", [
    {"guideword": "Equipment / systems", "hazard": "Undetected erroneous position (track jump, azimuth bias) of an aircraft", "causes": "Worn rotary joint; encoder error; tracker coasting after missed detections",
     "consequences": "Separation planned on a wrong position; loss of separation", "controls": "Multi-sensor tracking where ADS-B available; STCA", "severity": "B", "likelihood": 4,
     "actions": "FTA of the erroneous-position failure condition; performance monitoring of Pd and azimuth bias", "owner": "CNS engineering", "detailed_method": "fta"},
    {"guideword": "Equipment / systems", "hazard": "Track drops and coasting in the north-east quadrant below FL150", "causes": "Pd ≈ 94 % in 030°–090°; single radar coverage",
     "consequences": "Aircraft not displayed for several scans; late conflict detection", "controls": "Coasting symbol; ATCO scan", "severity": "C", "likelihood": 4,
     "actions": "FMEA of the radar chain; RBD of E3 surveillance availability", "owner": "CNS engineering", "detailed_method": "fmea"},
    {"guideword": "People", "hazard": "Controllers keep applying 5 NM on degraded tracks", "causes": "Degradation not declared; no criteria; trust in the display",
     "consequences": "Separation minimum not matched to data quality", "controls": "None formal", "severity": "B", "likelihood": 3,
     "actions": "STPA of the degraded-mode declaration; HRA of detection", "owner": "ACC unit chief", "detailed_method": "stpa"},
    {"guideword": "Procedures", "hazard": "No degraded-surveillance procedure or criteria", "causes": "Manual of ATS covers total loss only",
     "consequences": "Inconsistent responses between watches", "controls": "Supervisor judgement", "severity": "C", "likelihood": 4,
     "actions": "Write the degraded-mode procedure (HTA); HAZOP of the declaration", "owner": "ATS standards", "detailed_method": "hazop"},
    {"guideword": "Organisation", "hazard": "Gradual degradation not detected by the maintenance regime", "causes": "RMM alarms on hard failures only; no periodic performance analysis",
     "consequences": "Degradation persists for months", "controls": "Daily ATSEP checks", "severity": "C", "likelihood": 4,
     "actions": "Radar performance analysis monthly (Pd, bias, false targets); SPI register", "owner": "Head of CNS maintenance", "detailed_method": "bowtie"},
    {"guideword": "Environment", "hazard": "Reflected false targets and FRUIT interference", "causes": "New telecom tower 1.2 km NE; new military interrogator",
     "consequences": "False target correlated with a real track; ATCO distraction", "controls": "Reflector processing (partly configured)", "severity": "C", "likelihood": 3,
     "actions": "Reflector map update; frequency/interrogator coordination with the military", "owner": "CNS engineering"},
    {"guideword": "Equipment / systems", "hazard": "STCA unreliable on degraded tracks (late, missed or nuisance alerts)", "causes": "STCA uses the same tracks as the controller",
     "consequences": "Safety net fails when most needed", "controls": "None independent", "severity": "B", "likelihood": 3,
     "actions": "Do not credit STCA as an independent layer (LOPA); tune STCA for coasting tracks", "owner": "ATM systems", "detailed_method": "lopa"},
    {"guideword": "Equipment / systems", "hazard": "Undetected spoofed ADS-B target while the radar cross-check is degraded", "causes": "ADS-B unauthenticated; radar comparison unreliable",
     "consequences": "False aircraft or false position displayed", "controls": "Radar/ADS-B comparison", "severity": "B", "likelihood": 2,
     "actions": "Security risk assessment", "owner": "IT security", "detailed_method": "sec"},
    {"guideword": "Transition", "hazard": "Radar returned to service misaligned after refurbishment", "causes": "Encoder replaced; north alignment and registration not verified",
     "consequences": "Systematic position error on all tracks", "controls": "Commissioning checklist", "severity": "B", "likelihood": 2,
     "actions": "SWIFT of the outage and return to service; registration check against ADS-B", "owner": "Radar engineer", "detailed_method": "swift"},
    {"guideword": "Traffic", "hazard": "Capacity of E3 exceeded under increased separation", "causes": "8 NM and procedural areas reduce throughput",
     "consequences": "Workload peaks; holding", "controls": "Flow measures", "severity": "D", "likelihood": 3,
     "actions": "Real-time simulation of the outage configuration", "owner": "ACC unit chief", "detailed_method": "sim"},
])

FHA = _rows("FC", [
    {"function": "F1 Provide position and identity of aircraft in E3", "failure_type": "Total loss", "condition": "Loss of all surveillance below FL150 in the NE quadrant (detected)",
     "effect": "Procedural separation; capacity reduced; workload peak during transition", "severity": "C", "requirements": "Procedural contingency and flow measures ready"},
    {"function": "F1 Provide position and identity of aircraft in E3", "failure_type": "Partial loss / degradation", "condition": "Track drops and coasting of individual aircraft (detected by the controller)",
     "effect": "Late detection of conflicts; extra RT for position checks", "severity": "C", "requirements": "Coasting symbol clearly distinct; criteria to declare degraded mode"},
    {"function": "F1 Provide position and identity of aircraft in E3", "failure_type": "Erroneous (undetected)", "condition": "Undetected erroneous position of a single aircraft (track jump ≥ 1 NM)",
     "effect": "Separation planned on a wrong position; loss of separation", "severity": "B", "requirements": "Radar/ADS-B position comparison alert; Pd and bias monitoring"},
    {"function": "F1 Provide position and identity of aircraft in E3", "failure_type": "Erroneous (undetected)", "condition": "Undetected systematic azimuth bias affecting all tracks",
     "effect": "Relative positions mostly preserved; terrain and airspace boundaries affected", "severity": "C", "requirements": "Registration check against ADS-B after any encoder work"},
    {"function": "F1 Provide position and identity of aircraft in E3", "failure_type": "Erroneous (undetected)", "condition": "False (reflected) target correlated with a real aircraft",
     "effect": "Wrong aircraft vectored or unnecessary avoiding action", "severity": "C", "requirements": "Reflector map maintained after new structures"},
    {"function": "F2 Provide pressure altitude (Mode C/S)", "failure_type": "Erroneous (undetected)", "condition": "Garbled Mode C level displayed without warning",
     "effect": "Level separation planned on a wrong level", "severity": "B", "requirements": "Mode C validation; Mode S altitude preferred"},
    {"function": "F3 Indicate surveillance quality to ATCO and ATSEP", "failure_type": "Total loss", "condition": "Degradation of Pd or accuracy not indicated",
     "effect": "Controllers keep 5 NM on degraded data", "severity": "B", "requirements": "Performance monitoring with thresholds; degraded-mode indication at the CWP"},
    {"function": "F4 Short-term conflict alert", "failure_type": "Partial loss / degradation", "condition": "STCA late or missing because tracks are degraded",
     "effect": "Safety net not effective when most needed", "severity": "B", "requirements": "STCA not credited as independent of the surveillance chain"},
    {"function": "F4 Short-term conflict alert", "failure_type": "Unintended", "condition": "Nuisance STCA alerts from false targets",
     "effect": "Distraction; alerts discounted ('cry wolf')", "severity": "D", "requirements": "Reflector processing; nuisance-alert SPI"},
])


def _bowtie():
    B = {}

    def b(bid, text, kind, owner, eff="unknown", critical=False, ver="existing-unverified", spi=""):
        B[bid] = {"id": bid, "text": text, "kind": kind, "effectiveness": eff, "owner": owner, "critical": critical, "verification": ver, "spi": spi}
    b("PB1", "Preventive maintenance of rotary joint and encoder (hours-based replacement)", "hardware", "Head of CNS maintenance", "poor", True, spi="RJ/encoder hours vs limit")
    b("PB2", "Monthly radar performance analysis (Pd, azimuth bias, false targets) with thresholds", "procedure", "CNS engineering", "unknown", True, "planned", "S-01, S-02, S-03")
    b("PB3", "Reflector map and interrogator coordination after new structures or emitters", "procedure", "CNS engineering", "poor", spi="S-03 false targets")
    b("PB4", "Degraded-mode declaration with criteria (ATSEP + supervisor)", "procedure", "ACC unit chief", "unknown", True, "planned", "S-06 time to declare")
    b("PB5", "Increased separation (8 NM) and procedural area below FL150 NE when declared", "procedure", "ACC supervisor", "unknown", True, "planned")
    b("PB6", "ADS-B / radar position comparison alert", "software", "ATM systems", "unknown", True, "planned", "S-04 mismatch alerts")
    b("PB7", "ATCO reporting of track anomalies via the occurrence system", "human", "ACC unit chief", "poor", spi="S-05 reports")
    b("PB8", "ADS-B plausibility checks against radar and multilateration", "software", "IT security", "unknown")
    b("RB1", "Controller detects jumped or coasting track and verifies position", "human", "ACC unit chief", "poor", True)
    b("RB2", "STCA (shares the surveillance data — not independent)", "software", "ATM systems", "poor", True, spi="S-07 STCA late/nuisance")
    b("RB3", "ACAS II RA followed", "human-hardware", "Airspace users", "good", True, "existing-verified")
    b("RB4", "Minimum vectoring altitude kept as hard limit; MSAW", "software", "ATM systems", "good")
    b("RB5", "Flow measures and sector configuration when capacity is reduced", "procedure", "ACC supervisor", "good")
    return {
        "hazard": f"Surveillance service for {SECTOR} based on the gradually degrading {SITE}",
        "top_event": "Controller provides separation on degraded or erroneous surveillance data without knowing it",
        "threats": [{"id": "T1", "text": "Rotary joint and encoder wear (missed detections, azimuth error)", "barriers": ["PB1", "PB2"]},
                    {"id": "T2", "text": "Reflections and FRUIT interference (false targets, garbling)", "barriers": ["PB3", "PB2"]},
                    {"id": "T3", "text": "Degradation below RMM alarm thresholds (not declared)", "barriers": ["PB2", "PB7", "PB4"]},
                    {"id": "T4", "text": "Tracker coasting and gaps in ADS-B equipage", "barriers": ["PB6", "PB5"]},
                    {"id": "T5", "text": "Spoofed ADS-B while the radar cross-check is degraded", "barriers": ["PB8", "PB6"]}],
        "consequences": [{"id": "C1", "text": "Loss of separation leading to mid-air collision", "severity": "A", "barriers": ["RB1", "RB2", "RB3"]},
                         {"id": "C2", "text": "Aircraft vectored towards terrain on a biased position", "severity": "A", "barriers": ["RB4", "RB1"]},
                         {"id": "C3", "text": "Workload peak and capacity loss in E3", "severity": "D", "barriers": ["RB5"]}],
        "barriers": B,
        "escalation": [{"id": "EF1", "text": "Controllers distrust a 'jumpy' display and discount STCA (cry wolf)", "barrier": "RB2",
                        "ef_barriers": ["Nuisance-alert SPI and STCA tuning (S-07)"]},
                       {"id": "EF2", "text": "Spare rotary joint not in stock; refurbishment delayed", "barrier": "PB1",
                        "ef_barriers": ["Critical spares list reviewed annually"]}],
    }


SEJ_EXPERTS = ["ATCO instructor", "ATSEP radar specialist", "Safety analyst"]
SEJ_ITEMS = [
    {"id": "S1", "label": "Formal reports of track anomalies in E3, June–August", "seed": True, "realisation": 9, "scale": "uni",
     "answers": {"ATCO instructor": [10, 20, 40], "ATSEP radar specialist": [4, 8, 15], "Safety analyst": [5, 12, 25]}},
    {"id": "S2", "label": "Measured Pd (%) in the 030°–090° sector, August", "seed": True, "realisation": 94.1, "scale": "uni",
     "answers": {"ATCO instructor": [90, 95, 98], "ATSEP radar specialist": [93, 95, 97], "Safety analyst": [96, 98, 99]}},
    {"id": "S3", "label": "Mean scans coasted per track drop", "seed": True, "realisation": 2.4, "scale": "uni",
     "answers": {"ATCO instructor": [1.5, 3, 5], "ATSEP radar specialist": [1.8, 2.5, 3.5], "Safety analyst": [1, 2, 4]}},
    {"id": "S4", "label": "Share of E3 flights ADS-B equipped (%)", "seed": True, "realisation": 71, "scale": "uni",
     "answers": {"ATCO instructor": [50, 65, 80], "ATSEP radar specialist": [60, 70, 78], "Safety analyst": [70, 85, 95]}},
    {"id": "Q1", "label": "P(controller does not detect a 2 NM track jump within one scan, moderate traffic)", "seed": False, "scale": "log",
     "answers": {"ATCO instructor": [0.02, 0.06, 0.2], "ATSEP radar specialist": [0.05, 0.12, 0.3], "Safety analyst": [0.01, 0.04, 0.15]}},
]
DELPHI = [{"round": 1, "estimates": {"P1": 0.05, "P2": 0.15, "P3": 0.08, "P4": 0.30, "P5": 0.04}},
          {"round": 2, "estimates": {"P1": 0.07, "P2": 0.12, "P3": 0.09, "P4": 0.18, "P5": 0.06}},
          {"round": 3, "estimates": {"P1": 0.08, "P2": 0.11, "P3": 0.09, "P4": 0.12, "P5": 0.07}}]

# ================================================================ P2 — design
FMEA = _rows("FM", [
    {"item": "Antenna rotary joint", "failure_mode": "Intermittent loss of sum/difference channel", "cause": "Wear (hours beyond limit)", "end_effect": "Missed detections; split plots; track jumps",
     "detection_method": "None automatic — gradual", "compensation": "Multi-sensor tracking where ADS-B", "s": 8, "o": 6, "d": 8, "rate": 2.5e-4},
    {"item": "Azimuth encoder (ACP/ARP)", "failure_mode": "Azimuth error growing to > 0.1°", "cause": "Bearing wear; coupling slip", "end_effect": "Systematic position error; registration error",
     "detection_method": "Registration vs ADS-B (not automated)", "compensation": "None", "s": 7, "o": 4, "d": 7, "rate": 1e-4},
    {"item": "MSSR transmitter (dual)", "failure_mode": "Output power low on active channel", "cause": "Ageing amplifier", "end_effect": "Range and Pd reduced at long range",
     "detection_method": "RMM power alarm", "compensation": "Changeover to standby", "s": 5, "o": 3, "d": 2, "rate": 5e-5},
    {"item": "Receiver / plot extractor", "failure_mode": "Garbled replies decoded as valid Mode C", "cause": "FRUIT from new interrogator", "end_effect": "Wrong level displayed",
     "detection_method": "Mode C validation partly", "compensation": "Mode S altitude preferred", "s": 8, "o": 4, "d": 6, "rate": 8e-5},
    {"item": "Reflector processing", "failure_mode": "False targets not suppressed", "cause": "Reflector map not updated for new tower", "end_effect": "False target near real traffic",
     "detection_method": "ATCO reports", "compensation": "ATCO judgement", "s": 6, "o": 5, "d": 5, "rate": 2e-4},
    {"item": "Remote monitoring (RMM)", "failure_mode": "No alarm for gradual performance loss", "cause": "Thresholds for hard failures only", "end_effect": "Degradation not declared",
     "detection_method": "None", "compensation": "Daily ATSEP check", "s": 7, "o": 7, "d": 9},
    {"item": "Site data link (main + VSAT)", "failure_mode": "Loss of both paths", "cause": "Carrier outage + VSAT rain fade", "end_effect": "Loss of radar data at SDPS",
     "detection_method": "Link alarm", "compensation": "ADS-B above FL100", "s": 6, "o": 2, "d": 1, "rate": 1e-5},
    {"item": "SDPS multi-sensor tracker", "failure_mode": "Coasting extrapolates wrongly in turns", "cause": "Missed detections for ≥ 3 scans", "end_effect": "Displayed position diverges from actual",
     "detection_method": "Coasting symbol (low salience)", "compensation": "ATCO scan", "s": 8, "o": 5, "d": 6, "rate": 3e-4},
    {"item": "Site power (mains, UPS, generator)", "failure_mode": "Loss of power to radar and ADS-B station", "cause": "Mains failure and UPS fault", "end_effect": "Loss of both sensors at the site",
     "detection_method": "Immediate", "compensation": "Gunung Tinggi above FL150 (west)", "s": 7, "o": 2, "d": 1, "rate": 2e-6},
])

FTA_TREE = {"top": "TOP", "nodes": {
    "TOP": {"type": "and", "label": "Undetected erroneous position of an aircraft displayed in Sector E3", "children": ["G1", "G2"]},
    "G1": {"type": "or", "label": "Erroneous position produced", "children": ["E1", "E2", "E3", "E4"]},
    "G2": {"type": "and", "label": "Error not detected before it is used for separation", "children": ["E5", "E6", "E7"]},
    "E1": {"type": "basic", "label": "Rotary joint dropouts → split plots / track jump", "p": 2.5e-4},
    "E2": {"type": "basic", "label": "Encoder azimuth error > 0.1°", "p": 1e-4},
    "E3": {"type": "basic", "label": "Reflected false target correlated with a real track", "p": 5e-5},
    "E4": {"type": "basic", "label": "Tracker coasting extrapolates wrongly after missed detections", "p": 3e-4},
    "E5": {"type": "basic", "label": "Performance monitoring does not flag the degradation (PFD)", "p": 0.5},
    "E6": {"type": "basic", "label": "No ADS-B position to cross-check (aircraft not equipped / below coverage)", "p": 0.3},
    "E7": {"type": "basic", "label": "Controller does not notice the error (HRA T1)", "p": 0.09},
}}
FTA_TREE_RESIDUAL = {"top": "TOP", "nodes": {**FTA_TREE["nodes"],
                                             "E5": {**FTA_TREE["nodes"]["E5"], "p": 0.05, "label": "Performance monitoring with thresholds does not flag the degradation (PFD)"},
                                             "E6": {**FTA_TREE["nodes"]["E6"], "p": 0.3}}}

CCA = {
    "zsa": _rows("Z", [
        {"zone": "Bukit Sari radar equipment room", "equipment": "MSSR cabinets, plot extractor, ADS-B ground station BS-1, site router",
         "concern": "Radar and ADS-B station share a room, UPS and router", "check": "Sensors claimed as backups in separate zones and utilities",
         "finding": "ADS-B BS-1 depends on the radar site router and UPS", "action": "Separate router and power path for BS-1, or rely on BS-2/BS-3 only as the backup"},
        {"zone": "Radar tower and radome", "equipment": "Antenna, rotary joint, encoder, obstruction lights", "concern": "Single point of failure for all radar data",
         "check": "No redundancy expected — covered by ADS-B and procedures", "finding": "Accepted; degraded mode must be ready", "action": "Degraded-mode procedure (P2 HTA)"}]),
    "pra": _rows("P", [
        {"risk": "EMI / RF interference", "zones": "Radar site and 40 NM around", "equipment": "MSSR receiver, ADS-B 1090 MHz receivers", "redundancy_defeated": True,
         "effect": "Garbling and FRUIT degrade radar and ADS-B on the same frequency (1090 MHz)", "severity": "B", "mitigation": "Interrogator coordination; Mode S",
         "action": "Coordinate interrogation rates with the military; monitor 1090 MHz occupancy"},
        {"risk": "Lightning", "zones": "Radar tower", "equipment": "Antenna drive, encoder, site electronics", "redundancy_defeated": True,
         "effect": "Loss of radar and BS-1 together", "severity": "C", "mitigation": "Lightning protection; surge arrestors", "action": "Inspect surge protection after the works"},
        {"risk": "Power surge", "zones": "Radar site", "equipment": "Both MSSR channels and BS-1", "redundancy_defeated": True, "effect": "Loss of site", "severity": "C",
         "mitigation": "UPS; generator", "action": "Load test of the generator monthly"}]),
    "cma": _rows("CM", [
        {"claim": "STCA is a barrier independent of the controller's detection", "items": "STCA, ATCO monitoring", "source": "Design / specification",
         "analysis": "Both use the same SDPS tracks; a coasting or jumped track deceives both", "independent": "No", "action": "Do not credit STCA as an IPL in LOPA; credit ADS-B comparison instead"},
        {"claim": "ADS-B is an independent backup to the radar", "items": "MSSR, ADS-B BS-1, BS-2, BS-3", "source": "Shared utilities (power, HVAC, network)",
         "analysis": "BS-1 shares router and UPS with the radar; all share 1090 MHz; BS-2 and BS-3 are independent of the site", "independent": "Partly", "action": "See Z-01; P-01"},
        {"claim": "Radar data paths (leased line and VSAT) fail independently", "items": "Main link, VSAT", "source": "Environment",
         "analysis": "Heavy rain causes both carrier faults and VSAT fade", "independent": "Partly", "action": "Use a β-factor in the FTA of loss of data"}]),
}

RBD = {"type": "series", "label": "Surveillance available for 5 NM separation in E3 (NE, below FL150)", "children": [
    {"type": "parallel", "label": "Sensors", "children": [
        {"type": "series", "label": "Bukit Sari MSSR", "children": [
            {"type": "block", "label": "Antenna, rotary joint, encoder (degraded)", "mtbf": 3000, "mttr": 48},
            {"type": "parallel", "label": "MSSR channels", "children": [
                {"type": "block", "label": "Channel A", "mtbf": 15000, "mttr": 6}, {"type": "block", "label": "Channel B", "mtbf": 15000, "mttr": 6}]}]},
        {"type": "block", "label": "ADS-B (BS-2, BS-3) — equipped aircraft only", "mtbf": 8000, "mttr": 12}]},
    {"type": "parallel", "label": "Site data link", "children": [
        {"type": "block", "label": "Leased line", "mtbf": 4000, "mttr": 8}, {"type": "block", "label": "VSAT", "mtbf": 3000, "mttr": 12}]},
    {"type": "parallel", "label": "SDPS", "children": [
        {"type": "block", "label": "Main tracker", "mtbf": 30000, "mttr": 2}, {"type": "block", "label": "Fallback tracker", "mtbf": 30000, "mttr": 2}]}]}
# radar state: OK → degraded (wear) → failed; degraded is 'down' for the 5 NM service because data quality is not assured
MARKOV = {"states": [{"id": "OK", "label": "Radar performance within specification", "up": True},
                     {"id": "DEG", "label": "Degraded (Pd/accuracy out of specification), not yet repaired", "up": False},
                     {"id": "FAIL", "label": "Radar failed (detected)", "up": False}],
          "transitions": [{"from": "OK", "to": "DEG", "rate": 1 / 4000, "label": "wear-out / interference begins"},
                          {"from": "OK", "to": "FAIL", "rate": 1 / 20000, "label": "hard failure"},
                          {"from": "DEG", "to": "FAIL", "rate": 1 / 2000, "label": "degradation becomes failure"},
                          {"from": "DEG", "to": "OK", "rate": 1 / 1460, "label": "detected and repaired (≈ 2 months today)"},
                          {"from": "FAIL", "to": "OK", "rate": 1 / 24, "label": "repaired"}]}
MARKOV_MONITORED = {**MARKOV, "transitions": [dict(t, rate=1 / 168, label="detected and repaired (≈ 1 week with monthly analysis and thresholds)")
                                               if t["from"] == "DEG" and t["to"] == "OK" else t for t in MARKOV["transitions"]]}

STPA = {
    "losses": [{"id": "L-1", "text": "Mid-air collision"}, {"id": "L-2", "text": "Controlled flight into terrain"},
               {"id": "L-3", "text": "Loss of ATS capacity (traffic held or rerouted)"}],
    "hazards": [{"id": "H-1", "text": "Aircraft separated with a minimum not supported by the surveillance data quality", "losses": ["L-1"]},
                {"id": "H-2", "text": "Aircraft vectored on a position error near terrain", "losses": ["L-2"]},
                {"id": "H-3", "text": "Sector capacity reduced without flow measures", "losses": ["L-3"]}],
    "constraints": [{"id": "SC-1", "text": "Separation minima must match the declared surveillance performance", "hazards": ["H-1"]},
                    {"id": "SC-2", "text": "Degradation must be declared before it affects separation", "hazards": ["H-1", "H-2"]},
                    {"id": "SC-3", "text": "Capacity must be reduced together with any increase in separation", "hazards": ["H-3"]}],
    "structure": {"nodes": [
        {"id": "MGT", "label": "ANSP management (CNS + ATS)", "kind": "controller", "x": 250, "y": 0, "process_model": "Maintenance regime; procedures"},
        {"id": "ATSEP", "label": "ATSEP technical supervisor", "kind": "controller", "x": 0, "y": 130, "process_model": "Radar health from RMM and checks"},
        {"id": "SUP", "label": "ACC supervisor", "kind": "controller", "x": 500, "y": 130, "process_model": "Sector configuration; surveillance status"},
        {"id": "RMM", "label": "RMM / performance analysis", "kind": "automation", "x": 0, "y": 300},
        {"id": "RDR", "label": "MSSR + SDPS tracker", "kind": "process", "x": 250, "y": 300},
        {"id": "ATCO", "label": "E3 controller", "kind": "controller", "x": 500, "y": 300, "process_model": "Traffic picture; minimum in force"},
        {"id": "CREW", "label": "Flight crew", "kind": "controller", "x": 500, "y": 460}],
        "edges": [
            {"id": "e1", "source": "MGT", "target": "ATSEP", "kind": "control", "label": "maintenance programme, thresholds"},
            {"id": "e2", "source": "MGT", "target": "SUP", "kind": "control", "label": "degraded-mode procedure"},
            {"id": "e3", "source": "ATSEP", "target": "RDR", "kind": "control", "label": "repair, changeover, return to service"},
            {"id": "e4", "source": "RMM", "target": "ATSEP", "kind": "feedback", "label": "alarms, Pd/bias reports"},
            {"id": "e5", "source": "RDR", "target": "RMM", "kind": "feedback", "label": "built-in test, plots"},
            {"id": "e6", "source": "ATSEP", "target": "SUP", "kind": "control", "label": "declare / cancel degraded mode"},
            {"id": "e7", "source": "SUP", "target": "ATCO", "kind": "control", "label": "apply 8 NM / procedural area"},
            {"id": "e8", "source": "RDR", "target": "ATCO", "kind": "feedback", "label": "tracks on the situation display"},
            {"id": "e9", "source": "ATCO", "target": "SUP", "kind": "feedback", "label": "track-anomaly reports"},
            {"id": "e10", "source": "ATCO", "target": "CREW", "kind": "control", "label": "clearances, vectors"},
            {"id": "e11", "source": "CREW", "target": "ATCO", "kind": "feedback", "label": "position reports, read-backs"}]},
    "ucas": [
        {"id": "UCA-1", "control_action": "declare degraded mode", "type": "Not providing causes hazard", "text": "ATSEP does not declare degraded mode",
         "context": "when Pd or bias is out of specification but no RMM alarm is raised", "hazards": ["H-1", "H-2"]},
        {"id": "UCA-2", "control_action": "apply 8 NM / procedural area", "type": "Not providing causes hazard", "text": "Supervisor does not apply increased separation",
         "context": "when controllers report jumpy tracks informally but no declaration exists", "hazards": ["H-1"]},
        {"id": "UCA-3", "control_action": "clearances, vectors", "type": "Providing causes hazard", "text": "Controller vectors an aircraft on a coasting track",
         "context": "when the coasting symbol is not noticed", "hazards": ["H-1", "H-2"]},
        {"id": "UCA-4", "control_action": "repair, changeover, return to service", "type": "Too early / too late / wrong order", "text": "Radar returned to service before alignment and registration are verified",
         "context": "after encoder replacement under schedule pressure", "hazards": ["H-1", "H-2"]},
        {"id": "UCA-5", "control_action": "declare / cancel degraded mode", "type": "Stopped too soon / applied too long", "text": "Degraded mode cancelled after the repair without a performance check",
         "context": "when interference (not wear) was also a cause", "hazards": ["H-1"]},
        {"id": "UCA-6", "control_action": "apply 8 NM / procedural area", "type": "Providing causes hazard", "text": "Increased separation applied without flow measures",
         "context": "at the morning peak", "hazards": ["H-3"]}],
    "scenarios": [
        {"id": "S-1", "uca": "UCA-1", "type": "Inadequate feedback", "text": "RMM reports hard failures only; no Pd or bias trend reaches the ATSEP", "requirement": "Monthly performance analysis with thresholds (PB2)"},
        {"id": "S-2", "uca": "UCA-2", "type": "Flawed process model", "text": "Supervisor believes the radar is serviceable because no NOTAM or ATSEP declaration exists", "requirement": "Criteria for a supervisor-initiated declaration on controller reports"},
        {"id": "S-3", "uca": "UCA-3", "type": "Inadequate feedback", "text": "Coasting symbol differs from a normal track only by a small mark", "requirement": "Distinct coasting symbol; age of the last update shown"},
        {"id": "S-4", "uca": "UCA-4", "type": "Conflicting control", "text": "Project plan sets the return date; commissioning checks are not a hold point", "requirement": "Registration check against ADS-B as a go/no-go hold point"},
        {"id": "S-5", "uca": "UCA-5", "type": "Flawed process model", "text": "ATSEP assumes the replaced parts were the only cause", "requirement": "Performance analysis before cancelling degraded mode"}],
}

HAZOP = {
    "nodes": [{"id": "N1", "name": "N1 Radar plots (ASTERIX CAT048) — site → SDPS tracker → display", "type": "data-flow",
               "intent": "Every aircraft in coverage is displayed at its true position and level, updated every scan (12 s)."},
              {"id": "N2", "name": "N2 Declaration of degraded surveillance — ATSEP → supervisor → controllers", "type": "procedural",
               "intent": "Degradation is declared, communicated and applied before it affects separation, and cancelled only after verification."}],
    "rows": _rows("HP", [
        {"node": "N1", "parameter": "Message", "guideword": "No / Not", "deviation": "No plot for an aircraft in coverage (missed detection)", "causes": "Rotary joint dropouts; garbling",
         "consequences": "Track coasts; position extrapolated", "safeguards": "Coasting symbol; ADS-B where equipped", "severity": "C", "likelihood": 4, "recommendation": "Pd per azimuth sector as SPI"},
        {"node": "N1", "parameter": "Content", "guideword": "Other than", "deviation": "Plot at a wrong azimuth", "causes": "Encoder error", "consequences": "Systematic position error",
         "safeguards": "Registration (manual)", "severity": "B", "likelihood": 3, "recommendation": "Automatic registration monitoring against ADS-B"},
        {"node": "N1", "parameter": "Content", "guideword": "As well as", "deviation": "False (reflected) plot in addition to the real one", "causes": "New tower; reflector map outdated",
         "consequences": "Duplicate or false target", "safeguards": "Reflector processing", "severity": "C", "likelihood": 3, "recommendation": "Update reflector map after any new structure within 5 km"},
        {"node": "N1", "parameter": "Content", "guideword": "Other than", "deviation": "Wrong Mode C level decoded", "causes": "FRUIT garbling", "consequences": "Wrong level displayed",
         "safeguards": "Mode C validation; Mode S altitude", "severity": "B", "likelihood": 2, "recommendation": "Prefer Mode S altitude; flag unvalidated Mode C"},
        {"node": "N1", "parameter": "Timing", "guideword": "Late", "deviation": "Plots delayed at the SDPS", "causes": "Link congestion on VSAT", "consequences": "Position lag in turns",
         "safeguards": "Time-stamping; latency monitor", "severity": "C", "likelihood": 2, "recommendation": "Latency alarm > 2 s"},
        {"node": "N2", "parameter": "Action", "guideword": "No / Not", "deviation": "Degraded mode not declared", "causes": "No criteria; no performance data", "consequences": "5 NM applied on degraded data",
         "safeguards": "None", "severity": "B", "likelihood": 4, "recommendation": "Declaration criteria (Pd < 97 % in any sector, bias > 0.1°, ≥ 3 anomaly reports per watch)"},
        {"node": "N2", "parameter": "Timing", "guideword": "Late", "deviation": "Declaration reaches controllers after the watch change", "causes": "Briefing only at watch start",
         "consequences": "Incoming watch unaware", "safeguards": "Supervisor log", "severity": "C", "likelihood": 3, "recommendation": "Status banner on every CWP and in the handover checklist"},
        {"node": "N2", "parameter": "Information", "guideword": "Less", "deviation": "Declaration without the affected area and levels", "causes": "Free-text message",
         "consequences": "Measures applied too widely or too narrowly", "safeguards": "None", "severity": "C", "likelihood": 3, "recommendation": "Standard declaration form with area, levels and minimum"},
        {"node": "N2", "parameter": "Sequence", "guideword": "Before", "deviation": "Degraded mode cancelled before the performance check", "causes": "Repair reported complete",
         "consequences": "5 NM restored on unverified data", "safeguards": "ATSEP sign-off", "severity": "B", "likelihood": 2, "recommendation": "Cancellation only after a performance report (Pd, bias) is signed"},
    ])}

SEC = _rows("SR", [
    {"asset": "ADS-B ground stations BS-1…BS-3", "threat": "Spoofed ADS-B targets injected while the radar cross-check is degraded", "source": "External attacker",
     "vulnerability": "ADS-B unauthenticated; radar comparison unreliable in NE quadrant", "c": 1, "i": 5, "a": 3, "likelihood": 3, "controls": "Radar/ADS-B comparison (degraded)",
     "safety_severity": "B", "treatment": "Plausibility checks (range/azimuth, multilateration time-difference); restore radar quickly", "owner": "IT security"},
    {"asset": "Radar remote maintenance access", "threat": "Compromised vendor account changes radar parameters", "source": "Supplier / third party",
     "vulnerability": "Remote access left open for the refurbishment period", "c": 2, "i": 5, "a": 4, "likelihood": 2, "controls": "VPN",
     "safety_severity": "B", "treatment": "Time-limited accounts with MFA; session approval and logging", "owner": "CNS engineering"},
    {"asset": "GNSS-based ADS-B positions", "threat": "GNSS interference degrades ADS-B (NIC/NACp drop) during the radar outage", "source": "External attacker",
     "vulnerability": "Fallback depends on GNSS", "c": 1, "i": 4, "a": 4, "likelihood": 2, "controls": "Integrity indicators", "safety_severity": "C",
     "treatment": "Procedural contingency; GNSS interference reporting", "owner": "CNS engineering"},
    {"asset": "Radar site", "threat": "Physical intrusion during works (gates open, contractors)", "source": "Physical intrusion",
     "vulnerability": "Access control relaxed during refurbishment", "c": 1, "i": 3, "a": 5, "likelihood": 2, "controls": "Guard at the gate",
     "safety_severity": "C", "treatment": "Contractor access list; CCTV; lock-up checklist", "owner": "Site manager"},
])

_LAT = {k: CRM_LATERAL[k] for k in ("pz0", "lx", "lz", "sx", "ey_same", "ey_opp", "dv", "v", "zdot", "ydot_sy", "tls")}
CRM_MODEL = {"vertical": {},
             "lateral": {**_LAT, "ly": CRM_LAT_MODEL["lam_y"], "model": "laplace", "scale": CRM_LAT_MODEL["scale"], "spacing": 10.0,
                         "spacings": [5, 7.5, 10, 12.5, 15, 20, 25]},
             "note": "Parallel RNAV 5 routes W-31 and W-33 cross the NE quadrant 10 NM apart. With radar monitoring the controller can intervene; "
                     "without it the spacing must meet the target level of safety on navigation performance alone. Lateral deviations: "
                     "double-exponential, scale 0.9 NM (no ATC intervention)."}

LOPA = {"scenario": "Undetected track jump in E3 leads to a potential mid-air collision",
        "initiating": {"label": "Undetected position error ≥ 1 NM on an aircraft in E3", "frequency": 2.0, "source": "FTA P2 (degraded state), about 2 per year at 6,000 flight hours"},
        "unit": "per year", "target": 1e-5,
        "modifiers": [{"label": "Another aircraft within 10 NM at a conflicting level", "probability": 0.1}],
        "safeguards": [
            {"label": "Controller detects the error and verifies the position", "pfd": 0.1, "independent": True, "effective": True, "dependable": True, "auditable": True,
             "dependencies": ["surveillance display"], "justification": "HRA T1 gives 0.09"},
            {"label": "STCA alert and controller resolution", "pfd": 0.1, "independent": False, "effective": True, "dependable": False, "auditable": True,
             "dependencies": ["surveillance display"], "justification": "Uses the same tracks as the controller (CCA CM-01) — not an IPL"},
            {"label": "ACAS II RA followed", "pfd": 0.1, "independent": True, "effective": True, "dependable": True, "auditable": True},
            {"label": "Increased separation (8 NM) in the declared area", "pfd": 0.1, "independent": True, "effective": True, "dependable": True, "auditable": True,
             "justification": "Absorbs a 2 NM jump with margin; applies only when degraded mode is declared"},
            {"label": "ADS-B / radar position comparison alert (proposed)", "pfd": 0.3, "independent": True, "effective": True, "dependable": False, "auditable": True,
             "justification": "Proposed; only for ADS-B-equipped aircraft (≈ 70 %) — tick Dependable when implemented"}]}

ETA = {"initiating": {"label": "Undetected position error (track jump ≥ 1 NM) in a conflict geometry", "frequency": 0.2, "unit": "per year"},
       "events": [{"id": "B1", "label": "Controller detects the error and resolves", "p_success": 0.91},
                  {"id": "B2", "label": "STCA alerts in time and controller resolves", "p_success": 0.5},
                  {"id": "B3", "label": "ACAS II RA followed", "p_success": 0.9}],
       "overrides": {},
       "outcomes": {"S": {"label": "Resolved by the controller — no loss of separation", "severity": "D"},
                    "F-S": {"label": "Loss of separation, resolved after STCA", "severity": "C"},
                    "F-F-S": {"label": "Serious loss of separation, resolved by ACAS", "severity": "B"},
                    "F-F-F": {"label": "Near mid-air collision / collision", "severity": "A"}},
       "terminate_on_success": True,
       "note": "B2 is low (0.5) because STCA uses the same degraded tracks: when the controller misses the error, STCA often misses it too."}

HTA = {"tasks": [
    {"id": "0", "parent": None, "title": "Operate Sector E3 in degraded surveillance mode", "plan": "Do 1, then 2 and 3 together; 4 continuously; 5 when the radar is restored and verified."},
    {"id": "1", "parent": "0", "title": "Recognise the degradation", "plan": "Any of 1.1, 1.2 or 1.3 triggers 2"},
    {"id": "1.1", "parent": "1", "title": "ATSEP: performance report exceeds a threshold (Pd, bias, false targets)", "error_modes": ["Check omitted", "Information not obtained"], "hra": "T2"},
    {"id": "1.2", "parent": "1", "title": "Controller: notice coasting or jumping tracks", "error_modes": ["Information not obtained"], "hra": "T1"},
    {"id": "1.3", "parent": "1", "title": "Controller: report the anomaly to the supervisor", "error_modes": ["Information not communicated"]},
    {"id": "2", "parent": "0", "title": "Declare degraded mode", "plan": "Do 2.1 then 2.2 and 2.3"},
    {"id": "2.1", "parent": "2", "title": "Supervisor and ATSEP agree area, levels and minimum on the standard form", "error_modes": ["Wrong information communicated"], "hra": "T4"},
    {"id": "2.2", "parent": "2", "title": "Set the status banner on all E3 and APP-S positions", "error_modes": ["Action omitted"]},
    {"id": "2.3", "parent": "2", "title": "Request NOTAM and inform adjacent units", "error_modes": ["Information not communicated"]},
    {"id": "3", "parent": "0", "title": "Apply the measures", "plan": "Do 3.1–3.3 for every aircraft entering the declared area"},
    {"id": "3.1", "parent": "3", "title": "Apply 8 NM in the declared area; procedural below FL150 NE", "error_modes": ["Wrong action"]},
    {"id": "3.2", "parent": "3", "title": "Verify positions of non-ADS-B aircraft by position reports", "error_modes": ["Check omitted"]},
    {"id": "3.3", "parent": "3", "title": "Request flow measures when demand exceeds the reduced capacity", "error_modes": ["Action too early / late"]},
    {"id": "4", "parent": "0", "title": "Monitor and hand over", "plan": "4.1 continuously; 4.2 at every handover"},
    {"id": "4.1", "parent": "4", "title": "Watch for further degradation and report"},
    {"id": "4.2", "parent": "4", "title": "Include degraded mode in the handover checklist", "error_modes": ["Information not communicated"]},
    {"id": "5", "parent": "0", "title": "Cancel degraded mode", "plan": "Only after 5.1"},
    {"id": "5.1", "parent": "5", "title": "ATSEP signs a performance report (Pd, bias, registration vs ADS-B)", "error_modes": ["Check omitted"], "hra": "T3"},
    {"id": "5.2", "parent": "5", "title": "Supervisor cancels; banner removed; NOTAM cancelled", "error_modes": ["Action too early / late"]},
]}

HRA_TASKS = [
    {"id": "T1", "task": "Controller notices a coasting or jumped track during the scan", "library": "cara", "gtt": "B1",
     "epcs": [{"code": "10", "apoa": 1.0}, {"code": "17", "apoa": 0.3}, {"code": "7", "apoa": 0.5}]},
    {"id": "T2", "task": "ATSEP recognises a gradual degradation from the daily check (no thresholds)", "library": "heart", "gtt": "E",
     "epcs": [{"code": "3", "apoa": 0.4}, {"code": "13", "apoa": 0.4}]},
    {"id": "T3", "task": "ATSEP restores the radar to service after encoder replacement, incl. alignment", "library": "heart", "gtt": "F",
     "epcs": [{"code": "17", "apoa": 0.5}, {"code": "14", "apoa": 0.4}, {"code": "10", "apoa": 0.2}]},
    {"id": "T4", "task": "Supervisor declares and applies the degraded mode correctly (new procedure)", "library": "cara", "gtt": "F",
     "epcs": [{"code": "1", "apoa": 0.5}, {"code": "2", "apoa": 0.2}]},
]

# ================================================================ P3 — implementation and transition
JHA = {"job": {"title": "Replace rotary joint and azimuth encoder, re-align and return the MSSR to service", "location": f"{SITE} — tower and radome (28 m)",
               "permits": "Permit to work; LOTO of antenna drive and transmitters; lifting plan; work at height permit; ATS coordination"},
       "rows": _rows("S", [
           {"step": "Coordinate the outage window with ATS; degraded mode and NOTAM in force", "hazards": "Radar removed without ATS awareness", "controls": "Signed outage request; supervisor confirmation before switch-off", "hierarchy": "Administrative", "responsible": "ATSEP team leader"},
           {"step": "Stop the antenna, lock out drive and both transmitters", "hazards": "Rotating antenna; RF exposure", "controls": "Mechanical antenna lock; LOTO with personal locks; RF off verified by meter", "hierarchy": "Engineering", "responsible": "Radar engineer"},
           {"step": "Climb to the radome with tools; rescue plan in place", "hazards": "Fall from height; dropped objects; heat in the radome", "controls": "Fixed ladder with fall arrest; tethered tools; exclusion zone; work–rest cycle; water", "hierarchy": "PPE", "responsible": "Climbers"},
           {"step": "Lift out the old rotary joint and lift in the new one (crane)", "hazards": "Suspended load; crane contact with the tower", "controls": "Lifting plan; certified rigger; tag lines; wind limit 10 m/s", "hierarchy": "Engineering", "responsible": "Lifting supervisor"},
           {"step": "Replace and couple the azimuth encoder", "hazards": "Pinch points at the bull gear", "controls": "Drive locked; guards", "hierarchy": "Engineering", "responsible": "Radar engineer"},
           {"step": "Remove locks, rotate, radiate at low power; align north and check registration against ADS-B", "hazards": "RF exposure of staff in the radome; wrong alignment", "controls": "Radome cleared before radiating; alignment and registration as a hold point", "hierarchy": "Administrative", "responsible": "Radar engineer"},
           {"step": "Hand back to ATS with the performance report", "hazards": "Radar back in service with unverified performance", "controls": "Signed performance report; supervisor acceptance", "hierarchy": "Administrative", "responsible": "ATSEP team leader"}])}

SWIFT = _rows("W", [
    {"guideword": "Timing and sequence", "what_if": "What if the works overrun into the morning departure peak?", "consequence": "E3 without radar at peak; holding; workload",
     "safeguards": "Night windows 22:00–05:00", "severity": "C", "likelihood": 3, "recommendation": "Hard stop at 04:30 with the antenna re-assembled or a declared extension", "owner": "ATSEP team leader"},
    {"guideword": "Equipment and utilities", "what_if": "What if the radar returns misaligned (encoder offset)?", "consequence": "Systematic position error on all tracks",
     "safeguards": "Commissioning checklist", "severity": "B", "likelihood": 2, "recommendation": "Registration against ADS-B as a hold point; ATCO first-hour check of radar/ADS-B overlay", "owner": "Radar engineer"},
    {"guideword": "Equipment and utilities", "what_if": "What if an ADS-B station fails during the outage?", "consequence": "Loss of surveillance for part of E3",
     "safeguards": "BS-2 and BS-3 overlap", "severity": "C", "likelihood": 2, "recommendation": "ADS-B stations checked before each window; procedural contingency", "owner": "CNS engineering"},
    {"guideword": "Information and communication", "what_if": "What if the NOTAM or the adjacent units are not informed?", "consequence": "Traffic delivered at radar spacing into a procedural area",
     "safeguards": "Supervisor checklist", "severity": "C", "likelihood": 3, "recommendation": "Coordination checklist; LoA addendum for the outage", "owner": "ACC supervisor"},
    {"guideword": "People", "what_if": "What if controllers rarely use procedural separation and are rusty?", "consequence": "Errors in procedural separation",
     "safeguards": "Refresher briefing", "severity": "C", "likelihood": 3, "recommendation": "Simulator refresher before the first window (RTS)", "owner": "Training"},
    {"guideword": "Location and environment", "what_if": "What if lightning or heavy rain occurs during the works?", "consequence": "Workers at risk; works suspended with the antenna open",
     "safeguards": "Weather watch", "severity": "C", "likelihood": 3, "recommendation": "Stop-work criteria; temporary weather cover for the radome", "owner": "Lifting supervisor"},
    {"guideword": "External events", "what_if": "What if GNSS interference degrades ADS-B during an outage?", "consequence": "ADS-B positions unreliable; procedural for all",
     "safeguards": "NIC/NACp display", "severity": "C", "likelihood": 2, "recommendation": "Procedural contingency briefed; report interference", "owner": "ACC supervisor"},
    {"guideword": "Management and organisation", "what_if": "What if the works are compressed into fewer, longer nights to save cost?", "consequence": "ATSEP fatigue; configuration errors",
     "safeguards": "None", "severity": "C", "likelihood": 3, "recommendation": "Use the 8-hour night roster (fatigue study)", "owner": "Head of CNS maintenance"},
])

SIM_EX = {"title": "RTS — Sector E3 during radar outage windows (ADS-B + procedural below FL150 NE)", "type": "Real-time simulation",
          "objectives": "Show that E3 can be operated without the Bukit Sari radar at the planned capacity of 26 flights/h with acceptable workload and no losses of separation.",
          "scenarios": "Night traffic 18 flights/h and early-morning 26 flights/h; 8 runs per condition; 4 controller teams; baseline = radar available",
          "participants": "8 E3 controllers, 4 pseudo-pilots, 1 supervisor"}
SIM_MEASURES = [
    {"id": "M1", "label": "Workload (ISA, 1–5), executive controller", "unit": "ISA", "better": "lower", "criterion": {"type": "threshold", "value": 4.0},
     "baseline": [2.8, 3.0, 2.9, 3.1, 2.7, 3.0, 2.9, 3.2], "solution": [3.6, 3.9, 3.7, 4.1, 3.5, 3.8, 3.9, 3.6]},
    {"id": "M2", "label": "R/T occupancy", "unit": "%", "better": "lower", "criterion": {"type": "threshold", "value": 65},
     "baseline": [41, 44, 39, 46, 42, 43, 40, 45], "solution": [55, 61, 58, 63, 57, 60, 59, 62]},
    {"id": "M3", "label": "Losses of applicable separation per run", "unit": "count", "better": "lower", "criterion": {"type": "no_worse", "value": 0.0},
     "baseline": [0, 0, 0, 0, 0, 0, 0, 0], "solution": [0, 0, 1, 0, 0, 0, 0, 0]},
    {"id": "M4", "label": "Flights handled per hour (26/h demand)", "unit": "/h", "better": "higher", "criterion": {"type": "threshold", "value": 22},
     "baseline": [26, 26, 26, 25, 26, 26, 26, 26], "solution": [23, 22, 21, 23, 22, 22, 23, 21]},
]
for _m in SIM_MEASURES:
    _m["baseline_text"], _m["solution_text"] = ", ".join(map(str, _m["baseline"])), ", ".join(map(str, _m["solution"]))

# ATSEP night works: four 12-hour nights versus six 8-hour nights (works windows 22:00–05:00)
FAT_SLEEP_12 = [[-1, 7], [8, 13], [32, 37], [56, 61], [80, 85]]  # day sleep cut short by heat and noise
FAT_12 = [[19, 31], [43, 55], [67, 79], [91, 103]]
FAT_SLEEP_8 = [[-1, 7], [8, 15], [32, 39], [56, 63], [80, 87], [104, 111], [128, 135]]
FAT_8 = [[21.5, 29.5], [45.5, 53.5], [69.5, 77.5], [93.5, 101.5], [117.5, 125.5], [141.5, 149.5]]
FATIGUE = {"start": 0, "end": 156, "step_minutes": 5, "kss_threshold": 7,
           "variants": [{"name": "Four 12-h nights 19:00–07:00", "sleeps": FAT_SLEEP_12, "duties": FAT_12},
                        {"name": "Six 8-h nights 21:30–05:30", "sleeps": FAT_SLEEP_8, "duties": FAT_8}],
           "sp_ratings": [
               {"id": "SP1", "date": "2026-10-05", "time": "21:15", "shift": "Night works", "controller": "ATSEP-04", "position": "Radome (alignment)", "score": 3, "outcome": "normal", "mitigations": [], "notes": "ATSEP crew rated before climbing"},
               {"id": "SP2", "date": "2026-10-05", "time": "21:15", "shift": "Night works", "controller": "ATSEP-11", "position": "Radome (rigging)", "score": 2, "outcome": "normal", "mitigations": [], "notes": ""},
               {"id": "SP3", "date": "2026-10-08", "time": "21:20", "shift": "Night works", "controller": "ATSEP-04", "position": "Radome (alignment)", "score": 5, "outcome": "mitigated", "mitigations": ["Rotation schedule adjusted"], "notes": "Fourth night; moved to ground-level checks, ATSEP-07 did the alignment"},
           ]}

# ================================================================ P4 — operations
FRAM = {"functions": [
    {"id": "F1", "name": "Produce radar plots", "type": "Technological", "x": 0, "y": 0, "aspects": {"Output": ["Radar plots"], "Resource": ["Antenna rotation", "Rotary joint"]},
     "variability": {"timing": "Too late", "precision": "Imprecise"}},
    {"id": "F2", "name": "Fuse tracks (SDPS)", "type": "Technological", "x": 330, "y": 0, "aspects": {"Input": ["Radar plots", "ADS-B reports"], "Output": ["Tracks on display"]},
     "variability": {"timing": "On time", "precision": "Imprecise"}},
    {"id": "F3", "name": "Monitor radar performance", "type": "Human", "x": 0, "y": 230, "aspects": {"Input": ["Radar plots"], "Output": ["Performance status"], "Control": ["Thresholds"]},
     "variability": {"timing": "Too late", "precision": "Imprecise"}},
    {"id": "F4", "name": "Decide sector configuration and minimum", "type": "Organisational", "x": 330, "y": 230, "aspects": {"Input": ["Performance status", "Anomaly reports"], "Output": ["Minimum in force"]},
     "variability": {"timing": "Too late", "precision": "Acceptable"}},
    {"id": "F5", "name": "Plan and provide separation", "type": "Human", "x": 660, "y": 120,
     "aspects": {"Input": ["Tracks on display"], "Control": ["Minimum in force"], "Output": ["Clearances"], "Precondition": ["Position verified"]},
     "variability": {"timing": "On time", "precision": "Imprecise"}},
    {"id": "F6", "name": "Report track anomalies", "type": "Human", "x": 660, "y": 340, "aspects": {"Input": ["Tracks on display"], "Output": ["Anomaly reports"]},
     "variability": {"timing": "Not at all", "precision": "Imprecise"}},
    {"id": "F7", "name": "Verify positions by RT (work-as-done)", "type": "Human", "x": 990, "y": 230, "aspects": {"Input": ["Tracks on display"], "Output": ["Position verified"], "Time": ["Clearances"]},
     "variability": {"timing": "Too late", "precision": "Acceptable"}},
]}

BBN_NET = {"nodes": [
    {"id": "RJ", "label": "Rotary joint worn", "states": ["yes", "no"], "parents": [], "cpt": [0.10, 0.90]},
    {"id": "EN", "label": "Encoder fault", "states": ["yes", "no"], "parents": [], "cpt": [0.05, 0.95]},
    {"id": "IF", "label": "FRUIT / interference", "states": ["yes", "no"], "parents": [], "cpt": [0.15, 0.85]},
    {"id": "RF", "label": "New reflecting structure", "states": ["yes", "no"], "parents": [], "cpt": [0.10, 0.90]},
    {"id": "PD", "label": "Pd drop in one sector", "states": ["yes", "no"], "parents": ["RJ", "IF"],
     "cpt": [[[0.90, 0.10], [0.70, 0.30]], [[0.40, 0.60], [0.03, 0.97]]]},
    {"id": "AZ", "label": "Azimuth bias > 0.1°", "states": ["yes", "no"], "parents": ["EN", "RJ"],
     "cpt": [[[0.95, 0.05], [0.90, 0.10]], [[0.20, 0.80], [0.02, 0.98]]]},
    {"id": "FT", "label": "False targets increase", "states": ["yes", "no"], "parents": ["RF", "IF"],
     "cpt": [[[0.95, 0.05], [0.85, 0.15]], [[0.50, 0.50], [0.05, 0.95]]]},
    {"id": "GC", "label": "Mode C garbling increase", "states": ["yes", "no"], "parents": ["IF"], "cpt": [[0.70, 0.30], [0.05, 0.95]]},
]}
BBN_EVIDENCE = {"PD": "yes", "AZ": "yes", "FT": "yes", "GC": "no"}

# ================================================================ P5 — occurrence investigation
ORC_OCC = [
    {"id": "OCC-RDR-01", "title": "Coasting track hid AAA101 converging with BBB202 at FL190; STCA late; avoiding action; 3.1 NM / 0 ft",
     "outcome": "Catastrophic accident", "barriers": "Limited", "severity_class": "B",
     "rat": {"separation": "50_75", "closure": "medium", "detection": "late", "planning": "inadequate", "execution": "correct",
             "ground_safety_net": "triggered", "recovery": "correct", "airborne_safety_net": "na"},
     "notes": "Investigated (ATSB method and SOAM)."},
    {"id": "OCC-RDR-02", "title": "Reflected false target near CCC303; controller gave unnecessary avoiding action", "outcome": "No accident outcome", "barriers": "Effective",
     "severity_class": "", "rat": {}, "notes": "Trend item: false targets after the new tower"},
    {"id": "OCC-RDR-03", "title": "Garbled Mode C showed DDD404 at FL170 instead of FL190; detected at read-back", "outcome": "Catastrophic accident", "barriers": "Effective",
     "severity_class": "", "rat": {}, "notes": "Trend item: Mode C garbling (FRUIT)"},
]


def _it(text, rating, source, etype="tangible", relevance="direct", comments=""):
    return {"text": text, "rating": rating, "source": source, "etype": etype, "relevance": relevance, "comments": comments, "expectation": ""}


def _t(items, conclusion, probability, summary="", target=None):
    t = {"items": [dict(i, id=f"i{k + 1}") for k, i in enumerate(items)], "conclusion": conclusion, "probability": probability, "summary": summary}
    if target is not None:
        t["target"] = target
    return t


def _a(aid, kind, org, desc, hierarchy, status="proposed", target="", ref="proposed (NAVRAP example)", classes=()):
    return {"id": aid, "kind": kind, "organisation": org, "description": desc, "hierarchy": hierarchy, "status": status, "classes": list(classes),
            "notified_on": "", "target_date": target, "ref": ref, "log": []}


ATSB_EVENTS = [
    ("2026-06-01", "", "Monthly flight-check data first show Pd below 98 % in the 030°–090° sector; no threshold exists, no action", "Performance data (retrospective)", "Maintenance", True, "RC", "F6"),
    ("2026-07-15", "", "A telecommunication tower 1.2 km north-east of the radar site is commissioned", "Site survey", "Environment", False, "", ""),
    ("2026-08-21 14:02", "", "AAA101 (not ADS-B equipped) enters E3 at FL190 north-east bound", "SDPS recording", "Aircraft", False, "", ""),
    ("2026-08-21 14:05", "", "The track of AAA101 coasts for three scans (36 s) and drifts from the aircraft's actual turn", "SDPS recording; radar plot data", "System", True, "TFM", "F2"),
    ("2026-08-21 14:05", "", "The controller plans BBB202's climb to FL190 behind the displayed position of AAA101", "RT recording; interview", "ATC", True, "IA", "F3"),
    ("2026-08-21 14:06", "", "The track of AAA101 updates and jumps 1.8 NM toward BBB202", "SDPS recording", "System", False, "", ""),
    ("2026-08-21 14:06", "", "STCA alerts 32 s before the closest point of approach", "System log", "ATC", True, "PC", "F10"),
    ("2026-08-21 14:06", "", "The controller instructs BBB202 to turn right 40 degrees, avoiding action", "RT recording", "ATC", True, "PA", "F11"),
    ("2026-08-21 14:07", "", "Separation reduces to 3.1 NM at FL190 (5 NM required)", "Radar replay", "Aircraft", False, "", ""),
    ("2026-08-21 14:20", "", "The controller files an occurrence report; the supervisor informs the ATSEP", "Occurrence report", "ATC", False, "", ""),
    ("2026-08-25", "", "Inspection finds the rotary joint worn beyond its hours limit and encoder bearing play", "Maintenance report", "Maintenance", False, "", ""),
]


def atsb_factors() -> list[dict]:
    F = []

    def add(**k):
        F.append({"further": True, "codes": [], "description": "", "actions": [], **k})
    add(id="F1", title="Separation between AAA101 and BBB202 reduced to 3.1 NM at FL190 where 5 NM was required", type="OE",
        existence=_t([_it("Radar replay and ADS-B data of BBB202 give the closest point of approach", "supports", "Radar replay")], "supported", "VC"),
        influence=_t([_it("The infringement is the occurrence", "supports", "Radar replay")], "supported", "VC", target="occurrence"))
    add(id="F2", title="The track of AAA101 coasted for three scans and the tracker's extrapolation diverged from the aircraft's turn", type="TFM",
        codes=["T2"], functional_area="Facilities maintenance (CNS/ATM)", actions=[_a("A6", "org", "CNS engineering", "Replace the rotary joint and azimuth encoder; re-align and verify registration", "elimination", status="closed", target="2026-10-12", ref="safety action taken")],
        description="Plot data show missed detections of AAA101 in three consecutive scans at azimuth 052°; the rotary joint was later found worn.",
        existence=_t([_it("Plot data: no plots for AAA101 at 14:05:12, 14:05:24, 14:05:36", "supports", "Radar plot data"),
                      _it("Rotary joint worn beyond hours limit", "supports", "Maintenance report 25 August", relevance="circumstantial")], "supported", "VL"),
        influence=_t([_it("The displayed position was 1.8 NM from the actual position when the plan was made", "supports", "Radar replay vs ADS-B of BBB202 and FDR of AAA101")],
                     "supported", "VL", target="F3"))
    add(id="F3", title="The controller planned the climb of BBB202 on the displayed (coasted) position of AAA101", type="IA",
        codes=["I3.1"], role="Air traffic controller", error_type="information",
        actions=[_a("A7", "org", "ACC unit chief", "Briefing and recurrent training: verify the position of non-ADS-B aircraft by RT when a track coasts before using it for separation", "administrative")],
        rationale="The coasting symbol differs from a normal track only by a small mark; tracks had been 'jumpy' for weeks and usually recovered; no degraded mode was in force, so 5 NM on the display was the normal practice.",
        existence=_t([_it("Climb clearance at 14:05:40 with 5.5 NM displayed spacing", "supports", "RT recording; radar replay"),
                      _it("Controller interview", "supports", "Interview", "testimonial")], "supported", "VC"),
        influence=_t([_it("With the true position the climb would not have been issued", "supports", "Radar replay", relevance="circumstantial")], "supported", "VL", target="F1"))
    add(id="F4", title="The radar's probability of detection between 030° and 090° had degraded to about 94 %", type="LC",
        codes=["L6.3"], functional_area="Facilities maintenance (CNS/ATM)", sufficiency_note="Explained by the worn rotary joint (F2 evidence) and by the missing performance thresholds (F6).",
        actions=[_a("A8", "org", "CNS engineering", "Declare degraded mode whenever Pd < 97 % in any 60° sector until repaired (see A1, A3)", "administrative")],
        existence=_t([_it("Performance analysis of August data: Pd 94.1 % in 030°–090°", "supports", "Performance report")], "supported", "VC"),
        influence=_t([_it("Lower Pd makes multi-scan coasting more likely", "supports", "Radar specialist", "testimonial", "circumstantial")], "supported", "L", target="F2"))
    add(id="F5", title="AAA101 was not ADS-B equipped, so no second source could correct the coasted track", type="LC",
        codes=["L3.6"], functional_area="Air traffic control", sufficiency_note="ADS-B carriage below FL245 is not mandated; outside AirNav's control.",
        actions=[_a("A9", "recommendation", "DGCA", "Consider an ADS-B carriage requirement below FL245 in the eastern FIR", "administrative", ref="NAVRAP proposal to the regulator")],
        existence=_t([_it("Flight plan equipment field and SDPS sensor data", "supports", "Flight plan; SDPS")], "supported", "VC"),
        influence=_t([_it("ADS-B updates would have kept the fused track on the aircraft", "supports", "SDPS specialist", "testimonial", "circumstantial")], "supported", "L", target="F2"))
    add(id="F6", title="Radar monitoring raised alarms for hard failures only; there were no thresholds for detection probability or azimuth bias", type="RC",
        codes=["R6.3", "R1.4"], functional_area="Facilities maintenance (CNS/ATM)", control_function="preventive",
        safety_issue=True, issue_owner="CNS engineering", issue_status="pending",
        existence=_t([_it("RMM configuration: no performance thresholds", "supports", "RMM configuration"),
                      _it("Maintenance manual: performance analysis 'as required'", "supports", "Maintenance manual")], "supported", "VC"),
        influence=_t([_it("A threshold at 97 % would have flagged the June data", "supports", "Performance data (retrospective)", relevance="circumstantial")], "supported", "VL", target="F4"),
        risk={"scheme": "airnav", "worst_possible": "Undetected degradation leads to a mid-air collision.",
              "existing_controls": [{"text": "Daily ATSEP check", "effectiveness": "Does not reveal gradual Pd loss"}, {"text": "ACAS II", "effectiveness": "Independent last barrier"}],
              "worst_credible": "Loss of separation with a serious incident while degradation persists for weeks.",
              "consequence": "B", "consequence_justification": "Hazardous: serious incident with a small margin.", "likelihood": 3,
              "likelihood_justification": "Remote: degradation episodes occur every few years per radar; without thresholds they last months."},
        actions=[_a("A1", "org", "CNS engineering", "Monthly radar performance analysis with thresholds (Pd ≥ 97 % per 60° sector, bias ≤ 0.1°, false targets) and automatic RMM alerts", "engineering", target="2026-12-31"),
                 _a("A2", "org", "Head of CNS maintenance", "Hours-based replacement of rotary joints and encoders; critical spares", "engineering")],
        evaluation={"residual": {"consequence": "B", "likelihood": 2}, "alarp": True,
                    "practicability": {"risk": "Significant", "knowledge": "Radar performance analysis tools are standard practice", "means": "Existing flight-check and plot data", "cost": "Low"}})
    add(id="F7", title="No procedure defined criteria for declaring degraded surveillance or the separation to apply", type="RC",
        codes=["R3"], functional_area="Air traffic control", control_function="preventive", sufficiency_note="The Manual of ATS was written for total radar failure; degraded performance was never assessed as a hazard (see F6).",
        safety_issue=True, issue_owner="ATS standards", issue_status="pending",
        existence=_t([_it("Manual of ATS covers total radar failure only", "supports", "Manual of ATS §8")], "supported", "VC"),
        influence=_t([_it("With a declaration, 8 NM would have applied in the NE quadrant", "supports", "Investigation team", "testimonial", "circumstantial")], "supported", "L", target="F3"),
        risk={"scheme": "airnav", "worst_possible": "Controllers apply radar minima on degraded data across a sector.",
              "existing_controls": [{"text": "Supervisor judgement", "effectiveness": "Inconsistent"}],
              "worst_credible": "Repeated losses of separation during a degradation episode.", "consequence": "B",
              "consequence_justification": "Hazardous.", "likelihood": 3, "likelihood_justification": "Remote."},
        actions=[_a("A3", "org", "ATS standards", "Degraded-surveillance procedure with criteria, standard declaration form, CWP status banner and 8 NM minimum", "administrative", target="2026-11-30")],
        evaluation={"residual": {"consequence": "B", "likelihood": 2}, "alarp": True,
                    "practicability": {"risk": "Significant", "knowledge": "Common practice in other ANSPs", "means": "Procedure and HMI banner", "cost": "Low"}})
    add(id="F8", title="The coasting symbol was not visually distinct from an updated track", type="RC",
        codes=["R1.1"], functional_area="Air traffic control", control_function="recovery", sufficiency_note="HMI specification inherited from the 2012 system; no human-factors review of coasting presentation.",
        existence=_t([_it("HMI specification: coasting shown by a 2-pixel mark", "supports", "HMI specification")], "supported", "VC"),
        influence=_t([_it("Controller did not notice the coasting", "supports", "Interview", "testimonial")], "supported", "L", target="F3"),
        actions=[_a("A4", "org", "ATM systems", "Distinct coasting symbol and age-of-update indication", "engineering")])
    add(id="F9", title="Controllers reported track anomalies informally rather than through the occurrence system", type="OI",
        codes=["O1"], functional_area="Air traffic control",
        existence=_t([_it("Nine formal reports June–August vs many verbal complaints", "supports", "Occurrence database; interviews", "testimonial")], "supported", "VL"),
        influence=_t([_it("More reports might have triggered an earlier inspection", "supports", "Investigation team", "testimonial", "circumstantial")], "not_supported", "MLN", target="F6"),
        importance={"passed": True, "justification": "Reporting is how controller-visible degradation reaches maintenance; worth addressing."},
        actions=[_a("A5", "org", "ACC unit chief", "Track-anomaly report category with feedback to ATSEP; SPI S-05", "administrative")])
    add(id="F10", title="STCA alerted 32 seconds before the closest point of approach", type="PC", codes=["R1.4"], functional_area="Air traffic control",
        existence=_t([_it("System log", "supports", "STCA log")], "supported", "VC"),
        influence=_t([_it("The alert prompted the avoiding action", "supports", "RT recording; interview", relevance="circumstantial")], "supported", "VL", target="F11"))
    add(id="F11", title="The controller gave avoiding action immediately after the STCA alert", type="PA", codes=["I3.3"],
        role="Air traffic controller", error_type="action", rationale="Trained response to STCA.",
        existence=_t([_it("RT recording 14:06:40", "supports", "RT recording")], "supported", "VC"),
        influence=_t([_it("Without the turn the aircraft would have passed about 1 NM apart", "supports", "Radar replay extrapolation", relevance="circumstantial")], "supported", "VL", target="occurrence"))
    add(id="F12", title="The controller lost situational awareness", type="IA", further=False,
        exclusion_reason="Restates the problem (e.g. 'loss of situation awareness')", further_justification="Restates F3; the reasons are F2, F4–F8.")
    return F


ATSB_REPORT = {
    "report_no": "NAVRAP-INV-OCC-RDR-01", "prepared_by": "Safety & Quality — illustrative NAVRAP worked example", "status": "Example (illustrative, not a real occurrence)",
    "consequences": "No injuries or damage. Serious incident: separation 3.1 NM / 0 ft against 5 NM required. No environmental impact.",
    "personnel": [{"role": "E3 executive controller", "details": "9 years' experience; valid rating; second hour of an afternoon shift"},
                  {"role": "ACC supervisor", "details": "Aware of informal reports of 'jumpy tracks'; no declaration in force"},
                  {"role": "ATSEP on duty", "details": "Daily checks completed; no RMM alarm"}],
    "assets": [{"item": SITE, "details": "Mode S MSSR, 12 s scan, single radar coverage below FL150 in the NE quadrant; rotary joint beyond hours limit"},
               {"item": "SDPS tracker", "details": "Multi-sensor tracker; coasting up to 5 scans"},
               {"item": "Aircraft", "details": "AAA101 (not ADS-B equipped) and BBB202 (ADS-B equipped), both at FL190 after the climb"}],
    "environment": "Daytime, visual meteorological conditions; moderate traffic (14 flights in E3).",
    "immediate_actions": ["Avoiding action to BBB202; traffic information to both aircraft",
                          "Supervisor applied 10 NM in the NE quadrant until the end of the day (informal)",
                          "SDPS and radar plot recordings secured; ATSEP performance analysis requested"],
    "interviews": [{"person": "E3 controller", "summary": "Tracks had been jumpy for weeks; usually they recovered. Did not see the coasting mark."},
                   {"person": "ATSEP", "summary": "No alarms; daily checks normal; performance analysis not routinely done."}],
    "layer_notes": {"E": "Control of the separation was lost when the coasted track of AAA101 updated 1.8 NM from where it was displayed.",
                    "I": "The plan was correct for the displayed picture; the display was wrong.",
                    "L": "Detection probability had degraded in the very sector where AAA101 flew, and no second sensor covered it.",
                    "R": "Monitoring, procedure and HMI defences were all absent or weak; only STCA and the controller's response worked.",
                    "O": "The maintenance regime and the reporting culture did not turn weeks of visible degradation into action."},
    "attachments": [], "source": "Illustrative occurrence for NAVRAP DEMO-08",
}


def atsb_model() -> dict:
    ev = [{"id": f"E{k + 1}", "start": s, "end": e, "title": t, "comments": "", "source": src, "theme": th, "display": True,
           "safety_factor": sf, "sf_type": st, "factor_id": fid} for k, (s, e, t, src, th, sf, st, fid) in enumerate(ATSB_EVENTS)]
    return {"occurrence": {"ref": "OCC-RDR-01", "date": "2026-08-21", "occurrence_type": "Loss of separation (serious incident)",
                           "title": "Loss of separation in Sector E3 after a coasting radar track (illustrative)", "location": SECTOR, "time": "14:07 LT",
                           "operator": "AirNav (ATS, CNS)", "summary": "A coasting track hid the converging AAA101 from the E3 controller, who climbed BBB202 to FL190. "
                                                                        "STCA alerted late and avoiding action restored separation at 3.1 NM."},
            "events": ev, "factors": atsb_factors(), "key_findings": [], "report": ATSB_REPORT,
            "review": {k: True for k in ("sufficiency", "missing", "enhance", "sense", "fair_individual", "fair_org", "organised", "no_merge", "bias")},
            "stop_rule": "Stopped at the ANSP's maintenance regime and procedures — both within AirNav's control."}


INV = {
    "occurrence": {"ref": "OCC-RDR-01", "date": "2026-08-21", "location": SECTOR,
                   "summary": "A coasting radar track hid AAA101 from the controller, who climbed BBB202 into conflict; STCA alerted 32 s before CPA; 3.1 NM / 0 ft."},
    "soam": {
        "barriers": [{"text": "Radar performance thresholds and alarms", "category": "Detection", "status": "absent", "bowtie_link": None},
                     {"text": "Degraded-surveillance declaration and 8 NM", "category": "Restriction", "status": "absent", "bowtie_link": None},
                     {"text": "Distinct coasting symbol", "category": "Awareness", "status": "failed", "bowtie_link": None},
                     {"text": "ADS-B second source", "category": "Detection", "status": "failed", "bowtie_link": None},
                     {"text": "STCA alert", "category": "Detection", "status": "effective", "bowtie_link": None},
                     {"text": "Controller avoiding action", "category": "Control and recovery", "status": "effective", "bowtie_link": None}],
        "human": ["Controller planned the climb on the coasted position", "ATSEP saw no alarm and did not analyse performance"],
        "contextual": [{"category": "Workplace conditions", "text": "Display tracks 'jumpy' for weeks; normalised"},
                       {"category": "Human performance limitations", "text": "Low salience of the coasting mark"}],
        "orgfactors": [{"category": "Maintenance management (MM)", "text": "Hard-failure-only monitoring; no hours-based replacement of the rotary joint"},
                       {"category": "Policies and procedures (PP)", "text": "No degraded-surveillance procedure"},
                       {"category": "Communication (CO)", "text": "Track-anomaly reports informal; no loop to ATSEP"},
                       {"category": "Equipment and infrastructure (EI)", "text": "Single radar coverage below FL150 in NE quadrant"}],
        "actions": [{"text": "Performance thresholds and monthly analysis", "addresses": "Radar performance thresholds and alarms", "owner": "CNS engineering"},
                    {"text": "Degraded-surveillance procedure", "addresses": "Policies and procedures (PP)", "owner": "ATS standards"},
                    {"text": "Distinct coasting symbol", "addresses": "Distinct coasting symbol", "owner": "ATM systems"}]},
    "hfacs": {"selected": {"Perceptual errors": "Coasted position taken as actual", "Technological environment": "Degraded radar; low-salience coasting symbol",
                           "Failed to correct a known problem": "Jumpy tracks known for weeks", "Organisational process": "Maintenance regime and no degraded-mode procedure"}},
    "tripod": {"events": [{"id": "EV1", "agent": "Converging aircraft AAA101", "object": "BBB202 climbing to FL190", "event": "Loss of separation (3.1 NM)",
                           "barriers": [{"barrier": "Displayed position of AAA101", "status": "failed", "immediate_cause": "Track coasted and diverged",
                                         "precondition": "Pd ≈ 94 % in the sector; no ADS-B", "underlying_cause": "Rotary joint wear not detected", "brf": "Maintenance management (MM)"},
                                        {"barrier": "Degraded-mode separation", "status": "missing", "immediate_cause": "", "precondition": "",
                                         "underlying_cause": "No procedure", "brf": "Procedures (PR)"},
                                        {"barrier": "STCA", "status": "effective", "immediate_cause": "", "precondition": "", "underlying_cause": "", "brf": ""}]}]},
}

# ================================================================ P6 — monitoring and argument
SPIS = _rows("S", [
    {"indicator": "Probability of detection per 60° azimuth sector (worst sector, %)", "type": "leading", "linked": "PB2 performance analysis", "baseline": "99.6", "target": "≥ 98", "alert": "< 97 → declare degraded mode",
     "frequency": "monthly", "owner": "CNS engineering", "current": "98.9", "status": "green", "escalation": "Degraded-mode declaration; inspection within 7 days"},
    {"indicator": "Azimuth bias against ADS-B (°)", "type": "leading", "linked": "PB2; registration", "baseline": "0.03", "target": "≤ 0.05", "alert": "> 0.1",
     "frequency": "monthly", "owner": "CNS engineering", "current": "0.04", "status": "green", "escalation": "Re-align; check encoder"},
    {"indicator": "False / reflected targets per 1,000 scans", "type": "leading", "linked": "PB3 reflector map", "baseline": "0.5", "target": "≤ 1", "alert": "> 3",
     "frequency": "monthly", "owner": "CNS engineering", "current": "1.4", "status": "amber", "escalation": "Update reflector map; survey new structures"},
    {"indicator": "ADS-B/radar position mismatch alerts per 1,000 flights", "type": "leading", "linked": "PB6 comparison alert; security", "baseline": "—", "target": "≤ 2", "alert": "> 5 or cluster",
     "frequency": "weekly", "owner": "ATM systems", "current": "1.1", "status": "green", "escalation": "Check radar and possible spoofing"},
    {"indicator": "Track-anomaly reports by controllers per month", "type": "leading", "linked": "PB7 reporting", "baseline": "3", "target": "reported, not suppressed", "alert": "≥ 3 per watch",
     "frequency": "monthly", "owner": "ACC unit chief", "current": "4", "status": "green", "escalation": "Supervisor-initiated declaration criteria"},
    {"indicator": "Time from threshold exceedance to degraded-mode declaration (h)", "type": "leading", "linked": "PB4 declaration", "baseline": "n/a", "target": "≤ 2", "alert": "> 8",
     "frequency": "per event", "owner": "ACC supervisor", "current": "—", "status": "", "escalation": "Review declaration process"},
    {"indicator": "STCA alerts late (< 40 s) or nuisance, per 1,000 flights", "type": "leading", "linked": "RB2 STCA", "baseline": "0.8", "target": "≤ 1", "alert": "> 2",
     "frequency": "monthly", "owner": "ATM systems", "current": "0.9", "status": "green", "escalation": "STCA tuning; check surveillance"},
    {"indicator": "1090 MHz FRUIT rate at the site (replies/s)", "type": "leading", "linked": "CCA P-01 interference", "baseline": "8,000", "target": "≤ 10,000", "alert": "> 15,000",
     "frequency": "quarterly", "owner": "CNS engineering", "current": "11,500", "status": "amber", "escalation": "Interrogator coordination with the military"},
    {"indicator": "Losses of separation with a surveillance factor (ERC ≥ 50)", "type": "lagging", "linked": "Bowtie C1", "baseline": "1 (Aug 2026)", "target": "0", "alert": "≥ 1",
     "frequency": "per event", "owner": "Safety & Quality", "current": "0", "status": "green", "escalation": "Investigation; review of thresholds"},
])


def _gsn(ids: dict):
    def sol(sid, parent, text, key):
        return {"id": sid, "type": "solution", "parent": parent, "text": text, "evidence": {"kind": "study", "ref": ids.get(key)}}
    return {"nodes": [
        {"id": "G0", "type": "goal", "text": f"Operation of {SECTOR} with the degrading {SITE}, its refurbishment and its return to service are acceptably safe"},
        {"id": "C1", "type": "context", "parent": "G0", "text": SCENARIO[:240] + "…"},
        {"id": "C2", "type": "context", "parent": "G0", "text": "Hazard types: technical, human, procedural, organisational, environmental, security, occupational"},
        {"id": "A1", "type": "assumption", "parent": "G0", "text": "ACAS II carriage and use as required by Indonesian regulations"},
        {"id": "S0", "type": "strategy", "parent": "G0", "text": "Argue over the six lifecycle phases of the change"},
        {"id": "G1", "type": "goal", "parent": "S0", "text": "P1: the hazards of degraded operation are identified and the decision to refurbish is justified"},
        sol("Sn1", "G1", "HAZID", "hazid"), sol("Sn2", "G1", "FHA with safety objectives", "fha"), sol("Sn3", "G1", "Bowtie", "bowtie"), sol("Sn4", "G1", "Expert judgement", "sej"),
        {"id": "G2", "type": "goal", "parent": "S0", "text": "P2: the degraded mode and the refurbished chain meet the safety objectives"},
        sol("Sn5", "G2", "FMEA", "fmea"), sol("Sn6", "G2", "FTA with residual case", "fta"), sol("Sn7", "G2", "Common cause analysis", "cca"), sol("Sn8", "G2", "RBD and Markov", "rbd"),
        sol("Sn9", "G2", "STPA", "stpa"), sol("Sn10", "G2", "HAZOP", "hazop"), sol("Sn11", "G2", "Security risk", "sec"), sol("Sn12", "G2", "CRM of parallel routes", "crm"),
        sol("Sn13", "G2", "LOPA", "lopa"), sol("Sn14", "G2", "ETA", "eta"), sol("Sn15", "G2", "HTA of the degraded mode", "hta"), sol("Sn16", "G2", "HRA", "hra"),
        {"id": "G3", "type": "goal", "parent": "S0", "text": "P3: the works are safe for workers and the transition is controlled"},
        sol("Sn17", "G3", "JHA", "jha"), sol("Sn18", "G3", "SWIFT", "swift"), sol("Sn19", "G3", "Real-time simulation", "sim"), sol("Sn20", "G3", "ATSEP fatigue", "fatigue"),
        {"id": "G4", "type": "goal", "parent": "S0", "text": "P4: work-as-done during residual degradation is understood and supported"},
        sol("Sn21", "G4", "FRAM", "fram"), sol("Sn22", "G4", "BBN diagnosis", "bbn"),
        {"id": "G5", "type": "goal", "parent": "S0", "text": "P5: lessons from occurrences during the degradation are learned"},
        sol("Sn23", "G5", "ERC/RAT", "orc"), sol("Sn24", "G5", "ATSB analysis", "atsb"), sol("Sn25", "G5", "SOAM/HFACS/Tripod", "inv"),
        {"id": "G6", "type": "goal", "parent": "S0", "text": "P6: performance is monitored with alert levels that trigger the degraded mode"},
        sol("Sn26", "G6", "SPI register", "spi"),
        {"id": "G7", "type": "goal", "parent": "S0", "undeveloped": True, "text": "Residual risks accepted by the appropriate authority (hazard log RDR-01 … RDR-12)"},
        {"id": "J1", "type": "justification", "parent": "S0", "text": "Methods chosen per phase and hazard type (Manual Appendix G); wildlife, organisational function map and the expert system not applicable"},
    ]}


# ================================================================ hazard log
HAZARDS = [  # ref, title, type, phase key, source key, row, init S/L, residual S/L, controls(text, side, ver, crit), rationale, owner
    ("RDR-01", "Undetected erroneous position of an aircraft displayed in Sector E3", "TEC", "fta", "TOP", ("B", 4), ("B", 2),
     [("Monthly performance analysis with thresholds", "prevention", "planned", True), ("ADS-B/radar comparison alert", "recovery", "planned", True),
      ("Increased separation when degraded", "prevention", "planned", True)],
     "FTA about 1e-5 per flight hour in the degraded state; about 1e-6 with performance thresholds — still above the FHA objective, so 8 NM in the declared area is required.", "CNS engineering"),
    ("RDR-02", "Track drops and coasting in the NE quadrant below FL150", "TEC", "fmea", "FM-01", ("C", 4), ("C", 2),
     [("Rotary joint and encoder replacement", "prevention", "planned", True), ("Distinct coasting symbol", "recovery", "planned", False)],
     "FMEA: rotary joint RPN 384; replacement removes the cause; coasting symbol helps detection.", "CNS engineering"),
    ("RDR-03", "Controllers apply 5 NM on degraded tracks without knowing", "HUM", "stpa", "UCA-2", ("B", 3), ("B", 2),
     [("Degraded-mode declaration with criteria and CWP banner", "prevention", "planned", True)], "STPA UCA-1/2; HRA T1 0.09.", "ACC unit chief"),
    ("RDR-04", "No criteria or procedure to declare degraded surveillance", "PRO", "hazop", "HP-06", ("B", 4), ("B", 2),
     [("Degraded-surveillance procedure (HTA)", "prevention", "planned", True)], "HAZOP N2; HTA tasks 2–5.", "ATS standards"),
    ("RDR-05", "STCA unreliable on degraded tracks (common mode with the controller)", "TEC", "cca", "CM-01", ("B", 3), ("B", 3),
     [("STCA not credited as an IPL", "recovery", "existing-verified", False), ("ACAS II", "recovery", "existing-verified", True)],
     "CCA CM-01; LOPA rejects STCA as an IPL; ETA B2 = 0.5.", "ATM systems"),
    ("RDR-06", "Reflected false targets and FRUIT garbling", "ENV", "hazid", "HZ-06", ("C", 3), ("C", 2),
     [("Reflector map update", "prevention", "planned", False), ("Interrogator coordination", "prevention", "planned", False)],
     "BBN: interference and reflection explain the false-target symptom.", "CNS engineering"),
    ("RDR-07", "Spoofed ADS-B undetected while the radar cross-check is degraded", "SEC", "sec", "SR-01", ("B", 3), ("B", 2),
     [("ADS-B plausibility checks", "prevention", "planned", True)], "Security risk SR-01.", "IT security"),
    ("RDR-08", "Gradual degradation not detected by the maintenance regime", "ORG", "atsb", "F6", ("B", 3), ("B", 2),
     [("Performance thresholds; hours-based replacement", "prevention", "planned", True), ("Track-anomaly reporting with feedback", "prevention", "planned", False)],
     "ATSB safety issue F6; Markov: monitoring cuts degraded time from ≈ 2 months to ≈ 1 week.", "Head of CNS maintenance"),
    ("RDR-09", "Worker injury during rotary joint and encoder replacement", "OHS", "jha", "S-03", ("B", 3), ("B", 1),
     [("LOTO of drive and transmitters", "prevention", "existing-verified", True), ("Fall arrest and rescue plan", "prevention", "existing-verified", True)],
     "JHA steps S-02 to S-06.", "ATSEP team leader"),
    ("RDR-10", "Radar returned to service misaligned after refurbishment", "PRO", "swift", "W-02", ("B", 2), ("B", 1),
     [("Registration against ADS-B as a hold point", "prevention", "planned", True)], "SWIFT W-02; STPA UCA-4; HRA T3 0.02.", "Radar engineer"),
    ("RDR-11", "Workload and capacity during radar outage windows", "HUM", "sim", "M1", ("C", 3), ("C", 2),
     [("Capacity 22/h during outages; flow measures", "prevention", "planned", True)], "RTS: ISA 3.76 (≤ 4.0), R/T 59 %, 22/h handled; one loss of separation in 8 runs.", "ACC unit chief"),
    ("RDR-12", "ATSEP fatigue during compressed night works", "HUM", "fatigue", "", ("C", 3), ("C", 2),
     [("Six 8-hour nights instead of four 12-hour nights", "prevention", "planned", False)], "Three-process model: no time at KSS ≥ 7 on 8-hour nights.", "Head of CNS maintenance"),
]
ACTIONS = [
    ("Implement monthly radar performance analysis with thresholds and RMM alerts", "CNS engineering", "RDR-08", 60),
    ("Publish the degraded-surveillance procedure with declaration form and CWP banner", "ATS standards", "RDR-04", 45),
    ("Implement the ADS-B/radar position comparison alert", "ATM systems", "RDR-01", 120),
    ("Make the coasting symbol distinct and show time since last update", "ATM systems", "RDR-02", 90),
    ("Update the reflector map and coordinate interrogation rates with the military", "CNS engineering", "RDR-06", 30),
    ("Make registration against ADS-B a go/no-go hold point in the return-to-service procedure", "Radar engineer", "RDR-10", 14),
    ("Introduce a track-anomaly report category with feedback to ATSEP", "ACC unit chief", "RDR-08", 30),
    ("Use level allocation on routes W-31/W-33 while the radar is degraded or out (CRM)", "ACC unit chief", "RDR-01", 7),
]


# ================================================================ build and seed
def _results():
    from .engines import atsb as atsb_engine
    lat = CRM_MODEL["lateral"]
    other = {k: lat[k] for k in ("lx", "lz", "sx", "dv", "v", "zdot", "ydot_sy")} | {"pz0": lat["pz0"], "ey_same": lat["ey_same"], "ey_opp": lat["ey_opp"], "tls": lat["tls"]}
    py = crm_engine.lateral_overlap(lat["spacing"], lat["ly"], lat["model"], lat["scale"])
    crm_lat = crm_engine.lateral(py_sy=py, pz0=lat["pz0"], lx=lat["lx"], ly=lat["ly"], lz=lat["lz"], sx=lat["sx"], ey_same=lat["ey_same"], ey_opp=lat["ey_opp"],
                                 dv=lat["dv"], v=lat["v"], zdot=lat["zdot"], ydot_sy=lat["ydot_sy"], tls=lat["tls"])
    crm_lat.update(curve=crm_engine.spacing_curve(lat["ly"], lat["model"], lat["scale"], lat["spacings"], other),
                   minimum_spacing=crm_engine.minimum_spacing(lat["ly"], lat["model"], lat["scale"], other), py_sy=py, spacing=lat["spacing"])
    fr = fat_engine.run(FAT_SLEEP_12, FAT_12, 0, 156)
    fr8 = fat_engine.run(FAT_SLEEP_8, FAT_8, 0, 156)
    return {
        "sej": {"classical": sej_engine.classical(SEJ_EXPERTS, SEJ_ITEMS), "delphi": sej_engine.delphi(DELPHI)},
        "fta": {**fta_engine.analyse(FTA_TREE), "residual": fta_engine.analyse(FTA_TREE_RESIDUAL)},
        "rbd": {"rbd": rbd_engine.rbd(RBD), "markov": rbd_engine.markov(**{k: MARKOV[k] for k in ("states", "transitions")}),
                "markov_monitored": rbd_engine.markov(**{k: MARKOV_MONITORED[k] for k in ("states", "transitions")})},
        "crm": {"lateral": crm_lat},
        "lopa": lopa_engine.analyse(LOPA["initiating"]["frequency"], LOPA["modifiers"], LOPA["safeguards"], LOPA["target"]),
        "eta": eta_engine.analyse(ETA),
        "hra": {"tasks": [{"id": t["id"], **hra_engine.assess(t["library"], t["gtt"], t["epcs"])} for t in HRA_TASKS]},
        "sim": {"measures": sim_engine.analyse(SIM_MEASURES)},
        "fatigue": {"duties": fr["duties"], "duties_8h": fr8["duties"], "engine_version": fr["engine_version"],
                    "samn_perelli": fat_engine.samn_perelli(FATIGUE["sp_ratings"])},
        "bbn": bbn_engine.query(BBN_NET, evidence=BBN_EVIDENCE),
        "orc": {"occurrences": [{"id": o["id"], "erc": orc_engine.erc(o["outcome"], o["barriers"]), **({"rat": orc_engine.rat(o["rat"])} if o["rat"] else {})} for o in ORC_OCC]},
        "atsb": atsb_engine.analyse(atsb_model()),
    }


def models() -> dict:
    return {
        "hazid": {"rows": HAZID}, "fha": {"rows": FHA}, "bowtie": _bowtie(),
        "sej": {"experts": SEJ_EXPERTS, "items": SEJ_ITEMS, "alpha": 0.0,
                "delphi": {"question": "Probability that a controller does not detect a 2 NM track jump within one scan (moderate traffic)", "rounds": DELPHI}},
        "fmea": {"rows": FMEA}, "fta": {"tree": FTA_TREE, "residual_tree": FTA_TREE_RESIDUAL}, "cca": CCA,
        "rbd": {"rbd": RBD, "markov": MARKOV, "markov_monitored": MARKOV_MONITORED}, "stpa": STPA, "hazop": HAZOP, "sec": {"rows": SEC},
        "crm": CRM_MODEL, "lopa": LOPA, "eta": ETA, "hta": HTA, "hra": {"tasks": HRA_TASKS},
        "jha": JHA, "swift": {"rows": SWIFT}, "sim": {"exercise": SIM_EX, "measures": SIM_MEASURES}, "fatigue": FATIGUE,
        "fram": FRAM, "bbn": {"network": BBN_NET, "evidence": BBN_EVIDENCE,
                              "positions": {"RJ": [0, 0], "EN": [220, 0], "IF": [440, 0], "RF": [660, 0], "PD": [110, 200], "AZ": [0, 400], "FT": [550, 200], "GC": [440, 400]}},
        "orc": {"occurrences": [dict(o) for o in ORC_OCC]}, "atsb": atsb_model(), "inv": INV, "spi": {"rows": SPIS},
    }


def coverage() -> list[dict]:
    return [{"phase": ph, "key": k, "method": m, "title": t, "types": ty} for k, ph, m, t, ty in STUDIES]


def description() -> str:
    return (SCENARIO + " Six assessments, one per lifecycle phase; each lists its studies with the hazard types they cover "
            "(TEC technical, HUM human, PRO procedural, ORG organisational, ENV environmental, SEC security, OHS occupational). "
            "Not used: " + "; ".join(f"{n} ({why[0].lower() + why[1:].rstrip('.')})" for n, why in NOT_USED) +
            ". See Manual Appendix G. All names, numbers and events are illustrative.")


def seed_demo_radar(db: Session):
    from .models import Action, Assessment, Control, Hazard, Project, RiskScheme, Study
    if db.query(Project).filter_by(code=CODE).first():
        return
    p = Project(code=CODE, title="Surveillance radar performance degradation — Bukit Sari MSSR (worked example)", change_type="system",
                units=f"{SECTOR}; APP-S; CNS engineering (radar site)", sponsor="Directorate of Operations and Directorate of CNS",
                description=description())
    db.add(p); db.flush()
    rs = db.query(RiskScheme).order_by(RiskScheme.version.desc()).first()
    parts = [{"name": "Safety assessor", "role": "Facilitator"}, {"name": "E3 controllers", "role": "SME"},
             {"name": "ATSEP radar specialist", "role": "SME"}, {"name": "ATM systems engineer", "role": "SME"}]
    assess = {}
    scopes = {
        "P1": "Identify the hazards of operating E3 with a degrading radar, set safety objectives for the surveillance functions and decide on refurbishment.",
        "P2": "Design the degraded-surveillance mode and show that the refurbished surveillance chain and the degraded mode meet the safety objectives.",
        "P3": "Plan the refurbishment works and the outage windows, protect workers and control the return to service.",
        "P4": "Understand how controllers and ATSEP work while residual degradation persists; support fault diagnosis.",
        "P5": "Classify the occurrences during the degradation and investigate OCC-RDR-01.",
        "P6": "Monitor surveillance performance with alert levels and bring the evidence together in a safety argument.",
    }
    for pid, name in PHASES:
        types = sorted({t for k, ph, m, ti, ty in STUDIES if ph == pid for t in ty})
        a = Assessment(project_id=p.id, title=f"{pid} · {name}", created_by="assessor", risk_scheme_version=rs.version if rs else 1,
                       scope=scopes[pid] + " Studies: " + "; ".join(f"{ti.split(' — ')[0]} [{' '.join(ty)}]" for k, ph, m, ti, ty in STUDIES if ph == pid) + ".",
                       environment=f"{SECTOR} and APP-S; {SITE}; ADS-B BS-1…BS-3; Gunung Tinggi MSSR above FL150 (west).",
                       assumptions="Hazard types covered: " + ", ".join(HAZARD_TYPES[t] for t in types) + ". All numbers are illustrative.")
        db.add(a); db.flush(); assess[pid] = a
    M, R, ids = models(), _results(), {}
    for key, ph, method, title, types in STUDIES:
        if key == "gsn":
            continue
        s = Study(assessment_id=assess[ph].id, method=method, title=title, model=M[key], results=R.get(key, {}), participants=parts, template_version="1.0")
        db.add(s); db.flush(); ids[key] = s.id
    hta = db.get(Study, ids["hta"]); hta.model = {**hta.model, "hra_study": ids["hra"]}
    s = Study(assessment_id=assess["P6"].id, method="gsn", title=dict((k, t) for k, _p, _m, t, _ty in STUDIES)["gsn"], model=_gsn(ids), participants=parts)
    db.add(s); db.flush(); ids["gsn"] = s.id
    # link the investigation's barriers to the bowtie
    links = {"Radar performance thresholds and alarms": "PB2", "Degraded-surveillance declaration and 8 NM": "PB4", "ADS-B second source": "PB6",
             "STCA alert": "RB2", "Controller avoiding action": "RB1", "Distinct coasting symbol": "RB1"}
    inv = db.get(Study, ids["inv"]); m = dict(inv.model); so = dict(m["soam"])
    so["barriers"] = [dict(b, bowtie_link=f"{ids['bowtie']}:{links[b['text']]}") if b["text"] in links else b for b in so["barriers"]]
    m["soam"] = so; inv.model = m
    phase_of = {k: ph for k, ph, *_ in STUDIES}
    review = date.today() + timedelta(days=90)
    H = {}
    for ref, title, typ, key, row, (is_, il), (rs_, rl), controls, rat, owner in HAZARDS:
        h = Hazard(ref=ref, title=title, unit=SECTOR if typ != "OHS" else f"{SITE} site", system="Surveillance", owner=owner,
                   assessment_id=assess[phase_of[key]].id, source_study_id=ids[key], source_row=row, initial_severity=is_, initial_likelihood=il,
                   residual_severity=rs_, residual_likelihood=rl, rationale=rat, review_date=review,
                   context=f"Hazard type: {HAZARD_TYPES[typ]} · Phase: {dict(PHASES)[phase_of[key]]}")
        db.add(h); db.flush(); H[ref] = h
        for text, side, ver, crit in controls:
            db.add(Control(hazard_id=h.id, text=text, side=side, verification=ver, critical=crit, kind="procedure"))
    for i, (text, owner, ref, days) in enumerate(ACTIONS, 1):
        db.add(Action(ref=f"RDR-A{i:02d}", text=text, owner=owner, due_date=date.today() + timedelta(days=days), hazard_id=H[ref].id,
                      assessment_id=H[ref].assessment_id, status="open"))
    db.commit()
