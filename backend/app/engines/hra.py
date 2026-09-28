"""Human reliability analysis: HEART (Williams) and CARA (EUROCONTROL, Kirwan & Gibson).

HEP = GTT × Π [ (EPC_i − 1) × APOA_i + 1 ],   APOA ∈ [0, 1] (CARA recommends 0.05–1), HEP capped at 1.
"""
from __future__ import annotations

ENGINE_VERSION = "hra-1.0.0"

HEART_GTT = {
    "A": ("Totally unfamiliar, performed at speed with no real idea of likely consequences", 0.55),
    "B": ("Shift or restore system to a new or original state on a single attempt without supervision or procedures", 0.26),
    "C": ("Complex task requiring high level of comprehension and skill", 0.16),
    "D": ("Fairly simple task performed rapidly or given scant attention", 0.09),
    "E": ("Routine, highly practised, rapid task involving relatively low level of skill", 0.02),
    "F": ("Restore or shift a system to original or new state following procedures, with some checking", 0.003),
    "G": ("Completely familiar, well-designed, highly practised routine task, performed by highly motivated, trained person", 0.0004),
    "H": ("Respond correctly to system command even when there is an augmented or automated supervisory system", 0.00002),
    "M": ("Miscellaneous task for which no description can be found", 0.03),
}
HEART_EPC = {
    "1": ("Unfamiliarity with a situation which is potentially important but occurs infrequently or is novel", 17),
    "2": ("Shortage of time available for error detection and correction", 11),
    "3": ("Low signal-to-noise ratio", 10),
    "4": ("Means of suppressing or overriding information or features too easily accessible", 9),
    "5": ("No means of conveying spatial and functional information in a readily assimilated form", 8),
    "6": ("Mismatch between operator's model of the world and that imagined by the designer", 8),
    "7": ("No obvious means of reversing an unintended action", 8),
    "8": ("Channel capacity overload, particularly by simultaneous presentation of non-redundant information", 6),
    "9": ("Need to unlearn a technique and apply one requiring an opposing philosophy", 6),
    "10": ("Need to transfer specific knowledge from task to task without loss", 5.5),
    "11": ("Ambiguity in the required performance standards", 5),
    "12": ("Mismatch between perceived and real risk", 4),
    "13": ("Poor, ambiguous or ill-matched system feedback", 4),
    "14": ("No clear, direct and timely confirmation of an intended action", 3),
    "15": ("Operator inexperience", 3),
    "16": ("Impoverished quality of information conveyed by procedures and person-person interaction", 3),
    "17": ("Little or no independent checking or testing of output", 3),
}
CARA_GTT = {
    "A": ("Offline tasks", 0.03),
    "B1": ("Active search of radar or flight progress strips, assuming some confusable information on display", 0.005),
    "B2": ("Respond to visual change in display (e.g. aircraft highlighted changes to low-lighted)", 0.13),
    "B3": ("Respond to unique and trusted audible and visual indication", 0.0004),
    "C1": ("Identify routine conflict", 0.01),
    "C2": ("Identify unanticipated change in radar display", 0.3),
    "D1": ("Solve conflict which includes some complexity", 0.01),
    "D2": ("Complex and time-pressured conflict solution", 0.19),
    "E": ("Plan aircraft in/out of sector", 0.01),
    "F": ("Routine element of sector management", 0.003),
    "G1": ("Verbal slips", 0.002),
    "G2": ("Physical slips (two simple choices)", 0.002),
    "M3": ("Routine maintenance task", 0.004),
}
CARA_EPC = {
    "1": ("Shortfalls in the quality of procedures", 5),
    "2": ("Unfamiliarity and inadequate training / experience", 20),
    "3": ("On-the-job training", 8),
    "4": ("Stereotype violation", 24),
    "5": ("Time pressure", 11),
    "6": ("Cognitive overload", 6),
    "7": ("Poor system feedback / HMI inadequacy", 5),
    "9": ("Little or no independent checking", 3),
    "10": ("Unreliable instrumentation", 1.6),
    "11": ("Workplace noise / lighting issues", 8),
    "12": ("Emotional stress / ill health", 5),
    "13": ("Low vigilance", 3),
    "14": ("Team coordination problems", 10),
    "15": ("Poor shift handover practices", 10),
    "17": ("Traffic complexity", 10),
    "20": ("Low morale / adverse organisational environment", 2),
    "21": ("Shift from anticipatory to reactive mode", 10),
    "22": ("Risk taking", 4),
}
LIBRARIES = {"heart": {"gtt": HEART_GTT, "epc": HEART_EPC}, "cara": {"gtt": CARA_GTT, "epc": CARA_EPC}}


def assess(library: str, gtt: str, epcs: list[dict]) -> dict:
    lib = LIBRARIES.get(library)
    if not lib:
        raise ValueError("library must be 'heart' or 'cara'")
    if gtt not in lib["gtt"]:
        raise ValueError(f"unknown generic task type {gtt}")
    base = lib["gtt"][gtt][1]
    hep = base
    factors = []
    for e in epcs:
        code = str(e["code"])
        if code not in lib["epc"]:
            raise ValueError(f"unknown EPC {code}")
        apoa = float(e["apoa"])
        if not 0 <= apoa <= 1:
            raise ValueError("APOA must be in [0,1]")
        mult = lib["epc"][code][1]
        f = (mult - 1) * apoa + 1
        hep *= f
        factors.append({"code": code, "description": lib["epc"][code][0], "max_effect": mult, "apoa": apoa, "factor": f})
    return {"engine_version": ENGINE_VERSION, "library": library, "gtt": gtt, "gtt_description": lib["gtt"][gtt][0],
            "nominal_hep": base, "factors": factors, "hep": min(1.0, hep), "capped": hep > 1}
