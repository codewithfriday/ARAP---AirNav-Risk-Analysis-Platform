# ARAP architecture notes (v0.7)

## Overview

```
Browser (React + TS) ──/api──► nginx ──► FastAPI (Python) ──► PostgreSQL
                                              │
                                              └── calculation engines (pure Python / NumPy / SciPy)
```

The back end is a single modular application (a "modular monolith", as recommended in SRS Appendix C). Calculation engines are plain Python modules with no web or database dependency. They can be tested and versioned on their own, and each result records the engine version that produced it (QA-01 to QA-03).

## Back end (`backend/app`)

| Module | Responsibility |
|---|---|
| `main.py` | App factory, start-up (create admin, default risk scheme, optional demo data) |
| `config.py` | Settings from `ARAP_*` environment variables |
| `db.py`, `models.py` | SQLAlchemy 2 models; JSON columns map to JSONB on PostgreSQL |
| `security.py` | bcrypt password hashing, JWT tokens, role checks |
| `api/routes.py` | REST API: auth, users, risk scheme, projects, assessments and workflow, studies, hazard log, actions, calculations, dashboard, audit |
| `audit.py` | Append-only audit records with before/after diffs |
| `reports.py` | Safety Assessment Report (DOCX) |
| `templates.py` | Method catalogue and worksheet templates (guidewords, columns, UCA types, FRAM aspects) |
| `demo.py`, `seed.py` | The Manual's worked examples (chapters 6–17) as demo data and test oracles |
| `demo2.py`, `seed2.py`, `seed_wildlife.py` | Worked examples of chapters 18–31 (project DEMO-02) and their reference inputs; the wildlife study is also added to existing databases on start-up |
| `demo3.py` | DEMO-03: the H24 alternate-aerodrome SRA case study |
| `assessment_templates.py` | Assessment templates (catalogue, builders). `build_aim(db, assessment, filled)` creates the 14 AIM studies; `filled=True` adds illustrative ratings, results, hazards and actions (DEMO-04). Exposed by `GET /assessment-templates` and `POST /assessments {template}` |
| `template_org.py` | Template *Major organisational change* (`build_org`) and DEMO-05 (`seed_demo_v5`) |
| `engines/` | `risk`, `fta`, `lopa`, `fmea`, `bbn`, `fatigue`; v0.2: `crm`, `eta`, `hra`, `orc`, `rbd`, `sej`, `sim`, `security`; v0.3: `wildlife` |

### Data model

`Project` 1—* `Assessment` 1—* `Study`. Each study stores its method-specific model as JSON (`model`) and the last calculation (`results`).

`Hazard` is the shared hazard-log entry. It links to the assessment and to its source study and row, and holds initial and residual ratings. Hazards have `Control`s; `Action`s link to hazards and assessments.

`Approval` records each workflow transition, `RiskScheme` is versioned configuration, and `AuditLog` records every change.

Method-specific objects (bowtie paths and barriers, HAZOP nodes, fault-tree gates, BBN nodes, STPA control structure, FRAM functions, event trees, GSN elements, task hierarchies, investigation charts) live inside the study's JSON model. Only results promoted to the hazard log become relational rows. This keeps the core schema small, and method templates can evolve without migrations.

### Workflow

`draft → in_review → endorsed → accepted → closed`, with `return` (to draft), `reject`, and `new-version` (copy to v+1; the old version becomes `superseded`). Endorsed, accepted, closed and superseded assessments are locked. Acceptance checks, in order:

1. The assessment has at least one hazard.
2. No residual risk is intolerable.
3. The worst residual region is in the accepting user's `authority_scope`.

Projects are `active` or `archived`. `POST /projects/{id}/archive` and `/restore` (editors) toggle the status; archived projects are left out of `GET /projects` and `GET /assessments` unless `include_archived=true`, and refuse new assessments. `DELETE /projects/{id}?confirm=<code>` (admin) removes the project with its assessments, studies, approvals, hazards, controls and actions. It is refused with 409 when any assessment is locked, and the audit entry keeps a snapshot of the project and the counts. At start-up the demo seeders skip any demo code that has an audit "delete" entry, so a deleted demo stays deleted.

### Investigation expert system (v0.7)

`InvCase` (table `inv_cases`) holds the case library: an AcciMap JSON model (`blocks`, `edges` with role input/context, `rules`), status draft/approved, provenance and report text. Categories, mechanisms, the ORLIO factor catalogue, the thesaurus and the demo cases are in `app/investigation.py`; routes in `app/api/ies.py`, study analysis in `app/api/ies_logic.py`. Engines: `fuzzy` (Mamdani inference per AcciMap, default rules, clues), `casebn` (naive-Bayes network learned from approved cases, virtual evidence, value of information, export to the BBN format), `casesearch` (thesaurus + TF-IDF + factor share), `draft` (offline drafter and optional Claude drafter via the Messages API with tool use; quotes verified against the report). The study method `ies` stores `category`, `narrative`, `selected` case ids and `ratings` (`f:<factor>` or `b:<case>:<block>`); results are recomputed by `POST /ies/analyse`.

