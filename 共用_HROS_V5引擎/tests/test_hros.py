from hros import MarketSignal, RevenueDecisionLayer, CRMValueEngine, DirectLTVEngine


def test_revenue_decision_layer_returns_reasonable_price():
    layer = RevenueDecisionLayer()
    signal = MarketSignal(
        market_price=1000,
        base_occ=0.76,
        star=4,
        district="NAPE",
        ota_booking_pace=0.70,
        event_density=0.50,
        border_flow=0.60,
        data_quality=0.85,
    )
    decision = layer.optimize_price(signal)
    assert 750 <= decision.recommended_price <= 1450
    assert 0.08 <= decision.predicted_occupancy <= 0.98
    assert decision.predicted_revpar > 0
    assert 0 <= decision.risk_score <= 100
    assert 0 <= decision.opportunity_score <= 100


def test_crm_offer_decision_positive_when_clv_supports_discount():
    engine = CRMValueEngine()
    decision = engine.evaluate_offer(
        base_price=1000,
        discount_rate=0.05,
        clv=6000,
        retention_lift=0.03,
        ota_commission_saved=80,
        upsell_expected_value=40,
    )
    assert decision.incremental_value > 0
    assert decision.apply_offer is True


def test_direct_ltv_advantage():
    engine = DirectLTVEngine()
    decision = engine.evaluate_direct_offer(
        direct_price=1100,
        ota_gross_price=1180,
        ota_commission_rate=0.18,
        repeat_probability=0.16,
        future_margin=720,
        crm_value=90,
        acquisition_cost=45,
        discount_cost=80,
    )
    assert decision.direct_ltv > 0
    assert decision.ota_net_revenue > 0
