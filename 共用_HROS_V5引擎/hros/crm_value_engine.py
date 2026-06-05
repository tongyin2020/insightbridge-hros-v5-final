"""CRM Value Engine - V5 configurable margin version.
P1 fix: default margin_rate reduced to 0.60 and made configurable.
"""
def calculate_crm_incremental_value(
    base_price: float,
    discount_rate: float,
    clv: float,
    retention_lift: float,
    ota_commission_saved: float = 0.0,
    upsell_expected_value: float = 0.0,
    margin_rate: float = 0.60,
) -> float:
    if not (0.0 <= discount_rate <= 1.0):
        raise ValueError("discount_rate must be between 0 and 1.")
    if not (0.0 <= margin_rate <= 1.0):
        raise ValueError("margin_rate must be between 0 and 1.")

    discount_cost = base_price * discount_rate * margin_rate
    incremental_value = (
        -discount_cost
        + clv * retention_lift
        + ota_commission_saved
        + upsell_expected_value
    )
    return round(incremental_value, 2)


# ── 向后兼容包装 ──────────────────────────────────────────────────────────
class CRMValueEngine:
    """Backward-compatible wrapper around calculate_crm_incremental_value."""
    def evaluate_offer(self, base_price, discount_rate, clv, retention_lift,
                       ota_commission_saved=0.0, upsell_expected_value=0.0,
                       margin_rate=0.60):
        from hros.schemas import CRMDecision
        val = calculate_crm_incremental_value(
            base_price, discount_rate, clv, retention_lift,
            ota_commission_saved, upsell_expected_value, margin_rate)
        cost = base_price * discount_rate * margin_rate
        return CRMDecision(
            apply_offer=val > 0,
            offer_discount_rate=discount_rate if val > 0 else 0.0,
            incremental_value=val,
            discount_cost=round(cost, 2),
            expected_future_value=round(clv * retention_lift, 2),
            decision_reason={"margin_rate": margin_rate, "incremental_value": val}
        )

    def recommend_discount_rate(self, loyalty_tier: str, churn_risk: float,
                                direct_share: float) -> float:
        tier = (loyalty_tier or "standard").lower()
        base = {"standard": 0.00, "silver": 0.03, "gold": 0.05, "platinum": 0.08}.get(tier, 0.00)
        if churn_risk > 0.65: base += 0.02
        if direct_share < 0.25: base += 0.01
        return min(base, 0.12)
