"""Eligibility Layer 1 → Quant: tách WATCH đủ dữ liệu khỏi INSUFFICIENT.

Bot và pipeline cùng dùng module này — pipeline KHÔNG được import bot.
"""

from __future__ import annotations

import json
import math
from typing import Any, Mapping

_SCORE_KEYS = (
    "growth_score",
    "quality_score",
    "safety_score",
    "valuation_score",
)

_PILLAR_LABEL = {
    "growth_score": "GROWTH",
    "quality_score": "QUALITY",
    "safety_score": "SAFETY",
    "valuation_score": "VALUATION",
}


def _as_mapping(row_or_payload: Any) -> Mapping[str, Any] | None:
    if row_or_payload is None:
        return None
    if isinstance(row_or_payload, Mapping):
        return row_or_payload
    # pandas Series / namedtuple-like
    try:
        return dict(row_or_payload)
    except (TypeError, ValueError):
        return None


def _headline_dict(row: Mapping[str, Any]) -> dict[str, Any]:
    """Parse ``headline_json`` nếu có; fallback an toàn khi malformed."""
    raw = row.get("headline_json")
    if isinstance(raw, dict):
        return raw
    if raw is None or raw == "":
        return {}
    try:
        data = json.loads(str(raw))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _is_missing_numeric(value: Any) -> bool:
    if value is None:
        return True
    try:
        # pandas NA / NaT
        if value != value:  # NaN
            return True
    except (TypeError, ValueError):
        pass
    try:
        num = float(value)
    except (TypeError, ValueError):
        return True
    return math.isnan(num) or math.isinf(num)


def _normalize_reason_text(raw: Any) -> str:
    if isinstance(raw, list):
        return " | ".join(str(x) for x in raw if x).strip()
    if raw is None:
        return ""
    text = str(raw).strip()
    if not text or text.upper() in {"NAN", "NONE", "NULL"}:
        return ""
    return text


def parse_classification_reason(row_or_payload: Any) -> str:
    """Lấy classification_reason từ row store, results_df, hoặc headline payload."""
    row = _as_mapping(row_or_payload)
    if not row:
        return ""

    direct = _normalize_reason_text(row.get("classification_reason"))
    if direct:
        return direct

    # Payload đã parse sẵn (headline dict) hoặc headline_json trên store row
    payload = row if ("headline" in row or "data_quality" in row) else _headline_dict(row)
    from_payload = _normalize_reason_text(payload.get("classification_reason"))
    if from_payload:
        return from_payload

    flags = _normalize_reason_text(row.get("classification_flags"))
    return flags


def _view_of(row: Mapping[str, Any]) -> str:
    raw = row.get("fundamental_view")
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        raw = row.get("classification")
    return str(raw or "").strip().upper()


def _critical_data_quality_flag(row: Mapping[str, Any]) -> bool:
    """True khi payload đánh dấu chất lượng dữ liệu critical (nếu field tồn tại)."""
    payload = _headline_dict(row)
    dq = payload.get("data_quality")
    if isinstance(dq, dict) and "critical_data_quality_flag" in dq:
        return bool(dq.get("critical_data_quality_flag"))
    if "critical_data_quality_flag" in payload:
        return bool(payload.get("critical_data_quality_flag"))
    if "critical_data_quality_flag" in row:
        return bool(row.get("critical_data_quality_flag"))
    return False


def _missing_core_modules(row: Mapping[str, Any]) -> list[str]:
    """Chỉ đánh dấu thiếu khi key trụ đã có trên row nhưng giá trị None/NaN."""
    missing: list[str] = []
    for key in _SCORE_KEYS:
        if key in row and _is_missing_numeric(row.get(key)):
            missing.append(_PILLAR_LABEL[key])
    return missing


def _headline_fundamental_score_missing(row: Mapping[str, Any]) -> bool:
    """Chỉ khi key ``fundamental_score`` tồn tại trong headline và giá trị None/NaN."""
    payload = _headline_dict(row)
    if "fundamental_score" not in payload:
        # Row-level fundamental_score (results_df) — chỉ khi key có mặt
        if "fundamental_score" in row:
            return _is_missing_numeric(row.get("fundamental_score"))
        return False
    return _is_missing_numeric(payload.get("fundamental_score"))


def is_fundamental_insufficient(row: Any) -> bool:
    """True khi Layer 1 thiếu dữ liệu đáng tin (≠ FAIL / WATCH đủ dữ liệu).

    Điều kiện (OR):
    1. Không có fundamental row
    2. classification_reason chứa INSUFFICIENT
    3. critical_data_quality_flag = true (nếu field tồn tại)
    4. Một trong 4 trụ score bị None/NaN
    5. fundamental_score trong headline_json là None (nếu key tồn tại)
    """
    mapping = _as_mapping(row)
    if mapping is None:
        return True

    reason = parse_classification_reason(mapping).upper()
    if "INSUFFICIENT" in reason:
        return True

    if _critical_data_quality_flag(mapping):
        return True

    if _missing_core_modules(mapping):
        return True

    if _headline_fundamental_score_missing(mapping):
        return True

    return False


def is_quant_eligible_fundamental(row: Any) -> bool:
    """Ticker được vào watchlist Quant khi PASS/WATCH và không insufficient."""
    mapping = _as_mapping(row)
    if mapping is None:
        return False
    if is_fundamental_insufficient(mapping):
        return False
    view = _view_of(mapping)
    return view in {"PASS", "WATCH"}


def build_data_quality_payload(row: Any) -> dict[str, Any] | None:
    """Sinh khối ``data_quality`` cho headline_json — chỉ khi biết chắc thiếu gì."""
    mapping = _as_mapping(row)
    if mapping is None:
        return None
    missing = _missing_core_modules(mapping)
    reason = parse_classification_reason(mapping).upper()
    critical = bool(missing) or ("INSUFFICIENT" in reason)
    if not critical and not missing:
        return None
    return {
        "critical_data_quality_flag": critical,
        "data_quality_flags": (["MISSING_MODULES"] if missing else [])
        + (["INSUFFICIENT_REASON"] if "INSUFFICIENT" in reason else []),
        "missing_modules": missing,
        "available_module_count": 4 - len(missing),
    }
