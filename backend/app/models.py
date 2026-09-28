from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, JSONType


def now():
    return datetime.now(timezone.utc)


ROLES = ("admin", "assessor", "reviewer", "authority", "viewer")
METHODS = ("bowtie", "hazid", "hazop", "jha", "fmea", "lopa", "fha", "stpa", "fta", "fatigue", "fram", "bbn",
           "crm", "eta", "hra", "orc", "gsn", "cca", "rbd", "swift", "hta", "sim", "sej", "sec", "inv",
           "wildlife")
ASSESSMENT_STATES = ("draft", "in_review", "endorsed", "accepted", "rejected", "closed", "superseded")
LOCKED_STATES = ("endorsed", "accepted", "closed", "superseded")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="viewer")
    unit: Mapped[str] = mapped_column(String(100), default="")
    # risk regions this user may accept (for role 'authority'/'admin')
    authority_scope: Mapped[list] = mapped_column(JSONType, default=list)
    lang: Mapped[str] = mapped_column(String(5), default="en")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class RiskScheme(Base):
    __tablename__ = "risk_schemes"
    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(Integer, unique=True)
    data: Mapped[dict] = mapped_column(JSONType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    created_by: Mapped[str] = mapped_column(String(64), default="system")


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    change_type: Mapped[str] = mapped_column(String(40), default="system")
    units: Mapped[str] = mapped_column(String(300), default="")
    sponsor: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    assessments: Mapped[list["Assessment"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Assessment(Base):
    __tablename__ = "assessments"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(String(300))
    scope: Mapped[str] = mapped_column(Text, default="")
    environment: Mapped[str] = mapped_column(Text, default="")
    assumptions: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    previous_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_scheme_version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    project: Mapped[Project] = relationship(back_populates="assessments")
    studies: Mapped[list["Study"]] = relationship(back_populates="assessment", cascade="all, delete-orphan")
    approvals: Mapped[list["Approval"]] = relationship(back_populates="assessment", cascade="all, delete-orphan",
                                                       order_by="Approval.at")

    @property
    def locked(self) -> bool:
        return self.status in LOCKED_STATES


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id"))
    action: Mapped[str] = mapped_column(String(20))
    from_status: Mapped[str] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20))
    username: Mapped[str] = mapped_column(String(64))
    comment: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    assessment: Mapped[Assessment] = relationship(back_populates="approvals")


class Study(Base):
    __tablename__ = "studies"
    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id"))
    method: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="open")
    template_version: Mapped[str] = mapped_column(String(20), default="1.0")
    participants: Mapped[list] = mapped_column(JSONType, default=list)
    sessions: Mapped[list] = mapped_column(JSONType, default=list)
    model: Mapped[dict] = mapped_column(JSONType, default=dict)
    results: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    assessment: Mapped[Assessment] = relationship(back_populates="studies")


class Hazard(Base):
    __tablename__ = "hazards"
    id: Mapped[int] = mapped_column(primary_key=True)
    ref: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    causes: Mapped[str] = mapped_column(Text, default="")
    consequences: Mapped[str] = mapped_column(Text, default="")
    context: Mapped[str] = mapped_column(Text, default="")
    unit: Mapped[str] = mapped_column(String(100), default="")
    system: Mapped[str] = mapped_column(String(100), default="")
    owner: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(20), default="open")
    review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    assessment_id: Mapped[int | None] = mapped_column(ForeignKey("assessments.id"), nullable=True)
    source_study_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_row: Mapped[str] = mapped_column(String(80), default="")
    initial_severity: Mapped[str | None] = mapped_column(String(1), nullable=True)
    initial_likelihood: Mapped[int | None] = mapped_column(Integer, nullable=True)
    residual_severity: Mapped[str | None] = mapped_column(String(1), nullable=True)
    residual_likelihood: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rationale: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    controls: Mapped[list["Control"]] = relationship(back_populates="hazard", cascade="all, delete-orphan")


class Control(Base):
    __tablename__ = "controls"
    id: Mapped[int] = mapped_column(primary_key=True)
    hazard_id: Mapped[int] = mapped_column(ForeignKey("hazards.id"))
    text: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(30), default="procedure")
    side: Mapped[str] = mapped_column(String(20), default="prevention")
    owner: Mapped[str] = mapped_column(String(100), default="")
    verification: Mapped[str] = mapped_column(String(30), default="existing-unverified")
    effectiveness: Mapped[str] = mapped_column(String(20), default="unknown")
    critical: Mapped[bool] = mapped_column(Boolean, default=False)
    spi: Mapped[str] = mapped_column(String(200), default="")
    hazard: Mapped[Hazard] = relationship(back_populates="controls")


class Action(Base):
    __tablename__ = "actions"
    id: Mapped[int] = mapped_column(primary_key=True)
    ref: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    text: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(String(100), default="")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")
    hazard_id: Mapped[int | None] = mapped_column(ForeignKey("hazards.id"), nullable=True)
    assessment_id: Mapped[int | None] = mapped_column(ForeignKey("assessments.id"), nullable=True)
    closure_evidence: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    username: Mapped[str] = mapped_column(String(64))
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(40))
    action: Mapped[str] = mapped_column(String(20))
    before: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
