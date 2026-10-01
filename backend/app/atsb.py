"""ATSB safety investigation analysis — reference data (Manual Appendix F).

Sources: ATSB Safety Investigation Guidelines Manual — Analysis (v1.07, 2015) [G] and Safety Investigation Tools
Manual — Analysis Supplement (v1.05, 2011) [T]. Taxonomy codes and checklist titles follow [T] Appendices C–E;
prompts are short paraphrases. Page numbers refer to those documents.
"""
from __future__ import annotations

# ------------------------------------------------------------------ safety factor types and taxonomy ([T] App. D)
TYPES = {
    "OE": {"name": "Occurrence event", "level": "E", "event": True, "issue_allowed": False,
           "hint": "What happened to the aircraft or the system. Coded as an occurrence type (e.g. loss of separation), not as a safety factor type."},
    "IA": {"name": "Individual action", "level": "I", "event": True, "issue_allowed": False,
           "hint": "An observable behaviour of operational personnel that increased risk. Subject + action verb; neutral wording."},
    "TFM": {"name": "Technical failure mechanism", "level": "T", "event": True, "issue_allowed": False,
            "hint": "How equipment failed (the 'how' behind a technical problem)."},
    "LC": {"name": "Local condition", "level": "L", "event": False, "issue_allowed": True,
           "hint": "A condition in the immediate context that influenced individual actions or technical events."},
    "RC": {"name": "Risk control", "level": "R", "event": False, "issue_allowed": True,
           "hint": "A problem with a measure the organisation put in place (preventive or recovery)."},
    "OI": {"name": "Organisational influence", "level": "O", "event": False, "issue_allowed": True,
           "hint": "A condition that establishes, maintains or influences the effectiveness of risk controls (internal or external)."},
    "PA": {"name": "Positive action", "level": "I", "event": True, "issue_allowed": False, "positive": True,
           "hint": "An action that substantially reduced risk beyond normal expectations ('saved the day')."},
    "PC": {"name": "Positive condition", "level": "R", "event": False, "issue_allowed": False, "positive": True,
           "hint": "Equipment or a risk control that significantly reduced risk beyond expectations (e.g. STCA alert, TCAS RA followed)."},
}

