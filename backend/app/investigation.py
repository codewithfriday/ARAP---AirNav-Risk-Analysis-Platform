"""Investigation expert system — occurrence categories, ORLIO factor catalogue, thesaurus and the demo case library
(Manual Appendix E). The ATS loss-of-separation cases are ILLUSTRATIVE: written for training, not real occurrences.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

# ------------------------------------------------------------------ categories and mechanisms
CATEGORIES = {
    "ats-los": {
        "name": "ATS — loss of separation",
        "taxonomy": "ADREP/ECCAIRS: ATM — separation minima infringement (MAC/ATM)",
        "mechanisms": [
            {"code": "M1", "label": "Controller clearance or instruction error", "keywords": ["wrong level", "incorrect clearance", "occupied level", "cleared to"]},
            {"code": "M2", "label": "Readback/hearback error not detected", "keywords": ["readback", "hearback", "wrong aircraft", "similar callsign"]},
            {"code": "M3", "label": "Pilot deviation from clearance", "keywords": ["level bust", "deviated", "climbed through", "descended through"]},
            {"code": "M4", "label": "Coordination failure between units or sectors", "keywords": ["coordination", "estimate", "transfer", "letter of agreement"]},
            {"code": "M5", "label": "Conflict not detected (monitoring / workload)", "keywords": ["not detected", "monitoring", "workload", "scan"]},
            {"code": "M6", "label": "Safety-net or system deficiency", "keywords": ["stca", "inhibition", "safety net", "system update"]},
        ],
    },
    "fuel": {
        "name": "Operational — fuel related",
        "taxonomy": "ATSB SIIMS: Operational › Fuel related (level 3 as mechanisms)",
        "mechanisms": [
            {"code": "FC", "label": "Fuel contamination", "keywords": ["water", "contamination", "contaminated"]},
            {"code": "FE", "label": "Fuel exhaustion", "keywords": ["exhaustion", "exhausted", "ran out of fuel", "no usable fuel"]},
            {"code": "FL", "label": "Fuel leaking or venting", "keywords": ["leak", "venting", "vented"]},
            {"code": "LF", "label": "Low fuel", "keywords": ["low fuel", "minimum fuel", "fuel emergency"]},
            {"code": "FS", "label": "Fuel starvation", "keywords": ["starvation", "fuel selector", "tank selected"]},
            {"code": "FO", "label": "Fuel related — other", "keywords": []},
        ],
    },
}


def _f(code, layer, label, keywords):
    return {"code": code, "layer": layer, "label": label, "keywords": keywords}


FACTORS = {
    "ats-los": [
        _f("O-CALLSIGN-MGMT", "O", "Similar-callsign management with operators not in place", ["callsign management", "callsign deconfliction", "similar callsign programme", "similar callsign program"]),
        _f("O-STAFFING", "O", "Staffing or rostering leads to minimum-staffing periods", ["minimum staffing", "staff shortage", "rostered at minimum", "roster planned", "overtime"]),
        _f("O-TRAINING", "O", "Recurrent training does not cover the threat", ["recurrent training", "refresher training", "training programme"]),
        _f("O-CHANGE-MGMT", "O", "System or procedure change not safety assessed", ["change management", "not safety assessed", "configuration management", "system update"]),
        _f("O-LOA-REVIEW", "O", "Letters of agreement not reviewed after change", ["loa not reviewed", "not reviewed", "agreement not updated"]),
        _f("R-CALLSIGN-ALERT", "R", "No similar-callsign alerting or strip marking", ["strip marking", "callsign alert", "similar callsign marking", "similar callsign warning"]),
        _f("R-SECTOR-COMBINING", "R", "Sector-combining criteria missing or not applied", ["combining criteria", "sector configuration", "criteria for combining"]),
        _f("R-OJT-SUPERVISION", "R", "OJT supervision / intervention criteria inadequate", ["ojti", "instructor intervention", "intervention criteria", "ojt supervision"]),
        _f("R-LOA-COORD", "R", "Coordination procedure or LoA unclear", ["letter of agreement", "loa", "transfer conditions", "coordination procedure"]),
        _f("R-STCA-CONFIG", "R", "STCA parameters or inhibition areas inappropriate", ["inhibition", "stca parameter", "safety net configuration", "inhibition volume"]),
        _f("R-READBACK-PROC", "R", "Readback/hearback procedure not specific", ["readback procedure", "hearback procedure", "readback confirmation"]),
        _f("R-FLOW-MEASURES", "R", "No flow measures for the peak or weather", ["flow regulation", "atfm", "flow control", "capacity measure"]),
        _f("L-SIMILAR-CALLSIGN", "L", "Similar callsigns on frequency", ["similar callsign", "callsign confusion", "callsigns differing"]),
        _f("L-FREQ-CONGESTION", "L", "Frequency congestion / blocked transmissions", ["frequency congestion", "congested", "blocked transmission", "stepped on", "simultaneous transmission"]),
        _f("L-COMBINED-SECTORS", "L", "Sectors combined", ["combined sector", "sectors combined", "bandbox", "band-box"]),
        _f("L-NIGHT-FATIGUE", "L", "Night duty / fatigue", ["night shift", "night duty", "fatigue", "tired", "last two hours"]),
        _f("L-HIGH-WORKLOAD", "L", "High workload / traffic peak", ["high workload", "traffic peak", "workload", "busy"]),
        _f("L-TRAINEE", "L", "Trainee controller on position", ["trainee", "ojt", "on-the-job training", "student controller"]),
        _f("L-WX-DEVIATIONS", "L", "Weather deviations", ["weather deviation", "thunderstorm", "cumulonimbus", "cb line", "deviating"]),
        _f("L-STCA-LATE", "L", "Safety-net alert late or absent", ["no stca", "stca alert late", "no alert", "alert late", "without an alert"]),
        _f("L-LANGUAGE", "L", "Language or phraseology issue", ["phraseology", "english proficiency", "non-standard"]),
        _f("I-HEARBACK-MISSED", "I", "Incorrect readback not detected (hearback)", ["readback not detected", "hearback", "incorrect readback", "readback error", "readback was not"]),
        _f("I-CLEARANCE-TO-WRONG-AC", "I", "Clearance acted on by the wrong aircraft", ["wrong aircraft", "took the clearance", "intended for", "acted on"]),
        _f("I-WRONG-LEVEL", "I", "Controller issued a conflicting level or clearance", ["wrong level", "occupied level", "conflicting level", "incorrect clearance"]),
        _f("I-PILOT-LEVEL-BUST", "I", "Pilot deviated from the cleared level", ["level bust", "climbed through", "descended through", "above the cleared", "below the cleared", "altitude deviation"]),
        _f("I-NO-COORD", "I", "Coordination not carried out", ["no coordination", "not coordinated", "without coordination", "estimate not passed"]),
        _f("I-MONITORING-LAPSE", "I", "Conflict not detected — monitoring lapse", ["conflict not detected", "conflict was not detected", "did not detect the conflict", "traffic not detected", "not detected until", "monitoring lapse", "relied on the safety net"]),
        _f("I-LATE-RESOLUTION", "I", "Late or ineffective avoiding action", ["avoiding action", "late resolution", "traffic information late"]),
        _f("E-LOS", "E", "Loss of separation", ["loss of separation", "separation infringement", "minimum separation", "less than the required"]),
    ],
    "fuel": [
        _f("L-FUEL-BELIEVED-FULL", "L", "Pilot believed the aircraft fully refuelled", ["fully refuelled", "believed", "full tanks"]),
        _f("L-FUEL-QTY-ASSESS", "L", "Incorrect fuel quantity assessment before take-off", ["fuel quantity assessment", "incorrect fuel quantity", "cross-check", "fuel receipt"]),
        _f("L-FUEL-PLAN-ERROR", "L", "Fuel plan used incorrect fuel content and weight", ["fuel plan", "fuel content", "fuel log"]),
        _f("L-FUEL-SUFFICIENT-BELIEF", "L", "Pilot ascertained sufficient fuel for the planned flight", ["sufficient fuel", "ascertained"]),
        _f("L-FUEL-EXHAUSTED", "L", "Aircraft fuel supply exhausted in flight", ["fuel exhaustion", "exhausted", "ran out of fuel"]),
        _f("L-ENGINES-SERVICEABLE", "L", "Engines serviceable", ["serviceable", "both engines"]),
        _f("L-ENGINE-SURGE", "L", "Engine surged", ["surged", "surging", "surge"]),
        _f("L-ENGINE-POWER-LOSS", "L", "Engine power loss in flight", ["power loss", "engine failure", "engine stopped", "ceased operating"]),
        _f("L-WATER-IN-FUEL", "L", "Water found in fuel samples", ["water", "contamination"]),
        _f("I-EMERG-PROC", "I", "Emergency engine-failure procedure conducted", ["emergency procedure", "engine failure procedure", "crossfeed"]),
    ],
}

# phrases that mean the same thing in different reports (the paper's "refuel / add fuel / fuel added" problem)
THESAURUS = [
    ["refuel", "refuelled", "refueled", "refuelling", "add fuel", "added fuel", "fuel added", "fuel uplift", "uplift", "request additional fuel"],
    ["engine power loss", "engine lost power", "engine failed", "engine failure", "engine stopped", "power loss", "ceased operating", "engine surged"],
    ["readback", "read back", "read-back", "readbacks"],
    ["hearback", "hear back", "hear-back"],
    ["callsign", "call sign", "call-sign", "callsigns", "call signs"],
    ["level bust", "altitude deviation", "level deviation", "deviated from the cleared level", "climbed through", "descended through"],
    ["combined sectors", "sectors combined", "combined sector", "bandbox", "band-box", "bandboxed", "collapsed sectors"],
    ["stca", "short term conflict alert", "short-term conflict alert", "safety net", "safety-net"],
    ["loss of separation", "separation infringement", "loss of minimum separation", "separation minima infringement", "airprox", "los"],
    ["coordination", "co-ordination", "coordinate", "co-ordinate", "coordinated", "co-ordinated"],
    ["fatigue", "tired", "tiredness", "fatigued", "sleepy"],
    ["night shift", "night duty", "midnight shift"],
    ["workload", "traffic load", "busy", "traffic peak"],
    ["frequency congestion", "blocked transmission", "blocked transmissions", "stepped on", "simultaneous transmission", "congested frequency"],
    ["trainee", "ojt", "on-the-job training", "student controller"],
    ["thunderstorm", "cumulonimbus", "cb", "weather deviation", "weather deviations", "deviating around weather"],
    ["letter of agreement", "loa", "letters of agreement"],
]


def factor_index(category: str) -> dict[str, dict]:
    return {f["code"]: f for f in FACTORS.get(category, [])}


def meta() -> dict:
    return {"categories": {k: {**v, "factors": FACTORS.get(k, [])} for k, v in CATEGORIES.items()}}


# ------------------------------------------------------------------ building a case model from a compact spec
def build_case(category: str, evidence: list, hyps: list, finding: tuple, context: list = ()) -> dict:
    """evidence: (id, factor|None, label, text, past[, layer]); hyps: (id, layer, label, factor|None, inputs, past);
    finding: (id, label, inputs, mechanism); context: (source, target) edges not used by the rules."""
    from .engines import fuzzy
    fi = factor_index(category)
    blocks, edges = [], []
    for e in evidence:
        bid, fac, label, text, past = e[:5]
        layer = e[5] if len(e) > 5 else fi[fac]["layer"]
        blocks.append({"id": bid, "layer": layer, "kind": "evidence", "label": label, "text": text, "factor": fac, "past": past})
    for bid, layer, label, fac, inputs, past in hyps:
        blocks.append({"id": bid, "layer": layer, "kind": "hypothesis", "label": label, "text": "", "factor": fac, "past": past})
        edges += [{"source": i, "target": bid, "role": "input"} for i in inputs]
    fid, flabel, finputs, mech = finding
    mechs = [m["code"] for m in CATEGORIES[category]["mechanisms"]]
    blocks.append({"id": fid, "layer": "E", "kind": "finding", "label": flabel, "text": "", "factor": None,
                   "past": {m: ("VP" if m == mech else "HU") for m in mechs}})
    edges += [{"source": i, "target": fid, "role": "input"} for i in finputs]
    edges += [{"source": s, "target": t, "role": "context"} for s, t in context]
    model = {"blocks": blocks, "edges": edges}
    model["rules"] = fuzzy.default_rules(model)
    return model


ILLUS = "Illustrative case written for ARAP training — not a real occurrence."
LOS = ("E-LOS",)

DEMO_CASES = [
    dict(ref="CASE-01", title="Similar callsigns — climb clearance taken by the wrong aircraft", category="ats-los", source=ILLUS, occurred="",
         summary="Day peak in an ACC sector. Two aircraft of one operator with callsigns differing in the last two digits were on a congested frequency. "
                 "A climb clearance to FL340 intended for one was read back and acted on by the other; the controller did not detect the readback. "
                 "STCA alerted and avoiding action was given. Minimum separation 3.1 NM / 500 ft.",
         model=lambda: build_case("ats-los", [
             ("e1", "L-SIMILAR-CALLSIGN", "Similar callsigns on frequency", "Two aircraft of one operator with callsigns differing in the last two digits.", "S"),
             ("e2", "L-FREQ-CONGESTION", "Frequency congested", "Two blocked transmissions in the minute before the clearance.", "S"),
             ("e3", "I-HEARBACK-MISSED", "Readback by the wrong aircraft not detected", "The controller did not detect that the readback came from the other aircraft.", "S"),
             ("e4", "R-CALLSIGN-ALERT", "No similar-callsign marking", "No similar-callsign marking on strips or track labels.", "S"),
             ("e5", "O-CALLSIGN-MGMT", "No callsign de-confliction with operators", "Similar-callsign de-confliction had not been agreed with operators.", "S"),
             ("e6", "E-LOS", "Loss of separation 3.1 NM / 500 ft", "Minimum 3.1 NM and 500 ft against 5 NM / 1000 ft.", "S")],
             [("h1", "I", "Clearance acted on by the wrong aircraft", "I-CLEARANCE-TO-WRONG-AC", ["e1", "e2", "e3"], "S"),
              ("h2", "R", "Similar-callsign risk not controlled", None, ["e4", "e5"], "S")],
             ("f1", "Loss of separation after a clearance was taken by the wrong aircraft", ["h1", "e6"], "M2"), [("h2", "f1")])),
    dict(ref="CASE-02", title="Combined sectors at night — converging traffic not detected", category="ats-los", source=ILLUS, occurred="",
         summary="Two sectors combined at 01:30 under minimum night staffing. The controller, in the last two hours of a night shift, did not detect "
                 "converging traffic at the same level until the STCA alerted; avoiding action was late. 4.2 NM at the same level.",
         model=lambda: build_case("ats-los", [
             ("e1", "L-COMBINED-SECTORS", "Sectors combined at 01:30", "Two sectors combined under reduced staffing.", "S"),
             ("e2", "L-NIGHT-FATIGUE", "Last two hours of a night shift", "Controller on duty since 22:00.", "S"),
             ("e3", "I-MONITORING-LAPSE", "Converging traffic not detected", "Conflict not detected until the STCA alerted.", "S"),
             ("e4", "I-LATE-RESOLUTION", "Late avoiding action", "Avoiding action given after the STCA.", "S"),
             ("e5", "R-SECTOR-COMBINING", "No criteria for combining at night", "No traffic criteria for combining sectors at night.", "S"),
             ("e6", "O-STAFFING", "Night roster at minimum staffing", "Night roster planned at minimum staffing.", "S"),
             ("e7", "E-LOS", "Loss of separation 4.2 NM / 0 ft", "4.2 NM at the same level against 5 NM.", "S")],
             [("h1", "I", "Conflict not detected in time", None, ["e1", "e2", "e3"], "S"),
              ("h2", "R", "Sector-configuration risk not controlled", None, ["e5", "e6"], "S")],
             ("f1", "Loss of separation — conflict not detected on combined sectors", ["h1", "e4", "e7"], "M5"), [("h2", "f1")])),
    dict(ref="CASE-03", title="Trainee issued a level already occupied", category="ats-los", source=ILLUS, occurred="",
         summary="During a traffic peak a trainee controller with an instructor issued descent to FL280, occupied by crossing traffic. "
                 "The instructor intervened late; intervention criteria were not defined.",
         model=lambda: build_case("ats-los", [
             ("e1", "L-TRAINEE", "Trainee on position", "Trainee controller on position with an instructor.", "S"),
             ("e2", "L-HIGH-WORKLOAD", "Traffic peak", "14 aircraft on frequency.", "S"),
             ("e3", "I-WRONG-LEVEL", "Descent to an occupied level issued", "Descent to FL280 issued; FL280 occupied by crossing traffic.", "S"),
             ("e4", "R-OJT-SUPERVISION", "Intervention criteria not defined", "No defined instructor intervention criteria.", "S"),
             ("e5", "E-LOS", "Loss of separation 3.8 NM / 600 ft", "3.8 NM and 600 ft against 5 NM / 1000 ft.", "S")],
             [("h1", "I", "Clearance error by the controller", None, ["e1", "e2", "e3"], "S"),
              ("h2", "R", "OJT supervision risk not controlled", None, ["e4"], "S")],
             ("f1", "Loss of separation after a clearance error", ["h1", "e5"], "M1"), [("h2", "f1")])),
    dict(ref="CASE-04", title="Pilot climbed through the cleared level (correct readback)", category="ats-los", source=ILLUS, occurred="",
         summary="The crew read back FL240 correctly but the aircraft climbed 700 ft above it; the crew reported altitude-select mode confusion. "
                 "STCA alerted in time and the controller gave immediate avoiding action.",
         model=lambda: build_case("ats-los", [
             ("e1", "I-PILOT-LEVEL-BUST", "Climbed 700 ft above cleared level", "Aircraft climbed 700 ft above the cleared FL240.", "S"),
             ("e2", None, "Altitude-select mode confusion", "Crew reported altitude-select mode confusion.", "S", "L"),
             ("e3", "I-HEARBACK-MISSED", "Readback correct and heard", "Readback of FL240 was correct — hearback was not a factor.", "O"),
             ("e4", "I-LATE-RESOLUTION", "Avoiding action immediate", "STCA alerted in time; immediate avoiding action.", "O"),
             ("e5", "E-LOS", "Loss of separation 4.5 NM / 300 ft", "4.5 NM and 300 ft.", "S")],
             [("h1", "I", "Aircraft deviated from the cleared level", None, ["e1", "e2"], "S")],
             ("f1", "Loss of separation after a pilot level deviation", ["h1", "e3", "e5"], "M3"), [("e4", "f1")])),
    dict(ref="CASE-05", title="Aircraft entered the sector without coordination at an FIR boundary", category="ats-los", source=ILLUS, occurred="",
         summary="An aircraft on a direct routing entered the sector without an estimate from the busy adjacent unit. "
                 "The letter of agreement was ambiguous for direct routings and had not been reviewed since an airspace change.",
         model=lambda: build_case("ats-los", [
             ("e1", "I-NO-COORD", "Estimate not passed", "The adjacent unit did not pass an estimate.", "S"),
             ("e2", "L-HIGH-WORKLOAD", "Adjacent unit busy", "Adjacent unit at peak traffic.", "S"),
             ("e3", "R-LOA-COORD", "LoA ambiguous for direct routings", "Transfer conditions for direct routings ambiguous.", "S"),
             ("e4", "O-LOA-REVIEW", "LoA not reviewed after airspace change", "LoA not reviewed since the airspace change.", "S"),
             ("e5", "E-LOS", "Loss of separation 7 NM / 0 ft (10 NM required)", "7 NM against 10 NM procedural.", "S")],
             [("h1", "I", "Transfer without coordination", None, ["e1", "e2"], "S"),
              ("h2", "R", "Coordination risk not controlled", None, ["e3", "e4"], "S")],
             ("f1", "Loss of separation after a coordination failure", ["h1", "e5"], "M4"), [("h2", "f1")])),
    dict(ref="CASE-06", title="Conflict inside an STCA inhibition volume", category="ats-los", source=ILLUS, occurred="",
         summary="No STCA alert was generated because the conflict was inside an inhibition volume enlarged by a system update that had not been "
                 "safety assessed. The controller, relying on the safety net in a busy period, gave late avoiding action.",
         model=lambda: build_case("ats-los", [
             ("e1", "L-STCA-LATE", "No STCA alert", "Conflict inside an inhibition volume — no alert.", "S"),
             ("e2", "R-STCA-CONFIG", "Inhibition volume too large", "Inhibition volume enlarged by a system update.", "S"),
             ("e3", "O-CHANGE-MGMT", "Update not safety assessed", "The system update was not safety assessed.", "S"),
             ("e4", "I-LATE-RESOLUTION", "Late avoiding action", "Avoiding action after visual detection on the display.", "S"),
             ("e5", "I-MONITORING-LAPSE", "Relied on the safety net", "Controller relied on the safety net in a busy period.", "S"),
             ("e6", "E-LOS", "Loss of separation 3.5 NM / 400 ft", "3.5 NM and 400 ft.", "S")],
             [("h1", "L", "Safety net did not alert", None, ["e1", "e2"], "S")],
             ("f1", "Loss of separation with a safety-net deficiency", ["h1", "e4", "e6"], "M6"), [("e3", "h1"), ("e5", "f1")])),
    dict(ref="CASE-07", title="Trainee missed an incorrect readback of heading and level", category="ats-los", source=ILLUS, occurred="",
         summary="On a congested frequency a trainee did not detect an incorrect readback of a combined heading and level instruction; "
                 "the unit procedure did not require confirmation and the instructor was not monitoring the readback.",
         model=lambda: build_case("ats-los", [
             ("e1", "L-TRAINEE", "Trainee on position", "Trainee controller on position.", "S"),
             ("e2", "L-FREQ-CONGESTION", "Frequency congested", "Several blocked transmissions.", "S"),
             ("e3", "I-HEARBACK-MISSED", "Incorrect readback not detected", "Incorrect readback of heading and level not detected.", "S"),
             ("e4", "R-READBACK-PROC", "Readback confirmation not required", "Unit procedure did not require readback confirmation.", "S"),
             ("e5", "R-OJT-SUPERVISION", "Instructor not monitoring readback", "Instructor was not monitoring readbacks.", "S"),
             ("e6", "E-LOS", "Loss of separation 4.0 NM / 700 ft", "4.0 NM and 700 ft.", "S")],
             [("h1", "I", "Incorrect readback not challenged", None, ["e1", "e2", "e3"], "S"),
              ("h2", "R", "Readback risk not controlled", None, ["e4", "e5"], "S")],
             ("f1", "Loss of separation after an undetected readback error", ["h1", "e6"], "M2"), [("h2", "f1")])),
    dict(ref="CASE-08", title="Weather deviations — conflict between deviating aircraft not detected", category="ats-los", source=ILLUS, occurred="",
         summary="Several aircraft deviated around a CB line during a traffic peak; no flow regulation had been applied despite the forecast. "
                 "A conflict between two deviating aircraft was not detected in time.",
         model=lambda: build_case("ats-los", [
             ("e1", "L-WX-DEVIATIONS", "Aircraft deviating around a CB line", "Several aircraft deviating around weather.", "S"),
             ("e2", "L-HIGH-WORKLOAD", "Traffic peak", "Traffic peak with many requests.", "S"),
             ("e3", "I-MONITORING-LAPSE", "Conflict not detected", "Conflict between deviating aircraft not detected in time.", "S"),
             ("e4", "R-FLOW-MEASURES", "No flow regulation", "No flow regulation despite the forecast CB line.", "S"),
             ("e5", "L-FREQ-CONGESTION", "Frequency congested", "Frequency congested by deviation requests.", "S"),
             ("e6", "E-LOS", "Loss of separation 3.9 NM / 0 ft", "3.9 NM at the same level.", "S")],
             [("h1", "I", "Conflict not detected in time", None, ["e1", "e2", "e3"], "S"),
              ("h2", "R", "Capacity risk not controlled", None, ["e4"], "S")],
             ("f1", "Loss of separation — conflict not detected during weather deviations", ["h1", "e6"], "M5"), [("h2", "f1"), ("e5", "h1")])),
    dict(ref="CASE-09", title="Level change not coordinated after a sector split", category="ats-los", source=ILLUS, occurred="",
         summary="During a sector split coordination responsibilities were unclear; a level change was not coordinated with the adjacent sector.",
         model=lambda: build_case("ats-los", [
             ("e1", "I-NO-COORD", "Level change not coordinated", "Level change not coordinated with the adjacent sector.", "S"),
             ("e2", "L-COMBINED-SECTORS", "Sector split in progress", "Sectors being split; responsibilities unclear.", "S"),
             ("e3", "R-LOA-COORD", "Coordination procedure unclear during split", "Procedure does not define coordination during a split.", "S"),
             ("e4", "L-HIGH-WORKLOAD", "Busy period", "Busy period during the split.", "S"),
             ("e5", "E-LOS", "Loss of separation 4.4 NM / 500 ft", "4.4 NM and 500 ft.", "S")],
             [("h1", "I", "Coordination not carried out", None, ["e1", "e2"], "S"),
              ("h2", "R", "Coordination risk not controlled", None, ["e3"], "S")],
             ("f1", "Loss of separation after a coordination failure", ["h1", "e5"], "M4"), [("h2", "f1"), ("e4", "h1")])),
    dict(ref="CASE-F01", title="Reference example — fuel exhaustion after incorrect fuel quantity assessment (Ng et al. 2022, AcciMap 23)",
         category="fuel", occurred="",
         source="Ng, Bil, Sardina & O'Bree (2022), Expert Systems with Applications 207, 117994, Fig. 12–13; based on ATSB report AO-2017-067.",
         summary="Paraphrase of the AcciMap used as the example in the paper: incorrect fuel quantity assessment and fuel planning led to fuel "
                 "exhaustion and loss of engine power; used as reference test TC-IES-01.",
         model=lambda: build_case("fuel", [
             ("e1", "L-FUEL-BELIEVED-FULL", "Pilot more likely to believe aircraft fully refuelled", "Pilot recorded a larger fuel uplift than delivered.", "S"),
             ("e2", "L-FUEL-QTY-ASSESS", "Incorrect fuel quantity assessment before take-off", "Refuel receipt error not detected; no cross-check.", "S"),
             ("e3", "L-FUEL-PLAN-ERROR", "Fuel plan used incorrect fuel content and weight", "Fuel log calculations carried the error forward.", "S"),
             ("e4", "L-FUEL-SUFFICIENT-BELIEF", "Pilot ascertained sufficient fuel for planned flight", "Error between calculated and actual fuel not detected.", "S"),
             ("e5", "L-ENGINES-SERVICEABLE", "Both engines serviceable", "Engines very likely serviceable.", "S"),
             ("e6", "L-ENGINE-SURGE", "Engine surged", "Engines surged after crossfeed.", "S"),
             ("e7", "L-ENGINE-POWER-LOSS", "Engine power loss in flight", "Both engines failed in flight.", "S"),
             ("e8", "I-EMERG-PROC", "Emergency engine-failure procedure conducted", "Crossfeed and emergency procedure conducted.", "S")],
             [("h1", "L", "Aircraft fuel supply exhausted in flight", "L-FUEL-EXHAUSTED", ["e1", "e2", "e3", "e4"], "S")],
             ("f1", "Single-engine landing — engine power lost in flight due to fuel exhaustion", ["h1", "e5", "e6", "e7", "e8"], "FE"))),
]

DEMO_OCCURRENCE = (
    "At 02:10 local two sectors were combined under night staffing. Two aircraft with similar callsigns, GIA612 and GIA621, were on frequency. "
    "The controller cleared GIA612 to climb to FL340; GIA621 read back the clearance and began to climb. The readback was not detected. "
    "There were blocked transmissions on the frequency just before. STCA alerted and avoiding action was given. "
    "Minimum separation was 3.2 NM and 400 ft against 5 NM / 1000 ft. The controller was in the last two hours of a night shift.")

DEMO_RATINGS = {"f:L-SIMILAR-CALLSIGN": "SS", "f:L-COMBINED-SECTORS": "S", "f:L-NIGHT-FATIGUE": "S", "f:I-HEARBACK-MISSED": "S",
                "f:L-FREQ-CONGESTION": "S", "f:I-LATE-RESOLUTION": "NE", "f:E-LOS": "SS"}


def seed_cases(db: Session):
    from .models import InvCase
    if db.query(InvCase).count():
        return
    for c in DEMO_CASES:
        db.add(InvCase(ref=c["ref"], title=c["title"], category=c["category"], source=c["source"], summary=c["summary"],
                       model=c["model"](), status="approved", provenance={"method": "manual"}, created_by="system",
                       approved_by="system"))
    db.commit()


def seed_demo_v6(db: Session):
    """Case library and DEMO-06: an illustrative ATS loss-of-separation investigation using the expert system."""
    from .api.ies_logic import analyse_study
    from .models import Assessment, Project, RiskScheme, Study
    seed_cases(db)
    if db.query(Project).filter_by(code="DEMO-06").first():
        return
    p = Project(code="DEMO-06", title="Investigation expert system — loss of separation (illustrative)", change_type="investigation",
                units="ACC — combined upper sectors", sponsor="Safety & Quality",
                description="Illustrative ATS occurrence investigation using the ORLIO case library, fuzzy AcciMap inference and the "
                            "Bayesian network with ranked clues (Manual Appendix E). Not a real occurrence.")
    db.add(p); db.flush()
    rs = db.query(RiskScheme).order_by(RiskScheme.version.desc()).first()
    a = Assessment(project_id=p.id, title="Occurrence investigation OCC-ILL-01 — loss of separation, similar callsigns (illustrative)",
                   created_by="assessor", risk_scheme_version=rs.version if rs else 1,
                   scope="Initial phase of an ATS occurrence investigation: search of past cases, evidence rating, clues for evidence collection.",
                   environment="Combined upper sectors at night; two aircraft of one operator with similar callsigns.",
                   assumptions="Case library of nine illustrative loss-of-separation cases; ratings from recordings and interviews on day 1.")
    db.add(a); db.flush()
    from .models import InvCase
    sel = [c.id for c in db.query(InvCase).filter(InvCase.ref.in_(["CASE-01", "CASE-02", "CASE-07"])).order_by(InvCase.ref)]
    model = {"category": "ats-los", "narrative": DEMO_OCCURRENCE, "selected": sel, "ratings": dict(DEMO_RATINGS),
             "notes": "Day 1 ratings from the radar replay, the RT recording and the controller interview."}
    results = analyse_study(db, model)
    db.add(Study(assessment_id=a.id, method="ies", title="Investigation expert system — OCC-ILL-01", model=model, results=results,
                 template_version="1.0"))
    db.commit()
