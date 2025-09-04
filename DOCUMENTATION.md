Smart Financial Coach – Design Documentation
## 1. Problem Statement

Managing personal finances is complex: users have to track expenses, understand patterns, forecast spending, and evaluate saving/investment opportunities. Existing tools often lack personalization, transparency, and secure handling of sensitive data.

This project designs a privacy-first AI financial coach that:

Ingests and enriches financial transactions.

Surfaces insights via dashboards and anomaly detection.

Provides contextual coaching powered by local AI models.

Recommends safe saving and investment options.

Prioritizes security, monitoring, and scalability from the ground up.

## 2. Design Goals

Security-first: Sensitive financial data is never sent to third-party APIs.

Responsible AI: Local LLM (Ollama) ensures privacy, with guardrails against financial advice misuse.

User-centric: Simple onboarding, CSV ingestion, personalized coaching.

Extensible: Architecture supports cloud deployment, new financial assets, and advanced forecasting.

Observable: Structured logging and future telemetry hooks for monitoring.

## 3. System Architecture
Backend

Framework: FastAPI (async, typed, OpenAPI docs).

DB Layer: SQLAlchemy with SQLite (MVP); Postgres + Alembic migrations in roadmap.

AI Integration: Ollama wrapper for local LLM inference, configurable via env vars.

Forecasting: Prophet (if available) or heuristic fallback.

Security:

Password hashing with pepper.

Secrets injected via .env or Docker secrets.

Retention purge endpoints for coach/goal data.

Logging: structlog with JSON output, request-context enrichment for observability.

Frontend

Framework: React + Vite for fast iteration.

Styling: TailwindCSS (responsive, minimal).

Charts: Recharts for spend breakdown, timeline, and forecasting visuals.

UX Patterns: Onboarding overlay, cluster renaming, subscription resolve UX.

Infrastructure

Containerization: Docker + docker-compose.

CI/CD: GitHub Actions for testing, linting, Docker build, CodeQL scanning.

Future Cloud Readiness: K8s deployment roadmap, secrets vault integration (e.g., HashiCorp Vault).

## 4. Key Features & Design Rationale
| Feature                          | Design Choice                                  | Rationale                                                        |
| -------------------------------- | ---------------------------------------------- | ---------------------------------------------------------------- |
| CSV ingestion & canonicalization | Header synonym matching, description inference | Reduces user friction; adapts to varied bank exports             |
| Enrichment (clustering)          | Tokenization + similarity scoring              | Lightweight, interpretable, extendable to ML later               |
| Forecasting                      | Prophet fallback to heuristic                  | Balances rigor with resilience; works offline                    |
| Coaching                         | Local Ollama models                            | Ensures privacy; no data leaves the device                       |
| Investments                      | Seeded instruments + yield curve               | Provides immediate value; roadmap includes stocks/options/crypto |
| Security                         | Auth with pepper, secrets via env              | Security-aligned with PANW mission                               |
| Observability                    | structlog + CI/CD scans                        | Ensures maintainability, prepares for scale                      |

5. Tradeoffs & Alternatives

DB: SQLite chosen for MVP simplicity; Postgres planned for scaling.

Forecasting: Prophet adds accuracy but requires heavier dependencies; fallback ensures coverage.

AI Provider: Ollama keeps data local, trading cloud-scale models for privacy/security.

Auth: auth is not implemented for MVP; JWT & RBAC planned for production readiness.

6. Roadmap

Investment integrations: stocks, ETFs, options, crypto.

Observability stack: Prometheus + Grafana + OpenTelemetry.

Postgres + migrations for scale.

Kubernetes deployment.

Stronger auth (JWT refresh, rate limits, RBAC).

Guardrails on AI prompts + disclaimers.

7. Responsible AI

Local-only inference: No data used for model training or external APIs.

Transparency: Clear disclaimers that coaching is educational, not financial advice.

Retention controls: User can purge history and goals.

Future work: PII stripping, hallucination checks, toxicity filters.

8. Tech Stack Summary

Backend: FastAPI, SQLAlchemy, Pandas, Prophet (optional), structlog.

Frontend: React, Vite, TailwindCSS, Recharts.

AI: Ollama (configurable models like phi3, mistral, llama3).

Infra: Docker, GitHub Actions, Dependabot, CodeQL.

Auth: Prototype session tokens with peppered password hashes.