"""REST API. All routes are mounted under /api."""
from __future__ import annotations

import copy
import csv
import difflib
import io
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import audit
from ..db import get_db
from ..engines import bbn, crm, eta, fatigue, fmea, fta, hra, lopa, orc, rbd, security, sej, sim, wildlife
from ..engines import risk as risk_engine
from ..models import (ASSESSMENT_STATES, LOCKED_STATES, METHODS, ROLES, Action, Approval, Assessment, AuditLog, Control, Hazard,
                      Project, RiskScheme, Study, User)
from ..reports import assessment_docx
from ..security import EDITORS, create_token, current_user, hash_password, require, verify_password
from ..templates import METHODS as METHOD_CATALOG
from ..assessment_templates import TEMPLATES as ASSESSMENT_TEMPLATES, catalogue as assessment_templates_catalogue
from .common import (active_scheme, ensure_editable, get_or_404, hazard_dict, next_ref, overdue_actions, rate,
                     scheme_version, to_dict)

router = APIRouter(prefix="/api")


# ================================================================ auth & users
@router.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    u = db.query(User).filter_by(username=form.username, active=True).first()
    if not u or not verify_password(form.password, u.password_hash):
        raise HTTPException(401, "Incorrect username or password")
    return {"access_token": create_token(u.username), "token_type": "bearer"}


@router.get("/auth/me")
def me(u: User = Depends(current_user)):
    return to_dict(u, exclude=("password_hash",))


class UserIn(BaseModel):
    username: str
    full_name: str = ""
    email: str = ""
    role: str = "viewer"
    unit: str = ""
    authority_scope: list[str] = []
    lang: str = "en"
    active: bool = True
    password: str | None = None


@router.get("/users")
def list_users(db: Session = Depends(get_db), u: User = Depends(require("reviewer"))):
    return [to_dict(x, exclude=("password_hash",)) for x in db.query(User).order_by(User.username)]


@router.post("/users")
def create_user(body: UserIn, db: Session = Depends(get_db), u: User = Depends(require())):
    if body.role not in ROLES:
        raise HTTPException(422, "unknown role")
    if db.query(User).filter_by(username=body.username).first():
        raise HTTPException(409, "username exists")
    if not body.password or len(body.password) < 8:
        raise HTTPException(422, "password of at least 8 characters required")
    x = User(**body.model_dump(exclude={"password"}), password_hash=hash_password(body.password))
    db.add(x); db.flush()
    audit.record(db, u.username, "user", x.id, "create", after=to_dict(x, exclude=("password_hash",)))
    db.commit()
    return to_dict(x, exclude=("password_hash",))


@router.put("/users/{uid}")
def update_user(uid: int, body: UserIn, db: Session = Depends(get_db), u: User = Depends(require())):
    x = get_or_404(db, User, uid)
    before = to_dict(x, exclude=("password_hash",))
    for k, v in body.model_dump(exclude={"password", "username"}).items():
        setattr(x, k, v)
    if body.password:
        x.password_hash = hash_password(body.password)
    audit.record(db, u.username, "user", x.id, "update", before, to_dict(x, exclude=("password_hash",)))
    db.commit()
    return to_dict(x, exclude=("password_hash",))


# ================================================================ meta & risk scheme
@router.get("/meta/methods")
def methods(_: User = Depends(current_user)):
    return METHOD_CATALOG


@router.get("/meta/engines")
def engines(_: User = Depends(current_user)):
    return {"risk": risk_engine.ENGINE_VERSION, "fta": fta.ENGINE_VERSION, "lopa": lopa.ENGINE_VERSION,
            "fmea": fmea.ENGINE_VERSION, "bbn": bbn.ENGINE_VERSION, "fatigue": fatigue.ENGINE_VERSION,
            "crm": crm.ENGINE_VERSION, "eta": eta.ENGINE_VERSION, "hra": hra.ENGINE_VERSION, "orc": orc.ENGINE_VERSION,
            "rbd": rbd.ENGINE_VERSION, "sej": sej.ENGINE_VERSION, "sim": sim.ENGINE_VERSION, "security": security.ENGINE_VERSION}


@router.get("/risk/scheme")
def get_scheme(db: Session = Depends(get_db), _: User = Depends(current_user)):
    rs = db.query(RiskScheme).order_by(RiskScheme.version.desc()).first()
    return {"version": rs.version if rs else 1, "data": active_scheme(db)}


@router.put("/risk/scheme")
def put_scheme(data: dict, db: Session = Depends(get_db), u: User = Depends(require())):
    # validate: every cell mapped exactly once
    cells = [c for r in data["regions"] for c in r["cells"]]
    expected = {f"{l['level']}{s['code']}" for l in data["likelihood"] for s in data["severity"]}
    if set(cells) != expected or len(cells) != len(expected):
        raise HTTPException(422, "every matrix cell must belong to exactly one region")
    last = db.query(RiskScheme).order_by(RiskScheme.version.desc()).first()
    v = (last.version if last else 0) + 1
    data["version"] = v
    db.add(RiskScheme(version=v, data=data, created_by=u.username))
    audit.record(db, u.username, "risk_scheme", v, "create", after={"version": v})
    db.commit()
    return {"version": v, "data": data}


