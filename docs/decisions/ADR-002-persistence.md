# ADR-002: PostgreSQL 16 with SQLAlchemy 2.x and Transactional Outbox

- **Status**: ACCEPTED
- **Date**: 2026-10-15
- **Deciders**: Principal Software Architect, Database Architect

---

## 1. Context & Problem Statement
SYNTRA requires an authoritative, durable persistence system to manage complex entity graphs (Organizations, Projects, Missions, Tasks, Dependencies, Leases, Artifacts, Events). The persistence layer must guarantee ACID compliance, optimistic concurrency control, safe worker lease claiming (`SELECT ... FOR UPDATE SKIP LOCKED`), and zero dual-write message loss between state mutations and event publishing.

---

## 2. Decision Drivers
- **Relational Integrity**: Foreign key constraints, unique checks, and cycle-free task dependencies.
- **Concurrency & Locking**: Row-level locking for worker lease acquisition under high contention.
- **Reliable Messaging**: Guaranteed delivery of workflow events to external streams (Redis / WebSockets).
- **Extensibility**: Support for future semantic search via `pgvector`.

---

## 3. Considered Options
1. **Option A: Document Database (MongoDB / DynamoDB)**: Flexible schema, but weak multi-entity transactional guarantees and complex constraint checking.
2. **Option B: Event Sourced Store**: Full event history, but high query complexity for active DAG traversals and lease reconciliation.
3. **Option C: Relational PostgreSQL 16 with Transactional Outbox**: ACID transactions, robust foreign keys, optimistic concurrency (`version`), row-level locking, and proven transactional outbox pattern.

---

## 4. Decision Outcome
**Chosen Option**: **Option C: PostgreSQL 16 with SQLAlchemy 2.x (asyncpg) and Transactional Outbox**.

### Key Rules:
- Primary keys are UUIDs; timestamps are `TIMESTAMPTZ` (UTC).
- Concurrency on mutable entities uses optimistic locking (`version INTEGER`).
- Asynchronous events are written to `transactional_outbox` inside the primary business transaction.
- Background worker relays outbox events to Redis Streams and WebSocket subscribers.
- Local development permits an SQLite fallback (`aiosqlite`) strictly for offline test suites.

### Tradeoffs:
- **Pros**: Strong relational guarantees, prevention of dual-write race conditions, atomic lease operations.
- **Cons**: Requires migration tooling (Alembic) and strict schema management.
