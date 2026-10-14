#!/usr/bin/env bash
# ==============================================================================
# SYNTRA System Diagnostic & Doctor Script
# Synchronized Intelligence for Autonomous Engineering
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

echo "============================================================"
echo "🩺 SYNTRA System Health & Environment Doctor"
echo "============================================================"

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

check_pass() {
    echo "  [OK] $1"
    PASS_COUNT=$((PASS_COUNT + 1))
}

check_warn() {
    echo "  [WARN] $1"
    WARN_COUNT=$((WARN_COUNT + 1))
}

check_fail() {
    echo "  [FAIL] $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

echo ""
echo "1. Host Runtime & Tooling:"

# Python
if command -v python3 >/dev/null 2>&1; then
    PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
    PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
    PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
    if [ "${PY_MAJOR}" -ge 3 ] && [ "${PY_MINOR}" -ge 11 ]; then
        check_pass "Python runtime: ${PY_VER}"
    else
        check_fail "Python runtime: ${PY_VER} (requires 3.11+)"
    fi
else
    check_fail "Python 3 is not installed or not in PATH"
fi

# uv
if command -v uv >/dev/null 2>&1; then
    check_pass "uv package manager: $(uv --version | head -n1)"
else
    check_fail "uv package manager is not installed"
fi

# Git
if command -v git >/dev/null 2>&1; then
    check_pass "Git: $(git --version)"
else
    check_fail "Git is not installed"
fi

# Docker
if command -v docker >/dev/null 2>&1; then
    check_pass "Docker CLI: $(docker --version)"
    if docker info >/dev/null 2>&1; then
        check_pass "Docker daemon is running"
    else
        check_warn "Docker daemon is not running (needed for compose services)"
    fi
else
    check_warn "Docker CLI is not installed (needed for full containerized stack)"
fi

echo ""
echo "2. Storage & Sandbox Directories:"
mkdir -p .syntra/sandboxes .syntra/artifacts .syntra/logs

if [ -w ".syntra/sandboxes" ]; then
    check_pass "Sandbox directory writable: .syntra/sandboxes"
else
    check_fail "Sandbox directory not writable: .syntra/sandboxes"
fi

if [ -w ".syntra/artifacts" ]; then
    check_pass "Artifacts directory writable: .syntra/artifacts"
else
    check_fail "Artifacts directory not writable: .syntra/artifacts"
fi

echo ""
echo "3. SYNTRA Python Package & Dependencies:"
if uv run python -c "import syntra; import fastapi; import sqlalchemy; import redis; import minio; import yaml" >/dev/null 2>&1; then
    check_pass "Core dependencies import cleanly"
else
    check_fail "Failed to import core dependencies in virtual environment"
fi

echo ""
echo "4. Subsystem Probes:"
PROBE_OUTPUT=$(uv run python -c "
import asyncio
from syntra.api.routes.health import readiness_check
from fastapi import Response

async def run_probe():
    resp = Response()
    res = await readiness_check(resp)
    for name, comp in res.components.items():
        print(f'{name}|{comp.status}|{comp.details}')

asyncio.run(run_probe())
")

while IFS='|' read -r comp status details; do
    if [ "${status}" = "healthy" ]; then
        check_pass "Subsystem [${comp}]: healthy (${details})"
    elif [ "${status}" = "unavailable" ]; then
        check_warn "Subsystem [${comp}]: unavailable (${details})"
    else
        check_fail "Subsystem [${comp}]: ${status} (${details})"
    fi
done <<< "${PROBE_OUTPUT}"

echo ""
echo "5. LLM Credentials:"
if uv run python -c "from syntra.core.config import get_settings; assert get_settings().is_api_key_configured()" >/dev/null 2>&1; then
    check_pass "Gemini API key is configured"
else
    check_warn "Gemini API key not configured (GEMINI_API_KEY). Mock provider will be used for testing."
fi

echo ""
echo "============================================================"
echo "Doctor Summary: ${PASS_COUNT} Passed, ${WARN_COUNT} Warnings, ${FAIL_COUNT} Failures"
echo "============================================================"

if [ "${FAIL_COUNT}" -eq 0 ]; then
    echo "🎉 SYNTRA environment is healthy and ready for development!"
    exit 0
else
    echo "❌ SYNTRA environment has failures that must be resolved."
    exit 1
fi