class ClassifyIn(BaseModel):
    severity: str
    likelihood: int


@router.post("/risk/classify")
def classify(body: ClassifyIn, db: Session = Depends(get_db), _: User = Depends(current_user)):
    try:
        return risk_engine.classify(body.severity, body.likelihood, active_scheme(db))
    except ValueError as e:
        raise HTTPException(422, str(e))


# ================================================================ projects
class ProjectIn(BaseModel):
    code: str
    title: str
    change_type: str = "system"
    units: str = ""
    sponsor: str = ""
    description: str = ""
    status: str = "active"


@router.get("/projects")
def list_projects(include_archived: bool = False, db: Session = Depends(get_db), _: User = Depends(current_user)):
    out = []
    q = db.query(Project)
    if not include_archived:
        q = q.filter(Project.status != "archived")
    for p in q.order_by(Project.created_at.desc()):
        d = to_dict(p)
        d["assessment_count"] = len(p.assessments)
        out.append(d)
    return out


@router.post("/projects")
def create_project(body: ProjectIn, db: Session = Depends(get_db), u: User = Depends(require(*EDITORS))):
    if db.query(Project).filter_by(code=body.code).first():
        raise HTTPException(409, "project code exists")
    p = Project(**body.model_dump()); db.add(p); db.flush()
    audit.record(db, u.username, "project", p.id, "create", after=to_dict(p)); db.commit()
    return to_dict(p)


