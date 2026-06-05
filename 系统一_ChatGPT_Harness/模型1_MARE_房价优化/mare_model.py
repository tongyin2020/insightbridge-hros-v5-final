# 系统一 | 模型1 | MARE 房价优化
# HROS V5 已集成 enrich_with_hros_v5()


# ============================================================
# scenario_catalog
# ============================================================

def scenario_catalog(base_price: float) -> list[ScenarioDefinition]:
    return [
        ScenarioDefinition("normal_weekday", "normal", 0.68, 120, 380, 18, 10, 0.10, 0.00, 0.45, 0.50, 0.42, 2800, 0.40, "medium", 0.20, "", "new", base_price * 0.99, base_price * 0.98, base_price * 0.97, base_price * 0.95, 4.2, 0.18, 0.10, "maximize_revenue"),
        ScenarioDefinition("weekend_pickup", "normal", 0.76, 85, 380, 26, 7, 0.09, 0.05, 0.40, 0.42, 0.60, 3200, 0.48, "medium", 0.18, "gold", "returning", base_price, base_price * 1.00, base_price * 0.99, base_price * 0.97, 4.3, 0.18, 0.10, "maximize_revenue"),
        ScenarioDefinition("festival_surge", "extreme", 0.93, 22, 380, 45, 2, 0.06, 0.12, 0.22, 0.18, 0.92, 5500, 0.62, "low", 0.10, "vip", "ota", base_price * 1.05, base_price * 1.04, base_price * 1.02, base_price * 0.98, 4.4, 0.20, 0.08, "maximize_profit"),
        ScenarioDefinition("soft_demand", "normal", 0.48, 210, 380, 8, 18, 0.16, -0.08, 0.62, 0.70, 0.25, 2200, 0.30, "high", 0.28, "", "new", base_price * 0.96, base_price * 0.97, base_price * 0.98, base_price * 0.94, 4.1, 0.18, 0.12, "maximize_revpar"),
        ScenarioDefinition("competitor_pressure", "adversarial", 0.61, 140, 380, 14, 9, 0.11, -0.03, 0.90, 0.64, 0.40, 2600, 0.35, "high", 0.22, "", "ota", base_price * 0.98, base_price * 0.99, base_price * 0.98, base_price * 0.95, 4.0, 0.18, 0.10, "maximize_revenue"),
        ScenarioDefinition("high_inventory", "normal", 0.44, 250, 380, 6, 4, 0.18, -0.10, 0.58, 0.76, 0.22, 2400, 0.32, "high", 0.25, "", "walk_in", base_price * 0.95, base_price * 0.96, base_price * 0.97, base_price * 0.93, 4.0, 0.17, 0.10, "maximize_revpar"),
        ScenarioDefinition("near_sellout", "extreme", 0.97, 6, 380, 52, 1, 0.04, 0.15, 0.15, 0.12, 0.98, 6800, 0.70, "low", 0.08, "platinum", "corporate", base_price * 1.08, base_price * 1.05, base_price * 1.03, base_price * 0.99, 4.5, 0.20, 0.06, "maximize_profit"),
        ScenarioDefinition("fairness_stress", "adversarial", 0.74, 95, 380, 24, 6, 0.09, 0.06, 0.38, 0.34, 0.66, 8000, 0.65, "medium", 0.20, "diamond", "returning", base_price * 0.92, base_price * 0.90, base_price * 0.88, base_price * 0.84, 4.2, 0.18, 0.08, "maximize_profit"),
        ScenarioDefinition("low_satisfaction_conflict", "adversarial", 0.86, 48, 380, 34, 3, 0.08, 0.08, 0.28, 0.24, 0.85, 4200, 0.44, "low", 0.22, "gold", "new", base_price * 1.01, base_price * 1.00, base_price * 0.99, base_price * 0.96, 3.1, 0.19, 0.09, "maximize_revenue"),
        ScenarioDefinition("dirty_data", "adversarial", 0.58, 999, 380, -5, 0, 0.55, 1.80, 1.40, -0.25, -0.10, -100, 1.40, "very_low", 1.20, "vip", "ota", 0, 0, 0, 0, 2.9, 0.30, 0.20, "maximize_direct_mix"),
        ScenarioDefinition("signal_conflict", "adversarial", 0.88, 30, 380, 12, 5, 0.22, -0.04, 0.80, 0.20, 0.30, 3600, 0.38, "high", 0.35, "", "new", base_price * 1.00, base_price * 1.01, base_price * 1.00, base_price * 0.97, 3.6, 0.20, 0.12, "maximize_direct_mix"),
    ]



# ============================================================
# _tier_guardrails
# ============================================================

def _tier_guardrails(base_price: float, star: int) -> tuple[float, float]:
    """按星级计算合理的 floor/ceiling，避免硬编码 750/1015 导致低端酒店价格被截断。"""
    # 以 base_price 为锚点，星级越高弹性越大
    ratios = {
        3: (0.83, 1.42),
        4: (0.80, 1.55),
        5: (0.75, 1.65),
    }
    lo, hi = ratios.get(star, (0.80, 1.45))
    return round(base_price * lo, 0), round(base_price * hi, 0)



