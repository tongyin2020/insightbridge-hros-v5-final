from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


DEFAULT_ELASTICITY: Dict[Tuple[int, str], float] = {
    (3, "TAIPA"): 0.93,
    (3, "NAPE"): 0.95,
    (3, "INNER"): 0.98,
    (3, "COT"): 0.91,
    (3, "PENINSULA"): 0.96,
    (4, "TAIPA"): 0.63,
    (4, "NAPE"): 0.72,
    (4, "INNER"): 0.74,
    (4, "COT"): 0.60,
    (4, "PENINSULA"): 0.68,
    (5, "TAIPA"): 0.38,
    (5, "NAPE"): 0.42,
    (5, "INNER"): 0.45,
    (5, "COT"): 0.28,
    (5, "PENINSULA"): 0.40,
}

DEFAULT_BY_STAR = {3: 0.95, 4: 0.68, 5: 0.38}
SEASON_MULTIPLIER = {
    "super_peak": 0.45,
    "peak": 0.65,
    "normal": 1.00,
    "low": 1.30,
}


@dataclass
class ElasticityConfig:
    low_premium_threshold: float = 0.05
    mid_premium_threshold: float = 0.15
    high_premium_threshold: float = 0.25
    low_premium_multiplier: float = 0.30
    mid_premium_multiplier: float = 1.00
    high_premium_multiplier: float = 1.80
    extreme_premium_multiplier: float = 3.00
    min_occupancy: float = 0.08
    max_occupancy: float = 0.98


class ElasticityEngine:
    """Practical hotel price elasticity engine.

    This is intentionally conservative. It does not assume that a hotel can
    raise price indefinitely. The penalty accelerates when the recommended
    price moves materially above the market/competitor benchmark.
    """

    def __init__(self, config: Optional[ElasticityConfig] = None):
        self.config = config or ElasticityConfig()
        self.hotel_coefficients: Dict[str, float] = {}

    def set_hotel_coefficient(self, hotel_id: str, elasticity: float) -> None:
        if elasticity <= 0:
            raise ValueError("elasticity must be positive")
        self.hotel_coefficients[hotel_id] = elasticity

    def get_elasticity(
        self,
        star: int,
        district: str,
        season: str = "normal",
        hotel_id: Optional[str] = None,
    ) -> float:
        if hotel_id and hotel_id in self.hotel_coefficients:
            base = self.hotel_coefficients[hotel_id]
        else:
            district_key = (district or "NAPE").upper()
            base = DEFAULT_ELASTICITY.get((star, district_key), DEFAULT_BY_STAR.get(star, 0.68))
        return round(base * SEASON_MULTIPLIER.get(season, 1.0), 4)

    def segmented_penalty(self, premium: float, elasticity: float) -> float:
        """Piecewise penalty: protects against overpricing in high-premium zones."""
        c = self.config
        if premium <= 0:
            # Discounting below market increases demand, but cap the benefit.
            return max(-0.35, elasticity * 0.45 * premium)
        if premium <= c.low_premium_threshold:
            return elasticity * c.low_premium_multiplier * premium
        if premium <= c.mid_premium_threshold:
            return elasticity * (
                c.low_premium_threshold * c.low_premium_multiplier
                + (premium - c.low_premium_threshold) * c.mid_premium_multiplier
            )
        if premium <= c.high_premium_threshold:
            return elasticity * (
                c.low_premium_threshold * c.low_premium_multiplier
                + (c.mid_premium_threshold - c.low_premium_threshold) * c.mid_premium_multiplier
                + (premium - c.mid_premium_threshold) * c.high_premium_multiplier
            )
        return elasticity * (
            c.low_premium_threshold * c.low_premium_multiplier
            + (c.mid_premium_threshold - c.low_premium_threshold) * c.mid_premium_multiplier
            + (c.high_premium_threshold - c.mid_premium_threshold) * c.high_premium_multiplier
            + (premium - c.high_premium_threshold) * c.extreme_premium_multiplier
        )

    def predict_occupancy(self, price: float, market_price: float, base_occ: float, elasticity: float) -> float:
        if market_price <= 0:
            market_price = max(price, 1.0)
        premium = (price - market_price) / market_price
        penalty = self.segmented_penalty(premium, elasticity)
        occ = base_occ * (1.0 - penalty)
        return round(max(self.config.min_occupancy, min(self.config.max_occupancy, occ)), 4)