TAXONOMY = {
    "IA": [("I1", "Aircraft operation action", [("I1.1", "Pre-flight inspecting"), ("I1.2", "Assessing and planning"), ("I1.3", "Aircraft handling"),
                                                 ("I1.4", "Using equipment"), ("I1.5", "Communicating and coordinating – internal"),
                                                 ("I1.6", "Communicating and coordinating – external"), ("I1.7", "Monitoring and checking"),
                                                 ("I1.8", "Other aircraft operation action")]),
           ("I2", "Aircraft maintenance action", [("I2.1", "Inspecting"), ("I2.2", "Replacing, repairing, and installing"), ("I2.3", "Using incorrect parts"),
                                                  ("I2.4", "Completing documentation"), ("I2.5", "Other aircraft maintenance action")]),
           ("I3", "ATS action", [("I3.1", "Assessing and planning"), ("I3.2", "Using equipment"), ("I3.3", "Communicating"),
                                 ("I3.4", "Handover / takeover"), ("I3.5", "Monitoring and checking"), ("I3.6", "Other ATS action")]),
           ("I4", "Other action", [("I4.1", "Cabin safety action"), ("I4.2", "Facilities maintenance action"), ("I4.3", "Ground handling action"),
                                   ("I4.4", "Passenger action"), ("I4.5", "Other action")])],
    "TFM": [("T1", "Fracture", []), ("T2", "Wear", []), ("T3", "Corrosion", []), ("T4", "Deformation", []), ("T5", "Electrical discontinuity", []),
            ("T6", "Mechanical discontinuity", []), ("T7", "Software / firmware anomaly", []), ("T8", "Other", [])],
    "LC": [("L1", "Personal factors", [("L1.1", "Physical limitations"), ("L1.2", "Health-related condition"), ("L1.3", "Fatigue"), ("L1.4", "Alcohol/drugs"),
                                       ("L1.5", "Motivation/attitude"), ("L1.6", "Stress/anxiety"), ("L1.7", "Preoccupations"), ("L1.8", "Spatial disorientation"),
                                       ("L1.9", "Other personal factors")]),
           ("L2", "Knowledge, skills, experience", [("L2.1", "Task knowledge/skills"), ("L2.2", "Task experience/recency"), ("L2.3", "Equipment knowledge/skills"),
                                                    ("L2.4", "Other knowledge, skills, experience factors")]),
           ("L3", "Task demands", [("L3.1", "High workload"), ("L3.2", "Task completion pressure"), ("L3.3", "Time pressure"), ("L3.4", "Distractions"),
                                   ("L3.5", "Incorrect task information"), ("L3.6", "Other task demand factors")]),
           ("L4", "Social environment", []),
           ("L5", "Workspace environment", [("L5.1", "Workspace lighting"), ("L5.2", "Noise"), ("L5.3", "Temperature/humidity"), ("L5.4", "Air quality"),
                                            ("L5.5", "Other workspace environment factors")]),
           ("L6", "Physical environment", [("L6.1", "Light conditions"), ("L6.2", "Runway/movement area surface"), ("L6.3", "Other physical environment factors")]),
           ("L7", "Weather conditions", [("L7.1", "Visibility"), ("L7.2", "Wind"), ("L7.3", "Windshear"), ("L7.4", "Turbulence"), ("L7.5", "Icing conditions"),
                                         ("L7.6", "Other weather conditions")])],
    "RC": [("R1", "Equipment", [("R1.1", "Displays/controls"), ("R1.2", "Workspace equipment"), ("R1.3", "Tools and materials"), ("R1.4", "Warning/detection systems"),
                                ("R1.5", "Protection/rescue systems"), ("R1.6", "Automation"), ("R1.7", "Other equipment factors")]),
           ("R2", "Facilities/infrastructure", [("R2.1", "Aerodrome lighting"), ("R2.2", "Aerodrome signage"), ("R2.3", "Runway design"), ("R2.4", "Navigation aids"),
                                                ("R2.5", "Other facilities/infrastructure factors")]),
           ("R3", "Procedures", []), ("R4", "Training and assessment", []), ("R5", "People management", []),
           ("R6", "Technical failure management", [("R6.1", "Design"), ("R6.2", "Manufacture"), ("R6.3", "Maintenance"), ("R6.4", "Operation")])],
    "OI": [("O1", "Safety management processes", []), ("O2", "Organisational characteristics", []), ("O3", "Regulatory influences", []),
           ("O4", "Other external influences", [])],
    "PA": [("PA", "Positive action", [])],
    "PC": [("PC", "Positive condition", [])],
}

CODING_HINTS = {
    "I3.1": "Focus on the assessing/planning task, not on the fact that a decision error was made. Includes path short-cuts without assessing implications and not requesting assistance under high workload.",
    "I3.3": "Communicating with flight crew, other ATS personnel or other parties. Problems during handover go to I3.4.",
    "I3.5": "Maintaining awareness of system states, serviceability, environment and traffic disposition.",
    "L1.6": "Ongoing stress. Short, high task demand goes under L3.1.",
    "L3.1": "If high workload was caused by another condition (experience, equipment design), code that condition instead. Not needed when the person was handling an emergency.",
    "L3.3": "Use Time pressure when the pressure is to finish by a certain time.",
    "L3.4": "External events. Internal attention goes to L1.7 Preoccupations.",
    "L3.5": "If the information problem can be coded as another person's communicating action, that is preferred.",
    "R1.4": "Design or availability of equipment that detects or alerts to abnormal states (e.g. STCA, MSAW).",
    "R1.7": "Usability design goes here; reliability design goes to R6.1.",
    "R2.5": "Includes radar coverage.",
    "R5": "First-line supervision, rostering and scheduling, staff mix, selection, monitoring qualifications and fitness for work, job design.",
    "O1": "Hazard identification, risk assessment, change management, training needs analysis, equipment selection and testing, internal auditing, safety data.",
    "O2": "Organisational design, management skills, resource allocation, internal communication, organisational learning.",
    "O3": "Regulatory material and compliance monitoring.",
    "O4": "Industry standards, industrial groups, government departments, the community.",
}

ERROR_TYPES = {"information": "Information error (perception, situation awareness)", "decision": "Decision error (plan not adequate)",
               "action": "Action error (slip, lapse, imprecise control)", "violation": "Violation (deliberate deviation)"}
