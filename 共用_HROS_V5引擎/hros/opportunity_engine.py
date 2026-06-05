"""Opportunity Engine - V5 weight-safe version.
P1 fix: keep practical maximum near 100, avoiding early saturation.
"""
def calculate_opportunity_score(signal: dict) -> float:
    event_density = float(signal.get("event_density", 0.0))
    border_flow = float(signal.get("border_flow", 0.0))
    zhuhai_saturation = float(signal.get("zhuhai_saturation", 0.0))
    ota_booking_pace = float(signal.get("ota_booking_pace", 0.0))
    pickup_ratio = float(signal.get("pickup_ratio") or 0.0)
    occupancy_pressure = float(signal.get("occupancy_pressure") or signal.get("occupancy") or 0.0)

    score = 0.0
    score += min(22.0, event_density * 22.0)
    score += min(18.0, border_flow * 18.0)
    score += min(18.0, zhuhai_saturation * 18.0)
    score += min(18.0, ota_booking_pace * 18.0)

    if signal.get("is_holiday", False):
        score += 10.0
    if signal.get("is_weekend", False):
        score += 5.0

    score += min(5.0, pickup_ratio * 12.0)
    score += min(4.0, occupancy_pressure * 10.0)

    return round(min(100.0, max(0.0, score)), 1)


# ── 向后兼容包装（供 revenue_decision_layer 和旧代码使用）────────────────
class OpportunityEngine:
    """Backward-compatible wrapper around calculate_opportunity_score."""
    def score(self, signal) -> float:
        if hasattr(signal, '__dict__') or hasattr(signal, '_asdict'):
            d = signal.__dict__ if hasattr(signal, '__dict__') else dict(signal._asdict())
        elif hasattr(signal, 'event_density'):
            d = {k: getattr(signal, k) for k in
                 ['event_density','border_flow','zhuhai_saturation','ota_booking_pace',
                  'is_holiday','is_weekend','pickup_ratio','current_occupancy']
                 if hasattr(signal, k)}
            d['occupancy'] = d.pop('current_occupancy', 0.0)
        else:
            d = dict(signal)
        return calculate_opportunity_score(d)

    def explain(self, signal) -> dict:
        return {"opportunity_score": self.score(signal)}
