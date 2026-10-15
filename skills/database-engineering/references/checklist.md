# Database-Engineering Checklist

- [ ] Every database change must include a forward upgrade and complete backward downgrade in Alembic.
- [ ] All tables must define UUID primary keys, created_at timestamps, and proper indexes.
- [ ] Destructive schema alterations on production tables must provide a non-breaking multi-phase migration plan.
