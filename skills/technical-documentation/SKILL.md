# Skill: Technical Documentation

## Overview
Authors clear, structured, and authoritative technical documentation, including system architecture specifications, API references, runbooks, and Mermaid diagrams.

## Required Input Evidence
1. **Source Code & Models**: Actual source code, schemas, and routes.
2. **Architecture Specifications & ADRs**: High-level designs and decisions.

## Step-by-Step Procedure
1. **Identify Target Audience & Scope**:
   - Determine whether document is developer guide, API reference, or architectural blueprint.
2. **Draft Document Structure**:
   - Title, Overview, Prerequisites, Architecture/Design, Step-by-Step Guides, Security & Failure Handling.
3. **Author Mermaid Diagrams**:
   - Build flowcharts, sequence diagrams, and class diagrams to visualize complex interactions.
4. **Embed Clickable Links**:
   - Link all referenced files and code symbols to local repository paths.
5. **Verify Syntax & Formatting**:
   - Check markdown rendering and validate Mermaid blocks.
6. **Publish Documentation Artifact**:
   - Persist document in `docs/`.

## Tool Requirements
- `syntra.workspace_search`, `syntra.read_file`, `syntra.list_directory`, `syntra.artifact_write`.

## Expected Output Artifacts
- `TechnicalSpecification`: Markdown specification file.

## Verification Procedure
- Verify Mermaid diagram syntax is free of parser errors.
- Verify file links point to existing files.

## Failure and Escalation Conditions
- Escalate if documented system behavior conflicts with actual code implementation.