ROLES = ["Air traffic controller", "ATC supervisor", "ATC trainee / OJT instructor", "Flight crew (all)", "Pilot in command", "Co-pilot",
         "Student pilot", "Instructor/check pilot", "Cabin crew", "Aircraft maintenance personnel", "Facilities maintenance personnel (CNS/ATM)",
         "Ground crew", "Passenger", "Other", "Unknown"]
FUNCTIONAL_AREAS = ["Air traffic control", "Flight operations", "Cabin safety", "Aircraft maintenance", "Facilities maintenance (CNS/ATM)",
                    "Ground handling", "Other", "Unknown"]
EVENT_SF_TYPES = ["OE", "IA", "LC", "PA"]   # types an event in the sequence list can be promoted as ([T] p.11)

EXCLUSION_REASONS = ["Not a safety factor (trivial risk)", "Evidence clearly shows it did not exist", "Duplicates another factor",
                     "Restates the problem (e.g. 'loss of situation awareness')", "Explains a safety issue but is not itself a safety issue",
                     "Addressing it is clearly impracticable", "Other (see justification)"]

# ------------------------------------------------------------------ evidence ([G] pp.64–69, 89)
ITEM_RATINGS = {"supports": "Supports", "opposes": "Opposes", "no_effect": "No effect", "unsure": "Unsure"}
EVIDENCE_TYPES = {"tangible": "Tangible (recordings, data, documents, physical)", "testimonial": "Testimonial (direct observation, hearsay, opinion)",
                  "accepted": "Accepted fact"}
RELEVANCE = {"direct": "Direct", "circumstantial": "Circumstantial", "ancillary": "Ancillary (about other evidence)"}
CREDIBILITY = ["validity", "reliability", "bias", "sensitivity"]
EXPECTATION = {"": "—", "expected_not_seen": "Expected but not seen", "unexpected_seen": "Not expected but seen"}

# probability expressions ([G] p.73): code, term, equivalent, lower bound %
PROBABILITY = [("VC", "Virtually certain", "almost certain", 99), ("HL", "Highly likely", "highly probable", 95),
               ("VL", "Very likely", "very probable", 90), ("L", "Likely", "probable", 66),
               ("MLN", "More likely than not", "on the balance of probabilities", 50), ("ALAN", "About as likely as not", "more or less likely", 33),
               ("U", "Unlikely", "improbable", 10), ("VU", "Very unlikely", "", 1), ("EU", "Exceptionally unlikely", "extremely unlikely", 0)]
PROB_LOWER = {c: lo for c, _, _, lo in PROBABILITY}
STANDARD_OF_PROOF = 66   # a finding needs 'likely' or stronger ([G] p.79)

# ------------------------------------------------------------------ checklists ([T] App. C, [G])
EXISTENCE_Q = ["Direct evidence", "Symptoms or effects", "Sources or reasons (beware circular arguments)", "Other correlated events or conditions",
               "Predictability", "Comparison with a known standard", "Unfulfilled expectations", "Unexpected evidence",
               "Known history of existence", "Alternative explanations of the evidence"]
INFLUENCE_Q = ["Relative timing", "Reversibility", "Relative location", "Magnitude of the factor", "Plausibility", "Known history of influence",
               "Presence of enhancers", "Presence of inhibitors", "Characteristics of the problem (error type)", "Required assumptions",
               "Alternative explanations for the problem", "Directionality of influence", "Counterfactual: without it, probably no problem?"]
IMPORTANCE_Q = ["Prior existence", "Scope of future existence", "Severity of the factor", "Controls in place (number, effectiveness, independence)",
                "Relationship to change", "Presence of underlying safety issues", "External interest (only exceptionally the sole reason)"]
ITEM_CRITERIA = ["Related to the finding", "Validity", "Reliability", "Bias or objectivity", "Sensitivity", "Scope or power of the test",
                 "Relationship to similar evidence (do not count duplicates twice)", "Reasonableness of assumptions, generalisations, analogies",
                 "Quality of the item description", "Level of precision"]
