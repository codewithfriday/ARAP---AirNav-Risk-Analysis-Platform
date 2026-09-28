from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import settings
from .db import Base, SessionLocal, engine
from .engines.risk import DEFAULT_SCHEME
from .models import RiskScheme, User
from .security import hash_password


def init_db():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.query(RiskScheme).first():
            db.add(RiskScheme(version=1, data=DEFAULT_SCHEME))
        if not db.query(User).filter_by(username=settings.admin_username).first():
            db.add(User(username=settings.admin_username, full_name="Administrator", role="admin",
                        authority_scope=["tolerable_upper", "tolerable_lower", "acceptable"],
                        password_hash=hash_password(settings.admin_password)))
        db.commit()
        if settings.seed_demo:
            from .demo import seed_demo
            from .demo2 import seed_demo_v2
            from .demo3 import seed_demo_v3
            seed_demo(db)
            seed_demo_v2(db)
            seed_demo_v3(db)
            from .seed_wildlife import seed_wildlife
            seed_wildlife(db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="ARAP — AirNav Risk Analysis Platform", version="0.3.0", lifespan=lifespan,
              docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None,
              description="Safety risk assessment with twenty-five methods (AirNav Risk Analysis Manual).")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": app.version}
