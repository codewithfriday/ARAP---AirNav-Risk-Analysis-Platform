from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..engines import risk as risk_engine
from ..models import Action, Assessment, Hazard, RiskScheme


def to_dict(obj, exclude=()) -> dict:
    out = {}
    for c in obj.__table__.columns:
        if c.key in exclude:
            continue
        v = getattr(obj, c.key)
        if isinstance(v, (datetime, date)):
            v = v.isoformat()
        out[c.key] = v
    return out


def active_scheme(db: Session) -> dict:
    rs = db.query(RiskScheme).order_by(RiskScheme.version.desc()).first()
    return rs.data if rs else risk_engine.DEFAULT_SCHEME


def scheme_version(db: Session, version: int | None = None) -> dict:
    if version is None:
        return active_scheme(db)
    rs = db.query(RiskScheme).filter_by(version=version).first()
    return rs.data if rs else active_scheme(db)


def rate(sev, lik, scheme) -> dict | None:
    if not sev or not lik:
        return None
    return risk_engine.classify(sev, int(lik), scheme)


def hazard_dict(h: Hazard, scheme: dict) -> dict:
    d = to_dict(h)
    d["initial_risk"] = rate(h.initial_severity, h.initial_likelihood, scheme)
    d["residual_risk"] = rate(h.residual_severity, h.residual_likelihood, scheme)
    d["controls"] = [to_dict(c) for c in h.controls]
    return d


def next_ref(db: Session, model, prefix: str) -> str:
    n = db.query(func.count(model.id)).scalar() or 0
    while True:
        n += 1
        ref = f"{prefix}-{n:04d}"
        if not db.query(model).filter_by(ref=ref).first():
            return ref


def ensure_editable(a: Assessment | None):
    if a is not None and a.locked:
        raise HTTPException(409, f"Assessment is {a.status} and locked; create a new version to change it.")


def get_or_404(db: Session, model, id_):
    obj = db.get(model, id_)
    if not obj:
        raise HTTPException(404, f"{model.__name__} {id_} not found")
    return obj


def overdue_actions(db: Session):
    today = date.today()
    return db.query(Action).filter(Action.status != "closed", Action.due_date != None, Action.due_date < today).all()  # noqa: E711
