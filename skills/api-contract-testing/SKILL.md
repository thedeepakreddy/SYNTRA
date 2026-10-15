# Skill: API Contract Testing

## Overview
Validates API endpoints against published OpenAPI specifications, ensuring that payload schemas, status codes, and error formats remain strictly backward-compatible.

## Required Input Evidence
1. **OpenAPI Specification**: Authoritative endpoint schemas and response definitions.
2. **Active Test Endpoint / ASGI Client**: Test harness client for dispatching requests.

## Step-by-Step Procedure
1. **Schema Ingestion**:
   - Parse OpenAPI JSON/YAML; extract path parameters, request bodies, and expected responses.
2. **Execute Contract Invocations**:
   - Send valid payloads; verify response status code and response schema match specification.
3. **Execute Boundary & Error Invocations**:
   - Send invalid payloads; verify 422/400 responses adhere to RFC 7807 schema.
4. **Detect Drift**:
   - Compare observed responses against prior baseline schemas; identify breaking changes.
5. **Publish Verification Report**:
   - Emit `ContractDriftReport` artifact.

## Tool Requirements
- `syntra.read_file`, `syntra.write_file`, `syntra.run_command`.

## Expected Output Artifacts
- `ContractDriftReport`: Analysis of contract compliance and drift.

## Verification Procedure
- Zero schema validation errors for all declared endpoints.

## Failure and Escalation Conditions
- Escalate if breaking API drift is detected without corresponding version increment.
