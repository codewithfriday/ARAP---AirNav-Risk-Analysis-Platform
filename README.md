# ARAP — AirNav Risk Analysis Platform

ARAP is a web application for conducting air navigation safety risk assessments with the twelve methods of the **AirNav Risk Analysis Manual**:

Bowtie · HAZID · HAZOP · JHA · FMEA/FMECA · LOPA · FHA · STPA · FTA · bio-mathematical fatigue modelling (three-process model) · FRAM · Bayesian belief networks

It provides one hazard log and one risk classification scheme across all methods, a review/endorse/accept workflow with locking and versioning, an audit trail, a dashboard, and a Word Safety Assessment Report.

![Dashboard](docs/screenshots/02-dashboard.png)

| Document | |
|---|---|
| [User guide](docs/USER_GUIDE.md) ([PDF](docs/ARAP_User_Guide.pdf)) | How to use the application |
| [AirNav Risk Analysis Manual](docs/AirNav_Risk_Analysis_Manual.pdf) | The methods — why, when and how |
| [Software Requirements Specification](docs/AirNav_Risk_Analysis_Software_Requirements.pdf) | Requirements, calculation specs, reference tests, recommended stack (App. C) |
| [Architecture notes](docs/ARCHITECTURE.md) | Code structure, data model, engines |

> **Status: version 0.1 (pilot).** Numbers in the demo data are the Manual's illustrative worked examples, not AirNav data. See [User guide §19](docs/USER_GUIDE.md#19-what-version-01-does-not-do-yet) for what is not yet implemented.

---

## Technology

Follows SRS Appendix C:

| Layer | Technology |
|---|---|
| Front end | React 19 + TypeScript (Vite), Ant Design 6, TanStack Query, Zustand, react-i18next (EN/ID) |
| Diagrams | React Flow (@xyflow/react) with a purpose-built bowtie layout; ELK.js for fault trees |
| Worksheets | AG Grid Community |
| Charts | Apache ECharts |
| Back end | Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, Alembic |
| Engines | In-house, versioned: BDD fault-tree engine, exact Bayesian variable elimination, three-process fatigue model, LOPA, FMEA/FMECA, risk matrix (NumPy) |
| Database | PostgreSQL 16 (SQLite for local development and tests) |
| Reports | python-docx |
| Packaging | Docker Compose (PostgreSQL + API + nginx); GitHub Actions workflow in `ci/` |

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

With `ARAP_SEED_DEMO=true` (the default) a demo project with one study per method and demo users (password `demo1234`) is created: `assessor`, `reviewer`, `director`, `accexec`, `viewer`. **Set `ARAP_SEED_DEMO=false` and change all passwords for real use.**

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

The suite has 32 tests. They include the **reference test cases of SRS §9**: every calculation engine must reproduce the Manual's worked examples. For example, fault-tree top event 1.22 × 10⁻⁶, LOPA 2.5 × 10⁻⁵/yr, Bayesian posterior P(fatigue | loss of separation) = 0.390, and fatigue-model minimum alertness 5.18 at 05:55. The Bayesian engine is also checked against brute-force enumeration. The API tests cover roles, the approval workflow, acceptance authority, locking, versioning, hazard promotion, exports and audit.

A GitHub Actions workflow is provided in `ci/github-actions-ci.yml`. It runs the back-end tests on SQLite and PostgreSQL and builds the front end. To enable it, move the file to `.github/workflows/ci.yml` and push with a token that has the `workflow` scope (or add it through the GitHub web interface).

## Security notes

- Change `ARAP_SECRET_KEY`, the admin password and all demo passwords; disable demo data in production.
- Serve over HTTPS (terminate TLS at nginx or a load balancer).
- Version 0.1 uses local accounts (bcrypt-hashed passwords, JWT bearer tokens). SSO via Keycloak (SRS SEC-01) is planned.
- Every create, change, approval and export is written to the append-only `audit_log` table.

## Repository layout

```
backend/        FastAPI application, engines, Alembic migrations, tests
frontend/       React + TypeScript application
docs/           User guide, Manual, SRS, architecture notes, screenshots
ci/            GitHub Actions workflow (move to .github/workflows/ to enable)
docker-compose.yml, .env.example
```
