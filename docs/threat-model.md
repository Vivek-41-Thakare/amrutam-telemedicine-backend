# Threat Model

## Assets and classification
- Public: API docs and public doctor search fields.
- Internal: operational metrics, deployment configuration, non-sensitive diagnostic logs.
- Confidential: account email/phone, payment references, authentication/session metadata.
- Restricted clinical: consultation reasons/notes, prescriptions, patient-doctor relationship, clinical audit events.

## Trust boundaries / attack surface
Internet clients -> HTTPS ingress -> FastAPI routes -> PostgreSQL/Redis -> background workers -> notification/payment providers; CI/CD and cloud control plane are separate trust boundaries.

## Principal threats and controls
- Broken object-level authorization: verify resource ownership on every consultation/prescription operation; negative cross-user tests.
- Credential stuffing/brute force: password hashing, rate limits, MFA for privileged roles, monitoring.
- Token theft/replay: short-lived access tokens, secure transport, refresh-token rotation/revocation; production key rotation.
- SQL injection: SQLAlchemy bound parameters; never concatenate user input into SQL.
- Booking race conditions: row-level lock, unique constraints, durable idempotency records and concurrent integration tests.
- Sensitive data leakage: response minimization, log redaction, encryption in transit/at rest, restricted database access.
- Privilege escalation: users cannot self-select doctor/admin roles; privileged account provisioning must be controlled.
- Secret exposure: `.env` ignored, `.env.example` contains placeholders, secret scanning in CI.
- Dependency/supply-chain compromise: pinned major ranges, vulnerability scanning, review and update dependencies.
- Audit tampering: append-only application behavior, restricted DB permissions, centralized protected log sink in production.
- Denial of service: request/body limits, rate limiting, bounded queries, timeouts and resource limits.

## Residual risks and production requirements
MFA delivery, refresh-token rotation endpoints, field-level clinical encryption, production rate limiting, payment-provider verification, external audit immutability, and cloud key management require completion and verification before real patient data or production traffic is used. This project is a development submission, not a compliance certification.