@router.get("/projects/{pid}")
def get_project(pid: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    p = get_or_404(db, Project, pid)
    d = to_dict(p)
    d["assessments"] = [to_dict(a) | {"study_count": len(a.studies)} for a in p.assessments]
    return d


@router.post("/projects/{pid}/archive")
def archive_project(pid: int, db: Session = Depends(get_db), u: User = Depends(require(*EDITORS))):
    """Hide a project from the project list; all records are kept and it can be restored (SRS COM-17)."""
    p = get_or_404(db, Project, pid)
    if p.status == "archived":
        raise HTTPException(409, "project is already archived")
    before = to_dict(p); p.status = "archived"
    audit.record(db, u.username, "project", p.id, "archive", before, to_dict(p)); db.commit()
    return to_dict(p)


@router.post("/projects/{pid}/restore")
def restore_project(pid: int, db: Session = Depends(get_db), u: User = Depends(require(*EDITORS))):
    p = get_or_404(db, Project, pid)
    if p.status != "archived":
        raise HTTPException(409, "project is not archived")
    before = to_dict(p); p.status = "active"
    audit.record(db, u.username, "project", p.id, "restore", before, to_dict(p)); db.commit()
    return to_dict(p)


@router.delete("/projects/{pid}")
def delete_project(pid: int, confirm: str = Query(..., description="The project code, typed to confirm"),
                   db: Session = Depends(get_db), u: User = Depends(require("admin"))):
    """Permanently delete a project and everything in it (SRS COM-18). Admin only; the project code must be typed to
    confirm; refused if any assessment has been endorsed, accepted, closed or superseded — those are safety records."""
    p = get_or_404(db, Project, pid)
    if confirm.strip() != p.code:
        raise HTTPException(422, "confirmation does not match the project code")
    locked = [a for a in p.assessments if a.status in LOCKED_STATES]
    if locked:
        raise HTTPException(409, f"cannot delete: {len(locked)} assessment(s) are {', '.join(sorted({a.status for a in locked}))}. "
                                 "Endorsed, accepted, closed and superseded assessments are safety records — archive the project instead.")
    aids = [a.id for a in p.assessments]
    hz = db.query(Hazard).filter(Hazard.assessment_id.in_(aids)).all() if aids else []
    hids = [h.id for h in hz]
    counts = {"assessments": len(aids), "studies": sum(len(a.studies) for a in p.assessments), "hazards": len(hids)}
    if aids or hids:
        acts = db.query(Action).filter((Action.assessment_id.in_(aids)) | (Action.hazard_id.in_(hids or [-1])))
        counts["actions"] = acts.count(); acts.delete(synchronize_session=False)
        if hids:
            db.query(Control).filter(Control.hazard_id.in_(hids)).delete(synchronize_session=False)
            db.query(Hazard).filter(Hazard.id.in_(hids)).delete(synchronize_session=False)
    snap = to_dict(p)
    db.delete(p)  # cascades to assessments → studies and approvals
    audit.record(db, u.username, "project", pid, "delete", before={**snap, "deleted": counts})
    db.commit()
    return {"deleted": snap["code"], **counts}


@router.put("/projects/{pid}")
def update_project(pid: int, body: ProjectIn, db: Session = Depends(get_db), u: User = Depends(require(*EDITORS))):
    p = get_or_404(db, Project, pid); before = to_dict(p)
    for k, v in body.model_dump().items():
        setattr(p, k, v)
    audit.record(db, u.username, "project", p.id, "update", before, to_dict(p)); db.commit()
    return to_dict(p)


# ================================================================ assessments & workflow
class AssessmentIn(BaseModel):
    project_id: int
    title: str
    scope: str = ""
    environment: str = ""
    assumptions: str = ""
    template: str | None = None


def assessment_full(a: Assessment, db: Session) -> dict:
    d = to_dict(a)
    d["locked"] = a.locked
    d["project"] = {"id": a.project.id, "code": a.project.code, "title": a.project.title}
    d["studies"] = [to_dict(s, exclude=("model", "results")) for s in a.studies]
    d["approvals"] = [to_dict(x) for x in a.approvals]
    scheme = scheme_version(db, a.risk_scheme_version)
    hz = db.query(Hazard).filter_by(assessment_id=a.id).all()
    d["hazards"] = [hazard_dict(h, scheme) for h in hz]
    regions = [(h["residual_risk"] or h["initial_risk"] or {}).get("region") for h in d["hazards"]]
    worst = risk_engine.worst_region([r for r in regions if r], scheme)
    d["worst_residual_region"] = worst
    d["required_authority"] = next((r["authority"] for r in scheme["regions"] if r["key"] == worst), None)
    d["actions"] = [to_dict(x) for x in db.query(Action).filter_by(assessment_id=a.id)]
    return d


@router.get("/assessments")
def list_assessments(status: str | None = None, include_archived: bool = False, db: Session = Depends(get_db),
                     _: User = Depends(current_user)):
    q = db.query(Assessment).join(Project)
    if status:
        q = q.filter(Assessment.status == status)
    if not include_archived:
        q = q.filter(Project.status != "archived")
    return [to_dict(a) | {"project_code": a.project.code, "project_status": a.project.status, "locked": a.locked}
            for a in q.order_by(Assessment.updated_at.desc())]


@router.post("/assessments")
def create_assessment(body: AssessmentIn, db: Session = Depends(get_db), u: User = Depends(require(*EDITORS))):
    if get_or_404(db, Project, body.project_id).status == "archived":
        raise HTTPException(409, "the project is archived — restore it before adding assessments")
    rs = db.query(RiskScheme).order_by(RiskScheme.version.desc()).first()
    tpl = None
    if body.template:
        tpl = ASSESSMENT_TEMPLATES.get(body.template)
        if not tpl:
            raise HTTPException(422, f"unknown assessment template {body.template}")
    a = Assessment(**body.model_dump(exclude={"template"}), created_by=u.username, risk_scheme_version=rs.version if rs else 1)
    db.add(a); db.flush()
    audit.record(db, u.username, "assessment", a.id, "create", after={**to_dict(a), "template": body.template}); db.commit()
    if tpl:
        tpl["build"](db, a, filled=False)
        db.commit()
    return assessment_full(a, db)


@router.get("/assessment-templates")
def list_assessment_templates(_: User = Depends(current_user)):
    return assessment_templates_catalogue()


@router.get("/assessments/{aid}")
def get_assessment(aid: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    return assessment_full(get_or_404(db, Assessment, aid), db)


@router.put("/assessments/{aid}")
def update_assessment(aid: int, body: AssessmentIn, db: Session = Depends(get_db), u: User = Depends(require(*EDITORS))):
    a = get_or_404(db, Assessment, aid); ensure_editable(a); before = to_dict(a)
    for k, v in body.model_dump(exclude={"project_id"}).items():
        setattr(a, k, v)
    audit.record(db, u.username, "assessment", a.id, "update", before, to_dict(a)); db.commit()
    return assessment_full(a, db)


TRANSITIONS = {  # action: (from states, to state, roles)
    "submit": (("draft", "rejected"), "in_review", ("assessor", "reviewer")),
    "return": (("in_review",), "draft", ("reviewer",)),
    "endorse": (("in_review",), "endorsed", ("reviewer",)),
    "accept": (("endorsed",), "accepted", ("authority",)),
    "reject": (("endorsed", "in_review"), "rejected", ("reviewer", "authority")),
    "close": (("accepted",), "closed", ("reviewer", "authority")),
}


class TransitionIn(BaseModel):
    action: str
    comment: str = ""


@router.post("/assessments/{aid}/transition")
def transition(aid: int, body: TransitionIn, db: Session = Depends(get_db), u: User = Depends(current_user)):
    a = get_or_404(db, Assessment, aid)
    if body.action not in TRANSITIONS:
        raise HTTPException(422, "unknown action")
    frm, to, roles = TRANSITIONS[body.action]
    if a.status not in frm:
        raise HTTPException(409, f"cannot {body.action} an assessment in status {a.status}")
    if u.role not in roles and u.role != "admin":
        raise HTTPException(403, f"'{body.action}' requires role {', '.join(roles)}")
    if body.action in ("return", "reject") and not body.comment.strip():
        raise HTTPException(422, "a comment is required when returning or rejecting")
    if body.action == "accept":
        full = assessment_full(a, db)
        worst = full["worst_residual_region"]
        if worst == "intolerable":
            raise HTTPException(409, "assessment contains an intolerable residual risk and cannot be accepted")
        if worst and u.role != "admin" and worst not in (u.authority_scope or []):
            raise HTTPException(403, f"residual risk region '{worst}' requires {full['required_authority']}")
        if not full["hazards"]:
            raise HTTPException(409, "an assessment with no hazards in the hazard log cannot be accepted")
        missing = [h["ref"] for h in full["hazards"] if not h["residual_risk"] and not h["initial_risk"]]
        if missing:
            raise HTTPException(409, f"hazards without a risk assessment: {', '.join(missing)}")
    db.add(Approval(assessment_id=a.id, action=body.action, from_status=a.status, to_status=to,
                    username=u.username, comment=body.comment))
    before = a.status; a.status = to
    audit.record(db, u.username, "assessment", a.id, body.action, {"status": before}, {"status": to}); db.commit()
    return assessment_full(a, db)


@router.post("/assessments/{aid}/new-version")
def new_version(aid: int, db: Session = Depends(get_db), u: User = Depends(require(*EDITORS))):
    a = get_or_404(db, Assessment, aid)
    if not a.locked:
        raise HTTPException(409, "only locked assessments need a new version")
    b = Assessment(project_id=a.project_id, title=a.title, scope=a.scope, environment=a.environment,
                   assumptions=a.assumptions, version=a.version + 1, previous_id=a.id, created_by=u.username,
                   risk_scheme_version=a.risk_scheme_version)
    db.add(b); db.flush()
    for s in a.studies:
        db.add(Study(assessment_id=b.id, method=s.method, title=s.title, template_version=s.template_version,
                     participants=copy.deepcopy(s.participants), sessions=[], model=copy.deepcopy(s.model),
                     results=copy.deepcopy(s.results)))
    for h in db.query(Hazard).filter_by(assessment_id=a.id):
        h.assessment_id = b.id  # hazard log entries follow the live version
    if a.status != "closed":
        a.status = "superseded"
    audit.record(db, u.username, "assessment", b.id, "new_version", after={"previous_id": a.id, "version": b.version})
    db.commit()
    return assessment_full(b, db)


@router.get("/assessments/{aid}/report.docx")
def report(aid: int, db: Session = Depends(get_db), u: User = Depends(current_user)):
    a = get_or_404(db, Assessment, aid)
    data = assessment_full(a, db)
    studies = [to_dict(s) for s in a.studies]
    content = assessment_docx(data, studies, engines(u))
    audit.record(db, u.username, "assessment", a.id, "export", after={"format": "docx"}); db.commit()
    return Response(content, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="NAVRAP-{a.project.code}-A{a.id}-v{a.version}.docx"'})


# ================================================================ studies
class StudyIn(BaseModel):
    assessment_id: int
    method: str
    title: str
    participants: list = []


class StudyUpdate(BaseModel):
    title: str | None = None
    status: str | None = None
    participants: list | None = None
    sessions: list | None = None
    model: dict | None = None
    results: dict | None = None


@router.post("/studies")
def create_study(body: StudyIn, db: Session = Depends(get_db), u: User = Depends(require(*EDITORS))):
    if body.method not in METHODS:
        raise HTTPException(422, "unknown method")
    a = get_or_404(db, Assessment, body.assessment_id); ensure_editable(a)
    s = Study(**body.model_dump(), model={}, template_version=METHOD_CATALOG[body.method]["template_version"])
    db.add(s); db.flush()
    audit.record(db, u.username, "study", s.id, "create", after={"method": s.method, "title": s.title}); db.commit()
    return to_dict(s)


@router.get("/studies")
def list_studies(method: str | None = None, db: Session = Depends(get_db), _: User = Depends(current_user)):
    """Index of all studies (id, method, title, status, assessment) — used to link GSN solutions to evidence."""
    q = db.query(Study)
    if method:
        q = q.filter_by(method=method)
    return [{"id": s.id, "method": s.method, "title": s.title, "status": s.status,
             "assessment": {"id": s.assessment.id, "title": s.assessment.title, "status": s.assessment.status}}
            for s in q.order_by(Study.id)]


@router.get("/studies/{sid}")
def get_study(sid: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    s = get_or_404(db, Study, sid)
    d = to_dict(s)
    d["locked"] = s.assessment.locked
    d["assessment"] = {"id": s.assessment.id, "title": s.assessment.title, "status": s.assessment.status}
    return d


@router.put("/studies/{sid}")
def update_study(sid: int, body: StudyUpdate, db: Session = Depends(get_db), u: User = Depends(require(*EDITORS))):
    s = get_or_404(db, Study, sid); ensure_editable(s.assessment)
    before = {"title": s.title, "status": s.status}
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(s, k, v)
    audit.record(db, u.username, "study", s.id, "update", before | {"model": "…"}, {"title": s.title, "status": s.status, "model": "updated" if body.model is not None else "…"})
    db.commit()
    return to_dict(s)


@router.delete("/studies/{sid}")
def delete_study(sid: int, db: Session = Depends(get_db), u: User = Depends(require(*EDITORS))):
    s = get_or_404(db, Study, sid); ensure_editable(s.assessment)
    audit.record(db, u.username, "study", s.id, "delete", before={"method": s.method, "title": s.title})
    db.delete(s); db.commit()
    return {"ok": True}


class PromoteRow(BaseModel):
    row_id: str = ""
    title: str
    causes: str = ""
    consequences: str = ""
    controls: list[str] = []
    severity: str | None = None
    likelihood: int | None = None
    owner: str = ""
    unit: str = ""
    system: str = ""


@router.post("/studies/{sid}/promote")
def promote(sid: int, rows: list[PromoteRow], db: Session = Depends(get_db), u: User = Depends(require(*EDITORS))):
    """Create hazard-log entries from worksheet rows or bowtie elements (COM-05)."""
    s = get_or_404(db, Study, sid); ensure_editable(s.assessment)
    scheme = active_scheme(db)
    created = []
    for r in rows:
        existing = db.query(Hazard).filter_by(source_study_id=s.id, source_row=r.row_id).first() if r.row_id else None
        h = existing or Hazard(ref=next_ref(db, Hazard, "HZ"), source_study_id=s.id, source_row=r.row_id,
                               assessment_id=s.assessment_id)
        h.title, h.causes, h.consequences = r.title, r.causes, r.consequences
        h.owner, h.unit, h.system = r.owner, r.unit, r.system
        h.initial_severity, h.initial_likelihood = r.severity, r.likelihood
        if not existing:
            db.add(h); db.flush()
            for c in r.controls:
                if c.strip():
                    db.add(Control(hazard_id=h.id, text=c.strip()))
        db.flush()
        audit.record(db, u.username, "hazard", h.id, "update" if existing else "create", after={"ref": h.ref, "title": h.title})
        created.append(h)
    db.commit()
    return [hazard_dict(h, scheme) for h in created]


# ================================================================ hazard log
class ControlIn(BaseModel):
    text: str
    kind: str = "procedure"
    side: str = "prevention"
    owner: str = ""
    verification: str = "existing-unverified"
    effectiveness: str = "unknown"
    critical: bool = False
    spi: str = ""


class HazardIn(BaseModel):
    title: str
    description: str = ""
    causes: str = ""
    consequences: str = ""
    context: str = ""
    unit: str = ""
    system: str = ""
    owner: str = ""
    status: str = "open"
    review_date: date | None = None
    assessment_id: int | None = None
    initial_severity: str | None = None
    initial_likelihood: int | None = None
    residual_severity: str | None = None
    residual_likelihood: int | None = None
    rationale: str = ""
    evidence: str = ""
    controls: list[ControlIn] | None = None


def _check_rating(body: HazardIn):
    for s, l in ((body.initial_severity, body.initial_likelihood), (body.residual_severity, body.residual_likelihood)):
        if (s is None) != (l is None):
            raise HTTPException(422, "severity and likelihood must be given together")
    if body.residual_severity and not body.rationale.strip():
        raise HTTPException(422, "a rationale is required for every risk judgement (COM-08)")


@router.get("/hazards")
def list_hazards(q: str | None = None, region: str | None = None, unit: str | None = None, status: str | None = None,
                 db: Session = Depends(get_db), _: User = Depends(current_user)):
    scheme = active_scheme(db)
    out = []
    qry = db.query(Hazard)
    if unit:
        qry = qry.filter(Hazard.unit.ilike(f"%{unit}%"))
    if status:
        qry = qry.filter_by(status=status)
    for h in qry.order_by(Hazard.ref):
        d = hazard_dict(h, scheme)
        if q and q.lower() not in (h.ref + h.title + h.description + h.causes + h.consequences).lower():
            continue
        cur = d["residual_risk"] or d["initial_risk"]
        if region and (not cur or cur["region"] != region):
            continue
        d["current_risk"] = cur
        d["review_overdue"] = bool(h.review_date and h.review_date < date.today())
        out.append(d)
    return out


@router.get("/hazards/similar")
def similar(text: str, db: Session = Depends(get_db), _: User = Depends(current_user)):
    """Duplicate detection (COM-06). Uses difflib locally; pg_trgm similarity is used on PostgreSQL deployments."""
    res = []
    for h in db.query(Hazard):
        r = difflib.SequenceMatcher(None, text.lower(), h.title.lower()).ratio()
        if r >= 0.6:
            res.append({"id": h.id, "ref": h.ref, "title": h.title, "similarity": round(r, 3)})
    return sorted(res, key=lambda x: -x["similarity"])[:10]


@router.get("/hazards/export.csv")
def export_hazards(db: Session = Depends(get_db), _: User = Depends(current_user)):
    rows = list_hazards(db=db, _=_)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["ref", "title", "unit", "system", "owner", "status", "initial", "residual", "region", "review_date", "controls"])
    for h in rows:
        cur = h["current_risk"] or {}
        w.writerow([h["ref"], h["title"], h["unit"], h["system"], h["owner"], h["status"],
                    (h["initial_risk"] or {}).get("index", ""), (h["residual_risk"] or {}).get("index", ""),
                    cur.get("region_name", ""), h["review_date"] or "", " | ".join(c["text"] for c in h["controls"])])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": 'attachment; filename="hazard-log.csv"'})


@router.post("/hazards")
def create_hazard(body: HazardIn, db: Session = Depends(get_db), u: User = Depends(require(*EDITORS))):
    _check_rating(body)
    if body.assessment_id:
        ensure_editable(get_or_404(db, Assessment, body.assessment_id))
    h = Hazard(ref=next_ref(db, Hazard, "HZ"), **body.model_dump(exclude={"controls"}))
    db.add(h); db.flush()
    for c in body.controls or []:
        db.add(Control(hazard_id=h.id, **c.model_dump()))
    audit.record(db, u.username, "hazard", h.id, "create", after={"ref": h.ref, "title": h.title}); db.commit()
    db.refresh(h)
    return hazard_dict(h, active_scheme(db))


@router.get("/hazards/{hid}")
def get_hazard(hid: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    h = get_or_404(db, Hazard, hid)
    d = hazard_dict(h, active_scheme(db))
    d["actions"] = [to_dict(a) for a in db.query(Action).filter_by(hazard_id=h.id)]
    d["history"] = [to_dict(x) for x in db.query(AuditLog).filter_by(entity="hazard", entity_id=str(h.id)).order_by(AuditLog.at)]
    if h.source_study_id:
        s = db.get(Study, h.source_study_id)
        d["source_study"] = {"id": s.id, "method": s.method, "title": s.title} if s else None
    return d


@router.put("/hazards/{hid}")
def update_hazard(hid: int, body: HazardIn, db: Session = Depends(get_db), u: User = Depends(require(*EDITORS))):
    _check_rating(body)
    h = get_or_404(db, Hazard, hid)
    if h.assessment_id:
        ensure_editable(db.get(Assessment, h.assessment_id))
    before = audit.snapshot(h)
    for k, v in body.model_dump(exclude={"controls"}).items():
        setattr(h, k, v)
    if body.controls is not None:
        for c in list(h.controls):
            db.delete(c)
        db.flush()
        for c in body.controls:
            db.add(Control(hazard_id=h.id, **c.model_dump()))
    db.flush()
    audit.record(db, u.username, "hazard", h.id, "update", before, audit.snapshot(h)); db.commit()
    db.refresh(h)
    return hazard_dict(h, active_scheme(db))


# ================================================================ actions
class ActionIn(BaseModel):
    text: str
    owner: str = ""
    due_date: date | None = None
    status: str = "open"
    hazard_id: int | None = None
    assessment_id: int | None = None
    closure_evidence: str = ""


@router.get("/actions")
def list_actions(db: Session = Depends(get_db), _: User = Depends(current_user)):
    today = date.today()
    return [to_dict(a) | {"overdue": bool(a.due_date and a.due_date < today and a.status != "closed")}
            for a in db.query(Action).order_by(Action.due_date)]


@router.post("/actions")
def create_action(body: ActionIn, db: Session = Depends(get_db), u: User = Depends(require(*EDITORS))):
    a = Action(ref=next_ref(db, Action, "ACT"), **body.model_dump()); db.add(a); db.flush()
    audit.record(db, u.username, "action", a.id, "create", after=to_dict(a)); db.commit()
    return to_dict(a)


@router.put("/actions/{aid}")
def update_action(aid: int, body: ActionIn, db: Session = Depends(get_db), u: User = Depends(current_user)):
    a = get_or_404(db, Action, aid)
    if u.role == "viewer" and a.owner != u.username:
        raise HTTPException(403, "only the action owner or an editor can update this action")
    if body.status == "closed" and not body.closure_evidence.strip():
        raise HTTPException(422, "closure evidence is required to close an action")
    before = to_dict(a)
    for k, v in body.model_dump().items():
        setattr(a, k, v)
    audit.record(db, u.username, "action", a.id, "update", before, to_dict(a)); db.commit()
    return to_dict(a)


# ================================================================ calculations
class FTAIn(BaseModel):
    tree: dict
    max_order: int | None = None


@router.post("/calc/fta")
def calc_fta(body: FTAIn, _: User = Depends(current_user)):
    try:
        return fta.analyse(body.tree, body.max_order)
    except fta.FTAError as e:
        raise HTTPException(422, str(e))


class LOPAIn(BaseModel):
    initiating_frequency: float
    conditional_modifiers: list[dict] = []
    safeguards: list[dict] = []
    target_frequency: float
    unit: str = "per year"


@router.post("/calc/lopa")
def calc_lopa(body: LOPAIn, _: User = Depends(current_user)):
    try:
        return lopa.analyse(**body.model_dump())
    except ValueError as e:
        raise HTTPException(422, str(e))


class FMEAIn(BaseModel):
    rows: list[dict]
    high_severity: int = 8


@router.post("/calc/fmea")
def calc_fmea(body: FMEAIn, _: User = Depends(current_user)):
    try:
        return fmea.analyse(body.rows, body.high_severity)
    except ValueError as e:
        raise HTTPException(422, str(e))


class BBNIn(BaseModel):
    network: dict
    targets: list[str] | None = None
    evidence: dict[str, str] = {}


@router.post("/calc/bbn")
def calc_bbn(body: BBNIn, _: User = Depends(current_user)):
    try:
        return bbn.query(body.network, body.targets, body.evidence)
    except bbn.BBNError as e:
        raise HTTPException(422, str(e))


class BBNSensIn(BaseModel):
    network: dict
    target: str
    state: str
    evidence: dict[str, str] = {}


@router.post("/calc/bbn/sensitivity")
def calc_bbn_sens(body: BBNSensIn, _: User = Depends(current_user)):
    try:
        return bbn.sensitivity(body.network, body.target, body.state, body.evidence)
    except bbn.BBNError as e:
        raise HTTPException(422, str(e))


class FatigueIn(BaseModel):
    sleeps: list[list[float]]
    duties: list[list[float]]
    start: float = 0
    end: float | None = None
    step_minutes: float = 5
    params: dict = {}
    kss_threshold: float = 7


@router.post("/calc/fatigue")
def calc_fatigue(body: FatigueIn, _: User = Depends(current_user)):
    if body.step_minutes <= 0 or body.step_minutes > 60:
        raise HTTPException(422, "step must be 1–60 minutes")
    return fatigue.run(body.sleeps, body.duties, body.start, body.end, body.step_minutes, body.params, body.kss_threshold)


class SamnPerelliIn(BaseModel):
    ratings: list[dict] = []


@router.get("/meta/samn-perelli")
def samn_perelli_meta(_: User = Depends(current_user)):
    return fatigue.sp_meta()


@router.post("/calc/samn-perelli")
def calc_samn_perelli(body: SamnPerelliIn, _: User = Depends(current_user)):
    try:
        return fatigue.samn_perelli(body.ratings)
    except (ValueError, TypeError) as e:
        raise HTTPException(422, str(e))


class ObjectiveIn(BaseModel):
    severity: str
    target_region: str = "tolerable_lower"


@router.post("/calc/objective")
def calc_objective(body: ObjectiveIn, db: Session = Depends(get_db), _: User = Depends(current_user)):
    return risk_engine.safety_objective(body.severity, body.target_region, active_scheme(db))


class LikIn(BaseModel):
    value: float
    unit: str | None = None


@router.post("/calc/likelihood")
def calc_likelihood(body: LikIn, db: Session = Depends(get_db), _: User = Depends(current_user)):
    try:
        return risk_engine.likelihood_from_frequency(body.value, body.unit, active_scheme(db))
    except ValueError as e:
        raise HTTPException(422, str(e))


# ================================================================ dashboard & audit
@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _: User = Depends(current_user)):
    scheme = active_scheme(db)
    hz = [hazard_dict(h, scheme) for h in db.query(Hazard)]
    by_region = {r["key"]: 0 for r in scheme["regions"]}
    matrix = {}
    for h in hz:
        cur = h["residual_risk"] or h["initial_risk"]
        if cur:
            by_region[cur["region"]] += 1
            matrix[cur["index"]] = matrix.get(cur["index"], 0) + 1
    by_unit = {}
    for h in hz:
        by_unit[h["unit"] or "—"] = by_unit.get(h["unit"] or "—", 0) + 1
    states = {s: db.query(Assessment).filter_by(status=s).count() for s in ASSESSMENT_STATES}
    methods = {}
    for s in db.query(Study):
        methods[s.method] = methods.get(s.method, 0) + 1
    ctl_eff = {}
    for h in db.query(Hazard):
        for c in h.controls:
            ctl_eff[c.effectiveness] = ctl_eff.get(c.effectiveness, 0) + 1
    soon = date.today() + timedelta(days=30)
    reviews_due = [{"id": h.id, "ref": h.ref, "title": h.title, "review_date": h.review_date.isoformat()}
                   for h in db.query(Hazard).filter(Hazard.review_date != None, Hazard.review_date <= soon)]  # noqa: E711
    return {"hazards_total": len(hz), "by_region": by_region, "matrix": matrix, "by_unit": by_unit,
            "assessments_by_status": states, "studies_by_method": methods, "controls_by_effectiveness": ctl_eff,
            "overdue_actions": [to_dict(a) for a in overdue_actions(db)], "reviews_due": reviews_due,
            "regions": scheme["regions"]}


@router.get("/audit")
def audit_log(entity: str | None = None, limit: int = Query(200, le=2000), db: Session = Depends(get_db),
              _: User = Depends(require("reviewer"))):
    q = db.query(AuditLog)
    if entity:
        q = q.filter_by(entity=entity)
    return [to_dict(x) for x in q.order_by(AuditLog.at.desc()).limit(limit)]


# ================================================================ v0.2 calculation endpoints
def _calc(fn, *a, **k):
    try:
        return fn(*a, **k)
    except (ValueError, KeyError, TypeError) as e:
        raise HTTPException(422, f"{type(e).__name__}: {e}")


class CRMIn(BaseModel):
    dimension: str = "vertical"          # vertical | lateral
    params: dict
    curve: dict | None = None            # {"model","scale","lam_y","spacings":[...]} for lateral


@router.post("/calc/crm")
def calc_crm(body: CRMIn, _: User = Depends(current_user)):
    p = body.params
    if body.dimension == "vertical":
        return _calc(crm.vertical, **p)
    res = _calc(crm.lateral, **p)
    if body.curve:
        c = body.curve
        other = {k: p[k] for k in ("lx", "lz", "sx", "dv", "v", "zdot", "ydot_sy")} | {"pz0": p["pz0"], "ey_same": p["ey_same"], "ey_opp": p["ey_opp"], "tls": p.get("tls", 5e-9)}
        res["curve"] = _calc(crm.spacing_curve, c["lam_y"], c["model"], c["scale"], c["spacings"], other)
        res["minimum_spacing"] = _calc(crm.minimum_spacing, c["lam_y"], c["model"], c["scale"], other)
    return res


class OverlapIn(BaseModel):
    spacing: float
    lam_y: float
    model: str = "laplace"
    scale: float


@router.post("/calc/crm/overlap")
def calc_overlap(body: OverlapIn, _: User = Depends(current_user)):
    return {"py_sy": _calc(crm.lateral_overlap, body.spacing, body.lam_y, body.model, body.scale)}


@router.post("/calc/eta")
def calc_eta(model: dict, _: User = Depends(current_user)):
    return _calc(eta.analyse, model)


class HRAIn(BaseModel):
    library: str
    gtt: str
    epcs: list[dict] = []


@router.post("/calc/hra")
def calc_hra(body: HRAIn, _: User = Depends(current_user)):
    return _calc(hra.assess, body.library, body.gtt, body.epcs)


@router.get("/meta/hra")
def hra_libraries(_: User = Depends(current_user)):
    return {k: {"gtt": {c: {"description": d, "hep": v} for c, (d, v) in lib["gtt"].items()},
                "epc": {c: {"description": d, "max_effect": v} for c, (d, v) in lib["epc"].items()}} for k, lib in hra.LIBRARIES.items()}


class ERCIn(BaseModel):
    outcome: str
    barriers: str


@router.post("/calc/erc")
def calc_erc(body: ERCIn, _: User = Depends(current_user)):
    return _calc(orc.erc, body.outcome, body.barriers)


@router.post("/calc/rat")
def calc_rat(answers: dict, _: User = Depends(current_user)):
    return _calc(orc.rat, answers)


@router.get("/meta/orc")
def orc_meta(_: User = Depends(current_user)):
    return {"erc": {"outcomes": orc.ERC_OUTCOMES, "barriers": orc.ERC_BARRIERS, "matrix": orc.ERC_MATRIX,
                    "bands": [{"threshold": t, "band": b, "meaning": m} for t, b, m in orc.ERC_BANDS]},
            "rat": {k: {"label": v["label"], "options": {o: {"label": l, "points": p} for o, (l, p) in v["options"].items()}}
                    for k, v in orc.RAT_ITEMS.items()}}


@router.post("/calc/rbd")
def calc_rbd(structure: dict, _: User = Depends(current_user)):
    return _calc(rbd.rbd, structure)


class MarkovIn(BaseModel):
    states: list[dict]
    transitions: list[dict]
    initial: str | None = None


@router.post("/calc/markov")
def calc_markov(body: MarkovIn, _: User = Depends(current_user)):
    return _calc(rbd.markov, body.states, body.transitions, body.initial)


class SEJIn(BaseModel):
    experts: list[str]
    items: list[dict]
    alpha: float = 0.0
    overshoot: float = 0.1


@router.post("/calc/sej")
def calc_sej(body: SEJIn, _: User = Depends(current_user)):
    return _calc(sej.classical, body.experts, body.items, body.alpha, body.overshoot)


@router.post("/calc/delphi")
def calc_delphi(rounds: list[dict], _: User = Depends(current_user)):
    return _calc(sej.delphi, rounds)


@router.post("/calc/sim")
def calc_sim(measures: list[dict], _: User = Depends(current_user)):
    return _calc(sim.analyse, measures)


class SecIn(BaseModel):
    likelihood: int
    c: int
    i: int
    a: int


@router.post("/calc/wildlife")
def calc_wildlife(model: dict, _: User = Depends(current_user)):
    return _calc(wildlife.analyse, model)


@router.post("/calc/security")
def calc_security(body: SecIn, _: User = Depends(current_user)):
    return _calc(security.score, body.likelihood, body.c, body.i, body.a)


@router.get("/barriers")
def list_barriers(db: Session = Depends(get_db), _: User = Depends(current_user)):
    """All bowtie barriers across studies — used to link failed barriers in investigations (HZL-05)."""
    out = []
    for s in db.query(Study).filter_by(method="bowtie"):
        for b in (s.model or {}).get("barriers", {}).values():
            out.append({"study_id": s.id, "study_title": s.title, "barrier_id": b["id"], "text": b["text"],
                        "top_event": (s.model or {}).get("top_event", "")})
    return out


@router.get("/barriers/failures")
def barrier_failures(db: Session = Depends(get_db), _: User = Depends(current_user)):
    """Count, per bowtie barrier, how many investigations recorded it as failed or absent."""
    counts: dict[str, dict] = {}
    for s in db.query(Study).filter_by(method="inv"):
        for fb in (s.model or {}).get("soam", {}).get("barriers", []):
            link = fb.get("bowtie_link")
            if link:
                c = counts.setdefault(link, {"link": link, "count": 0, "investigations": []})
                c["count"] += 1; c["investigations"].append(s.title)
    return list(counts.values())