SET_CRITERIA = ["Accounts for all parts of the finding", "Key items of evidence present", "Quantity of evidence", "Consistency",
                "Opposing evidence accounted for", "Independence of sources", "Convergence", "Direct evidence present", "Logical validity",
                "Qualification of the finding matches the strength of evidence"]
EVENTS_TO_LOOK_FOR = ["Occurrence events", "Significant state changes (phase, configuration, speed, level, equipment serviceability)",
                      "Environmental changes", "Changes in other important variables (frequency, controller, sector configuration, automation)",
                      "Milestones", "Unusual or unexpected events", "Decision points", "Post-occurrence events (alerting, rescue)",
                      "Risk-increasing events", "Risk-reducing ('saved the day') events"]
LEVEL_QUESTIONS = {
    "E": ["Which events were unusual, salient or absent?", "Equipment, system or infrastructure problems?", "Did anything escalate the outcome?"],
    "I": ["Which actions were unusual or did not conform to procedures?", "Which actions initiated higher risk, reduced detection or correction, or increased severity?",
          "Did an action affect another person's performance or equipment?", "Why did the action make sense at the time? (substitution test)"],
    "T": ["How did the equipment fail (fracture, wear, discontinuity, software anomaly…)?"],
    "L": ["Which conditions were unusual or at inappropriate levels?", "Significant changes before the events?", "Which conditions encouraged the individual actions or technical problems?"],
    "R": ["Which controls were in place, and were they effective and operating as designed?", "Controls unusual or absent compared with similar organisations?",
          "Non-conformance with regulation? Recent changes?"],
    "O": ["Safety management unusual compared with peers?", "SMS non-conformance or recent structural change?", "External pressures? No monitoring of control effectiveness?"],
}
JUDGEMENTAL_WORDS = ["failed", "failure to", "failure of", "deficient", "deficiency", "negligent", "careless", "inadequate", "poor", "unsafe act", "blame", "fault"]
VAGUE_WORDS = ["significant", "not robust", "suboptimal", "various", "etc", "some issues", "appropriate"]
REVIEW_CHECKLIST = [
    ("sufficiency", "Completeness", "Test for sufficiency: do the verified explanatory factors fully account for every verified factor?"),
    ("missing", "Completeness", "Is something important missing?"),
    ("enhance", "Completeness", "Have we identified the factors that can enhance safety?"),
    ("sense", "Completeness", "Do the findings make sense overall?"),
    ("fair_individual", "Fairness", "No finding appears to blame an individual without the reasons for their actions having been identified."),
    ("fair_org", "Fairness", "Reasonableness and practicability were considered for findings about organisations."),
    ("organised", "Organise findings", "Findings are ordered as contributing safety factors, other safety factors, other key findings."),
    ("no_merge", "Organise findings", "No safety issues were combined at this stage."),
    ("bias", "Reasoning", "Alternatives were sought (confirmation bias) and actions judged on the information available before the event (hindsight bias)."),
]
KEY_FINDING_KINDS = {"other_key": "Other key finding", "positive": "Positive safety factor", "intermediate": "Intermediate finding",
                     "scenario": "Possible scenario (no firm finding)"}

# ------------------------------------------------------------------ safety action ([G] pp.174–184, [T] App. E)
ACTION_CLASSES = {
    "Technical": ["Inspection", "Replace", "Repair/modify", "New/install", "Design/redesign"],
    "Policy": ["Amend", "New", "Review"],
    "Procedures": ["Amend", "New", "Review"],
    "Training": ["New/amend", "Review", "Re-training"],
    "Communication/education": ["Awareness", "Documentation", "Service bulletins, advisories, circulars"],
    "Mandatory requirements": ["Directives", "Legislation", "Review of requirements"],
    "Organisational surveillance": ["QA, audits, monitoring", "Risk assessment", "Further research/study"],
    "External surveillance": ["QA, audits, monitoring"],
    "No action": [],
    "Other": [],
}
ACTION_KINDS = {"org": "Safety action by the organisation", "recommendation": "Safety recommendation (states the problem, not the solution)",
                "advisory": "Safety advisory notice (no formal response required)"}
