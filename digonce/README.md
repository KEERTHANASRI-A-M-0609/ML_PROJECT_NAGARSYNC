# NagarSync: Intelligent Urban Infrastructure Management System

> **All data is SIMULATED across Tamil Nadu districts. Results are not real-world performance.**

## Problem

Urban infrastructure departments (roads, water, streetlights, bridges) operate independently, each paying a full mobilisation cost per visit. When multiple assets share a street corridor, coordinating repairs into a single visit eliminates redundant mobilisation costs.

**Research question:** *When does coordinating repairs across asset types beat repairing each asset independently, and by how much, under a fixed budget?*

The demo covers **Tamil Nadu statewide** — corridors clustered around 37 district hubs from Chennai to Kanniyakumari (simulated).

## Architecture

```
datasets/raw/          Simulated CSVs (corridors, assets, water, traffic, rainfall)
datasets/processed/    asset_month_panel.csv, current_snapshot.csv
ml/                    City simulation, leak detection, traffic, risk model,
                       optimiser, scheduling, simulation, experiments
models/                Trained model artefacts + metrics JSON
reports/               experiments.json + PNG figures
backend/app/           FastAPI (main.py, services.py, schemas.py)
frontend/src/          React + Vite (5 pages)
tests/                 ML unit tests
backend/tests/         API smoke tests
docs/                  architecture.md, methodology.md
```

## Setup

```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

### Run locally on Windows

The backend is a Python/FastAPI service, not an npm project. Do not run `npm start` from `backend/`; it has no `package.json`.

Open two PowerShell terminals:

**Terminal 1 — backend (from the project root):**

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

**Terminal 2 — frontend:**

```powershell
Set-Location .\frontend
npm run dev
```

Open the Vite URL printed in Terminal 2. Keep both terminals running. The frontend `package.json` provides `npm run dev`, `npm run build`, and `npm run preview`; it does not define an `npm start` script.

If Vite reports `ECONNREFUSED` for `/api` or `/ws`, check Terminal 1: the proxy requires the FastAPI backend to finish starting. In particular, a Windows message such as `Application Control policy has blocked this file` while importing scikit-learn means Windows prevented a native Python extension from loading. NagarSync then uses its preloaded, simulated 37-district fixture with a transparent condition-priority rule so the local dashboard and recommender remain usable. This fallback is not the trained ML model and does not represent every municipality or verified municipal assets. Use an organization-approved Python environment or ask your administrator to review the policy to run the trained model; do not disable or bypass it. The Vite proxy targets `127.0.0.1:8000`, matching Uvicorn's default local address.

### Demo data and record management

The checked-in generated fixture contains 2,781 simulated asset snapshots across 37 Tamil Nadu districts. The dashboard, map, ward summaries, sensor examples, and recommender can use this fixture when Windows blocks the trained model's native dependency. In that case the recommender uses a deterministic condition-priority score, not a predicted failure probability. Demo-mode pages identify the data and scoring method; treat all locations, condition indicators, and recommendations as illustrative only. This is not a municipality-by-municipality inventory or a connection to government systems.

Administrators can create, view, edit, archive, and restore citizen reports, incidents, managed user accounts, and manually managed asset records under **Manage Records**. Those records use the configured database or local JSON fallback. Manually managed assets are deliberately kept separate from the simulated model fixture and are not scored or added to recommendations.

## One-command run

```bash
python -m ml.run_pipeline --phase all --fast   # data + train + simulate (10 seeds)
uvicorn backend.app.main:app --port 8000        # API + serves built frontend
```

## First administrator setup

Guest visitors can read the public overview without signing in. Citizen account creation does not sign the user in automatically; the new user must sign in before opening account features. Self-registration creates citizen accounts only. There are no shared/default administrator credentials. To provision the first administrator, set a private bootstrap key and JWT secret in the backend process environment before starting the API:

```powershell
$env:NAGARSYNC_BOOTSTRAP_KEY = "use-a-long-random-one-time-key"
$env:JWT_SECRET = "use-a-different-long-random-secret"
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

In another PowerShell terminal, use the same bootstrap key to create the first administrator. Replace the sample email and choose a unique password of at least 10 characters:

```powershell
$key = "use-a-long-random-one-time-key"
$body = @{
  email = "admin@example.org"
  password = "replace-with-a-unique-password"
  name = "Municipal Administrator"
  bootstrap_key = $key
} | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/api/auth/bootstrap -Method Post -ContentType "application/json" -Body $body
```

