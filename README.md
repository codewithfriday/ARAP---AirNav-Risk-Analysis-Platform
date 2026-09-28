# ARAP — AirNav Risk Analysis Platform

ARAP is a web application for conducting air navigation safety risk assessments with the 25 methods of the **AirNav Risk Analysis Manual** (edition 0.2):

**Core (Manual ch. 6–17):** Bowtie · HAZID · HAZOP · JHA · FMEA/FMECA · LOPA · FHA · STPA · FTA · bio-mathematical fatigue modelling (three-process model) · FRAM · Bayesian belief networks

**Extended (Manual ch. 18–30):** collision risk modelling (Reich) · event tree analysis · human reliability (HEART/CARA) · occurrence risk classification (ARMS ERC / EUROCONTROL RAT) · GSN safety arguments · common cause analysis (ZSA/PRA/CMA) · RBD and Markov availability · SWIFT · hierarchical task analysis · real-/fast-time simulation evidence · structured expert judgement (Cooke, Delphi) · security risk with safety impact (ISO/IEC 27005, ED-205) · occurrence investigation (SOAM, HFACS, Tripod Beta)

It provides one hazard log and one risk classification scheme across all methods, a review/endorse/accept workflow with locking and versioning, an audit trail, a dashboard, and a Word Safety Assessment Report.

![Dashboard](docs/screenshots/02-dashboard.png)

| Document | |
|---|---|
| [User guide](docs/USER_GUIDE.md) ([PDF](docs/ARAP_User_Guide.pdf)) | How to use the application |
| [AirNav Risk Analysis Manual](docs/AirNav_Risk_Analysis_Manual.pdf) | The methods — why, when and how |
| [Software Requirements Specification](docs/AirNav_Risk_Analysis_Software_Requirements.pdf) | Requirements, calculation specs, reference tests, recommended stack (App. C) |
| [Architecture notes](docs/ARCHITECTURE.md) | Code structure, data model, engines |

> **Status: version 0.2 (pilot).** Numbers in the demo data are the Manual's illustrative worked examples, not AirNav data. See [User guide §20](docs/USER_GUIDE.md#20-what-version-02-does-not-do-yet) for what is not yet implemented.

---

## Technology

Follows SRS Appendix C:

| Layer | Technology |
|---|---|
| Front end | React 19 + TypeScript (Vite), Ant Design 6, TanStack Query, Zustand, react-i18next (EN/ID) |
| Diagrams | React Flow (@xyflow/react) with a purpose-built bowtie layout; ELK.js for fault trees, GSN arguments and task hierarchies; SVG for event trees, RBDs, Markov and SOAM charts |
| Worksheets | AG Grid Community |
| Charts | Apache ECharts |
| Back end | Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, Alembic |
| Engines | In-house, versioned: BDD fault-tree engine, exact Bayesian variable elimination, three-process fatigue model, LOPA, FMEA/FMECA, risk matrix; Reich collision risk, event trees, HEART/CARA, ARMS ERC / RAT, RBD and Markov, Cooke's classical model and Delphi, simulation statistics, security scoring (NumPy, SciPy) |
| Database | PostgreSQL 16 (SQLite for local development and tests) |
| Reports | python-docx |
| Packaging | Docker Compose (PostgreSQL + API + nginx); GitHub Actions CI in `.github/workflows/` |

---

## Quick start with Docker

Requires Docker with Compose v2.

```bash
git clone https://github.com/codewithfriday/ARAP---AirNav-Risk-Analysis-Platform.git arap
cd arap
cp .env.example .env        # then edit .env: set POSTGRES_PASSWORD, ARAP_SECRET_KEY, ARAP_ADMIN_PASSWORD
docker compose up -d --build
```

Open **http://localhost:8080** and sign in as `admin` with the password from `.env`.

With `ARAP_SEED_DEMO=true` (the default) three demo projects (DEMO-01 for the core methods, DEMO-02 for the extended methods, DEMO-03 the H24 alternate-aerodrome SRA case study) with one study per method and demo users (password `demo1234`) is created: `assessor`, `reviewer`, `director`, `accexec`, `viewer`. **Set `ARAP_SEED_DEMO=false` and change all passwords for real use.**

The API applies database migrations (`alembic upgrade head`) on start-up. Interactive API documentation (OpenAPI) is at `http://localhost:8080/api/docs`.

## Development setup

**Back end** (Python 3.11+):

```bash
cd backend
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000     # SQLite file arap.db by default
```

Use PostgreSQL by setting `ARAP_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/arap` and running `alembic upgrade head`.

**Front end** (Node 22):

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173, proxies /api to :8000
npm run build        # production build in dist/
```

### Configuration

All settings are environment variables with the prefix `ARAP_`:

| Variable | Default | Purpose |
|---|---|---|
| `ARAP_DATABASE_URL` | `sqlite:///./arap.db` | SQLAlchemy database URL |
| `ARAP_SECRET_KEY` | *(dev value)* | JWT signing key — **set a long random value** |
| `ARAP_TOKEN_MINUTES` | `480` | Session length |
| `ARAP_ADMIN_USERNAME` / `ARAP_ADMIN_PASSWORD` | `admin` / `admin` | Initial administrator |
| `ARAP_SEED_DEMO` | `true` | Load the Manual's worked examples and demo users |
| `ARAP_CORS_ORIGINS` | `http://localhost:5173,http://localhost:8080` | Allowed browser origins |

## Tests

```bash
cd backend
pytest -q                                   # SQLite
ARAP_DATABASE_URL=postgresql+psycopg://... pytest -q -p no:cacheprovider   # PostgreSQL
```

The suite has 48 tests. They include the **reference test cases of SRS §9**: every calculation engine must reproduce the Manual's worked examples. For example, fault-tree top event 1.22 × 10⁻⁶, LOPA 2.5 × 10⁻⁵/yr, Bayesian posterior P(fatigue | loss of separation) = 0.390, fatigue-model minimum alertness 5.18 at 05:55, RVSM vertical collision risk 1.873 × 10⁻⁹, minimum lateral route spacing 11.68 NM, CARA HEP 2.016 × 10⁻³, Markov unavailability 2.04 × 10⁻⁶ and Cooke expert weight 0.814. The Bayesian engine is also checked against brute-force enumeration. The API tests cover roles, the approval workflow, acceptance authority, locking, versioning, hazard promotion, exports and audit.

GitHub Actions (`.github/workflows/ci.yml`) runs the back-end tests on SQLite and PostgreSQL and builds the front end on every push and pull request.

## Security notes

- Change `ARAP_SECRET_KEY`, the admin password and all demo passwords; disable demo data in production.
- Serve over HTTPS (terminate TLS at nginx or a load balancer).
- Version 0.2 uses local accounts (bcrypt-hashed passwords, JWT bearer tokens). SSO via Keycloak (SRS SEC-01) is planned.
- Every create, change, approval and export is written to the append-only `audit_log` table.

## Repository layout

```
backend/        FastAPI application, engines, Alembic migrations, tests
.github/        GitHub Actions CI workflow
frontend/       React + TypeScript application
docs/           User guide, Manual, SRS, architecture notes, screenshots
docker-compose.yml, .env.example
```
