"""Risk Engine - V5 normalized version.
P1 fix: normalize raw risk instead of clamping all high-risk cases to 100.
"""
def calculate_price_risk(
    price: float,
    market_price: float,
    predicted_occ: float,
    ota_booking_pace: float,
    competitor_price: float | None = None,
    data_quality: float = 1.0,
) -> float:
    reference_price = market_price
    if competitor_price and competitor_price > 0:
        reference_price = (market_price + competitor_price) / 2.0

    premium = (price - reference_price) / reference_price if reference_price else 0.0

    premium_risk = max(0.0, premium - 0.05) * 180.0
    occ_risk = max(0.0, 0.70 - predicted_occ) * 80.0
    pace_risk = max(0.0, 0.45 - ota_booking_pace) * 60.0
    dq_risk = max(0.0, 0.60 - data_quality) * 35.0

    raw_score = premium_risk + occ_risk + pace_risk + dq_risk
    normalized_score = raw_score / 3.0
    return round(min(100.0, max(0.0, normalized_score)), 1)


# ── 向后兼容包装 ──────────────────────────────────────────────────────────
class RiskEngine:
    """Backward-compatible wrapper around calculate_price_risk."""
    def price_risk(self, price: float, signal, predicted_occupancy: float) -> float:
        market = getattr(signal, 'market_price', price)
        comp   = getattr(signal, 'competitor_price', None)
        pace   = getattr(signal, 'ota_booking_pace', 0.5)
        dq     = getattr(signal, 'data_quality', 1.0)
        return calculate_price_risk(price, market, predicted_occupancy, pace, comp, dq)

    def inventory_risk(self, signal) -> float:
        inv = getattr(signal, 'inventory_remaining', None)
        tot = getattr(signal, 'room_inventory', None)
        if inv is None or not tot:
            return 30.0
        return round(min(100.0, (inv / max(tot, 1)) * 70.0), 1)

    def explain(self, price: float, signal, predicted_occupancy: float) -> dict:
        return {"risk_score": self.price_risk(price, signal, predicted_occupancy)}
