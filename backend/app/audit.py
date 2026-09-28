from datetime import date, datetime

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from .models import AuditLog


def snapshot(obj) -> dict:
    out = {}
    for c in inspect(obj).mapper.column_attrs:
        v = getattr(obj, c.key)
        if isinstance(v, (datetime, date)):
            v = v.isoformat()
        out[c.key] = v
    return out


def record(db: Session, username: str, entity: str, entity_id, action: str, before=None, after=None):
    if before is not None and after is not None:
        changed = {k for k in after if before.get(k) != after.get(k)}
        before = {k: before[k] for k in changed if k in before}
        after = {k: after[k] for k in changed}
    db.add(AuditLog(username=username, entity=entity, entity_id=str(entity_id), action=action, before=before, after=after))
