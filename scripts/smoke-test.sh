#!/usr/bin/env bash
# ==============================================================================
# SYNTRA Smoke Test Script
# Synchronized Intelligence for Autonomous Engineering
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

echo "============================================================"
echo "🔥 Running SYNTRA Smoke Test Suite"
echo "============================================================"

# 1. Package import verification
echo "1. Checking SYNTRA package import..."
uv run python -c "
import syntra
from syntra.core.config import get_settings
from syntra.storage.database import get_db_manager
from syntra.api.app import app
print(f'   SYNTRA v{syntra.__version__} imports successfully.')
"

# 2. CLI help verification
echo "2. Checking CLI binary..."
uv run syntra --help >/dev/null
echo "   CLI responsive."

# 3. Skills manifests validation
echo "3. Validating 16 skill manifests..."
uv run python -c "
from pathlib import Path
import yaml

skills_root = Path('skills')
assert skills_root.exists()
skills = [d for d in skills_root.iterdir() if d.is_dir()]
assert len(skills) == 16, f'Expected 16 skills, found {len(skills)}'
for s in skills:
    manifest = yaml.safe_load((s / 'manifest.yaml').read_text())
    assert manifest['name'] == s.name
print('   All 16 skill manifests verified.')
"

# 4. Automated test suite execution
echo "4. Executing pytest test suite..."
uv run pytest --maxfail=1 -q

echo "============================================================"
echo "🎉 SYNTRA Smoke Test Passed Successfully!"
echo "============================================================"
