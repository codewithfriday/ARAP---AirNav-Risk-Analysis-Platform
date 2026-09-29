"""Investigation expert system API: case library, search, fuzzy inference, Bayesian network, AI drafting (SRS §4.33)."""
from __future__ import annotations

import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import audit
from ..config import settings
from ..db import get_db
from ..engines import casebn, casesearch, draft as drafter, fuzzy
from ..investigation import CATEGORIES, FACTORS, THESAURUS, factor_index, meta
from ..models import Assessment, InvCase, Study, User
from ..security import EDITORS, current_user, require
from ..templates import METHODS as METHOD_CATALOG
from .common import ensure_editable, get_or_404, to_dict
from .ies_logic import analyse_study, bn_analysis, infer_cases, library, network, factor_ratings

router = APIRouter(prefix="/api")


def _cat(category: str) -> dict:
    if category not in CATEGORIES:
        raise HTTPException(422, f"unknown occurrence category {category}")
    return CATEGORIES[category]


def _check_model(m: dict):
    try:
        fuzzy.blocks_by_id(m)
        fuzzy.topo(m)
        for bid, rules in (m.get("rules") or {}).items():
            for r in rules:
                for i, terms in r.get("when", {}).items():
                    if any(t not in fuzzy.SUPPORT for t in terms):
                        raise fuzzy.FuzzyError(f"rule of {bid}: unknown term in {terms}")
    except fuzzy.FuzzyError as e:
        raise HTTPException(422, str(e))


def case_dict(c: InvCase, full: bool = True) -> dict:
    d = to_dict(c, exclude=() if full else ("model", "report_text"))
    blocks = c.model.get("blocks", [])
    d["n_blocks"] = len(blocks)
    d["unverified_quotes"] = sum(1 for b in blocks if b.get("quote") and b.get("quote_verified") is False)
    d["mechanism"] = casebn.case_mechanism(c.model)
    return d


# ------------------------------------------------------------------ meta
@router.get("/ies/meta")
def ies_meta(_: User = Depends(current_user)):
    return meta() | {"layers": fuzzy.LAYER_NAMES, "support_terms": fuzzy.SUPPORT_LABEL, "prob_terms": fuzzy.PROB_LABEL,
                     "crisp": fuzzy.CRISP, "ai_available": bool(settings.anthropic_api_key), "llm_model": settings.llm_model,
                     "engines": [fuzzy.ENGINE_VERSION, casebn.ENGINE_VERSION, casesearch.ENGINE_VERSION, drafter.ENGINE_VERSION]}


# ------------------------------------------------------------------ case library
class CaseIn(BaseModel):
    ref: str | None = None
    title: str
    category: str
    source: str = ""
    occurred: str = ""
    summary: str = ""
    model: dict | None = None


def _next_ref(db: Session) -> str:
    n = (db.query(func.count(InvCase.id)).scalar() or 0) + 1
    while db.query(InvCase).filter_by(ref=f"CASE-{n:03d}").first():
        n += 1
    return f"CASE-{n:03d}"


@router.get("/cases")
def list_cases(category: str | None = None, status: str | None = None, db: Session = Depends(get_db),
               _: User = Depends(current_user)):
    q = db.query(InvCase)
    if category:
        q = q.filter_by(category=category)
    if status:
        q = q.filter_by(status=status)
    return [case_dict(c, full=False) for c in q.order_by(InvCase.ref)]


@router.post("/cases")
def create_case(body: CaseIn, db: Session = Depends(get_db), u: User = Depends(require(*EDITORS))):
    _cat(body.category)
    m = body.model or {"blocks": [], "edges": [], "rules": {}}
    _check_model(m)
    ref = body.ref or _next_ref(db)
    if db.query(InvCase).filter_by(ref=ref).first():
        raise HTTPException(409, f"case {ref} already exists")
    c = InvCase(ref=ref, title=body.title, category=body.category, source=body.source, occurred=body.occurred,
                summary=body.summary, model=m, status="draft", provenance={"method": "manual"}, created_by=u.username)
    db.add(c); db.flush()
    audit.record(db, u.username, "case", c.id, "create", after={"ref": ref, "title": c.title}); db.commit()
    return case_dict(c)


