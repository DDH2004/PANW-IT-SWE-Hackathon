<div align="center">

# Smart Financial Coach

AI-assisted personal finance coach: ingest & enrich transactions, surface insights, cluster emergent spending themes, recommend safe saving instruments, and provide contextual chat coaching with personalization.

</div>

## ✨ Major Capabilities

| Area | Highlights |
|------|------------|
| Ingestion | CSV upload, header synonym mapping, automatic description column inference (scored candidates, dry‑run analyze, force toggle), sign inference, canonical rename to `description` |
| Enrichment | Heuristic categorization, clustering of emergent descriptions, cluster renaming with historical propagation |
| Insights | Dashboard (timeframe: 1M / 1Y / All), category & merchant breakdown, timeline, anomalies (outliers + duplicate detection + selective deletion), subscriptions detection |
| Goals & Forecast | Goal CRUD + AI daily spend forecasting (Prophet w/ fallback), adjustable horizon, confidence bands, heuristic annual projection |
| Coaching | Local LLM (Ollama) chat, personalized context injection (recent spend, goals), chat history persistence, feedback (+/–) & retention purge |
| Investment Ideas | Seeded instruments & yield curve, safe save recommendations endpoint (`/coach/recommendations`) |
| Personalization | Stored coach messages per user, feedback storage, cluster rename memory |
| Auth (MVP) | User register/login, session tokens, password hashing + pepper |
| Onboarding | First-visit overlay (quick start cards) + persistent Guide button to reopen |
| UX | Description confirmation dialog, force selection toggle, raw ingestion debug view, timeframe filter, cluster rename UI (enrichment) |

## 🗺 First Run Flow
1. Register / login (if auth enabled branch retained; otherwise proceed directly).
2. Onboarding overlay appears (cards: Upload, Dashboard, Coach, Goals).
3. Upload CSV (use dry‑run Analyze first to inspect candidate description columns).
4. Confirm or force a description column → data canonicalized.
5. Visit Dashboard (use timeframe toggle) & Coach for contextual suggestions.
6. (Optional) Run Enrichment to build clusters; rename them for cleaner analytics.
7. Create a Goal → coaching answers begin referencing it.
8. Ask for safe saving ideas → pulls instrument & yield context.

## 🧱 Architecture Overview

Backend (FastAPI + SQLAlchemy / SQLite):
* Routes segmented by concern (`upload`, `dashboard`, `breakdown`, `enrich`, `goals`, `coach`, `invest`, `subscriptions`, `anomalies`, `auth`).
* Lightweight online "migration" pattern (models created at startup if missing).
* Ollama provider wrapper with adaptive timeout & localhost fallback.
* Clustering uses simple tokenization + Jaccard-like similarity for emergent themes.
* Description column inference scores: non-empty ratio, richness, sample diversity.
* Structured logging using `structlog` (JSON friendly, request-context enrichment ready for correlation IDs / tracing).

Frontend (React + Vite + Tailwind + Recharts):
* Modular pages loaded inside `App.jsx` nav.
* Onboarding overlay component with quick actions & localStorage flag.
* Coach chat with history load, feedback actions, and recommendation insertion.
* Timeframe filtering logic client-side on fetched aggregates.

## 🛠 CI/CD & Deployment
Workflows (GitHub Actions):
* `ci.yml` – parallel backend (pytest + coverage + pip-audit) & frontend (lint + build) jobs, Docker build stage (push scaffold commented out).
* `codeql.yml` – static analysis (Python + JavaScript) per push/PR & weekly schedule.
* `release.yml` – tag (`v*.*.*`) driven release with git log snippet & image build.
* `dependabot.yml` – automated weekly dependency update PRs (pip, npm, actions).

Recommended production hardening:
* Add coverage upload & badge (Codecov).
* Image security: SBOM (syft), vulnerability scan (Trivy/Grype) + policy gate.
* Image signing (cosign) before push to GHCR / registry.
* Staged deploy (staging env → production) with manual approval.

Secrets & Docker:
* Provide DB passwords / peppers as runtime secrets (Actions secrets / env vars), never baked into layers.
* Compose / K8s: mount via secrets objects or external vault (e.g., HashiCorp Vault, AWS Secrets Manager).

## 📦 Tech Stack
Backend: FastAPI, SQLAlchemy, Pandas, structlog, Prophet (if available) + heuristic fallback forecasting  
AI: Local Ollama (default model configurable)  
Frontend: React, TailwindCSS, Recharts, Axios  
Infra: Docker / docker-compose  
Auth: Basic session tokens (not production hardened)  

## 🚀 Quick Start

### 1. Backend
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```
Open Swagger: http://localhost:8000/docs

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```
App: http://localhost:5173

### 3. (Optional) Docker
```bash
docker compose up --build
```

### 4. (Optional) Change Model
```bash
curl -X POST http://localhost:8000/coach \
	-H 'Content-Type: application/json' \
	-d '{"message":"Tip to save on groceries","model":"mistral"}'
```

### 5. (Optional) Local LLM (Ollama) Setup
If you want fully local inference (default path) ensure Ollama is installed and the model pulled.

