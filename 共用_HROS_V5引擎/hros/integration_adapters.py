from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional

from .schemas import MarketSignal
from .revenue_decision_layer import RevenueDecisionLayer
from .crm_value_engine import CRMValueEngine
from .direct_ltv_engine import DirectLTVEngine
from .model_quality import model_quality_score


def normalize_signal(raw: Dict[str, Any]) -> MarketSignal:
    """Convert existing system dictionaries into a HROS MarketSignal."""
    market_price = float(raw.get("market_price") or raw.get("mkt_price") or raw.get("real_bar_avg") or raw.get("base_price") or 0.0)
    if market_price <= 0:
        raise ValueError("Cannot normalize MarketSignal: market price is missing")

    return MarketSignal(
        market_price=market_price,
        base_occ=float(raw.get("base_occ") or raw.get("base_occupancy") or raw.get("occupancy") or 0.72),
        demand_level=str(raw.get("demand_level") or raw.get("demand") or "NORMAL").upper(),
        season=str(raw.get("season") or "normal"),
        star=int(raw.get("star") or raw.get("hotel_star") or 4),
        district=str(raw.get("district") or raw.get("area") or "NAPE").upper(),
        event_density=float(raw.get("event_density") or 0.0),
        border_flow=float(raw.get("border_flow") or 0.0),
        zhuhai_saturation=float(raw.get("zhuhai_saturation") or 0.0),
        ota_booking_pace=float(raw.get("ota_booking_pace") or 0.5),
        weather_celsius=raw.get("weather_celsius"),
        is_holiday=bool(raw.get("is_holiday") or False),
        is_weekend=bool(raw.get("is_weekend") or False),
        current_occupancy=raw.get("current_occupancy"),
        pickup_ratio=raw.get("pickup_ratio"),
        direct_share=raw.get("direct_share"),
        competitor_price=raw.get("competitor_price"),
        inventory_remaining=raw.get("inventory_remaining") or raw.get("avail_level"),
        room_inventory=raw.get("room_inventory"),
        data_quality=float(raw.get("data_quality") or 0.75),
        extra={k: v for k, v in raw.items() if k not in {"market_price", "mkt_price", "real_bar_avg", "base_price"}},
    )


def apply_hros_to_mare_result(result: Dict[str, Any], raw_signal: Dict[str, Any]) -> Dict[str, Any]:
    """Drop-in adapter for MARE output dictionaries."""
    try:
        signal = normalize_signal(raw_signal)
    except (ValueError, TypeError) as _e:
        return {**result, 'hros_error': str(_e), 'risk_score': None, 'opportunity_score': None}
    layer = RevenueDecisionLayer()
    decision = layer.optimize_price(
        signal=signal,
        candidate_price=float(result.get("recommended_price") or raw_signal.get("candidate_price") or signal.market_price),
        ancillary_revenue_per_occ_room=float(raw_signal.get("ancillary_revenue_per_occ_room") or 0.0),
        clv_value_per_occ_room=float(raw_signal.get("clv_value_per_occ_room") or 0.0),
        market_share_weight=float(raw_signal.get("market_share_weight") or 0.0),
        hotel_id=raw_signal.get("hotel_id"),
    )
    out = dict(result)
    out.update(asdict(decision))
    out["recommended_price"] = decision.recommended_price
    out["expected_revenue_lift"] = f"{decision.lift_pct:+.1f}%"
    out["price_risk_score"] = decision.risk_score
    out["rate_confidence"] = decision.confidence
    out["model_quality_score"] = model_quality_score(out)
    return out


def apply_hros_to_crm_result(result: Dict[str, Any], raw_customer: Dict[str, Any]) -> Dict[str, Any]:
    engine = CRMValueEngine()
    discount_rate = float(result.get("discount_rate") or raw_customer.get("discount_rate") or 0.0)
    decision = engine.evaluate_offer(
        base_price=float(raw_customer.get("base_price") or result.get("base_price") or 0.0),
        discount_rate=discount_rate,
        clv=float(raw_customer.get("clv") or raw_customer.get("customer_lifetime_value") or 0.0),
        retention_lift=float(raw_customer.get("retention_lift") or 0.02),
        ota_commission_saved=float(raw_customer.get("ota_commission_saved") or 0.0),
        upsell_expected_value=float(raw_customer.get("upsell_expected_value") or 0.0),
    )
    out = dict(result)
    out.update({
        "apply_crm_offer": decision.apply_offer,
        "crm_discount_rate": decision.offer_discount_rate,
        "crm_incremental_value": decision.incremental_value,
        "crm_discount_cost": decision.discount_cost,
        "crm_expected_future_value": decision.expected_future_value,
        "crm_decision_reason": decision.decision_reason,
    })
    return out


def apply_hros_to_selfacq_result(result: Dict[str, Any], raw_offer: Dict[str, Any]) -> Dict[str, Any]:
    engine = DirectLTVEngine()
    decision = engine.evaluate_direct_offer(
        direct_price=float(raw_offer.get("direct_price") or result.get("direct_price") or 0.0),
        ota_gross_price=float(raw_offer.get("ota_gross_price") or raw_offer.get("ota_price") or 0.0),
        ota_commission_rate=float(raw_offer.get("ota_commission_rate") or 0.18),
        repeat_probability=float(raw_offer.get("repeat_probability") or 0.10),
        future_margin=float(raw_offer.get("future_margin") or 0.0),
        crm_value=float(raw_offer.get("crm_value") or 0.0),
        acquisition_cost=float(raw_offer.get("acquisition_cost") or 0.0),
        discount_cost=float(raw_offer.get("discount_cost") or 0.0),
    )
    out = dict(result)
    out.update({
        "direct_wins_vs_ota": decision.direct_wins,
        "direct_ltv": decision.direct_ltv,
        "ota_net_revenue": decision.ota_net_revenue,
        "direct_ltv_advantage": decision.direct_advantage,
        "direct_ltv_reason": decision.decision_reason,
    })
    return out
