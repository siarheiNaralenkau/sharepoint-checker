import pytest
from pathlib import Path
import tempfile
import yaml

from sharepoint_checker.config import load_config, ConfigError


MINIMAL_CONFIG = {
    "tenant_id": "test-tenant",
    "client_id": "test-client",
}

FULL_CONFIG = {
    "tenant_id": "test-tenant",
    "client_id": "test-client",
    "client_secret_env": "MY_SECRET",
    "discovery": {
        "mode": "prefix",
        "site_prefixes": ["EPAM SAP SE"],
    },
    "rules": {
        "leadership_folder_regex": r"^Project SAP-[a-z][A-Z]{3,4}-leadership$",
        "roaster_folder_name": "Roaster",
    },
    "execution": {
        "max_parallel_sites": 2,
        "page_size": 100,
    },
    "reporting": {
        "output_dir": "./out",
        "formats": ["json", "csv"],
    },
}


def _write_config(data: dict) -> Path:
    f = tempfile.NamedTemporaryFile(
        suffix=".yaml", mode="w", delete=False, encoding="utf-8"
    )
    yaml.dump(data, f)
    f.close()
    return Path(f.name)


def test_load_minimal_config():
    path = _write_config(MINIMAL_CONFIG)
    config = load_config(path)
    assert config.tenant_id == "test-tenant"
    assert config.client_id == "test-client"
    assert config.discovery.mode == "prefix"


def test_load_full_config():
    path = _write_config(FULL_CONFIG)
    config = load_config(path)
    assert config.rules.leadership_folder_regex == r"^Project SAP-[a-z][A-Z]{3,4}-leadership$"
    assert config.rules.roaster_folder_name == "Roaster"
    assert config.execution.max_parallel_sites == 2
    assert "json" in config.reporting.formats


def test_missing_file_raises():
    with pytest.raises(ConfigError, match="not found"):
        load_config("/nonexistent/path/config.yaml")


def test_invalid_yaml_raises():
    f = tempfile.NamedTemporaryFile(
        suffix=".yaml", mode="w", delete=False, encoding="utf-8"
    )
    f.write(": invalid: yaml: [")
    f.close()
    with pytest.raises(ConfigError, match="YAML"):
        load_config(f.name)


def test_missing_required_field_raises():
    path = _write_config({"client_id": "x"})
    with pytest.raises(ConfigError, match="validation failed"):
        load_config(path)
