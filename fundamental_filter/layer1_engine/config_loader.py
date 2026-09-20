"""Load scoring / classification thresholds from pipeline/config.yaml.

Maps repo keys (`scoring.pass_percentile`, `scoring.fail_percentile`) onto the
layer1 CLASSIFICATION_CONFIG shape (`pass_percentile`, `watch_percentile`).
Falls back to fundamental_config defaults when YAML is missing or unreadable.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .fundamental_config import CLASSIFICATION_CONFIG

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG_PATH = _REPO_ROOT / "pipeline" / "config.yaml"


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError:  # pragma: no cover - pyyaml is in root requirements
        return {}
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def load_scoring_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Return classification thresholds synced with pipeline/config.yaml.

    Output keys mirror CLASSIFICATION_CONFIG, plus optional module enable flags
    under ``fundamental_filter`` when present in YAML.
    """
    path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
    yaml_cfg = _read_yaml(path)
    merged = deepcopy(CLASSIFICATION_CONFIG)

    scoring = yaml_cfg.get("scoring") or {}
    if "pass_percentile" in scoring:
        merged["pass_percentile"] = float(scoring["pass_percentile"])
    # Repo uses fail_percentile; layer1 historically used watch_percentile
    # for the same lower threshold (below → FAIL).
    if "fail_percentile" in scoring:
        merged["watch_percentile"] = float(scoring["fail_percentile"])
    elif "watch_percentile" in scoring:
        merged["watch_percentile"] = float(scoring["watch_percentile"])

    ff = yaml_cfg.get("fundamental_filter") or {}
    if ff:
        merged["fundamental_filter"] = ff

    merged["config_path"] = str(path)
    merged["config_loaded"] = bool(yaml_cfg)
    return merged