# ============================================================
# build_payload
# ============================================================

def build_payload(snapshot: ExternalSnapshot, scenario: ScenarioDefinition, hotel_id: str, base_price: float, market_segment: str | None, star: int = 3) -> dict[str, Any]:
    # 修正(2026-06-01)：优先用DSEC星级专属ADR作为竞对基准价
    # snapshot.competitor_price 在MakCorps停用后=3★DSEC×1.05（已修正）
    # 但4★/5★仍需从dsec_cold_adr取各自的专属值，避免用3★价作为高端酒店基准
    _dsec_adr = (snapshot.dsec_cold_adr or {}).get(star, 0)
    competitor_price = round(_dsec_adr * 1.05, 0) if _dsec_adr > 0 else snapshot.competitor_price
    if scenario.name == "competitor_pressure":
        competitor_price = round(competitor_price * 0.90, 0)
    elif scenario.name == "near_sellout":
        competitor_price = round(competitor_price * 1.08, 0)
    elif scenario.name == "dirty_data":
        competitor_price = -50.0

    payload = {
        "hotel_id": hotel_id,
        "market_segment": market_segment,
        "base_price": round(base_price, 2),
        "season": "shoulder" if snapshot.event_density < 0.45 else "peak",
        "current_occupancy": scenario.current_occupancy,
        "competitor_price": round(competitor_price, 2),
        "competitor_availability": scenario.competitor_availability,
        "elasticity_signal": scenario.elasticity_signal,
        "holiday": snapshot.holiday,
        "event_ticket_sales": snapshot.event_ticket_sales,
        "weekend": snapshot.weekend,
        "border_flow": snapshot.border_flow,
        "visitors_stats": snapshot.visitors_stats,
        "flight_ferry": snapshot.flight_ferry,
        "zhuhai_saturation": 0.25 if scenario.category != "adversarial" else 0.65,
        "ota_booking_pace": 0.52 if scenario.category != "adversarial" else 0.18,
        "weather": snapshot.weather,
        "remaining_inventory": scenario.remaining_inventory,
        "total_rooms": scenario.total_rooms,
        "booking_velocity_24h": scenario.booking_velocity_24h,
        "days_to_arrival": scenario.days_to_arrival,
        "cancellation_rate": scenario.cancellation_rate,
        "guest_segment": scenario.guest_segment,
        "avg_clv": max(scenario.avg_clv, 0),
        "repurchase_probability": clamp(scenario.repurchase_probability, 0.0, 1.0),
        "price_sensitivity": scenario.price_sensitivity,
        "churn_risk": clamp(scenario.churn_risk, 0.0, 1.0),
        "loyalty_tier": scenario.loyalty_tier,
        "previous_price": max(scenario.previous_price, 0),
        "avg_30d_price": max(scenario.avg_30d_price, 0),
        "historical_avg": max(scenario.historical_avg, 0),
        "max_deviation_pct": 20.0,
        "customer_historical_rate": max(scenario.customer_historical_rate, 0),
        "upper_tier_adr": snapshot.upper_tier_adr,
        "neighborhood_availability": scenario.neighborhood_availability,
        "same_day_demand_score": scenario.same_day_demand_score,
        "event_density": snapshot.event_density,
        "ota_prices": snapshot.ota_prices,
        "ota_commission_rate": scenario.ota_commission_rate,
        "vip_discount_rate": scenario.vip_discount_rate,
        "guest_satisfaction": scenario.guest_satisfaction,
        "data_freshness_minutes": 15.0,
        # DSEC 澳门统计局需求信号（硬核市场数据，归一化到 -1~+1）
        "dsec_market_occ": round(snapshot.dsec_market_occ, 4),
    }
    # 按星级注入合理的 floor/ceiling（替代 pricing_engine 的硬编码 750/1015）
    floor_p, ceil_p = _tier_guardrails(base_price, star)
    payload["floor_price"] = floor_p
    payload["ceiling_price"] = ceil_p
    return payload



# ============================================================
# run_mare
# ============================================================

def run_mare(repo_path: Path, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    script = r"""
import json, sys
from types import SimpleNamespace
from app.services.pricing_engine import recommend
payload = json.loads(sys.argv[1])
data = SimpleNamespace(**payload)
# 用 payload 里的 floor/ceiling 创建 hotel_settings，不再传 None
hotel_settings = SimpleNamespace(
    floor_price=float(payload.get("floor_price", 750)),
    ceiling_price=float(payload.get("ceiling_price", 1015)),
)
result = recommend(data, hotel_settings)
print(json.dumps(result))
"""
    return run_python_snippet(repo_path / "api", repo_path / "api", script, payload)


