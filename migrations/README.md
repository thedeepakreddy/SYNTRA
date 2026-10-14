# Database Migrations

This directory hosts database migration scripts (Alembic) for SYNTRA's PostgreSQL persistence layer.

## Guidelines
- All schema changes must be reversible with explicit `upgrade()` and `downgrade()` methods.
- Phase 2 formally introduces Alembic migration files and models.
