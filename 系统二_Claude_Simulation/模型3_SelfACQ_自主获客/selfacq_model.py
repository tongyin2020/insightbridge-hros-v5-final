# 系统二 | 模型3 | SELFACQ_ALL 自主获客

def run_45star_test(hotel: dict, signal: dict, real_data: dict,
                    scenario: HotelScenario) -> dict:
    """
    测试自主获客/OTA脱依赖模型（4-5星）。
    核心验证：在不同ObjectiveMode下，模型是否能为高净值客户
    给出优于OTA标准定价的直销方案。
    场景注入：竞对价格乘数、入住率、客户画像均来自scenario。
    """
    from objective_modes import OBJECTIVE_PROFILES

    base = hotel["base_price"]
    occupancy = scenario.occupancy

    # OTA参考价：Booking.com实时4-5星均价 × 场景竞对系数
    real_45_avg = real_data.get("upper_tier_adr_real")
    if real_45_avg and real_45_avg > 0:
        ota_standard_price = max(base * 0.70,
                                 real_45_avg * scenario.competitor_price_multiplier
                                 * random.uniform(0.96, 1.04))
    else:
        ota_standard_price = base * scenario.competitor_price_multiplier * random.uniform(0.95, 1.05)

    # 客户画像：优先使用场景定义的细分和忠诚度
    segment = scenario.guest_segment
    clv = scenario.avg_clv
    loyalty = scenario.loyalty_tier

    # 对于4-5星专属VIP场景，如果场景是普通budget，映射到对应高端客群
    if segment == "budget" and hotel["star"] == 5:
        segment = "luxury_leisure"
        clv = max(clv, 8000)

    guest_profile = {
        "segment":     segment,
        "clv":         clv,
        "sensitivity": "low" if loyalty in ("platinum", "gold") else "medium",
        "loyalty":     loyalty,
    }

    # 根据细分市场选择目标模式
    if guest_profile["sensitivity"] == "low":
        mode = ObjectiveMode.MAXIMIZE_DIRECT_MIX
    elif occupancy < 0.65:
        mode = ObjectiveMode.MAXIMIZE_REVPAR
    else:
        mode = ObjectiveMode.MAXIMIZE_REVENUE

    weights = get_objective_weights(mode)

    # 计算直销调整幅度
    direct_bias = weights.direct_bias
    bundle_aggr = weights.bundle_aggressiveness

    # 直销价格逻辑：高净值 -> 专属折扣 + 增值服务抵消
    if guest_profile["loyalty"] in ("platinum", "gold"):
        direct_price_discount = 0.08 + direct_bias * 0.10
    else:
        direct_price_discount = 0.03 + direct_bias * 0.05

    # ── 修复：直销定价锚定真实市场价（而非 base_price）──────────────────
    # 当有真实OTA市场数据时，直销报价应与市场价竞争，而非与成本基准比较。
    # base_price 仅作为下限保护（防止直销报价低于运营成本）。
    if real_data.get("upper_tier_adr_real") and real_data["upper_tier_adr_real"] > 0:
        # 以OTA标准价为锚，给出有竞争力的直销优惠（通常低于OTA 3-8%）
        price_anchor = ota_standard_price
    else:
        price_anchor = base

    direct_offer_price = round(max(base * 1.05,                         # 不低于成本基准+5%
                                   price_anchor * (1.0 - direct_price_discount)))

    # 判断直销是否优于OTA（核心逻辑验证）
    ota_commission_rate = 0.18  # OTA佣金约18%
    ota_net_revenue = ota_standard_price * (1 - ota_commission_rate)
    direct_net_revenue = direct_offer_price  # 直销无佣金

    direct_wins = direct_net_revenue >= ota_net_revenue * 0.92

    result = {
        "hotel_id": hotel["hotel_id"],
        "guest_segment": guest_profile["segment"],
        "loyalty_tier": guest_profile["loyalty"],
        "objective_mode": mode.value,
        "ota_standard_price": round(ota_standard_price, 0),
        "ota_net_revenue": round(ota_net_revenue, 0),
        "direct_offer_price": direct_offer_price,
        "direct_net_revenue": round(direct_net_revenue, 0),
        "direct_wins_vs_ota": direct_wins,
        "direct_bias": direct_bias,
        "bundle_aggressiveness": bundle_aggr,
        "occupancy": occupancy,
        "demand_high": signal["is_holiday"] or signal["is_weekend"],
    }

    # ── Phase 2：弹性引擎验证 SelfACQ 直销价格合理性 ─────────────────────────
    if _ELASTICITY_OK and direct_offer_price > 0:
        mkt_price = float(real_data.get("upper_tier_adr_real") or base)
        er = _elasticity_optimize(
            candidate_price = direct_offer_price,
            market_price    = mkt_price,
            star            = hotel.get("star", 4),
            district        = hotel.get("district", "NAPE"),
            demand_level    = "HIGH" if result["demand_high"] else "NORMAL",
            season          = signal.get("season", "normal"),
            hotel_id        = hotel.get("hotel_id"),
        )
        result["elasticity_validated_price"] = er.optimal_price
        result["predicted_occupancy"]        = er.predicted_occupancy
        result["revpar_lift_vs_market"]      = f"+{er.true_lift_pct:.1f}%"
        result["elasticity_used"]            = er.elasticity_used

    return result