### Engines

| Engine | Method |
|---|---|
| `fta` | Reduced ordered BDD with an ite cache for the exact top-event probability. MOCUS-style expansion with absorption for minimal cut sets. Birnbaum and Fussell–Vesely by conditioning. β-factor CCF expansion; vote gates; rate, MTTR and test-interval models. |
| `bbn` | Exact variable elimination with NumPy `einsum` and a min-degree ordering. Validates the DAG and CPTs; brute-force enumeration oracle for tests; tornado sensitivity. |
| `fatigue` | Three-process model (S, C, W; optional U) on a fixed time step with exact exponential updates; per-duty indicators. |
| `lopa` | IPL criteria gating, shared-dependency warnings, gap to target. |
| `fmea` | RPN, high-severity flag, MIL-STD-1629A mode and item criticality. |
| `risk` | Matrix classification, frequency-to-likelihood mapping with unit check, FHA safety objectives, worst region. |
| `crm` | Reich model (ICAO Doc 9689 occupancy form) for vertical and lateral risk; Gaussian / double-exponential lateral overlap; risk–spacing curve; minimum spacing by bisection on log risk. |
| `eta` | Event-tree enumeration with path-conditional probabilities, barrier or functional trees, sum check, frequency by severity. |
| `hra` | HEART and CARA libraries (GTTs, EPCs) and HEP = GTT × Π[(EPC−1)·APoA+1]. |
| `orc` | ARMS ERC matrix and bands; EUROCONTROL RAT marksheet points. |
| `rbd` | Series / parallel / k-out-of-n availability and block importance; CTMC Markov solver (steady state, failure frequency, MDT, MTTFF). |
| `sej` | Cooke's classical model (calibration by χ², information, α cut-off, performance- and equal-weight decision makers); Delphi round statistics. |
| `sim` | Descriptive statistics, 95% CI, Welch's t-test, success criteria. |
| `security` | L × max(C, I, A) scoring and levels. |
| `wildlife` | Species strike risk: likelihood from strikes per year, severity from damaging share or body-mass/flocking surrogate, L × S banding, rate per 10,000 movements and trend. |

## Front end (`frontend/src`)

| Path | Responsibility |
|---|---|
| `App.tsx`, `main.tsx` | Layout, routing (data router with unsaved-changes blocking), providers |
| `api.ts`, `store.ts`, `hooks.ts` | API client with JWT, auth store, shared queries |
| `i18n.ts` | English / Bahasa Indonesia strings |
| `risk.ts` | Client-side mirror of matrix classification for display (the server stays authoritative) |
| `pages/` | Dashboard, projects, assessment, study host, hazard log, actions, risk scheme, users, audit, guide |
| `components/` | Risk matrix picker, risk tags, generic AG Grid worksheet (incl. SWIFT and security kinds), `EditableTable` for small inline lists |
| `methods/` | One editor per method: `BowtieEditor` + `bowtieLayout`, `WorksheetEditor` (HAZID, HAZOP, JHA, FMEA, FHA), `LopaEditor`, `FtaEditor` (ELK layout), `FatigueEditor`, `BbnEditor`, `StpaEditor`, `FramEditor`; v0.2: `CrmEditor`, `EtaEditor`, `HraEditor`, `OrcEditor`, `GsnEditor` (ELK), `CcaEditor`, `RbdEditor`, `HtaEditor` (ELK), `SimEditor`, `SejEditor`, `InvEditor`, `WildlifeEditor`; SWIFT, security, the organisational function map (`orgmap`, gap flags via `ofmGaps`) and the SPI register (`spi`, RAG status) use `WorksheetEditor`; a HAZID/SWIFT model may carry its own `guidewords` list |

Method editors are lazy-loaded. Each receives `{model, setModel, results, setResults, readOnly, scheme, template, promote}` from `StudyPage`, which owns saving and hazard-log promotion.

### Bowtie layout

`bowtieLayout.ts` computes positions deterministically:

- Threats go in a column on the left and consequences on the right.
- Barriers sit in slots along each path.
- Rows grow when a path carries escalation factors, which hang below the barrier they degrade.
- A shared barrier is one object rendered on every path that uses it, with a ×n badge.

This produces a stable, tidy diagram without manual positioning, as in BowTieXP.

### Cross-study links (v0.2)

Some v0.2 modules refer to other studies by id inside their JSON model. No foreign keys are used, so a deleted target shows as "not found" instead of breaking the study.

| Link | Stored as | Used by |
|---|---|---|
| GSN solution → evidence | `evidence: {kind: study\|hazard\|document, ref}` | `GET /studies`, `GET /hazards` for status display |
| CCA claim ← FTA gate | copied at import (`items`, `analysis`) | `GET /studies?method=fta` |
| HTA task → HRA task | `hra_study` (study id) + task `hra` (task id) | HEP display |
| Investigation barrier → bowtie barrier | `bowtie_link: "studyId:barrierId"` | `GET /barriers`, `GET /barriers/failures` (count shown in the bowtie editor) |
