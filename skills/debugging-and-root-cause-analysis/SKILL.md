# Skill: Debugging and Root Cause Analysis

## Overview
Systematically analyzes stack traces, error outputs, and execution logs to diagnose defects, formulate testable hypotheses, and deliver surgical fix patches.

## Required Input Evidence
1. **Failing Test Output / Stderr**: Raw trace, assertion failure message, and environment details.
2. **Affected Source Files**: Code under test and test fixtures.

## Step-by-Step Procedure
1. **Triage & Classification**:
   - Classify defect: Syntax, Type Error, Logic Regression, Concurrency Race, Resource Exhaustion, or Environment Discrepancy.
2. **Formulate Root Cause Hypothesis**:
   - Trace data flow from input to failure point. Identify where actual behavior diverged from contract.
3. **Author Minimal Reproducing Test**:
   - Create an isolated test case that fails deterministically on the defect.
4. **Author Surgical Fix**:
   - Apply minimal patch to resolve the root cause without side effects.
5. **Verify Resolution**:
   - Run the reproducing test; verify it passes.
   - Run full regression suite; confirm zero unintended regressions.
6. **Submit Root Cause Analysis Report**:
   - Publish `RootCauseAnalysisReport` artifact with timeline and fix.

## Tool Requirements
- `syntra.read_file`, `syntra.write_file`, `syntra.run_command`.

## Expected Output Artifacts
- `RootCauseAnalysisReport`: Detailed diagnosis document.
- `MinimalFixPatch`: Surgical unified diff patch.

## Verification Procedure
- Reproducing test must fail before patch and pass after patch.
- Regression suite remains 100% green.

## Failure and Escalation Conditions
- Escalate if defect originates from external third-party dependency bug requiring library upgrade or architectural workaround.
