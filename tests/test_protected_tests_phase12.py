"""Unit and adversarial tests for ProtectedTestRegistry (Phase 12)."""

import hashlib
from pathlib import Path

import pytest

from syntra.domain.exceptions import ProtectedTestViolationError
from syntra.verification.registry import ProtectedTestRegistry


def test_protected_path_matching() -> None:
    registry = ProtectedTestRegistry()

    assert registry.is_protected_path("tests/protected/test_security.py")
    assert registry.is_protected_path("tests/protected/deep/nested/test_core.py")
    assert registry.is_protected_path("tests/regression/test_reg.py")
    assert registry.is_protected_path("tests/baseline/test_base.py")
    assert registry.is_protected_path("tests/test_phase10_independent_qa.py")
    assert registry.is_protected_path("tests/test_phase11_memory.py")
    assert registry.is_protected_path("tests/test_phase12_verification.py")

    assert not registry.is_protected_path("src/syntra/domain/entities.py")
    assert not registry.is_protected_path("src/syntra/api/routes.py")
    assert not registry.is_protected_path("tests/unit/test_custom_feature.py")


def test_extract_touched_files_from_diff() -> None:
    registry = ProtectedTestRegistry()

    patch = """diff --git a/src/app.py b/src/app.py
index 1234567..89abcdef 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1,3 +1,4 @@
 def main():
+    print("hello")
     return 0
diff --git a/tests/test_app.py b/tests/test_app.py
--- a/tests/test_app.py
+++ b/tests/test_app.py
@@ -1 +1 @@
-assert True
+assert False
"""
    touched = registry.extract_touched_files(patch)
    assert "src/app.py" in touched
    assert "tests/test_app.py" in touched


def test_protected_suite_mutation_blocked() -> None:
    """Category B: Diff attempting to modify an existing protected test file is rejected."""
    registry = ProtectedTestRegistry()

    adversarial_patch = """diff --git a/tests/protected/test_auth.py b/tests/protected/test_auth.py
--- a/tests/protected/test_auth.py
+++ b/tests/protected/test_auth.py
@@ -10,3 +10,3 @@
-def test_strict_auth():
-    assert verify_token() is True
+def test_strict_auth():
+    assert True
"""
    with pytest.raises(ProtectedTestViolationError) as exc_info:
        registry.check_patch(adversarial_patch)

    assert "tests/protected/test_auth.py" in str(exc_info.value)
    assert "Developer agents are strictly barred" in str(exc_info.value)


def test_protected_test_phase_file_mutation_blocked() -> None:
    """Category B: Diff attempting to mutate a baseline phase test suite is rejected."""
    registry = ProtectedTestRegistry()

    adversarial_patch = """diff --git a/tests/test_phase10_mission_live.py b/tests/test_phase10_mission_live.py
--- a/tests/test_phase10_mission_live.py
+++ b/tests/test_phase10_mission_live.py
@@ -5,2 +5,2 @@
-def test_critical_mission():
-    assert run_mission() == "SUCCESS"
+def test_critical_mission():
+    pass
"""
    with pytest.raises(ProtectedTestViolationError) as exc_info:
        registry.check_patch(adversarial_patch)

    assert "tests/test_phase10_mission_live.py" in str(exc_info.value)


def test_test_suppression_directive_blocked() -> None:
    """Category C: Diff attempting to add @pytest.mark.skip is rejected."""
    registry = ProtectedTestRegistry()

    adversarial_patch = """diff --git a/tests/unit/test_worker.py b/tests/unit/test_worker.py
--- a/tests/unit/test_worker.py
+++ b/tests/unit/test_worker.py
@@ -15,2 +15,3 @@
+@pytest.mark.skip(reason="bypass failing test")
 def test_worker_fails():
     assert execute_worker() is True
"""
    with pytest.raises(ProtectedTestViolationError) as exc_info:
        registry.check_patch(adversarial_patch)

    assert "@pytest.mark.skip" in str(exc_info.value)
    assert "Skipping or disabling assertions" in str(exc_info.value)


def test_test_suppression_pytest_skip_call_blocked() -> None:
    """Category C: Diff attempting to add pytest.skip() is rejected."""
    registry = ProtectedTestRegistry()

    adversarial_patch = """diff --git a/tests/unit/test_worker.py b/tests/unit/test_worker.py
--- a/tests/unit/test_worker.py
+++ b/tests/unit/test_worker.py
@@ -15,2 +15,3 @@
 def test_worker_fails():
+    pytest.skip("skipping to pass")
     assert execute_worker() is True
"""
    with pytest.raises(ProtectedTestViolationError) as exc_info:
        registry.check_patch(adversarial_patch)

    assert "pytest.skip" in str(exc_info.value)


def test_legitimate_application_patch_allowed() -> None:
    """Valid unified diff touching application code without skipping tests is allowed."""
    registry = ProtectedTestRegistry()

    legit_patch = """diff --git a/src/syntra/domain/services.py b/src/syntra/domain/services.py
--- a/src/syntra/domain/services.py
+++ b/src/syntra/domain/services.py
@@ -10,3 +10,3 @@
-def compute_total(a, b):
-    return a - b
+def compute_total(a, b):
+    return a + b
"""
    # Should not raise
    registry.check_patch(legit_patch)


def test_manifest_computation_and_workspace_validation(tmp_path: Path) -> None:
    """Manifest calculation detects untampered files and catches modified files."""
    registry = ProtectedTestRegistry(patterns=["tests/protected/**"])

    protected_dir = tmp_path / "tests" / "protected"
    protected_dir.mkdir(parents=True)
    test_file = protected_dir / "test_gate.py"
    test_file.write_text("def test_one(): assert 1 == 1\n", encoding="utf-8")

    manifest = registry.compute_manifest(tmp_path)
    assert "tests/protected/test_gate.py" in manifest.protected_files
    expected_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()
    assert manifest.protected_files["tests/protected/test_gate.py"] == expected_hash

    # Validate workspace passes on clean file
    registry.validate_workspace(tmp_path, manifest)

    # Tamper with the file
    test_file.write_text("def test_one(): pass\n", encoding="utf-8")
    with pytest.raises(ProtectedTestViolationError) as exc_info:
        registry.validate_workspace(tmp_path, manifest)
    assert "tampered in workspace" in str(exc_info.value)

    # Delete the file
    test_file.unlink()
    with pytest.raises(ProtectedTestViolationError) as exc_info:
        registry.validate_workspace(tmp_path, manifest)
    assert "missing from workspace" in str(exc_info.value)