# ── DirectorAI CRM集成模型测试（3星）────────────────────────────────────────


# detect_anomalies
def detect_anomalies(hotel: dict, result: dict, signal: dict, model_type: str) -> list[str]:
    anomalies = []

    if model_type == "MARE_ALL":
        rec_price = result.get("recommended_price", 0)
        base = hotel["base_price"]
        star = hotel.get("star", 3)
        floor_warn = {3: 350, 4: 650, 5: 1000}.get(star, 350)

        if rec_price <= 0:
            anomalies.append("CRITICAL: 推荐价格为零或负数")
        if rec_price > base * 2.5:
            anomalies.append(f"WARN: 价格异常高 MOP {rec_price} (>{base*2.5:.0f} = 2.5x基础价)")
        if rec_price < base * 0.5:
            anomalies.append(f"WARN: 价格异常低 MOP {rec_price} (<{base*0.5:.0f} = 0.5x基础价)")
        if rec_price < floor_warn:
            anomalies.append(f"WARN: 价格低于{star}★市场底线 MOP {rec_price} (底线={floor_warn})")

        # Guardrail违规
        violations = result.get("guardrail_report", {}).get("violations", [])
        if violations:
            anomalies.append(f"GUARDRAIL: {len(violations)}项规则违反: {[v.get('rule','?') for v in violations[:3]]}")

    elif model_type == "DIRECTOR_CRM_ALL":
        if result.get("psrs_status") == "error":
            anomalies.append("CRITICAL: PSRS系统同步失败—预订数据未入库")
        if result.get("integration_score", 1.0) < 0.25:
            anomalies.append(f"WARN: CRM集成评分过低 {result.get('integration_score')}")
        crm_price = result.get("crm_adjusted_price", 0)
        base = hotel["base_price"]
        if crm_price < base * 0.85:
            anomalies.append(f"WARN: CRM忠诚价格折扣异常 MOP {crm_price} (低于基础价85%)")
        if result.get("whatsapp_sent") and not result.get("whatsapp_delivered"):
            anomalies.append("WARN: WhatsApp发送失败—客户触达中断")

    elif model_type == "SELFACQ_ALL":
        if not result.get("direct_wins_vs_ota", True):
            anomalies.append("LOGIC: 直销净收益低于OTA净收益—自主获客模型失效")
        dp = result.get("direct_offer_price", 0)
        base = hotel["base_price"]
        if dp < base * 0.60:
            anomalies.append(f"WARN: 直销报价过低 MOP {dp} (低于基础价60%)")

    return anomalies


# ── 每日汇总 ───────────────────────────────────────────────────────────────────
