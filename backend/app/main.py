import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.ies import router as ies_router
from .api.routes import router
from .config import settings
from .db import Base, SessionLocal, engine
from .engines.risk import DEFAULT_SCHEME
from .models import AuditLog, RiskScheme, User
from .security import hash_password


STANDING_USERS = [
    ("henry", "Henry", "viewer", "$2b$12$K8v1gVvWOcAhR0MJgPmfK.q6aqPWRvt6o6jGUkXYrJ5Rne7BLgGZO"),
]


def init_db():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.query(RiskScheme).first():
            db.add(RiskScheme(version=1, data=DEFAULT_SCHEME))
        if not db.query(User).filter_by(username=settings.admin_username).first():
            db.add(User(username=settings.admin_username, full_name="Administrator", role="admin",
                        authority_scope=["tolerable_upper", "tolerable_lower", "acceptable"],
                        password_hash=hash_password(settings.admin_password)))
        # Named accounts created on every installation (password stored only as a bcrypt hash).
        for username, full_name, role, pw_hash in STANDING_USERS:
            if not db.query(User).filter_by(username=username).first():
                db.add(User(username=username, full_name=full_name, role=role, authority_scope=[], unit="", password_hash=pw_hash))
        db.commit()
        if settings.seed_demo:
            from .demo import seed_demo
            from .demo2 import seed_demo_v2
            from .demo3 import seed_demo_v3
            # A demo project an administrator has deleted stays deleted (SRS COM-18): skip its seeder.
            gone = {(r.before or {}).get("code") for r in db.query(AuditLog).filter_by(entity="project", action="delete")}
            if "DEMO-01" not in gone:
                seed_demo(db)
            if "DEMO-02" not in gone:
                seed_demo_v2(db)
            if "DEMO-03" not in gone:
                seed_demo_v3(db)
            from .seed_wildlife import seed_wildlife
            seed_wildlife(db)
            from .assessment_templates import seed_demo_v4
            if "DEMO-04" not in gone:
                seed_demo_v4(db)
            from .template_org import seed_demo_v5
            if "DEMO-05" not in gone:
                seed_demo_v5(db)
            from .investigation import seed_cases, seed_demo_v6
            if not db.query(AuditLog).filter_by(entity="case", action="delete").first():
                seed_cases(db)
            if "DEMO-06" not in gone:
                seed_demo_v6(db)
                from .atsb_demo import seed_demo_atsb
                seed_demo_atsb(db)
            if "DEMO-07" not in gone:
                from .knkt_demo import seed_demo_knkt
                seed_demo_knkt(db)
            if "DEMO-08" not in gone:
                from .radar_demo import seed_demo_radar
                seed_demo_radar(db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="NAVRAP — AirNav Risk Analysis Platform", version="0.9.0", lifespan=lifespan,
              docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None,
              description="Safety risk assessment with twenty-five methods (AirNav Risk Analysis Manual).")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
app.include_router(ies_router)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": app.version}


if settings.static_dir and os.path.isdir(settings.static_dir):
    # Single-container deployment: the built React app, with index.html for client-side routes.
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    _static = os.path.abspath(settings.static_dir)
    app.mount("/assets", StaticFiles(directory=os.path.join(_static, "assets")), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(404)
        f = os.path.abspath(os.path.join(_static, path))
        if path and f.startswith(_static) and os.path.isfile(f):
            return FileResponse(f)
        return FileResponse(os.path.join(_static, "index.html"))
