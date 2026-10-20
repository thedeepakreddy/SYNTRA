# Phase 13 Inventory Management Service (Benchmark Target Fixture)

This repository serves as the external target repository for SYNTRA Phase 13 end-to-end integration benchmarks.

## Architecture
- **Framework**: FastAPI (REST API)
- **Persistence**: SQLAlchemy 2.0 with SQLite / PostgreSQL backend
- **Domain**: Warehouse inventory management, inter-warehouse transfers, and stock ledger tracking.

## Known Issues (Intentional Defects for Multi-Agent Resolution)
1. **Transfer Overdraft Defect**: The warehouse transfer logic in `service.py` checks `source_stock.quantity <= 0` instead of `source_stock.quantity < transfer_quantity`, allowing requests to overdraw stock and drive warehouse inventory negative.
2. **Timezone Offset Comparison Defect**: The historical stock ledger query compares naive database timestamps with timezone-aware filter parameters without UTC normalization, causing runtime comparison failures (`TypeError` / 500 error).
