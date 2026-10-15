# Skill: Requirements Analysis

## Overview
Transforms unstructured user objectives and problem statements into exhaustive, verifiable Product Requirements Documents (PRDs) with formal acceptance criteria.

## Required Input Evidence
1. **User Objective String**: The raw mission prompt or feature request from the user.
2. **Repository Baseline**: Existing README, architecture docs, and API documentation.
3. **Domain Constraints**: Organizational policies, compliance baselines, and performance targets.

## Step-by-Step Procedure
1. **Deconstruct User Objective**:
   - Extract core functional goals, target user personas, and intended business outcomes.
   - Separate explicit constraints from assumed behaviors.
2. **Repository Context Ingestion**:
   - Inspect existing domain models, endpoints, and docs via `syntra.workspace_search`.
   - Ensure the new requirement integrates cleanly without duplicating existing capabilities.
3. **Formulate Requirements**:
   - Author functional requirements specifying inputs, transformations, and persistent effects.
   - Author non-functional requirements (latencies, security posture, concurrency).
4. **Draft Acceptance Criteria (Given-When-Then)**:
   - Every requirement must have at least one testable criterion in standard Given-When-Then format.
5. **Log Ambiguities**:
   - Record open questions, assumptions made, and technical tradeoffs in the ambiguity log.
6. **Submit PRD Artifact**:
   - Publish the structured `PRDDocument` artifact for architectural review.

## Tool Requirements
- `syntra.workspace_search`: Discover existing repository capabilities and documentation.
- `syntra.read_file`: Read existing specifications and README.
- `syntra.list_directory`: Discover file trees.
- `syntra.artifact_write`: Persist the final PRDDocument.

## Expected Output Artifacts
- `PRDDocument`: Complete markdown artifact with YAML frontmatter.

## Verification Procedure
- Assert every requirement has testable Given-When-Then criteria.
- Assert zero source code modifications were performed by the agent.

## Failure and Escalation Conditions
- Escalate to Human Delivery Gate if the user objective fundamentally contradicts existing system invariants.
