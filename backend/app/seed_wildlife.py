"""Worked example for the species wildlife strike risk module (Manual ch. 31): cattle egret, Bubulcus ibis.

All strike counts, movements and survey numbers are ILLUSTRATIVE — chosen to demonstrate the method at a lowland
Indonesian aerodrome surrounded by rice fields — and are not data from any real aerodrome.
"""
from sqlalchemy.orm import Session

from .engines import wildlife
from .models import Assessment, Project, Study

YEARS = [2021, 2022, 2023, 2024, 2025]


def _y(vals):
    return {str(y): v for y, v in zip(YEARS, vals)}


WILDLIFE_MODEL = {
    "aerodrome": "Aerodrome X (illustrative lowland aerodrome, rice fields on both approaches)",
    "years": YEARS,
    "movements": _y([42000, 58000, 71000, 76000, 80000]),
    "species": [
        {"id": "SP-01", "common": "Cattle egret (kuntul kerbau)", "scientific": "Bubulcus ibis", "mass_kg": 0.34, "flocking": True,
         "strikes": _y([9, 12, 14, 11, 16]), "damaging": _y([1, 1, 2, 1, 2]),
         "notes": "Includes the eastern population (B. i. coromandus), treated as a separate species by some authorities."},
        {"id": "SP-02", "common": "Javan pond heron (blekok sawah)", "scientific": "Ardeola speciosa", "mass_kg": 0.25, "flocking": False,
         "strikes": _y([4, 3, 5, 6, 4]), "damaging": _y([0, 0, 1, 0, 0])},
        {"id": "SP-03", "common": "Barn swallow (layang-layang asia)", "scientific": "Hirundo rustica", "mass_kg": 0.018, "flocking": True,
         "strikes": _y([14, 18, 20, 17, 21]), "damaging": _y([0, 0, 0, 0, 0])},
        {"id": "SP-04", "common": "Eurasian tree sparrow (burung gereja)", "scientific": "Passer montanus", "mass_kg": 0.022, "flocking": True,
         "strikes": _y([6, 8, 7, 9, 10]), "damaging": _y([0, 0, 0, 0, 0])},
        {"id": "SP-05", "common": "Pacific golden plover (cerek kernyut)", "scientific": "Pluvialis fulva", "mass_kg": 0.13, "flocking": True,
         "strikes": _y([2, 1, 3, 2, 3]), "damaging": _y([0, 0, 1, 0, 0]), "notes": "Non-breeding migrant, September–April."},
        {"id": "SP-06", "common": "Large flying fox (kalong besar)", "scientific": "Pteropus vampyrus", "mass_kg": 1.0, "flocking": True,
         "strikes": _y([0, 1, 0, 1, 1]), "damaging": _y([0, 1, 0, 0, 0]), "notes": "Bat, not a bird; night strikes on approach."},
    ],
    "profiles": {
        "SP-01": {
            "ecology": ("Small white heron, 0.3–0.4 kg, wingspan about 0.9 m. Feeds in flocks on insects and small vertebrates in short grass, "
                        "behind mowers and grazing cattle, and in rice fields during ploughing and harvest. Roosts communally in trees or "
                        "mangrove and commutes to feeding areas at dawn and back at dusk, often along the same flight lines. Numbers rise "
                        "in the wet season and during harvest."),
            "monthly_counts": [45, 52, 60, 38, 30, 22, 25, 28, 35, 48, 70, 58],
            "monthly_strikes": [6, 7, 8, 5, 3, 2, 2, 3, 4, 6, 9, 7],
            "diurnal": "Most strikes 05:30–08:00 and 17:00–18:30 local, matching roost commuting flights.",
            "mitigations": [
                {"text": "Long-grass policy on the runway strip (sward kept at 150–200 mm) so egrets cannot see or reach insects", "type": "Habitat", "owner": "Aerodrome operator", "status": "planned"},
                {"text": "Mow outside the dawn/dusk peaks and never ahead of arrival waves; patrol immediately after mowing", "type": "Habitat", "owner": "Aerodrome operator", "status": "planned"},
                {"text": "Dawn and dusk dispersal patrols with pyrotechnics and distress calls, logged with counts", "type": "Dispersal", "owner": "Aerodrome operator (wildlife unit)", "status": "existing"},
                {"text": "Agreement with neighbouring farmers: no cattle grazing inside the fence line and notice of ploughing/harvest on the approach", "type": "Land use", "owner": "Aerodrome operator & local government", "status": "planned"},
                {"text": "Map roost-to-feeding flight lines; alert TWR when commuting flocks cross the approach", "type": "Detection", "owner": "Wildlife unit & TWR", "status": "planned"},
                {"text": "ATC passes bird information (ATIS remark, real-time warnings on reported flocks); NOTAM for seasonal peaks", "type": "ATS", "owner": "AirNav TWR/APP", "status": "existing"},
                {"text": "Every strike reported with species identified (feather/DNA sample for unknown remains)", "type": "Reporting", "owner": "Aerodrome operator, airlines, AirNav", "status": "existing"},
            ],
        },
    },
    "attractants": [
        {"id": "AT-01", "site": "Runway strip and infield grass", "land_use": "Grass (short after mowing)", "distance_km": 0.0, "species": ["SP-01", "SP-02", "SP-03"], "action": "Long-grass policy; mowing schedule", "owner": "Aerodrome operator"},
        {"id": "AT-02", "site": "Grazing land beside the eastern fence", "land_use": "Cattle grazing", "distance_km": 0.8, "species": ["SP-01"], "action": "Grazing agreement; fence repair", "owner": "Aerodrome operator & village"},
        {"id": "AT-03", "site": "Rice fields under the RWY 27 approach", "land_use": "Rice fields (sawah)", "distance_km": 2.5, "species": ["SP-01", "SP-02", "SP-05"], "action": "Harvest/ploughing notice; patrols on approach days", "owner": "Local government (agriculture office)"},
        {"id": "AT-04", "site": "Fish and shrimp ponds, coastal side", "land_use": "Tambak (aquaculture)", "distance_km": 3.5, "species": ["SP-02", "SP-05"], "action": "Survey; netting of ponds under the approach", "owner": "Local government"},
        {"id": "AT-05", "site": "Egret roost (heronry) in mangrove", "land_use": "Roost / nesting colony", "distance_km": 6.0, "species": ["SP-01"], "action": "Map commuting flight lines; seasonal NOTAM", "owner": "Wildlife unit"},
        {"id": "AT-06", "site": "Municipal landfill (TPA)", "land_use": "Landfill", "distance_km": 9.0, "species": ["SP-01", "SP-06"], "action": "Daily cover; object to expansion in the planning forum", "owner": "Local government"},
        {"id": "AT-07", "site": "Fruit orchards, river valley", "land_use": "Orchard (fruit)", "distance_km": 14.0, "species": ["SP-06"], "action": "Monitor; outside 13 km circle", "owner": "—"},
    ],
}


def seed_wildlife(db: Session):
    """Add the wildlife worked example to the DEMO-02 assessment (also on databases created before this module existed)."""
    p = db.query(Project).filter_by(code="DEMO-02").first()
    if not p:
        return
    a = db.query(Assessment).filter_by(project_id=p.id).order_by(Assessment.id).first()
    if not a or db.query(Study).filter_by(assessment_id=a.id, method="wildlife").first():
        return
    db.add(Study(assessment_id=a.id, method="wildlife", title="Wildlife strike risk — cattle egret Bubulcus ibis (Manual §31.4)",
                 model=WILDLIFE_MODEL, results=wildlife.analyse(WILDLIFE_MODEL),
                 participants=[{"name": "Ayu Assessor", "role": "Facilitator"}, {"name": "Aerodrome wildlife officer", "role": "SME"},
                               {"name": "TWR ATCO", "role": "SME"}]))
    db.commit()
