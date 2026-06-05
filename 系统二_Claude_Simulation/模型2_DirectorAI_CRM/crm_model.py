# 系统二 | 模型2 | DIRECTOR_CRM_ALL

def run_director_crm_test(hotel: dict, signal: dict, real_data: dict,
                          scenario: HotelScenario) -> dict:
    """
    测试DirectorAI CRM/PSRS集成模型在3星酒店的表现。
    内部数据（渠道分布/PSRS状态/CRM识别率/客户忠诚度）来自scenario，
    覆盖"数据缺失"到"系统故障"到"理想状态"的全谱运营条件。
    """
    occupancy = scenario.occupancy

    # ── 渠道来源（使用场景定义的分布，而非固定随机）──────────────────
    channel_labels = ["direct_web", "ota_booking", "ota_agoda",
                      "walk_in", "whatsapp_direct", "phone_call"]
    channel = random.choices(channel_labels, weights=list(scenario.channel_weights), k=1)[0]

    # ── 回头客与忠诚度（来自场景，体现不同客群结构）─────────────────
    loyalty_tier = scenario.loyalty_tier
    is_returning = loyalty_tier != "none"
    clv_estimate = round(scenario.avg_clv * random.uniform(0.85, 1.15))

    # ── CRM匹配率（场景可强制覆盖，测试CRM失效/故障场景）────────────
    if scenario.crm_match_rate_override is not None:
        crm_match_prob = scenario.crm_match_rate_override
    else:
        base_rate = 0.55 if is_returning else 0.08
        crm_match_prob = min(0.92, base_rate * (1.12 if signal["is_holiday"] else 1.0))
    crm_matched = random.random() < crm_match_prob

    # ── 增值销售（满房/无库存场景则无法升房）────────────────────────
    upsell_menu = {
        "room_upgrade":      {"prob": 0.22, "revenue": 150},
        "late_checkout":     {"prob": 0.32, "revenue": 80},
        "breakfast_package": {"prob": 0.38, "revenue": 120},
        "airport_transfer":  {"prob": 0.18, "revenue": 200},
    }
    upsell_type, upsell_accepted, upsell_revenue = None, False, 0
    if occupancy < 0.95 and scenario.remaining_inventory_ratio > 0.02:
        upsell_type = random.choice(list(upsell_menu.keys()))
        accept_p = upsell_menu[upsell_type]["prob"]
        loyalty_bonus = {"platinum": 1.45, "gold": 1.35, "silver": 1.18,
                         "bronze": 1.08, "none": 1.0}[loyalty_tier]
        upsell_accepted = random.random() < min(0.75, accept_p * loyalty_bonus)
        upsell_revenue = upsell_menu[upsell_type]["revenue"] if upsell_accepted else 0

    # ── PSRS状态（场景驱动：healthy/degraded/error）──────────────────
    if scenario.psrs_health == "healthy":
        psrs_status = random.choices(["synced", "pending", "error"], weights=[88, 9, 3])[0]
    elif scenario.psrs_health == "degraded":
        psrs_status = random.choices(["synced", "pending", "error"], weights=[45, 40, 15])[0]
    else:
        psrs_status = random.choices(["synced", "pending", "error"], weights=[8, 25, 67])[0]

    # ── WhatsApp触达（PSRS故障时推送中断）───────────────────────────
    whatsapp_eligible = (channel in ("whatsapp_direct", "direct_web")
                         or (crm_matched and loyalty_tier not in ("none",)))
    whatsapp_sent = whatsapp_eligible
    delivery_rate = {"synced": 0.94, "pending": 0.62, "error": 0.18}[psrs_status]
    whatsapp_delivered = whatsapp_sent and random.random() < delivery_rate

    # ── 直销佣金节省 ──────────────────────────────────────────────────
    direct_ch = ("direct_web", "whatsapp_direct", "phone_call")
    ota_commission_saved = round(hotel["base_price"] * 0.185) if channel in direct_ch else 0

    # ── CRM忠诚度调价 ─────────────────────────────────────────────────
    discount_map = {"platinum": 0.10, "gold": 0.08, "silver": 0.04, "bronze": 0.02, "none": 0.0}
    crm_adjusted_price = round(hotel["base_price"] * (1.0 - discount_map[loyalty_tier]))

    # ── 集成健康评分（0-1）────────────────────────────────────────────
    integration_score = round(
        (0.40 if crm_matched else 0.0) +
        (0.25 if psrs_status == "synced" else 0.08 if psrs_status == "pending" else 0.0) +
        (0.20 if whatsapp_delivered else 0.0) +
        (0.15 if upsell_accepted else 0.05),
        3,
    )

    result = {
        "hotel_id":             hotel["hotel_id"],
        "scenario":             scenario.name,
        "channel":              channel,
        "is_returning_guest":   is_returning,
        "loyalty_tier":         loyalty_tier,
        "clv_estimate":         clv_estimate,
        "crm_matched":          crm_matched,
        "upsell_type":          upsell_type,
        "upsell_accepted":      upsell_accepted,
        "upsell_revenue":       upsell_revenue,
        "psrs_status":          psrs_status,
        "whatsapp_sent":        whatsapp_sent,
        "whatsapp_delivered":   whatsapp_delivered,
        "crm_adjusted_price":   crm_adjusted_price,
        "ota_commission_saved": ota_commission_saved,
        "integration_score":    integration_score,
        "occupancy":            occupancy,
        "demand_high":          signal["is_holiday"] or signal["is_weekend"],
    }

    # ── Phase 2：弹性引擎验证 CRM 调价的 RevPAR 合理性 ───────────────────────
    if _ELASTICITY_OK and crm_adjusted_price > 0:
        mkt_price = hotel["base_price"]   # CRM以base_price为锚
        er = _elasticity_optimize(
            candidate_price = crm_adjusted_price,
            market_price    = mkt_price,
            star            = hotel.get("star", 3),
            district        = hotel.get("district", "NAPE"),
            demand_level    = "HIGH" if result["demand_high"] else "NORMAL",
            season          = signal.get("season", "normal"),
            hotel_id        = hotel.get("hotel_id"),
        )
        result["elasticity_revpar"]       = er.predicted_revpar
        result["elasticity_lift_pct"]     = er.true_lift_pct
        result["elasticity_used"]         = er.elasticity_used
        # CRM价格本身不覆盖（CRM有其忠诚度折扣逻辑），仅记录RevPAR验证结果

    return result


# ── CrewAI兼容别名（run_23star_test已重命名为run_3star_test）────────────────────
run_23star_test = run_3star_test


# ── 异常检测 ───────────────────────────────────────────────────────────────────
