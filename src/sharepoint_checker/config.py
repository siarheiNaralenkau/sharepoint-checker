from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import ValidationError

from .models.config_models import CheckerConfig

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    pass


def load_config(path: str | Path) -> CheckerConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        with config_path.open() as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in config file: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError("Config file must be a YAML mapping at the top level")

    try:
        config = CheckerConfig.model_validate(raw)
    except ValidationError as exc:
        errors = "\n".join(
            f"  {' -> '.join(str(l) for l in e['loc'])}: {e['msg']}"
            for e in exc.errors()
        )
        raise ConfigError(f"Config validation failed:\n{errors}") from exc

    logger.info("Loaded config from %s", config_path)
    return config
