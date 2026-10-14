#!/usr/bin/env bash
# ==============================================================================
# SYNTRA Environment Bootstrap Script
# Synchronized Intelligence for Autonomous Engineering
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

echo "============================================================"
echo "⚡ Bootstrapping SYNTRA Development Environment"
echo "============================================================"

# 1. Check Python version
PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "❌ Error: Python 3 not found in PATH." >&2
    exit 1
fi

PY_VERSION=$("${PYTHON_BIN}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$("${PYTHON_BIN}" -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$("${PYTHON_BIN}" -c 'import sys; print(sys.version_info.minor)')

if [ "${PY_MAJOR}" -lt 3 ] || { [ "${PY_MAJOR}" -eq 3 ] && [ "${PY_MINOR}" -lt 12 ]; }; then
    echo "❌ Error: SYNTRA requires Python 3.12+. Detected: Python ${PY_VERSION}" >&2
    exit 1
fi
echo "✅ Python ${PY_VERSION} detected."

# 2. Check uv package manager
if ! command -v uv >/dev/null 2>&1; then
    echo "⚠️  uv not found. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="${HOME}/.local/bin:${PATH}"
fi
echo "✅ uv $(uv --version) available."

# 3. Virtual environment setup
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment (.venv)..."
    uv venv .venv
else
    echo "✅ Virtual environment (.venv) already exists."
fi

# 4. Install locked dependencies
echo "📥 Installing pinned dependencies from uv.lock..."
uv sync --locked --extra dev --extra test --extra integrations

# 5. Create runtime state directories
echo "📁 Initializing local .syntra storage directories..."
mkdir -p .syntra/sandboxes .syntra/artifacts .syntra/logs .syntra/data

# 6. Copy default .env if missing
if [ ! -f ".env" ]; then
    echo "📄 Creating initial .env from .env.example..."
    cp .env.example .env
else
    echo "✅ Existing .env detected."
fi

# 7. Verification
echo "🔍 Validating SYNTRA installation..."
uv run python -c "import syntra; from syntra.core.config import get_settings; print(f'✅ SYNTRA v{syntra.__version__} initialized in {get_settings().autonomy_mode.value} mode.')"

echo "============================================================"
echo "🚀 SYNTRA environment successfully bootstrapped!"
echo "   Run 'make doctor' to verify system health."
echo "   Run 'make test' to execute test suite."
echo "============================================================"
