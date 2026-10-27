# Backup and Disaster Recovery

## Targets
Business stakeholders must set the Recovery Point Objective (RPO) and Recovery Time Objective (RTO). Do not infer or promise RPO/RTO from this local Compose deployment.

## Production baseline
- Use a managed PostgreSQL service with automated backups and point-in-time recovery.
- Enable high availability and multi-zone failover where available.
- Encrypt backups and restrict restore permissions.
- Keep backup credentials separate from application credentials.
- Back up infrastructure configuration and store Terraform state remotely with locking and encryption.
- Define retention and deletion schedules with legal/compliance stakeholders.

## Recovery runbook
1. Declare incident and identify authoritative recovery point.
2. Stop unsafe writes if data consistency is uncertain.
3. Restore database to a clean isolated environment or initiate managed PITR.
4. Validate schema migrations, record counts, constraints, and application smoke tests.
5. Reconcile queued/outbox events before resuming asynchronous delivery.
6. Switch traffic only after integrity checks and approval.
7. Record actual RPO/RTO and complete a post-incident review.

## Exercises
Run restore drills periodically and record evidence. A successful backup job alone does not prove that data can be restored.
