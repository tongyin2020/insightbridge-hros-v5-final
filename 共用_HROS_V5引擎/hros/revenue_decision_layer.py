from __future__ import annotations

from typing import Dict, Optional

from .elasticity import ElasticityEngine
from .opportunity_engine import OpportunityEngine
from .risk_engine import RiskEngine
from .schemas import MarketSignal, RevenueDecision


PRICE_FLOOR = {3: 680.0, 4: 750.0, 5: 1200.0}
PRICE_CEILING = {3: 1250.0, 4: 2000.0, 5: 8000.0}


class RevenueDecisionLayer:
    """Unified HROS revenue optimization layer.

    One function should eventually sit below DirectorAI, Harness, Claude
    Simulation and CrewAI. MARE, CRM and SelfACQ can pass different objective
    weights, but they should share the same economic logic.
    """

    def __init__(
        self,
        elasticity_engine: Optional[ElasticityEngine] = None,
        opportunity_engine: Optional[OpportunityEngine] = None,
        risk_engine: Optional[RiskEngine] = None,
    ):
        self.elasticity_engine = elasticity_engine or ElasticityEngine()
        self.opportunity_engine = opportunity_engine or OpportunityEngine()
        self.risk_engine = risk_engine or RiskEngine()

    def optimize_price(
        self,
        signal: MarketSignal,
        candidate_price: Optional[float] = None,
        floor_price: Optional[float] = None,
        ceiling_price: Optional[float] = None,
        step: int = 10,
        ancillary_revenue_per_occ_room: float = 0.0,
        clv_value_per_occ_room: float = 0.0,
        market_share_weight: float = 0.0,
        hotel_id: Optional[str] = None,
    ) -> RevenueDecision:
        if signal.market_price <= 0:
            raise ValueError("signal.market_price must be positive")
        if step <= 0:
            raise ValueError("step must be positive")

        elasticity = self.elasticity_engine.get_elasticity(
            star=signal.star,
            district=signal.district,
            season=signal.season,
            hotel_id=hotel_id,
        )

        default_floor = PRICE_FLOOR.get(signal.star, 680.0)
        default_ceiling = PRICE_CEILING.get(signal.star, 3000.0)
        market = signal.market_price
        floor = max(default_floor, floor_price if floor_price is not None else market * 0.70)
        ceiling = min(default_ceiling, ceiling_price if ceiling_price is not None else market * 1.45)
        if floor > ceiling:
            floor, ceiling = min(floor, ceiling), max(floor, ceiling)

        best: Optional[Dict[str, float]] = None
        price = round(floor / step) * step
        search_steps = 0
        while price <= ceiling + 0.001:
            occ = self.elasticity_engine.predict_occupancy(price, market, signal.base_occ, elasticity)
            revpar = price * occ
            trevpar = revpar + ancillary_revenue_per_occ_room * occ
            clv_adjusted = trevpar + clv_value_per_occ_room * occ
            objective = clv_adjusted + market_share_weight * occ * market

            if best is None or objective > best["objective"]:
                best = {
                    "price": price,
                    "occupancy": occ,
                    "revpar": revpar,
                    "trevpar": trevpar,
                    "objective": objective,
                }
            price += step
            search_steps += 1

        assert best is not None
        baseline_revpar = market * signal.base_occ
        lift_pct = ((best["revpar"] - baseline_revpar) / baseline_revpar * 100.0) if baseline_revpar > 0 else 0.0
        opportunity = self.opportunity_engine.score(signal)
        risk = self.risk_engine.price_risk(best["price"], signal, best["occupancy"])
        confidence = self._confidence(risk, signal.data_quality, search_steps)

        return RevenueDecision(
            recommended_price=round(best["price"], 0),
            predicted_occupancy=round(best["occupancy"], 4),
            predicted_revpar=round(best["revpar"], 1),
            predicted_trevpar=round(best["trevpar"], 1),
            baseline_revpar=round(baseline_revpar, 1),
            lift_pct=round(lift_pct, 2),
            risk_score=risk,
            opportunity_score=opportunity,
            confidence=confidence,
            search_steps=search_steps,
            objective_value=round(best["objective"], 2),
            decision_reason={
                "market_price": market,
                "candidate_price_input": candidate_price,
                "elasticity_used": elasticity,
                "premium_vs_market": round((best["price"] - market) / market, 4),
                "floor_price": round(floor, 2),
                "ceiling_price": round(ceiling, 2),
                "ancillary_revenue_per_occ_room": ancillary_revenue_per_occ_room,
                "clv_value_per_occ_room": clv_value_per_occ_room,
                "market_share_weight": market_share_weight,
                "opportunity_breakdown": self.opportunity_engine.explain(signal),
                "risk_breakdown": self.risk_engine.explain(best["price"], signal, best["occupancy"]),
            },
        )

    @staticmethod
    def _confidence(risk_score: float, data_quality: float, search_steps: int) -> float:
        confidence = 95.0 - risk_score * 0.35 + max(0.0, data_quality - 0.60) * 20.0
        if search_steps < 8:
            confidence -= 10.0
        return round(max(40.0, min(98.0, confidence)), 1)