@router.get("/cases/{cid}")
def get_case(cid: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    return case_dict(get_or_404(db, InvCase, cid))


@router.put("/cases/{cid}")
def update_case(cid: int, body: CaseIn, db: Session = Depends(get_db), u: User = Depends(require(*EDITORS))):
    c = get_or_404(db, InvCase, cid)
    _cat(body.category)
    m = body.model if body.model is not None else c.model
    _check_model(m)
    if c.report_text:
        drafter.verify_quotes(m, c.report_text)
    before = {"title": c.title, "status": c.status}
    c.title, c.category, c.source, c.occurred, c.summary, c.model = body.title, body.category, body.source, body.occurred, body.summary, m
    if body.ref and body.ref != c.ref:
        if db.query(InvCase).filter_by(ref=body.ref).first():
            raise HTTPException(409, f"case {body.ref} already exists")
        c.ref = body.ref
    if c.status == "approved":  # an edited case must be approved again before the engines use it
        c.status, c.approved_by = "draft", ""
    audit.record(db, u.username, "case", c.id, "update", before, {"title": c.title, "status": c.status}); db.commit()
    return case_dict(c)


@router.delete("/cases/{cid}")
def delete_case(cid: int, db: Session = Depends(get_db), u: User = Depends(require(*EDITORS))):
    c = get_or_404(db, InvCase, cid)
    if c.status == "approved" and u.role != "admin":
        raise HTTPException(403, "only an administrator can delete an approved case")
    audit.record(db, u.username, "case", c.id, "delete", before={"ref": c.ref, "title": c.title, "status": c.status})
    db.delete(c); db.commit()
    return {"deleted": c.ref}


def approval_problems(c: InvCase) -> list[str]:
    m = c.model
    probs = []
    blocks = m.get("blocks", [])
    if not any(b["kind"] == "evidence" for b in blocks):
        probs.append("no evidence block")
    fins = [b for b in blocks if b["kind"] == "finding"]
    if len(fins) != 1:
        probs.append("exactly one finding block is needed")
    elif casebn.case_mechanism(m) is None:
        probs.append("the finding must rate one mechanism Probable or higher")
    ins = fuzzy.inputs_of(m)
    for b in blocks:
        if b["kind"] != "evidence" and ins[b["id"]] and not (m.get("rules") or {}).get(b["id"]):
            probs.append(f"block {b['id']} has no rules")
    for b in blocks:
        if b.get("quote") and b.get("quote_verified") is False:
            probs.append(f"block {b['id']}: quote not found in the report text — correct or clear it")
    return probs


@router.post("/cases/{cid}/approve")
def approve_case(cid: int, db: Session = Depends(get_db), u: User = Depends(require("reviewer"))):
    c = get_or_404(db, InvCase, cid)
    if c.status == "approved":
        raise HTTPException(409, "case is already approved")
    probs = approval_problems(c)
    if probs:
        raise HTTPException(409, "cannot approve: " + "; ".join(probs))
    c.status, c.approved_by = "approved", u.username
    audit.record(db, u.username, "case", c.id, "approve", {"status": "draft"}, {"status": "approved"}); db.commit()
    return case_dict(c)


@router.post("/cases/{cid}/default-rules")
def case_default_rules(cid: int, db: Session = Depends(get_db), u: User = Depends(require(*EDITORS))):
    c = get_or_404(db, InvCase, cid)
    m = dict(c.model)
    try:
        m["rules"] = fuzzy.default_rules(m)
    except fuzzy.FuzzyError as e:
        raise HTTPException(422, str(e))
    c.model = m
    if c.status == "approved":
        c.status, c.approved_by = "draft", ""
    audit.record(db, u.username, "case", c.id, "update", {"rules": "…"}, {"rules": "default"}); db.commit()
    return case_dict(c)


# ------------------------------------------------------------------ drafting (phase 3)
class DraftIn(BaseModel):
    category: str
    title: str
    source: str = ""
    text: str
    use_ai: bool = False


def _draft(db: Session, u: User, category: str, title: str, source: str, text: str, use_ai: bool) -> dict:
    cat = _cat(category)
    if use_ai and not settings.anthropic_api_key:
        raise HTTPException(422, "AI drafting is not configured on this server (ARAP_ANTHROPIC_API_KEY); use the offline drafter")
    if len(text.strip()) < 200:
        raise HTTPException(422, "the report text is too short to draft from")
    try:
        d = drafter.draft(text, cat, FACTORS[category], casesearch.Normaliser(THESAURUS), use_ai=use_ai,
                          key=settings.anthropic_api_key, model_name=settings.llm_model, url=settings.llm_url)
    except drafter.DraftError as e:
        raise HTTPException(422, str(e))
    c = InvCase(ref=_next_ref(db), title=title, category=category, source=source, summary=d["summary"], report_text=text,
                model=d["model"], status="draft", created_by=u.username,
                provenance={"method": d["method"], "model": settings.llm_model if d["method"] == "llm" else None,
                            "engine": d["engine_version"], "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            "unverified_quotes": d["unverified_quotes"], "mechanism": d["mechanism"]})
    db.add(c); db.flush()
    audit.record(db, u.username, "case", c.id, "draft", after={"ref": c.ref, "method": d["method"]}); db.commit()
    return case_dict(c)


@router.post("/cases/draft")
def draft_case(body: DraftIn, db: Session = Depends(get_db), u: User = Depends(require(*EDITORS))):
    return _draft(db, u, body.category, body.title, body.source, body.text, body.use_ai)


@router.post("/cases/draft-pdf")
async def draft_case_pdf(file: UploadFile = File(...), category: str = Form(...), title: str = Form(...), source: str = Form(""),
                         use_ai: bool = Form(False), db: Session = Depends(get_db), u: User = Depends(require(*EDITORS))):
    data = await file.read()
    if len(data) > 30 * 1024 * 1024:
        raise HTTPException(413, "PDF larger than 30 MB")
    try:
        from pypdf import PdfReader
        text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
    except Exception as e:
        raise HTTPException(422, f"could not read the PDF: {e}")
    return _draft(db, u, category, title, source or file.filename or "", text, use_ai)


# ------------------------------------------------------------------ search, inference, network
class SearchIn(BaseModel):
    category: str
    text: str
    include_drafts: bool = False
    limit: int = 10


@router.post("/ies/search")
def ies_search(body: SearchIn, db: Session = Depends(get_db), _: User = Depends(current_user)):
    _cat(body.category)
    cases = [{"id": c.id, "ref": c.ref, "title": c.title, "summary": c.summary, "status": c.status, "model": c.model}
             for c in library(db, body.category, body.include_drafts)]
    return casesearch.search(body.text, cases, FACTORS[body.category], THESAURUS, body.limit)


class InferIn(BaseModel):
    case_ids: list[int]
    ratings: dict[str, str] = {}


@router.post("/ies/infer")
def ies_infer(body: InferIn, db: Session = Depends(get_db), _: User = Depends(current_user)):
    cases = db.query(InvCase).filter(InvCase.id.in_(body.case_ids)).order_by(InvCase.ref).all()
    try:
        return infer_cases(cases, body.ratings)
    except fuzzy.FuzzyError as e:
        raise HTTPException(422, str(e))


class InferModelIn(BaseModel):
    model: dict
    states: dict[str, str | None] = {}
    category: str | None = None


@router.post("/ies/infer-model")
def ies_infer_model(body: InferModelIn, _: User = Depends(current_user)):
    """Run one AcciMap with given evidence states (used by the case editor to test its rules)."""
    mechs = [m["code"] for m in CATEGORIES.get(body.category or "", {}).get("mechanisms", [])] or None
    try:
        return fuzzy.infer(body.model, body.states, mechs)
    except fuzzy.FuzzyError as e:
        raise HTTPException(422, str(e))


class RulesIn(BaseModel):
    model: dict


@router.post("/ies/default-rules")
def ies_default_rules(body: RulesIn, _: User = Depends(current_user)):
    """Default rule set for an (unsaved) AcciMap: confirming, weakening and contradicting rules per derived block."""
    try:
        fuzzy.topo(body.model)
        return fuzzy.default_rules(body.model)
    except fuzzy.FuzzyError as e:
        raise HTTPException(422, str(e))


class BNIn(BaseModel):
    category: str
    ratings: dict[str, str] = {}


@router.post("/ies/bn")
def ies_bn(body: BNIn, db: Session = Depends(get_db), _: User = Depends(current_user)):
    _cat(body.category)
    try:
        return bn_analysis(db, body.category, body.ratings)
    except casebn.CaseBNError as e:
        raise HTTPException(422, str(e))


class AnalyseIn(BaseModel):
    model: dict


@router.post("/ies/analyse")
def ies_analyse(body: AnalyseIn, db: Session = Depends(get_db), _: User = Depends(current_user)):
    _cat(body.model.get("category", ""))
    try:
        return analyse_study(db, body.model)
    except (fuzzy.FuzzyError, casebn.CaseBNError) as e:
        raise HTTPException(422, str(e))


class ExportIn(BaseModel):
    assessment_id: int
    category: str
    ratings: dict[str, str] = {}
    title: str | None = None


@router.post("/ies/bn/export")
def ies_bn_export(body: ExportIn, db: Session = Depends(get_db), u: User = Depends(require(*EDITORS))):
    """Create a Bayesian-network study (Manual Ch. 17) holding the learned network and the current ratings."""
    cat = _cat(body.category)
    a = get_or_404(db, Assessment, body.assessment_id); ensure_editable(a)
    net = network(db, body.category)
    labels = {f: x["label"] for f, x in factor_index(body.category).items()}
    exp = casebn.to_bbn(net, factor_ratings(body.ratings), labels)
    ids = [n["id"] for n in exp["network"]["nodes"]]
    pos = {"C": [0, 0]}
    fnodes = [i for i in ids if i.startswith("F_")]
    for k, nid in enumerate(fnodes):
        pos[nid] = [(k - len(fnodes) / 2) * 190, 220]
        if f"obs_{nid}" in ids:
            pos[f"obs_{nid}"] = [(k - len(fnodes) / 2) * 190, 440]
    s = Study(assessment_id=a.id, method="bbn", title=body.title or f"Case-library Bayesian network — {cat['name']}",
              model={"network": exp["network"], "positions": pos, "evidence": exp["evidence"]}, results={},
              template_version=METHOD_CATALOG["bbn"]["template_version"])
    db.add(s); db.flush()
    audit.record(db, u.username, "study", s.id, "create", after={"method": "bbn", "title": s.title, "from": "ies"}); db.commit()
    return to_dict(s)
