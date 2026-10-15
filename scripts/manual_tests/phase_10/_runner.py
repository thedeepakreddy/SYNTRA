"""Runnable acceptance scenarios using real repository interfaces through pytest fixtures.

No production database defaults, paid provisioning, host target execution, or
invented results. The live tests own cleanup of their UUID resources.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
MISSION = "tests/test_phase10_mission_live.py::test_complete_engineering_mission_real_infrastructure"
SCENARIOS = {
    "02": ["tests/test_phase10_agents.py", "-k", "pm_ or unknown_or_unauthorized"],
    "03": ["tests/test_phase10_agents.py", "-k", "software_architect"],
    "04": ["tests/test_phase10_agents.py", "-k", "engineering_manager or task_plan"],
    "05": ["tests/test_phase10_agents.py", "-k", "skills or skill"],
    "06": ["tests/test_phase10_independent_qa.py", "-k", "gateway or qa_write or claimed_write"],
    "07": [MISSION + "[accepted]"],
    "08": [MISSION + "[accepted]"],
    "09": [MISSION + "[review_rejection_and_debugging]"],
    "10": [MISSION],
    "11": ["tests/test_phase10_worker_live.py"],
    "12": [MISSION],
    "13": ["tests/test_phase10_mission_live.py::test_live_gemini_engineering_mission"],
}


def run(scenario: str) -> int:
    load_dotenv(ROOT / ".env")
    if scenario == "01":
        from syntra.cli.engineering import registry

        agents = registry()
        assert len(agents.definitions) == 10
        print(
            json.dumps(
                {
                    "scenario": scenario,
                    "mode": "REAL_REGISTRY_VALIDATION",
                    "roles": [r.value for r in agents.definitions],
                    "result": "PASS",
                }
            )
        )
        return 0
    infrastructure = scenario in {"07", "08", "09", "10", "11", "12", "13"}
    if infrastructure and not os.environ.get("SYNTRA_TEST_POSTGRES_URL"):
        print(
            json.dumps(
                {
                    "scenario": scenario,
                    "result": "BLOCKED_BY_DEPENDENCY",
                    "prerequisite": "dedicated SYNTRA_TEST_POSTGRES_URL, Redis and Docker test image",
                }
            )
        )
        return 77
    mode = (
        "MOCK_MODEL_REAL_POSTGRES_REDIS_DOCKER" if infrastructure else "DETERMINISTIC_MODEL_REAL_POLICY_AND_CONTRACTS"
    )
    environment = dict(os.environ)
    if scenario == "13":
        from syntra.llm.gemini_provider import GeminiModelProvider

        if not GeminiModelProvider().is_configured():
            print(
                json.dumps(
                    {"scenario": scenario, "result": "BLOCKED_BY_CREDENTIALS", "provider_execution": "UNVERIFIED"}
                )
            )
            return 77
        environment["SYNTRA_RUN_PHASE10_GEMINI"] = "1"
        mode = "LIVE_GEMINI_REAL_POSTGRES_REDIS_DOCKER"
    print(
        json.dumps(
            {
                "scenario": scenario,
                "mode": mode,
                "harness": "pytest production-interface acceptance scenarios",
                "prerequisites": "isolated test data; no production services",
            }
        ),
        flush=True,
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=short", *SCENARIOS[scenario]], cwd=ROOT, env=environment
    )
    print(
        json.dumps(
            {
                "scenario": scenario,
                "exit_code": result.returncode,
                "result": "PASS" if result.returncode == 0 else "FAIL",
            }
        ),
        flush=True,
    )
    return result.returncode
