from __future__ import annotations

import json
import logging
from pathlib import Path

from ..models.result_models import RunSummary

logger = logging.getLogger(__name__)


def write_json_report(summary: RunSummary, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "run-summary.json"
    data = json.loads(summary.model_dump_json(indent=2))
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    logger.info("JSON report written to %s", path)
    return path
