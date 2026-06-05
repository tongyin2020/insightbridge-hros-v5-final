from hros.direct_ltv_engine import DirectLTVEngine
from hros.risk_engine import calculate_price_risk
from hros.opportunity_engine import calculate_opportunity_score
from hros.crm_value_engine import calculate_crm_incremental_value


def test_direct_ltv_discount_factor():
    decision = DirectLTVEngine().evaluate_direct_offer(
        direct_price=1100,
        ota_gross_price=1040,
        ota_commission_rate=0.15,
        repeat_probability=0.20,
        future_margin=700,
        acquisition_cost=20,
        discount_cost=0,
        discount_rate=0.10,
    )
    assert decision.discounted_future_value == 127.27
    assert decision.direct_ltv == 1207.27
    assert decision.direct_wins is True


def test_risk_score_normalized():
    score = calculate_price_risk(
        price=1300,
        market_price=1000,
        predicted_occ=0.50,
        ota_booking_pace=0.20,
        data_quality=0.40,
    )
    assert 0 < score < 100


def test_opportunity_score_not_over_saturated():
    score = calculate_opportunity_score({
        "event_density": 1,
        "border_flow": 1,
        "zhuhai_saturation": 1,
        "ota_booking_pace": 1,
        "is_holiday": True,
        "is_weekend": True,
        "pickup_ratio": 1,
        "occupancy_pressure": 1,
    })
    assert score == 100.0


def test_crm_value_margin_configurable():
    value = calculate_crm_incremental_value(
        base_price=1200,
        discount_rate=0.05,
        clv=8000,
        retention_lift=0.03,
        ota_commission_saved=100,
        margin_rate=0.60,
    )
    assert value == 304.0
