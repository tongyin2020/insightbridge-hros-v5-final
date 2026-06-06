"""Direct LTV Engine - V5 fixed version.
P0 fix: discount future value before adding it to current direct revenue.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class DirectLTVDecision:
    direct_ltv: float
    ota_net_revenue: float
    direct_advantage: float
    direct_wins: bool
    discount_rate: float
    discounted_future_value: float
    decision_reason: dict = None  # Added V5.1: matches schemas.py interface

class DirectLTVEngine:
    def evaluate_direct_offer(
        self,
        direct_price: float,
        ota_gross_price: float,
        ota_commission_rate: float,
        repeat_probability: float,
        future_margin: float,
        crm_value: float = 0.0,
        acquisition_cost: float = 0.0,
        discount_cost: float = 0.0,
        discount_rate: float = 0.10,
    ) -> DirectLTVDecision:
        if ota_commission_rate < 0 or ota_commission_rate >= 1:
            raise ValueError("ota_commission_rate must be in [0, 1).")
        if discount_rate < 0:
            raise ValueError("discount_rate must be >= 0.")

        repeat_probability = max(0.0, min(1.0, repeat_probability))
        ota_net_revenue = ota_gross_price * (1.0 - ota_commission_rate)

        discounted_future_value = repeat_probability * future_margin / (1.0 + discount_rate)
        direct_ltv = (
            direct_price
            + discounted_future_value
            + crm_value
            - acquisition_cost
            - discount_cost
        )
        direct_advantage = direct_ltv - ota_net_revenue

        return DirectLTVDecision(
            direct_ltv=round(direct_ltv, 2),
            ota_net_revenue=round(ota_net_revenue, 2),
            direct_advantage=round(direct_advantage, 2),
            direct_wins=direct_advantage > 0,
            discount_rate=discount_rate,
            discounted_future_value=round(discounted_future_value, 2),
            decision_reason={
                'direct_price': direct_price, 'ota_gross_price': ota_gross_price,
                'ota_commission_rate': ota_commission_rate,
                'repeat_probability': repeat_probability,
                'future_margin': future_margin, 'discount_rate': discount_rate,
            },
        )
