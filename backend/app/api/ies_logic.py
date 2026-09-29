"""Investigation expert system — analysis of an investigation study (fuzzy per case + Bayesian network)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..engines import casebn, fuzzy
from ..investigation import CATEGORIES, factor_index
from ..models import InvCase


def rating_key(case_id: int, block: dict) -> str:
    return f"f:{block['factor']}" if block.get("factor") else f"b:{case_id}:{block['id']}"


def case_states(case: InvCase, ratings: dict[str, str]) -> dict[str, str | None]:
    ins = fuzzy.inputs_of(case.model)
    out = {}
    for b in case.model.get("blocks", []):
        if b["kind"] == "evidence" or not ins[b["id"]]:
            t = ratings.get(rating_key(case.id, b))
            out[b["id"]] = t if t in fuzzy.CRISP else None
    return out


def infer_cases(cases: list[InvCase], ratings: dict[str, str]) -> dict:
    per_case, clues = [], {}
    for c in cases:
        mechs = [m["code"] for m in CATEGORIES.get(c.category, {}).get("mechanisms", [])]
        r = fuzzy.infer(c.model, case_states(c, ratings), mechs or None)
        blocks = {b["id"]: b for b in c.model["blocks"]}
        findings = []
        for bid, br in r["blocks"].items():
            if br["kind"] == "finding":
                outs = {m: o for m, o in br["outputs"].items() if o["crisp"] is not None}
                findings.append({"block": bid, "label": blocks[bid]["label"], "determined": br["determined"],
                                 "outputs": {m: {"crisp": round(o["crisp"], 3), "term": o["term"]} for m, o in outs.items()}})
        for cl in r["clues"]:
            b = blocks[cl["block"]]
            k = rating_key(c.id, b)
            e = clues.setdefault(k, {"key": k, "label": cl["label"], "layer": cl["layer"], "factor": cl.get("factor"),
                                     "cases": [], "priority": 0.0})
            e["cases"].append({"id": c.id, "ref": c.ref, "for": [blocks[x]["label"] for x in cl["for"] if x in blocks]})
            e["priority"] = max(e["priority"], cl["priority"])
        per_case.append({"id": c.id, "ref": c.ref, "title": c.title, "blocks": _round(r["blocks"]), "findings": findings,
                         "clues": r["clues"]})
    cl = sorted(clues.values(), key=lambda x: (-x["priority"], -len(x["cases"])))
    return {"cases": per_case, "clues": cl, "engine_version": fuzzy.ENGINE_VERSION}


def _round(blocks: dict) -> dict:
    out = {}
    for k, v in blocks.items():
        v = dict(v)
        if v.get("crisp") is not None:
            v["crisp"] = round(v["crisp"], 3)
        if "outputs" in v:
            v["outputs"] = {m: {"crisp": (round(o["crisp"], 3) if o["crisp"] is not None else None), "term": o["term"]}
                            for m, o in v["outputs"].items()}
        out[k] = v
    return out


def library(db: Session, category: str, include_drafts: bool = False) -> list[InvCase]:
    q = db.query(InvCase).filter_by(category=category)
    if not include_drafts:
        q = q.filter_by(status="approved")
    return q.order_by(InvCase.ref).all()


def network(db: Session, category: str) -> dict:
    cases = library(db, category)
    mechs = [m["code"] for m in CATEGORIES[category]["mechanisms"]]
    return casebn.learn([{"id": c.id, "ref": c.ref, "model": c.model} for c in cases], mechs,
                        [f["code"] for f in factor_index(category).values()])


def factor_ratings(ratings: dict[str, str]) -> dict[str, str]:
    return {k[2:]: v for k, v in (ratings or {}).items() if k.startswith("f:") and v in fuzzy.CRISP}


def bn_analysis(db: Session, category: str, ratings: dict[str, str]) -> dict:
    net = network(db, category)
    fi = factor_index(category)
    res = casebn.analyse(net, factor_ratings(ratings), fi)
    labels = {m["code"]: m["label"] for m in CATEGORIES[category]["mechanisms"]}
    res["mechanism_labels"] = labels
    return res


def analyse_study(db: Session, model: dict) -> dict:
    cat = model.get("category")
    if cat not in CATEGORIES:
        return {}
    ratings = model.get("ratings") or {}
    sel = [c for c in db.query(InvCase).filter(InvCase.id.in_(model.get("selected") or [])).order_by(InvCase.ref)]
    return {"fuzzy": infer_cases(sel, ratings), "bn": bn_analysis(db, cat, ratings),
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
