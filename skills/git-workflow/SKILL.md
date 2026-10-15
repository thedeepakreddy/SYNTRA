# Skill: Git Workflow

## Overview
Executes safe, isolated version control operations using Git worktrees, feature branching, conventional commits, and clean patch extraction.

## Required Input Evidence
1. **Target Branch / Task ID**: Identifiers for the work branch.
2. **Worktree Path**: Isolated directory location for task execution.

## Step-by-Step Procedure
1. **Provision Worktree**:
   - Create isolated worktree branching from baseline: `git worktree add <path> -b <branch_name>`.
2. **Execute Changes**:
   - Engineer works strictly within the isolated worktree directory.
3. **Stage & Commit**:
   - Stage modified files selectively (exclude generated artifacts, caches, logs).
   - Format commit message according to Conventional Commits: `<type>(<scope>): <description>`.
4. **Extract Unified Diff**:
   - Generate diff against baseline branch: `git diff origin/main...HEAD`.
5. **Clean Up Worktree**:
   - Safely remove worktree after patch extraction: `git worktree remove <path>`.

## Tool Requirements
- `syntra.read_file`, `syntra.write_file`, `syntra.run_command`, `syntra.git_branch`, `syntra.git_diff`.

## Expected Output Artifacts
- `WorktreeBranch`: Branch reference.
- `UnifiedDiff`: Clean unified diff patch.

## Verification Procedure
- Verify worktree is completely clean and removed after completion.

## Failure and Escalation Conditions
- Escalate if merge conflicts cannot be resolved cleanly against main branch.
