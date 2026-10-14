# Skill: API Contract Testing

## Overview
Guarantee that API implementations adhere strictly to their published contracts without breaking drift.

## Methodology
1. **Schema Comparison**: Validate runtime JSON responses against Pydantic/OpenAPI specs.
2. **Status Codes**: Confirm error scenarios return appropriate HTTP status codes.
3. **Idempotency**: Test that repeated requests behave according to HTTP semantics.