macOS / Linux install:
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Pull the default lightweight model (as referenced by `OLLAMA_MODEL` env var):
```bash
ollama pull phi3:mini
```

Optionally pull other models for experimentation:
```bash
ollama pull mistral
ollama pull llama3
```

Verify Ollama is running (defaults to http://localhost:11434):
```bash
curl http://localhost:11434/api/tags
```

Switch backend default model (set before starting API):
```bash
export OLLAMA_MODEL=mistral
uvicorn backend.main:app --reload
```

Test coaching endpoint end‑to‑end:
```bash
curl -X POST http://localhost:8000/coach \
	-H 'Content-Type: application/json' \
	-d '{"message":"give me a one-sentence saving tip"}'
```

Docker compose note: if you introduce an Ollama service container, set `OLLAMA_HOST` to that internal hostname (e.g. `http://ollama:11434`) and pre-pull models in the image build or via an init job.

## 📄 CSV Ingestion Details
Supports loose header synonyms for core fields. The system attempts to infer the best textual narrative column:
* Dry Run: `POST /upload?dry_run=true` → returns candidates with scoring (no DB writes).
* Force: `force_description_choice=true` to require explicit user confirmation even if high confidence.
* Auto-confirm: `auto_confirm_description=true` to accept top candidate if score threshold met.
* After confirmation the chosen column is renamed/canonicalized to `description` for downstream consistency.

Edge Handling:
* If user selects a category column as description, original category derivation preserved.
* Sign inference normalizes expense (negative) vs income (positive) when obvious patterns exist.

## 🔗 Enrichment & Clustering
`POST /enrich/` builds clusters of similar descriptions.  
Rename clusters: `POST /enrich/rename_cluster` (propagates to historical rows + metadata).
Latest snapshot: `GET /enrich/latest`.

## 💬 Coaching & Personalization
* Chat: `POST /coach` (includes recent context and optional recommendations snapshot).
* History: `GET /coach/history` (persisted per user/session).
* Feedback: `POST /coach` payload includes `feedback` path (or dedicated feedback route if added later) to score responses.
* Recommendations: `GET /coach/recommendations` uses seeded instruments + yield curve for “safe save ideas”.

## 💰 Investment Context
* Instruments list: `GET /instruments`
* Yield curve: `GET /yield_curve`
* Coach recommendations: `GET /coach/recommendations`

Planned Investment Integrations:
* Market data (stocks & ETFs) ingestion via public APIs or CSV.
* Options snapshot (basic Greeks / IV) for educational insights (non-advisory).
* Crypto balances (CSV/API) → holistic allocation & cash flow mix.
* Portfolio allocation & risk band overlays inside dashboard.

## 🎯 Goals
Endpoints under `/goals` support create, list, fetch, forecast, and sync operations. A goal forecast uses current savings velocity (basic placeholder) until advanced modeling is added.

## 📊 Breakdown & Insights
* Dashboard aggregate: `GET /dashboard`
* Category / merchants / timeline: `/breakdown/categories`, `/breakdown/merchants`, `/breakdown/timeline`
* Subscriptions: `GET /subscriptions`
* Anomalies: `GET /anomalies/` (outliers + duplicate groups) and `POST /anomalies/dedupe` (permanent removal of selected duplicate transaction IDs; confirmation shown in UI). Deletions are irreversible (no undo log retained).
* Forecast (AI + fallback): `GET /forecast` (daily spend projection with optional Prophet confidence intervals)

### Forecasting Details
The system attempts an AI-based forecast using Facebook/Meta Prophet if the library is installed and there is sufficient historical transaction span (>= ~45 days of daily data). If Prophet is unavailable or data is insufficient, it falls back to a simple average daily spend projection.

Frontend `Forecast` page features:
* Method selector: `auto` (default), `prophet`, or `simple`.
* Horizon selector (14–365 days) controlling forecast length.
* Stats summary: actual method used, annual projection (heuristic), next 30/60/90 day aggregate spend (if within horizon).
* Daily chart: predicted spend area + optional dashed upper/lower confidence bands (Prophet only).
* Reason note: explains fallback causes (e.g., `prophet_library_missing`, `insufficient_history`).

API: `GET /forecast`
Query Params:
* `method` (optional): `auto` | `prophet` | `simple` (default: auto)
* `horizon_days` (optional): int (default: 90)

Sample Response (Prophet path):
```json
{
	"forecast_method": "prophet",
	"annual_spend_projection": 18250.42,
	"next_30d_spend": 1520.33,
	"next_60d_spend": 3015.87,
	"next_90d_spend": 4550.11,
	"daily_forecast": [
		{ "date": "2025-09-05", "predicted_spend": 52.13, "lower": 41.9, "upper": 63.8 },
		{ "date": "2025-09-06", "predicted_spend": 50.77, "lower": 40.6, "upper": 61.4 }
	],
	"reason": null
}
```

Fallback Response (simple heuristic) example (no interval band):
```json
{
	"forecast_method": "simple",
	"annual_spend_projection": 17400.00,
	"next_30d_spend": 1450.00,
	"daily_forecast": [
		{ "date": "2025-09-05", "predicted_spend": 48.33, "lower": 48.33, "upper": 48.33 }
	],
	"reason": "prophet_library_missing"
}
```

Quick curl:
```bash
curl "http://localhost:8000/forecast?method=auto&horizon_days=120"
```

## 👤 Auth (Prototype)
* Register: `POST /auth/register`
* Login: `POST /auth/login` → returns token (header or query usage depending on frontend integration branch).
Passwords hashed + pepper (environment variable). Not production grade (no refresh tokens / rate limiting / lockouts yet).

## 🛠 API Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /upload | CSV ingest (supports dry_run, force, auto-confirm params) |
| GET | /dashboard | High-level KPIs + timeframe base data |
| GET | /insights | Legacy spend insights summary |
| GET | /transactions | List transactions |
| GET | /transactions/{id}/category/history | Category change audit |
| POST | /admin/wipe | Development data wipe |
| GET | /subscriptions | Recurring spend detection |
 | GET | /forecast | Daily spend forecast (Prophet or heuristic) |
| GET | /breakdown/categories | Category aggregation |
| GET | /breakdown/merchants | Merchant aggregation |
| GET | /breakdown/timeline | Time series spending |
| POST | /enrich/ | Build description clusters |
| GET | /enrich/latest | Latest cluster snapshot |
| POST | /enrich/rename_cluster | Rename a cluster |
| GET | /anomalies/ | Outlier transactions |
| POST | /anomalies/dedupe | Delete selected duplicate transactions (permanent) |
| GET | /instruments | Investment instruments seed data |
| GET | /yield_curve | Yield curve points |
| GET | /coach/recommendations | Safe saving recommendations |
| POST | /coach | Chat completion (local LLM) |
| GET | /coach/history | Chat history |
| GET | /coach/debug | Provider status & models |
| POST | /auth/register | Create user |
| POST | /auth/login | Login / token |
| GET | /goals/ | List goals |
| POST | /goals/ | Create goal |
| GET | /goals/{id} | Fetch goal |
| POST | /goals/{id}/sync | Recompute state |
| GET | /goals/{id}/forecast | Goal attainment forecast |
| GET | /health | Health check |

## ⚙️ Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| DATABASE_URL | sqlite:///./data/app.db | DB connection string |
| OLLAMA_HOST | http://localhost:11434 | Ollama endpoint |
| OLLAMA_MODEL | phi3:mini | Default model name |
| MODEL_PROVIDER | ollama | Provider switch (future multi-provider) |
| AUTH_PEPPER | pepper123 | Password pepper (change in prod) |
| MONTHLY_BUDGET | 0 | Optional budget for dashboard KPI |

Example `.env`:
```bash
DATABASE_URL=sqlite:///./data/app.db
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=phi3:mini
MODEL_PROVIDER=ollama
AUTH_PEPPER=change_me
MONTHLY_BUDGET=2500
```

## 🔐 Security / Privacy Notes (Current Status)
* Local model inference (no outbound AI API by default).
* Basic auth only; add robust authN/Z before production.
* Chat + goals persisted in SQLite; provide retention purge endpoints (coach clear).
* Avoid storing secrets in code; rely on `.env`.

## 🤖 Responsible AI
* Data stays local (Ollama) – no user financial data sent to third-party LLM APIs by default.
* No user content used for model training / fine-tuning.
* Retention purge endpoint lets users clear history (extensible to time-based retention policies).
* Guardrails (in-progress): restrict high-risk financial advice; responses framed as educational insights.
* Planned: prompt sanitization (PII stripping), lightweight hallucination / toxicity heuristics, visible disclaimer banner for investment queries.

## 🧪 Testing
```bash
pytest -q
```
(Add more granular test modules under `tests/` as features mature.)

## 🧭 Roadmap (Next Pass)
* Deeper forecast-goal integration (what-if savings scenarios, goal attainment probability curves).
* Production auth (JWT refresh, role isolation, rate limiting).
* Rich anomaly explanations & root-cause suggestions.
* Natural language query to SQL with guardrails.
* Notification channels (email / webhook) for threshold & anomaly alerts.
* Cluster quality metrics + manual merge/split.
* Postgres migration + seeded migrations (Alembic) replacing SQLite (scaling step) + optional cloud deployment (container orchestration).
* Frontend state sync for auth-gated navigation (if reverted earlier).
* Improved risk-adjusted recommendation scoring.
* Expanded asset coverage: stocks, ETFs, options, crypto ingestion & allocation analytics.
* Observability stack: Prometheus metrics + Grafana dashboards + OpenTelemetry traces.
* Kubernetes (Helm chart) for horizontal scaling & rolling deploys.

## 🛡 Disclaimer
Prototype / educational build. Not audited. Don’t use with real financial data without hardening, security review, and compliance checks.

## 🤝 Contributions
Issues / PRs welcome: docs clarity, tests, performance, model prompt improvements.

---
Happy building – explore, upload, enrich, coach, and iterate.
