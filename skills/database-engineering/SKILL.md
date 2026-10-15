# Skill: Database Engineering

## Overview
Authors type-safe SQLAlchemy 2.0 ORM models, manages transactional constraints, and creates fully reversible Alembic database migrations.

## Required Input Evidence
1. **Data Model Specification**: Entity relationships, constraints, and index requirements.
2. **Current Models & Migrations**: Existing models in `src/syntra/persistence/models.py` and applied migrations in `alembic/versions/`.

## Step-by-Step Procedure
1. **Define SQLAlchemy Models**:
   - Subclass `Base`, use `Mapped[T]` and `mapped_column()` type annotations.
   - Enforce UUID primary keys, foreign keys with ON DELETE policies, and explicit indexes.
2. **Generate Alembic Migration**:
   - Create new migration revision script in `alembic/versions/`.
   - Implement `upgrade()` and mirror in `downgrade()`.
3. **Verify DDL Compilation**:
   - Verify models compile without errors under PostgreSQL dialect.
4. **Test Migration Lifecycle**:
   - Execute `alembic upgrade head` and `alembic downgrade -1` in test harness to guarantee reversibility.
5. **Update Repository Interfaces**:
   - Add corresponding query methods in persistence repository layer.

## Tool Requirements
- `syntra.read_file`, `syntra.write_file`, `syntra.run_command`.

## Expected Output Artifacts
- `MigrationScript`: Reversible Alembic migration file.
- `SQLAlchemyModels`: Updated model definitions.

## Verification Procedure
- Both upgrade and downgrade execute without raising database exceptions.
- DDL compilation test passes.

## Failure and Escalation Conditions
- Escalate if data migration risks downtime or permanent data loss.
