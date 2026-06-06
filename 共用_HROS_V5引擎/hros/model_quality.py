from __future__ import annotations

from typing import Any, Dict


def model_quality_score(result: Dict[str, Any]) -> float:
    """Risk-adjusted score for comparing nine models under one standard."""
    lift = float(result.get("lift_pct", result.get("true_lift_pct", 0.0)) or 0.0)
    risk = float(result.get("risk_score", result.get("price_risk_score", 50.0)) or 50.0)
    _conf_raw = result.get("confidence", result.get("rate_confidence", 70.0))
    if isinstance(_conf_raw, str):
        confidence = {"High": 85.0, "Medium": 70.0, "Low": 55.0}.get(_conf_raw, 70.0)
    else:
        confidence = float(_conf_raw or 70.0)
    opportunity = float(result.get("opportunity_score", 50.0) or 50.0)
    forecast_error = float(result.get("forecast_error_pct", 0.0) or 0.0)
    return round(lift * 2.0 - risk * 0.4 + confidence * 0.3 + opportunity * 0.2 - forecast_error * 0.8, 2)
