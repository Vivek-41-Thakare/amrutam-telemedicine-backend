# Amrutam Telemedicine Backend
efrg
A Python/FastAPI + PostgreSQL + Redis starter for a telemedicine backend engineering assignment. It includes initial user authentication, role checks, doctor profiles, availability, transactional consultation booking with a PostgreSQL-backed idempotency record, consultation lifecycle, prescriptions, audit events, Docker Compose, OpenAPI, starter tests, CI, and design/security documents.

> **Important:** This is an assignment starter, not a certified or production-approved healthcare system. Do not use real patient data or expose it publicly until the production checklist is completed and independently reviewed. MFA, full refresh-token lifecycle, production rate limiting, payment-provider integration, complete metrics/tracing instrumentation, and cloud Terraform resources are not fully implemented yet.

## Prerequisites
- Docker Desktop with Docker Compose
- Git
- Optional for running tests locally: Python 3.12+

## Quick start (Windows PowerShell)
1. Extract the ZIP and open the extracted folder in VS Code.
2. Create your local environment file:
   ```powershell
   Copy-Item .env.example .env
   ```
3. Generate a local secret and replace `JWT_SECRET_KEY` in `.env`:
   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
   Do not commit `.env`. The Compose database password is for local development only.
4. Build and start:
   ```powershell
   docker compose up --build -d
   ```
5. Apply schema migrations:
   ```powershell
   docker compose exec api alembic upgrade head
   ```
6. Check:
   - Liveness: http://localhost:8000/health/live
   - Readiness: http://localhost:8000/health/ready
   - Swagger/OpenAPI: http://localhost:8000/docs
7. Logs:
   ```powershell
   docker compose logs -f api
   ```
8. Stop:
   ```powershell
   docker compose down
   ```
   To delete the local database volume too (destructive):
   ```powershell
   docker compose down -v
   ```

## API starter workflow
- `POST /api/v1/auth/register` creates a patient.
- `POST /api/v1/auth/login` returns a bearer access token.
- `GET /api/v1/users/me` checks the token.
- Doctor account creation is intentionally not self-service: provision a user with `role=doctor` through a controlled administrative process for local demo, then `POST /api/v1/doctors` to create the doctor profile.
- Admin verification is also a controlled provisioning step; never let public registration choose admin/doctor roles.
- `POST /api/v1/doctors/me/availability` creates a future availability slot for a verified doctor.
- `POST /api/v1/consultations` requires `Authorization: Bearer <token>` and `Idempotency-Key: <unique-key>`.
- `GET /api/v1/docs` is not the Swagger path; use `/docs`.

## Tests (local Python)
Create a venv, activate it, install dependencies, set `DATABASE_URL` to a test PostgreSQL database, then run:
```powershell
pip install -r requirements.txt
pip install email-validator
pytest
ruff check app tests
```
Some integration tests require a reachable PostgreSQL instance and migrated schema. Never point tests at a production database.

## Repository map
- `app/`: API, models, configuration, auth, DB access
- `migrations/`: Alembic schema migration
- `tests/`: starter automated tests
- `docs/`: architecture, threat model, security checklist, ER and sequence diagrams, DR notes
- `monitoring/`: Prometheus starter configuration
- `infra/terraform/`: Terraform deployment plan/scaffold (cloud resources still need implementation)

## Known limitations before production
- MFA and refresh-token rotation/revocation flows are not complete.
- Payment records exist, but no payment gateway is integrated.
- Rate limiting needs a production implementation and tests.
- Prometheus config is a scaffold; `/metrics` and full OpenTelemetry tracing need instrumentation.
- Terraform is a scaffold and does not provision resources yet.
- CI and tests must be run and green in the target environment.
- Define retention, privacy, clinical encryption, backup, RPO/RTO, and compliance requirements with the service owner.