The bootstrap endpoint is disabled unless `NAGARSYNC_BOOTSTRAP_KEY` is configured and refuses to create another administrator once one exists. Keep both secrets out of source control. Administrators can create field-worker accounts after signing in.

Administrators are taken to the Admin Console after sign-in. Use **Manage Records** for create, view, edit, archive, and restore actions for reports, incidents, user accounts, and manually managed asset records. Manually managed assets are stored separately and remain unscored; they are not included in the simulated ML recommendations.

Municipal administrators can also open **Ward KPIs** for API-backed ward summaries, **Audit Log** for account and municipal record changes, and the work-order console to assign eligible jobs to registered field workers. Citizens receive in-app updates as reports and related work orders progress. Citizen report submission and status history support English and Tamil; choose a language on the report page. Notifications are in-app only—this demo does not send SMS or email.

Area-scoped community reporting is available from the citizen reports page. Residents select and follow a district plus a local area, then see matching reports, acknowledge them, and add community updates. Municipal administrators can search reports and work orders by district; field work status histories are visible in the matching area feed. Public community responses omit reporter identity and exact coordinates. Locality names are currently entered by users because this repository does not include an authoritative Tamil Nadu taluk/municipality/panchayat directory. Reports and work orders require a district and at least one local subdivision to appear in the community feed. The feed is a demonstration workflow, not an official notification service or verified government record.

The authenticated **Governance Overview** uses persisted reports and work orders for its counts and lists all 37 project district hubs, including districts with no records. It does not invent activity for empty districts. To populate an isolated, local JSON-backed demo with 15 illustrative reports, 10 sample work orders, and 10 editable unscored sample assets, run this in the backend PowerShell terminal before starting FastAPI:

