# Architecture — Amrutam Telemedicine Backend

## 1. Scope and design
This repository is a production-oriented starter for a telemedicine REST API. It uses a modular-monolith approach: FastAPI routes, domain services, SQLAlchemy persistence, PostgreSQL transactions, Redis for supporting infrastructure, and containerized deployment. Modules can be extracted into services later if measured load or team boundaries justify it.

## 2. High-level architecture and data flow
Clients connect over HTTPS to a stateless API deployment. Authentication validates a short-lived signed access token; authorization checks the caller's role and ownership of the requested resource. The API validates inputs, applies business rules, and performs durable writes in PostgreSQL. Redis is an optional cache/coordination component and is not the source of truth for bookings. Background work should be queued through a transactional outbox pattern so a committed business transaction is not lost between database commit and event publication.

## 3. Booking flow
1. Patient authenticates and submits a booking with an `Idempotency-Key`.
2. API validates the request and hashes its normalized payload.
3. A PostgreSQL transaction serializes reuse of the same actor/key and locks the selected availability row.
4. API checks that the slot is available, in the future, and owned by a verified doctor.
5. Consultation, slot status, idempotency result, and audit event are written in one transaction.
6. Duplicate requests replay the stored result; key reuse with a different payload returns conflict.
7. A slot uniqueness constraint and row lock prevent two patients from booking the same slot.

## 4. Data model
Core entities: users, doctors, availability_slots, consultations, prescriptions, payments, audit_logs, idempotency_records, refresh_tokens. UUID primary keys and foreign keys provide referential integrity. Query indexes support doctor schedule lookup, patient consultation history, and doctor consultation queues. Large audit tables can be partitioned by month when measured volume and retention needs justify it.

## 5. Reliability and retry policy
Use explicit connect/read/write timeouts for external dependencies. Retry only transient failures, with exponential backoff and jitter, bounded attempts, and a total deadline. Do not automatically retry validation errors, permission failures, or business conflicts. Use idempotency for retried writes. Background tasks need bounded retries, failure visibility, and dead-letter/manual replay procedures. Database deadlock retries must rerun the entire transaction, not only the last statement.

## 6. Caching and concurrency
Cache only low-risk, non-sensitive read data with explicit TTL and invalidation rules. Do not cache clinical records by default. PostgreSQL remains authoritative for slot status and booking uniqueness. Use row-level locking and unique constraints for booking. Use connection pooling and inspect query plans before adding indexes or introducing read replicas.

## 7. Security
Passwords are hashed using Argon2id. API access tokens are short-lived. Production must use TLS, managed secrets, strong token-signing keys, database encryption at rest, least-privilege database roles, MFA for privileged users, audit controls, dependency scanning, and tested key rotation. Clinical data must not appear in logs. This repository is not a certified healthcare-compliance product.

## 8. Availability, backup and DR
Target availability is 99.95%, but this repository alone does not prove that SLO. Production needs redundant application instances, managed database HA, health checks, alerting, tested backups, point-in-time recovery, and a documented failover runbook. Set RPO/RTO with the business, test restoration periodically, and measure actual recovery time.

## 9. Scaling and validation
100,000 consultations/day is an average of about 1.16 consultations/second, but peak traffic and read amplification determine capacity. Load-test representative search, booking, and consultation workloads. Record p50/p95/p99 latency, throughput, errors, and resource utilization. Do not claim targets are met without repeatable test results.
