"""Unit tests verifying integrity of versioned YAML configuration files."""

from pathlib import Path

import pytest
import yaml


@pytest.mark.unit
def test_all_configuration_yaml_files_valid():
    """Verify all 6 configuration files exist and parse into valid dictionaries."""
    config_dir = Path("config")
    assert config_dir.exists()

    required_configs = [
        "application.yaml",
        "models.yaml",
        "agents.yaml",
        "tools.yaml",
        "skills.yaml",
        "mcp.yaml",
    ]

    for config_name in required_configs:
        config_path = config_dir / config_name
        assert config_path.exists(), f"Missing configuration file: {config_name}"
        data = yaml.safe_load(config_path.read_text())
        assert isinstance(data, dict), f"Config {config_name} must parse into a dictionary"
        assert len(data) > 0, f"Config {config_name} must not be empty"
