# Security Checklist

## Implemented in starter
- [x] Password hashing with Argon2id
- [x] Short-lived signed access tokens
- [x] Role checks on privileged routes
- [x] Object ownership checks on consultation and prescription routes
- [x] Input validation using Pydantic
- [x] Database constraints and booking transaction
- [x] Idempotency record persisted in PostgreSQL
- [x] Audit events for key workflows
- [x] `.env` excluded from Git
- [x] Health endpoints separated into liveness/readiness

## Must complete before production
- [ ] Enforce HTTPS at ingress and configure secure headers
- [ ] Production secret manager and signing-key rotation
- [ ] MFA enrollment, recovery, and enforcement for doctors/admins
- [ ] Refresh-token rotation/revocation API and session management
- [ ] Production-grade rate limiting and request/body limits
- [ ] Encrypt sensitive clinical fields where required; verify key management
- [ ] Restrict and harden database roles; protect audit logs from modification
- [ ] Configure retention/deletion policies and applicable legal requirements
- [ ] Payment provider integration with signed webhook verification
- [ ] Dependency, container, and secret scans in CI
- [ ] Backup restore and disaster-recovery exercise
- [ ] Concurrency, authorization, and load tests against PostgreSQL
- [ ] Security review and penetration testing before handling real patient data

Never log passwords, bearer tokens, full prescriptions, or unnecessary patient data.
