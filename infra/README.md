# SYNTRA Infrastructure

This directory contains deployment and infrastructure definitions.

## Key Services
- **PostgreSQL 16**: Primary relational storage and outbox event log (`docker-compose.yml`, `compose.yaml`).
- **Redis 7**: Distributed task queue, worker leases, and streaming bus.
- **MinIO**: S3-compatible object storage for patches, task logs, and build artifacts.
