"""Reference models from the AirNav Risk Analysis Manual, used as demo data and as test oracles."""

FTA_TREE = {
    "top": "TOP",
    "nodes": {
        "TOP": {"type": "or", "label": "Total loss of surveillance picture at ACC sector", "children": ["G1", "G2", "G3"]},
        "G1": {"type": "or", "label": "Loss of all surveillance inputs", "children": ["G1a", "E4"]},
        "G1a": {"type": "and", "label": "All sensors fail", "children": ["E1", "E2", "E3"]},
        "G2": {"type": "and", "label": "SDP failure and no fallback", "children": ["E5", "E6"]},
        "G3": {"type": "and", "label": "Loss of power at CWP", "children": ["E7", "E8", "E9"]},
        "E1": {"type": "basic", "label": "Radar A fails", "p": 1e-4},
        "E2": {"type": "basic", "label": "Radar B fails", "p": 1e-4},
        "E3": {"type": "basic", "label": "ADS-B ground network fails", "p": 5e-5},
        "E4": {"type": "basic", "label": "Common-cause loss of surveillance WAN", "p": 1e-6},
        "E5": {"type": "basic", "label": "Main surveillance data processor fails", "p": 2e-5},
        "E6": {"type": "basic", "label": "Fallback fails to take over (PFD)", "p": 1e-2},
        "E7": {"type": "basic", "label": "Mains power failure", "p": 1e-3},
        "E8": {"type": "basic", "label": "UPS fails", "p": 2e-3},
        "E9": {"type": "basic", "label": "Generator fails to start (PFD)", "p": 1e-2},
    },
}

BBN_NET = {
    "nodes": [
        {"id": "F", "label": "ATCO fatigue", "states": ["yes", "no"], "parents": [], "cpt": [0.15, 0.85]},
        {"id": "W", "label": "Workload", "states": ["high", "normal"], "parents": [], "cpt": [0.30, 0.70]},
        {"id": "E", "label": "Coordination error", "states": ["yes", "no"], "parents": ["F", "W"],
         "cpt": [[[0.020, 0.980], [0.008, 0.992]], [[0.006, 0.994], [0.002, 0.998]]]},
        {"id": "S", "label": "STCA available", "states": ["yes", "no"], "parents": [], "cpt": [0.98, 0.02]},
        {"id": "L", "label": "Loss of separation", "states": ["yes", "no"], "parents": ["E", "S"],
         "cpt": [[[0.05, 0.95], [0.30, 0.70]], [[0.0, 1.0], [0.0, 1.0]]]},
    ]
}