ACTION_STATUS = {"proposed": "Proposed", "monitor": "Monitor", "closed": "Closed"}
ISSUE_STATUS = {"pending": "Safety action pending", "adequately": "Adequately addressed", "partially": "Partially addressed", "not": "Not addressed"}
PRACTICABILITY = [("risk", "Level of risk (if critical, the other factors do not apply)"), ("knowledge", "State of knowledge (incl. industry-wide)"),
                  ("means", "Availability and suitability of the means"), ("cost", "Cost relative to the risk and the organisation")]
FOLLOW_UP_DAYS = 182
# Hierarchy of controls (most to least effective) for corrective actions in the investigation report
HIERARCHY = [("elimination", "Elimination", "Remove the hazard or the task (e.g. withdraw the unsafe equipment)"),
             ("substitution", "Substitution", "Replace with something less hazardous"),
             ("engineering", "Engineering controls", "Physical or design change (interlocks, guards, alerts)"),
             ("administrative", "Administrative controls", "Procedures, training, checklists, supervision, oversight"),
             ("ppe", "Personal protective equipment", "Protects the individual; least effective")]
REPORT_LAYERS = [("E", "3.1", "Occurrence events (O)", ("OE", "TFM"),
                  "The final physical outcomes and the specific technical failure mechanisms that triggered the accident."),
                 ("I", "3.2", "Individual actions (I)", ("IA", "PA"),
                  "The direct actions, omissions or decisions made by frontline operators (pilots, controllers, drivers, technicians)."),
                 ("L", "3.3", "Local conditions (L)", ("LC",),
                  "Environmental, situational or task-specific variables affecting human performance at the time of the event."),
                 ("R", "3.4", "Risk controls (R)", ("RC", "PC"),
                  "Existing safeguards, defences, barriers or safety procedures meant to intercept errors or break the accident chain."),
                 ("O", "3.5", "Organisational influences (O)", ("OI",),
                  "Latent systemic, corporate or policy-level choices that fostered unsafe local conditions or weakened risk controls.")]


def taxonomy_flat() -> dict[str, dict]:
    out = {}
    for t, groups in TAXONOMY.items():
        for code, name, subs in groups:
            out[code] = {"code": code, "name": name, "type": t, "level": 2 if subs or "." not in code else 2}
            for sc, sn in subs:
                out[sc] = {"code": sc, "name": f"{name} › {sn}", "type": t, "level": 3}
    return out


def meta() -> dict:
    return {"types": TYPES, "taxonomy": {t: [{"code": c, "name": n, "children": [{"code": sc, "name": sn} for sc, sn in s]} for c, n, s in g]
                                         for t, g in TAXONOMY.items()},
            "coding_hints": CODING_HINTS, "error_types": ERROR_TYPES, "roles": ROLES, "functional_areas": FUNCTIONAL_AREAS,
            "event_sf_types": EVENT_SF_TYPES, "exclusion_reasons": EXCLUSION_REASONS, "item_ratings": ITEM_RATINGS,
            "evidence_types": EVIDENCE_TYPES, "relevance": RELEVANCE, "credibility": CREDIBILITY, "expectation": EXPECTATION,
            "probability": [{"code": c, "term": t, "equivalent": e, "lower": lo} for c, t, e, lo in PROBABILITY],
            "standard_of_proof": STANDARD_OF_PROOF, "existence_q": EXISTENCE_Q, "influence_q": INFLUENCE_Q, "importance_q": IMPORTANCE_Q,
            "item_criteria": ITEM_CRITERIA, "set_criteria": SET_CRITERIA, "events_to_look_for": EVENTS_TO_LOOK_FOR, "level_questions": LEVEL_QUESTIONS,
            "review_checklist": [{"key": k, "group": g, "text": t} for k, g, t in REVIEW_CHECKLIST], "key_finding_kinds": KEY_FINDING_KINDS,
            "action_classes": ACTION_CLASSES, "action_kinds": ACTION_KINDS, "action_status": ACTION_STATUS, "issue_status": ISSUE_STATUS,
            "practicability": [{"key": k, "text": t} for k, t in PRACTICABILITY], "follow_up_days": FOLLOW_UP_DAYS,
            "hierarchy": [{"key": k, "name": n, "hint": h} for k, n, h in HIERARCHY],
            "report_layers": [{"key": k, "num": n, "name": nm, "types": list(t), "definition": d} for k, n, nm, t, d in REPORT_LAYERS]}