```powershell
$env:MONGODB_URI = ''
.\.venv\Scripts\python.exe -m backend.app.seed_demo_governance --confirm-local-demo
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

Keep `$env:MONGODB_URI = ''` in that terminal while the backend runs so it uses the same local JSON stores as the seed command; this overrides the `.env` value only for that PowerShell session. Seeding refuses to run when a database URI is configured, is safe to rerun, and does not write to a shared database. Do not clear the URI in an environment where you intend to use a shared database. The sample taluk, local-body, ward, issue, work-order, and asset details are fictional scenarios, not verified place records, repairs, or service updates. Seeded reports and work orders are clearly marked as samples, and sample assets are editable from **Manage Records**. Governance resource-category counts summarize work orders only; they are not an asset inventory or live sensor feed.

The **Development Projects** workspace at `/governance` now reads persistent project records rather than hardcoded portfolio totals. Project records use the MongoDB `development_projects` collection when connected, or `reports/development_projects.json` for local development. Only administrators can create or change projects, record milestones/expenditure, or archive a project. Citizen and field-worker views only include public lifecycle statuses (`APPROVED`, `PLANNED`, `ONGOING`, `DELAYED`, `COMPLETED`, `VERIFIED`); proposed records remain private. Status changes and financial records are audit logged, expenditure is checked against the estimated cost, and public project updates notify followed locality subscribers where the project has a district and subdivision. No government project registry or verified finance source is connected.

To add three fictional project examples to the same isolated local JSON demo, run this alongside (or after) the governance sample seed:

```powershell
$env:MONGODB_URI = ''
.\.venv\Scripts\python.exe -m backend.app.seed_demo_projects --confirm-local-demo
```

The project seed is repeatable and refuses to run when `MONGODB_URI` is configured. Keep the environment variable blank in the same backend terminal when starting FastAPI to view these local JSON records. Sample locations, work descriptions, budgets, progress, and expenditure are fictional and marked **ILLUSTRATIVE SAMPLE**.

### Current implementation boundaries

This repository is still an academic demonstration, not a production government system. Authentication currently has three roles (`citizen`, `admin`, and `field_worker`); administrators are not yet restricted by municipality, taluk, or district jurisdiction. Do not provision this version for real authority use or store official/confidential records in it. The project workflow records milestones and self-entered expenditure but does not yet support project document/photo attachments, project approval evidence, or formal completion verification evidence. There is no verified statewide taluk/local-body/ward registry or boundary import workflow. Maps and sensor/ML analytics use the existing simulated fixture where labeled; real IoT feeds and official infrastructure/project data sources are not connected. These controls and integrations must be completed and security-reviewed before any real-world deployment.

### Create local demo accounts

For a local demo, run this from the project root:

```powershell
.\.venv\Scripts\python.exe -m backend.app.create_demo_accounts
```

The generated passwords are printed only in the local terminal. To rotate all three local demonstration account passwords and print their new values once, run:

```powershell
.\.venv\Scripts\python.exe -m backend.app.create_demo_accounts --reset-passwords
```

To rotate only the administrator demo password:

```powershell
.\.venv\Scripts\python.exe -m backend.app.create_demo_accounts --reset-passwords --role admin
```

The login screen contains only the sign-in and account-creation forms. It does not display demonstration account emails or passwords.

All application pages redirect unauthenticated visitors to sign-in. API endpoints and the live WebSocket also require a valid session; only registration, sign-in, and server-key-protected first-administrator bootstrap are public.

If Windows Application Control blocks a scikit-learn DLL, the API can still start for authentication and account management. Analytics routes return HTTP 503 until the server runs in an organization-approved Python environment; this application does not bypass Windows Application Control.

The normal command creates `municipal-admin@example.test`, `municipal-worker@example.test`, and `demo-citizen@example.test` accounts with randomly generated passwords, then prints credentials only for accounts it created. Save them before closing the terminal; they are not displayed in the browser or stored in plaintext. Existing demo accounts are left unchanged and missing accounts are created. The `--reset-passwords` option above rotates all three passwords. Do not use demo accounts in production.

### Recover an existing administrator account

If an administrator account already exists but its password is unknown, reset it from a local project-root terminal. The new password is entered through a hidden prompt, never added to source code, and existing sessions are revoked:

```powershell
.\.venv\Scripts\python.exe -m backend.app.recover_admin
```

After signing in as the administrator, create or reset field-worker accounts from **Manage Records**. The recovery command only changes active administrator accounts; it does not create fixed default credentials.

Or step by step:
```bash
python -m ml.run_pipeline --phase data
python -m ml.run_pipeline --phase train
python -m ml.run_pipeline --phase simulate --fast
cd frontend && npm run build && cd ..
uvicorn backend.app.main:app --port 8000
```

## Tests

```bash
pytest tests/ backend/tests/ -v
```

## Results (read from reports/experiments.json — simulated data)

Results are generated by the pipeline and read from `reports/experiments.json`.
Run the pipeline to populate them. Key metrics printed at end of simulate phase.

## Design Decisions

1. **Fixed-charge cost model**: A corridor visit costs mobilisation M_c once plus work costs. Uncoordinated planning pays M_c per asset. This shared-cost assumption is the primary driver of the headline saving — see Limitations.

2. **Co-location correlation**: Assets in the same corridor share a frailty term and vintage age factor, making their failure risks correlated. This is a modelling assumption documented in `ml/city.py`.

3. **ILP with greedy fallback**: `scipy.optimize.milp` solves the binary selection problem. If it times out or fails, `greedy_coordinated` is used as fallback.

4. **Calibrated risk**: Isotonic regression calibration on held-out months reduces ECE. Raw probabilities are never used as input features (no leakage).

5. **Common random numbers**: All strategies share the same failure draws per seed, making paired comparisons valid.

## Limitations

- **Simulated data only**: All city geometry, asset properties, failure rates, and outcomes are synthetic. Do not interpret as real-world performance.
- **Shared-cost assumption drives the headline saving**: If mobilisation costs are zero or very small, coordination provides no extra benefit (break-even scale shown in experiments).
- **Co-location correlation is an assumption**: Real cities may have different spatial correlation structures.
- **Greedy vs ILP gap**: The greedy coordinated heuristic may not reach the ILP optimum, especially at high budgets with many corridors.
- **Single-period optimisation**: The planner optimises one month at a time; multi-period planning could improve long-run outcomes.

## How to plug in real data

- **Leaks**: Replace `datasets/raw/water_daily.csv` with BattLeDIM-format MNF/pressure data. The `IsolationForest` detector requires no label changes.
- **Traffic**: Replace `datasets/raw/traffic_hourly.csv` with PeMS or local loop-detector data. Retrain with `python -m ml.run_pipeline --phase train`.
- **Assets**: Replace `datasets/raw/assets.csv` and `corridors.csv` with GIS exports. Ensure column names match `DATA_DICTIONARY.md`.

## Future Work

- Multi-period (annual) ILP with budget carryover
- Spatial clustering of corridors for joint mobilisation
- Real sensor integration (IoT condition monitoring)
- Uncertainty quantification on risk scores
- Equity-constrained multi-objective optimisation
