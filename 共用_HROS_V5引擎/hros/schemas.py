from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class MarketSignal:
    """Signals required by the HROS revenue decision layer.

    Values are normalized where possible:
    - event_density, border_flow, zhuhai_saturation, ota_booking_pace: 0..1
    - occupancy/base_occ/pickup_ratio/direct_share: 0..1
    """

    market_price: float
    base_occ: float = 0.72
    demand_level: str = "NORMAL"  # LOW/NORMAL/HIGH
    season: str = "normal"        # low/normal/peak/super_peak
    star: int = 4
    district: str = "NAPE"
    event_density: float = 0.0
    border_flow: float = 0.0
    zhuhai_saturation: float = 0.0
    ota_booking_pace: float = 0.5
    weather_celsius: Optional[float] = None
    is_holiday: bool = False
    is_weekend: bool = False
    current_occupancy: Optional[float] = None
    pickup_ratio: Optional[float] = None
    direct_share: Optional[float] = None
    competitor_price: Optional[float] = None
    inventory_remaining: Optional[int] = None
    room_inventory: Optional[int] = None
    data_quality: float = 0.75
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RevenueDecision:
    recommended_price: float
    predicted_occupancy: float
    predicted_revpar: float
    predicted_trevpar: float
    baseline_revpar: float
    lift_pct: float
    risk_score: float
    opportunity_score: float
    confidence: float
    search_steps: int
    objective_value: float
    decision_reason: Dict[str, Any]


@dataclass(frozen=True)
class CRMDecision:
    apply_offer: bool
    offer_discount_rate: float
    incremental_value: float
    discount_cost: float
    expected_future_value: float
    decision_reason: Dict[str, Any]


# DirectLTVDecision moved to direct_ltv_engine.py (V5.1)